"""Core domain vocabulary. Everything else imports from here."""
from __future__ import annotations
import time
from enum import IntEnum, StrEnum
from typing import Any, Literal
from pydantic import BaseModel, Field


class Tier(IntEnum):
    """Privilege tiers. IntEnum so `tool.tier > Tier.T1` works."""
    T0 = 0   # read-only, no side effects
    T1 = 1   # low-risk reversible writes inside the workspace
    T2 = 2   # real side effects; requires approval
    T3 = 3   # privileged; approval every time, no session grants


class Trust(StrEnum):
    """UNTRUSTED = anything an attacker could have authored: web pages,
    downloaded files, third-party tool output. Data, never instructions."""
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class Role(StrEnum):
    SYSTEM = "system"; USER = "user"; ASSISTANT = "assistant"; TOOL = "tool"


class Message(BaseModel):
    role: Role
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    trust: Trust = Trust.TRUSTED

    def to_api(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.tool_call_id: d["tool_call_id"] = self.tool_call_id
        if self.name: d["name"] = self.name
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
    def denied(cls, call_id: str, reason: str) -> "ToolResult":
        # Denials are observations, not exceptions. The model must SEE them
        # so it can choose a different approach instead of retrying blindly.
        return cls(call_id=call_id, ok=False, content=f"DENIED: {reason}", error=reason)

    @classmethod
    def failed(cls, call_id: str, err: str) -> "ToolResult":
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


class BudgetExceeded(Exception): ...


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

    def charge(self, u: Usage) -> None:
        self.tokens_used += u.input_tokens + u.output_tokens
        self.inr_used += u.cost_inr

    def tick(self) -> None:
        self.steps_used += 1

    def check(self) -> None:
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
                f"Rs {self.inr_used:.2f}, {time.monotonic()-self.started_at:.0f}s")


class TaskType(StrEnum):
    CHAT="chat"; CODE="code"; REASON="reason"; EXTRACT="extract"; SUMMARIZE="summarize"

class Privacy(StrEnum):
    PUBLIC="public"; PERSONAL="personal"; SECRET="secret"

class Complexity(StrEnum):
    TRIVIAL="trivial"; NORMAL="normal"; HARD="hard"


class RouteRequest(BaseModel):
    task_type: TaskType = TaskType.CHAT
    privacy: Privacy = Privacy.PERSONAL
    complexity: Complexity = Complexity.NORMAL
    est_input_tokens: int = 0
    needs_tools: bool = False
    offline: bool = False


class ModelSpec(BaseModel):
    name: str
    provider: Literal["ollama", "openai_compat"]
    supports_tools: bool = True
    max_context: int = 8192
    inr_per_1k_in: float = 0.0
    inr_per_1k_out: float = 0.0
    is_local: bool = True
    # MEASURED, not inferred. Load the model, read nvidia-smi, write it down.
    weights_vram_mb: int = 0
    kv_bytes_per_token: int = 0

    def cost(self, u: Usage) -> float:
        return u.input_tokens/1000*self.inr_per_1k_in + u.output_tokens/1000*self.inr_per_1k_out


class Context(BaseModel):
    """Per-turn state. `untrusted_seen` is the security workhorse."""
    session_id: str
    budget: Budget = Field(default_factory=Budget)
    session_tier: Tier = Tier.T2
    untrusted_seen: bool = False
    workspace: str = "~/sarathi/workspace"
