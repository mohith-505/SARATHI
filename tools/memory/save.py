"""Save a fact, preference, or context note into SARATHI's memory vault."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from core.memory.vault import MemoryVault
from tools.base import Tool
from tools.types import PermissionLevel, ToolResult


class _Args(BaseModel):
    key: str = Field(
        ...,
        description="Unique alphanumeric identifier (e.g. 'user_name', 'favorite_ide').",
    )
    content: str = Field(..., description="Fact or note to remember.")
    category: Literal["profile", "preference", "fact", "project"] = Field(
        default="fact", description="Category of memory."
    )


class MemorySaveTool(Tool):
    name = "memory_save"
    description = (
        "Save a fact, user preference, or project note into SARATHI's persistent memory vault."
    )
    permission_level = PermissionLevel.T1
    input_schema = _Args

    def __init__(self, vault: MemoryVault) -> None:
        self.vault = vault

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]
        try:
            entry = await self.vault.save_entry(
                key=args.key,
                content=args.content,
                category=args.category,
            )
            return ToolResult(success=True, output=entry, verified=True)
        except Exception as e:
            return ToolResult(success=False, error=f"Memory save failed: {e}")
