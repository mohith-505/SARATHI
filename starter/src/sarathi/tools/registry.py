"""Tool registration. A tool is a schema + a tier + a function. Nothing more."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from pydantic import BaseModel
from sarathi.core.types import Context, Tier, Trust


@dataclass
class Tool:
    name: str
    description: str
    schema: type[BaseModel]
    tier: Tier
    run: Callable[[BaseModel, Context], Awaitable[str]]
    output_trust: Trust = Trust.TRUSTED

    def to_api(self) -> dict[str, Any]:
        return {"type": "function", "function": {
            "name": self.name, "description": self.description,
            "parameters": self.schema.model_json_schema()}}


class Registry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def permitted(self, ctx: Context) -> list[dict[str, Any]]:
        """Only advertise tools the current tier could actually run. Showing a
        tool you will always deny just wastes tokens and invites failed calls."""
        cap = Tier.T1 if ctx.untrusted_seen else ctx.session_tier
        return [t.to_api() for t in self._tools.values() if t.tier <= cap]
