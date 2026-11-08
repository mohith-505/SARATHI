"""Tool primitives: permission levels and structured results."""

from __future__ import annotations

from enum import IntEnum
from typing import Any

from pydantic import BaseModel, Field


class PermissionLevel(IntEnum):
    """Permission tiers as defined in the SARATHI security model.

    Enforcement is minimal in V0.2 (T2/T3 prompt the user); the full
    confirmation + audit system lands in V0.4.
    """

    T0 = 0  # Information        — automatic
    T1 = 1  # Safe actions       — automatic
    T2 = 2  # Potentially destructive — require confirmation
    T3 = 3  # Critical           — explicit confirmation every time


class ToolResult(BaseModel):
    """Standard result returned by every tool."""

    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    verified: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "verified": self.verified,
        }
