"""Create a directory, bounded by allowed roots."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from core.errors.exceptions import PathAccessError
from security.paths import resolve_under_roots
from tools.base import Tool
from tools.types import PermissionLevel, ToolResult


class _Args(BaseModel):
    path: str
    parents: bool = Field(True, description="Create intermediate directories.")


class MakeDirTool(Tool):
    name = "directory_create"
    description = "Create a directory. With parents=true, creates intermediate directories."
    permission_level = PermissionLevel.T1
    input_schema = _Args

    def __init__(self, allowed_roots: list[Path]) -> None:
        self.allowed_roots = allowed_roots

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]
        try:
            p = resolve_under_roots(args.path, self.allowed_roots)
        except PathAccessError as e:
            return ToolResult(success=False, error=str(e))

        if p.exists():
            if p.is_dir():
                return ToolResult(
                    success=True,
                    output={"path": str(p), "created": False},
                    verified=True,
                )
            return ToolResult(success=False, error=f"Path exists and is not a directory: {p}")

        try:
            p.mkdir(parents=args.parents, exist_ok=False)
        except OSError as e:
            return ToolResult(success=False, error=f"mkdir failed: {e}")

        return ToolResult(
            success=True,
            output={"path": str(p), "created": True},
            verified=p.is_dir(),
        )
