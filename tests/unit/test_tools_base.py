from __future__ import annotations

import pytest
from pydantic import BaseModel

from tools.base import Tool
from tools.types import PermissionLevel, ToolResult


class _Args(BaseModel):
    x: int = 0


class _EchoTool(Tool):
    name = "echo"
    description = "Echo x back."
    permission_level = PermissionLevel.T0
    input_schema = _Args

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]
        return ToolResult(success=True, output={"x": args.x}, verified=True)


@pytest.mark.asyncio
async def test_tool_default_verify_follows_success():
    t = _EchoTool()
    r = await t.execute(_Args(x=5))
    assert await t.verify(r) is True


def test_permission_level_ordering():
    assert PermissionLevel.T0 < PermissionLevel.T1 < PermissionLevel.T2 < PermissionLevel.T3
