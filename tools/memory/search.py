"""Search SARATHI's memory vault by keyword."""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.memory.vault import MemoryVault
from tools.base import Tool
from tools.types import PermissionLevel, ToolResult


class _Args(BaseModel):
    query: str = Field(..., description="Search keyword or phrase.")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results to return.")


class MemorySearchTool(Tool):
    name = "memory_search"
    description = "Search remembered facts, user preferences, and project notes by keyword."
    permission_level = PermissionLevel.T0
    input_schema = _Args

    def __init__(self, vault: MemoryVault) -> None:
        self.vault = vault

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]
        try:
            entries = await self.vault.search_entries(args.query, limit=args.limit)
            return ToolResult(
                success=True,
                output={"query": args.query, "results": entries, "count": len(entries)},
                verified=True,
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Memory search failed: {e}")
