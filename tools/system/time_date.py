"""Current date/time tool."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel

from tools.base import Tool
from tools.types import PermissionLevel, ToolResult


class _Args(BaseModel):
    """No arguments."""


class TimeDateTool(Tool):
    name = "current_time"
    description = "Return the current local date and time."
    permission_level = PermissionLevel.T0
    input_schema = _Args

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]  # noqa: ARG002
        now = datetime.now(UTC).astimezone()
        return ToolResult(
            success=True,
            output={
                "iso": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "timezone": now.tzname(),
            },
            verified=True,
        )
