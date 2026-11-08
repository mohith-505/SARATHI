"""Tool registry: register, look up, and describe tools for the LLM."""

from __future__ import annotations

import json

from core.errors.exceptions import ToolNotFoundError
from tools.base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool, as_name: str | None = None) -> None:
        name = as_name or tool.name
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        self._tools[name] = tool

    def register_alias(self, alias: str, tool: Tool) -> None:
        """Register an alias pointing to an existing tool."""
        self._tools[alias] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as e:
            raise ToolNotFoundError(f"Unknown tool: {name}") from e

    def all(self) -> list[Tool]:
        return list(dict.fromkeys(self._tools.values()))

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def describe_for_llm(self) -> str:
        lines: list[str] = []
        for t in self.all():
            schema = t.input_schema.model_json_schema()
            lines.append(
                f"- {t.name} [{t.permission_level.name}]: {t.description}\n"
                f"  args schema: {json.dumps(schema, separators=(',', ':'))}"
            )
        return "\n".join(lines)

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self.all())
