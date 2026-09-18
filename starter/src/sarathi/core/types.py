"""Core domain vocabulary. Everything else imports from here.

This module has NO dependencies on other sarathi modules. That is deliberate:
it is the bottom of the dependency graph, which is what keeps the layers from
tangling as the project grows.
"""

from __future__ import annotations

import time
from enum import IntEnum, StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Tier(IntEnum):
    """Privilege tiers. IntEnum so `tool.tier > Tier.T1` works."""

    T0 = 0  # read-only, no side effects
    T1 = 1  # low-risk reversible writes inside the workspace
    T2 = 2  # real side effects; requires approval
    T3 = 3  # privileged; approval every single time, no session grants


class Trust(StrEnum):
    """Where a piece of content came from.

    UNTRUSTED content is anything an attacker could have authored: web pages,
    downloaded files, third-party tool output. It is data, never instructions.
    """

    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    role: Role
    content: str
    name: str | None = None          # tool name, for TOOL messages
    tool_call_id: str | None = None
    trust: Trust = Trust.TRUSTED

    def to_api(self) -> dict[str, Any]:
        """Serialise for an OpenAI-compatible chat endpoint."""
        d: dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d


class ToolCall(BaseModel):
    id: str
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    call_id: str
    ok: bool
    content: str
    trust: Trust = Trust.TRUSTED
    truncated: bool = False
    error: str | None = None

    @classmethod
    def denied(cls, call_id: str, reason: str) -> ToolResult:
        # Denials come back as normal observations, not exceptions. The model
        # needs to see them so it can choose a different approach.
        return cls(call_id=call_id, ok=False, content=f"DENIED: {reason}", error=reason)

    @classmethod
    def failed(cls, call_id: str, err: str) -> ToolResult:
        return cls(call_id=call_id, ok=False, content=f"ERROR: {err}", error=err)


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost_inr: float = 0.0


class ModelResponse(BaseModel):
    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    model: str = ""
    stop_reason: str = ""

    @property
    def is_final(self) -> bool:
        return not self.tool_calls


# --------------------------------------------------------------------------
# Budgets. Nothing runs without one.
# --------------------------------------------------------------------------

class BudgetExceeded(Exception):
    pass


class Budget(BaseModel):
    max_steps: int = 15
    max_tokens: int = 100_000
    max_inr: float = 20.0
    max_seconds: float = 600.0
    max_stalls: int = 3
    tokens_per_observation: int = 2_000

    steps_used: int = 0
    tokens_used: int = 0
    inr_used: float = 0.0
    started_at: float = Field(default_factory=time.monotonic)

    def charge(self, usage: Usage) -> None:
        self.tokens_used += usage.input_tokens + usage.output_tokens
        self.inr_used += usage.cost_inr

    def tick(self) -> None:
        self.steps_used += 1

    def check(self) -> None:
        """Raise if any limit is blown. Called at the top of every agent step."""
        if self.steps_used >= self.max_steps:
            raise BudgetExceeded(f"step limit {self.max_steps}")
        if self.tokens_used >= self.max_tokens:
            raise BudgetExceeded(f"token limit {self.max_tokens}")
        if self.inr_used >= self.max_inr:
            raise BudgetExceeded(f"cost limit Rs {self.max_inr}")
        if time.monotonic() - self.started_at >= self.max_seconds:
            raise BudgetExceeded(f"time limit {self.max_seconds}s")

    def summary(self) -> str:
        return (f"{self.steps_used} steps, {self.tokens_used} tok, "
                f"Rs {self.inr_used:.2f}, {time.monotonic() - self.started_at:.0f}s")


# --------------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------------

class TaskType(StrEnum):
    CHAT = "chat"
    CODE = "code"
    REASON = "reason"
    EXTRACT = "extract"
    SUMMARIZE = "summarize"


class Privacy(StrEnum):
    PUBLIC = "public"      # fine to send anywhere
    PERSONAL = "personal"  # prefer local, cloud allowed
    SECRET = "secret"      # never leaves this machine


class Complexity(StrEnum):
    TRIVIAL = "trivial"
    NORMAL = "normal"
    HARD = "hard"


class RouteRequest(BaseModel):
    task_type: TaskType = TaskType.CHAT
    privacy: Privacy = Privacy.PERSONAL
    complexity: Complexity = Complexity.NORMAL
    est_input_tokens: int = 0
    needs_tools: bool = False
    offline: bool = False


class ModelSpec(BaseModel):
    """A routable model. `provider` names a registered ModelProvider."""

    name: str
    provider: Literal["ollama", "openai_compat"]
    supports_tools: bool = True
    max_context: int = 8192
    inr_per_1k_in: float = 0.0
    inr_per_1k_out: float = 0.0
    is_local: bool = True
    # Measured, not inferred. Run the model, read nvidia-smi, put the number here.
    # Never parse capability out of a model name.
    weights_vram_mb: int = 0
    kv_bytes_per_token: int = 0

    def cost(self, usage: Usage) -> float:
        return (usage.input_tokens / 1000 * self.inr_per_1k_in
                + usage.output_tokens / 1000 * self.inr_per_1k_out)


class Context(BaseModel):
    """Per-turn state. The taint flag is the security workhorse."""

    session_id: str
    budget: Budget = Field(default_factory=Budget)
    session_tier: Tier = Tier.T2
    untrusted_seen: bool = False
    workspace: str = "~/sarathi/workspace"

    model_config = {"arbitrary_types_allowed": True}
