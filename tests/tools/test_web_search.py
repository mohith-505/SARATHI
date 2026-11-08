from __future__ import annotations

from unittest.mock import patch

import pytest

from tools.web.search import WebSearchTool, _Args


@pytest.mark.asyncio
async def test_web_search_parses_results():
    fake = [
        {"title": "A", "href": "https://a.example", "body": "aaa"},
        {"title": "B", "href": "https://b.example", "body": "bbb"},
    ]

    class FakeDDGS:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def text(self, q, max_results=5): return iter(fake)

    with patch("ddgs.DDGS", FakeDDGS):
        t = WebSearchTool()
        r = await t.execute(_Args(query="hello", max_results=2))
    assert r.success
    assert r.output["results"][0]["title"] == "A"
    assert r.output["results"][1]["url"] == "https://b.example"


@pytest.mark.asyncio
async def test_web_search_handles_failure():
    class BoomDDGS:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def text(self, *a, **k): raise RuntimeError("network down")

    with patch("ddgs.DDGS", BoomDDGS):
        t = WebSearchTool()
        r = await t.execute(_Args(query="hello"))
    assert not r.success
    assert "network down" in (r.error or "")
