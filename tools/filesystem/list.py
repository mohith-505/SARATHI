"""List files and directories within allowed roots."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from core.errors.exceptions import PathAccessError
from security.paths import resolve_under_roots
from tools.base import Tool
from tools.types import PermissionLevel, ToolResult


class _Args(BaseModel):
    path: str = Field(".", description="Directory path to list.")
    max_entries: int = Field(100, ge=1, le=1000)


class FileListTool(Tool):
    name = "fs.list"
    description = (
        "List files and directories in a given path. Refuses paths outside allowed roots."
    )
    permission_level = PermissionLevel.T0
    input_schema = _Args

    def __init__(self, allowed_roots: list[Path]) -> None:
        self.allowed_roots = allowed_roots

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]
        try:
            p = resolve_under_roots(args.path, self.allowed_roots)
        except PathAccessError as e:
            return ToolResult(success=False, error=str(e))
        if not p.exists():
            return ToolResult(success=False, error=f"Not found: {p}")
        if not p.is_dir():
            return ToolResult(success=False, error=f"Not a directory: {p}")

        entries: list[dict[str, object]] = []
        try:
            for item in sorted(p.iterdir()):
                if len(entries) >= args.max_entries:
                    break
                is_dir = item.is_dir()
                size = 0 if is_dir else item.stat().st_size
                entries.append({"name": item.name, "is_dir": is_dir, "size_bytes": size})
        except OSError as e:
            return ToolResult(success=False, error=f"List failed: {e}")

        return ToolResult(
            success=True,
            output={"path": str(p), "count": len(entries), "entries": entries},
            verified=True,
        )
