"""Write a UTF-8 text file, bounded by allowed roots."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from core.errors.exceptions import PathAccessError
from security.paths import resolve_under_roots
from tools.base import Tool
from tools.types import PermissionLevel, ToolResult


class _Args(BaseModel):
    path: str
    content: str
    overwrite: bool = Field(False, description="If false, refuse to overwrite existing files.")


class FileWriteTool(Tool):
    name = "filesystem_write"
    description = (
        "Write UTF-8 text to a file. Creates parent directories. Refuses to "
        "overwrite unless overwrite=true."
    )
    permission_level = PermissionLevel.T2
    input_schema = _Args

    def __init__(self, allowed_roots: list[Path]) -> None:
        self.allowed_roots = allowed_roots

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]
        try:
            p = resolve_under_roots(args.path, self.allowed_roots)
        except PathAccessError as e:
            return ToolResult(success=False, error=str(e))
        if p.exists():
            if not p.is_file():
                return ToolResult(success=False, error=f"Path is not a file: {p}")
            if not args.overwrite:
                return ToolResult(
                    success=False,
                    error=f"File exists (overwrite=false): {p}",
                )
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(args.content, encoding="utf-8")
        except OSError as e:
            return ToolResult(success=False, error=f"Write failed: {e}")

        # Verify by reading back.
        try:
            ok = p.read_text(encoding="utf-8") == args.content
        except OSError:
            ok = False
        return ToolResult(
            success=True,
            output={"path": str(p), "bytes": len(args.content.encode("utf-8"))},
            verified=ok,
            error=None if ok else "Post-write verification mismatch",
        )
