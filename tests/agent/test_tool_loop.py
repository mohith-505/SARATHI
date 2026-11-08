from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from core.agent.agent import Agent
from core.config.settings import SarathiSettings
from core.types.messages import Role
from models.base import AIProvider
from tools.base import Tool
from tools.registry import ToolRegistry
from tools.types import PermissionLevel, ToolResult


class _ScriptedProvider(AIProvider):
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[list] = []

    async def chat(self, messages, *, model=None):
        self.calls.append(list(messages))
        if not self.responses:
            return "done"
        return self.responses.pop(0)

    async def stream(self, messages, *, model=None):
        yield await self.chat(messages, model=model)


class _Args(BaseModel):
    x: int = 0


class _EchoTool(Tool):
    name = "echo"
    description = "echo"
    permission_level = PermissionLevel.T0
    input_schema = _Args

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]
        return ToolResult(success=True, output={"echoed": args.x}, verified=True)


def _settings() -> SarathiSettings:
    s = SarathiSettings.load(Path("does-not-exist.toml"))
    s.agent.max_tool_iterations = 3
    return s


@pytest.mark.asyncio
async def test_agent_executes_tool_then_answers():
    tool_call = json.dumps({"tool": "echo", "arguments": {"x": 42}})
    provider = _ScriptedProvider([tool_call, "the answer is 42"])
    registry = ToolRegistry()
    registry.register(_EchoTool())
    agent = Agent(provider, _settings(), registry=registry)

    reply = await agent.run("please echo 42")
    assert reply == "the answer is 42"

    # Check that a tool-role message exists with the echoed value.
    tool_msgs = [m for m in agent.conversation.messages if m.role is Role.TOOL]
    assert len(tool_msgs) == 1
    assert tool_msgs[0].name == "echo"
    payload = json.loads(tool_msgs[0].content)
    assert payload["success"] is True
    assert payload["output"]["echoed"] == 42


@pytest.mark.asyncio
async def test_agent_iteration_cap_hit():
    tool_call = json.dumps({"tool": "echo", "arguments": {"x": 1}})
    provider = _ScriptedProvider([tool_call] * 5)
    registry = ToolRegistry()
    registry.register(_EchoTool())
    settings = _settings()
    settings.agent.max_tool_iterations = 2
    agent = Agent(provider, settings, registry=registry)

    reply = await agent.run("loop")
    assert "maximum number of tool steps" in reply


@pytest.mark.asyncio
async def test_agent_rolls_back_on_provider_failure():
    class _Boom(AIProvider):
        async def chat(self, messages, *, model=None):
            raise RuntimeError("provider down")
        async def stream(self, messages, *, model=None):
            raise RuntimeError("provider down")
            yield ""  # pragma: no cover

    agent = Agent(_Boom(), _settings(), registry=ToolRegistry())
    before = len(agent.conversation)
    with pytest.raises(RuntimeError):
        await agent.run("hi")
    assert len(agent.conversation) == before


@pytest.mark.asyncio
async def test_confirm_callback_blocks_t2_tool():
    class _DangerousTool(Tool):
        name = "danger"
        description = "dangerous"
        permission_level = PermissionLevel.T2
        input_schema = _Args
        async def execute(self, args):
            raise AssertionError("should not run")

    tool_call = json.dumps({"tool": "danger", "arguments": {"x": 1}})
    provider = _ScriptedProvider([tool_call, "I did not run it"])
    registry = ToolRegistry()
    registry.register(_DangerousTool())

    async def deny(name, description, args):
        return False

    agent = Agent(provider, _settings(), registry=registry, confirm=deny)
    reply = await agent.run("do it")
    assert reply == "I did not run it"
    tool_msgs = [m for m in agent.conversation.messages if m.role is Role.TOOL]
    assert len(tool_msgs) == 1
    payload = json.loads(tool_msgs[0].content)
    assert payload["success"] is False
    assert "denied" in payload["error"].lower()
