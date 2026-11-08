"""Web search via DuckDuckGo (ddgs). Full web intelligence is V0.7."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel, Field

from core.logging.logger import get_logger
from tools.base import Tool
from tools.types import PermissionLevel, ToolResult

log = get_logger("tools.web_search")


class _Args(BaseModel):
    query: str = Field(..., min_length=1, max_length=400)
    max_results: int = Field(5, ge=1, le=10)


def _run_search(query: str, max_results: int) -> list[dict[str, str]]:
    from ddgs import DDGS

    with DDGS() as ddgs:
        raw = list(ddgs.text(query, max_results=max_results))
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "snippet": r.get("body", ""),
        }
        for r in raw
    ]


class WebSearchTool(Tool):
    name = "web_search"
    description = (
        "Search the web via DuckDuckGo. Returns up to N results with title, "
        "url, and snippet. Use only when the user's question needs current "
        "information that is not in the conversation."
    )
    permission_level = PermissionLevel.T0
    input_schema = _Args

    async def execute(self, args: _Args) -> ToolResult:  # type: ignore[override]
        try:
            results = await asyncio.to_thread(_run_search, args.query, args.max_results)
        except ImportError:
            return ToolResult(success=False, error="ddgs package is not installed.")
        except Exception as e:  # noqa: BLE001
            log.warning("web search failed: %s", e)
            return ToolResult(success=False, error=f"Web search failed: {e}")
        return ToolResult(
            success=True,
            output={"query": args.query, "results": results},
            verified=True,
        )
