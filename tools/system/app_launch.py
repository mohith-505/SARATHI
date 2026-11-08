"""Launch an installed application by name or path."""

from __future__ import annotations

import shutil
import subprocess

from pydantic import BaseModel, Field

from core.logging.logger import get_logger
from tools.base import Tool
from tools.types import PermissionLevel, ToolResult

log = get_logger("tools.app_launch")


class _Args(BaseModel):
    executable: str = Field(..., description="Exe name or path.")
    args: list[str] = Field(default_factory=list, description="Arguments to pass.")


class AppLaunchTool(Tool):
    name = "application_launch"
    description = "Launch an installed application by executable name or absolute path."
    permission_level = PermissionLevel.T1
    input_schema = _Args

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]  # type: ignore[override]
        exe = shutil.which(args.executable) or args.executable
        try:
            proc = subprocess.Popen([exe, *args.args], close_fds=True)  # noqa: S603, ASYNC220
        except FileNotFoundError:
            return ToolResult(success=False, error=f"Executable not found: {args.executable}")
        except OSError as e:
            return ToolResult(success=False, error=f"Launch failed: {e}")
        return ToolResult(
            success=True,
            output={"pid": proc.pid, "executable": exe, "args": args.args},
            verified=True,
        )
