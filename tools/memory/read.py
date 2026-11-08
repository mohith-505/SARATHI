"""Read a memory entry from SARATHI's memory vault."""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.memory.vault import MemoryVault
from tools.base import Tool
from tools.types import PermissionLevel, ToolResult


class _Args(BaseModel):
    key: str = Field(..., description="Identifier of the memory entry to retrieve.")


class MemoryReadTool(Tool):
    name = "memory_read"
    description = "Read a specific memory entry by its key."
    permission_level = PermissionLevel.T0
    input_schema = _Args

    def __init__(self, vault: MemoryVault) -> None:
        self.vault = vault

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]
        try:
            entry = await self.vault.get_entry(args.key)
            if entry is None:
                return ToolResult(
                    success=False, error=f"Memory key {args.key!r} not found."
                )
            return ToolResult(success=True, output=entry, verified=True)
        except Exception as e:
            return ToolResult(success=False, error=f"Memory read failed: {e}")
