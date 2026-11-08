"""Abstract Tool interface. Every tool subclasses this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel

from tools.types import PermissionLevel, ToolResult


class Tool(ABC):
    """Contract for a SARATHI tool.

    Subclasses declare:
        name:             unique identifier used by the LLM
        description:      short one-line description for the LLM
        permission_level: T0..T3
        input_schema:     Pydantic model class for arguments
    """

    name: ClassVar[str]
    description: ClassVar[str]
    permission_level: ClassVar[PermissionLevel]
    input_schema: ClassVar[type[BaseModel]]

    @abstractmethod
    async def execute(self, args: BaseModel) -> ToolResult:
        """Run the tool with validated arguments."""

    async def verify(self, result: ToolResult) -> bool:
        """Confirm the tool actually did what it claims.

        Default: trust ``result.success``. Tools that perform real-world
        side effects should override this to re-check state.
        """
        return result.success
