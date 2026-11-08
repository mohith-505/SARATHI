from __future__ import annotations

import pytest
from pydantic import BaseModel

from core.errors.exceptions import ToolNotFoundError
from tools.base import Tool
from tools.registry import ToolRegistry
from tools.types import PermissionLevel, ToolResult


class _Args(BaseModel):
    pass


class _Noop(Tool):
    name = "noop"
    description = "does nothing"
    permission_level = PermissionLevel.T0
    input_schema = _Args

    async def execute(self, args):  # type: ignore[override]
        return ToolResult(success=True)


def test_register_and_get():
    r = ToolRegistry()
    r.register(_Noop())
    assert "noop" in r
    assert r.get("noop").name == "noop"
    assert len(r) == 1


def test_duplicate_registration_rejected():
    r = ToolRegistry()
    r.register(_Noop())
    with pytest.raises(ValueError):
        r.register(_Noop())


def test_unknown_tool_raises():
    r = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        r.get("nope")


def test_describe_for_llm_contains_name_and_schema():
    r = ToolRegistry()
    r.register(_Noop())
    text = r.describe_for_llm()
    assert "noop" in text
    assert "T0" in text
    assert "args schema" in text
