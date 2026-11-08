"""List all remembered keys and categories in SARATHI's memory vault."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from core.memory.vault import MemoryVault
from tools.base import Tool
from tools.types import PermissionLevel, ToolResult


class _Args(BaseModel):
    category: Literal["profile", "preference", "fact", "project"] | None = Field(
        default=None, description="Optional category filter."
    )


class MemoryListTool(Tool):
    name = "memory_list"
    description = "List all keys and categories currently remembered in SARATHI's vault."
    permission_level = PermissionLevel.T0
    input_schema = _Args

    def __init__(self, vault: MemoryVault) -> None:
        self.vault = vault

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]
        try:
            entries = await self.vault.list_entries(category=args.category)
            return ToolResult(
                success=True,
                output={"entries": entries, "count": len(entries)},
                verified=True,
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Memory list failed: {e}")
