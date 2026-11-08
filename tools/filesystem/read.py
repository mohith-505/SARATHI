"""Read a UTF-8 text file, bounded by size and allowed roots."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from core.errors.exceptions import PathAccessError
from security.paths import resolve_under_roots
from tools.base import Tool
from tools.types import PermissionLevel, ToolResult


class _Args(BaseModel):
    path: str = Field(..., description="File path to read.")
    max_bytes: int = Field(200_000, ge=1, le=5_000_000)


class FileReadTool(Tool):
    name = "filesystem_read"
    description = (
        "Read a UTF-8 text file. Refuses paths outside allowed roots or "
        "files larger than max_bytes."
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
        if not p.is_file():
            return ToolResult(success=False, error=f"Not a file: {p}")
        size = p.stat().st_size
        if size > args.max_bytes:
            return ToolResult(
                success=False,
                error=f"File too large: {size} bytes > {args.max_bytes}",
            )
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ToolResult(success=False, error="File is not valid UTF-8 text.")
        except OSError as e:
            return ToolResult(success=False, error=f"Read failed: {e}")
        return ToolResult(
            success=True,
            output={"path": str(p), "size_bytes": size, "content": text},
            verified=True,
        )
