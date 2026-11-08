"""Run safe, allowlisted terminal commands.

This is NOT a shell. Only specific binaries with specific argument
tuples are permitted. Arguments are passed as argv to ``subprocess``
with ``shell=False``. Shell metacharacters are rejected as an extra
belt-and-suspenders measure.
"""

from __future__ import annotations

import shutil
import subprocess

from pydantic import BaseModel, Field

from tools.base import Tool
from tools.types import PermissionLevel, ToolResult

# Binary name -> set of allowed arg tuples.
# ``None`` means "no fixed pattern", but shell metacharacters are still blocked.
_SAFE: dict[str, set[tuple[str, ...]] | None] = {
    "python": {("--version",), ("-V",)},
    "python3": {("--version",), ("-V",)},
    "pip": {("--version",)},
    "pip3": {("--version",)},
    "git": {("status",), ("log",), ("branch",), ("diff",), ("show",)},
    "whoami": {()},
    "hostname": {()},
    "date": {()},
    "pwd": {()},
    "ls": {()},
    "dir": {()},
    "node": {("--version",), ("-v",)},
    "npm": {("--version",), ("-v",)},
    "echo": None,
}

_SHELL_META = (";", "|", "&", ">", "<", "`", "$(", "${", "\n", "\r")


class _Args(BaseModel):
    command: str = Field(..., description="Allowlisted binary name, e.g. 'git'.")
    args: list[str] = Field(default_factory=list, description="Arguments to pass.")


class SafeCommandTool(Tool):
    name = "terminal_safe"
    description = (
        "Run a safe, allowlisted command (e.g. `git status`, `python --version`). "
        "Destructive commands and shell metacharacters are rejected."
    )
    permission_level = PermissionLevel.T1
    input_schema = _Args

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]
        name = args.command
        if name not in _SAFE:
            return ToolResult(
                success=False,
                error=f"Command not in allowlist: {name!r}. Allowed: {sorted(_SAFE)}",
            )

        for a in args.args:
            if any(m in a for m in _SHELL_META):
                return ToolResult(
                    success=False,
                    error=f"Disallowed characters in argument: {a!r}",
                )

        pattern = _SAFE[name]
        if pattern is not None:
            tup = tuple(args.args)
            if tup not in pattern:
                return ToolResult(
                    success=False,
                    error=(
                        f"Args {tup!r} not permitted for '{name}'. "
                        f"Permitted: {sorted(pattern)}"
                    ),
                )

        exe = shutil.which(name)
        if not exe:
            return ToolResult(success=False, error=f"Binary not found: {name}")

        try:
            out = subprocess.run(  # noqa: S603, ASYNC221
                [exe, *args.args],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error="Command timed out after 15s")
        except OSError as e:
            return ToolResult(success=False, error=f"Execution failed: {e}")

        return ToolResult(
            success=out.returncode == 0,
            output={
                "exit_code": out.returncode,
                "stdout": out.stdout[:4000],
                "stderr": out.stderr[:2000],
            },
            error=None if out.returncode == 0 else f"Non-zero exit: {out.returncode}",
            verified=True,
        )
