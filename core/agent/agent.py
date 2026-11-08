"""SARATHI Agent.

V0.2 responsibilities:
- Hold conversation state (system prompt + bounded history).
- Detect and execute tool calls in a bounded loop.
- Enforce permission confirmation via an optional callback.
- Never fabricate responses; roll back failed turns.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from pydantic import ValidationError

from core.config.settings import SarathiSettings
from core.errors.exceptions import ToolNotFoundError
from core.logging.logger import get_logger
from core.prompts.system import build_system_prompt
from core.types.messages import Conversation, Message, Role
from models.base import AIProvider
from tools.base import Tool
from tools.registry import ToolRegistry
from tools.types import PermissionLevel, ToolResult

log = get_logger("agent")

ConfirmFn = Callable[[str, str, dict[str, Any]], Awaitable[bool]]
ToolEventFn = Callable[[str, dict[str, Any]], Awaitable[None]]
ToolResultFn = Callable[[str, ToolResult], Awaitable[None]]


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Find the first balanced JSON object in ``text``.

    Handles raw JSON, JSON in prose, and JSON in code fences.
    """
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    start = -1
    depth = 0
    in_str = False
    esc = False
    for i, c in enumerate(text):
        if esc:
            esc = False
            continue
        if c == "\\":
            esc = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                chunk = text[start : i + 1]
                try:
                    obj = json.loads(chunk)
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    pass
                start = -1
    return None


class Agent:
    def __init__(
        self,
        provider: AIProvider,
        settings: SarathiSettings,
        registry: ToolRegistry | None = None,
        *,
        on_tool_call: ToolEventFn | None = None,
        on_tool_result: ToolResultFn | None = None,
        confirm: ConfirmFn | None = None,
        memory_context: str | None = None,
    ) -> None:
        self.provider = provider
        self.settings = settings
        self.registry = registry
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result
        self.confirm = confirm
        self.memory_context = memory_context
        self.conversation = Conversation()
        self._seed_system_prompt()

    def _seed_system_prompt(self) -> None:
        self.conversation.add_system(build_system_prompt(self.registry, self.memory_context))

    def update_memory_context(self, memory_context: str | None) -> None:
        self.memory_context = memory_context
        if self.conversation.messages and self.conversation.messages[0].role == Role.SYSTEM:
            self.conversation.messages[0].content = build_system_prompt(
                self.registry, self.memory_context
            )
        else:
            self._seed_system_prompt()

    def _trim_history(self) -> None:
        max_messages = self.settings.agent.max_history_messages
        messages = self.conversation.messages
        if len(messages) <= max_messages:
            return
        system = messages[0]
        if system.role is not Role.SYSTEM:
            log.warning("System prompt was not at index 0; rebuilding.")
            self.conversation.messages = messages[-max_messages:]
            return
        tail = messages[-(max_messages - 1):]
        self.conversation.messages = [system, *tail]

    async def ask(self, user_input: str) -> str:
        """Single-shot request without tools. Rolls back on failure."""
        self.conversation.add_user(user_input)
        try:
            reply = await self.provider.chat(
                self.conversation.messages, model=self.settings.model.name
            )
        except Exception:
            self.conversation.messages.pop()
            raise
        self.conversation.add_assistant(reply)
        self._trim_history()
        return reply

    async def stream(self, user_input: str) -> AsyncIterator[str]:
        """Stream a plain response (no tools). Rolls back on failure."""
        self.conversation.add_user(user_input)
        buffer: list[str] = []
        try:
            async for chunk in self.provider.stream(
                self.conversation.messages, model=self.settings.model.name
            ):
                buffer.append(chunk)
                yield chunk
        except Exception:
            self.conversation.messages.pop()
            raise
        self.conversation.add_assistant("".join(buffer))
        self._trim_history()

    async def run(self, user_input: str) -> str:
        """Run a full tool-using turn until a final answer is produced."""
        snapshot = list(self.conversation.messages)
        self.conversation.add_user(user_input)

        max_iter = self.settings.agent.max_tool_iterations

        try:
            for iteration in range(max_iter):
                log.debug("tool loop iteration %d/%d", iteration + 1, max_iter)
                response = await self.provider.chat(
                    self.conversation.messages, model=self.settings.model.name
                )

                tool_call = self._parse_tool_call(response)
                if tool_call is None:
                    self.conversation.add_assistant(response)
                    self._trim_history()
                    return response

                name, args = tool_call
                self.conversation.add_assistant(response)

                if self.registry is None or name not in self.registry:
                    result = ToolResult(
                        success=False,
                        error=f"Unknown tool requested: {name!r}. "
                        f"Available: {self.registry.names() if self.registry else []}",
                    )
                else:
                    if self.on_tool_call is not None:
                        await self.on_tool_call(name, args)
                    result = await self._execute_tool(name, args)
                    if self.on_tool_result is not None:
                        await self.on_tool_result(name, result)

                self.conversation.messages.append(
                    Message(
                        role=Role.TOOL,
                        content=json.dumps(result.to_json(), ensure_ascii=False),
                        name=name,
                    )
                )
                self._trim_history()

            final = (
                "I reached the maximum number of tool steps "
                f"({max_iter}) without producing a final answer. "
                "Please refine the request or raise `agent.max_tool_iterations`."
            )
            self.conversation.add_assistant(final)
            self._trim_history()
            return final
        except Exception:
            log.exception("tool loop failed; rolling back conversation")
            self.conversation.messages = snapshot
            raise

    # ---- internals ----

    def _parse_tool_call(self, text: str) -> tuple[str, dict[str, Any]] | None:
        obj = _extract_json_object(text)
        if obj is None:
            return None
        tool = obj.get("tool")
        if not isinstance(tool, str):
            return None
        args = obj.get("arguments", {})
        if not isinstance(args, dict):
            args = {}
        return tool, args

    async def _execute_tool(self, name: str, args: dict[str, Any]) -> ToolResult:
        assert self.registry is not None
        try:
            tool: Tool = self.registry.get(name)
        except ToolNotFoundError as e:
            return ToolResult(success=False, error=str(e))

        if tool.permission_level >= PermissionLevel.T2 and self.confirm is not None:
            allowed = await self.confirm(name, tool.description, args)
            if not allowed:
                return ToolResult(success=False, error="User denied execution.")

        try:
            validated = tool.input_schema.model_validate(args)
        except ValidationError as e:
            return ToolResult(success=False, error=f"Invalid arguments: {e}")

        try:
            result = await tool.execute(validated)
        except Exception as e:  # noqa: BLE001
            log.exception("tool %s raised", name)
            return ToolResult(success=False, error=f"Tool raised: {type(e).__name__}: {e}")

        try:
            verified = await tool.verify(result)
            result.verified = bool(verified)
        except Exception as e:  # noqa: BLE001
            log.warning("verify() raised for %s: %s", name, e)

        return result

    def reset(self) -> None:
        self.conversation.clear()
        self._seed_system_prompt()
