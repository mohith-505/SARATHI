from __future__ import annotations

import pytest

from tools.system.time_date import TimeDateTool, _Args


@pytest.mark.asyncio
async def test_returns_iso_and_components():
    t = TimeDateTool()
    r = await t.execute(_Args())
    assert r.success
    assert r.verified
    assert "iso" in r.output
    assert "date" in r.output
    assert "time" in r.output
    # date looks like YYYY-MM-DD
    assert len(r.output["date"]) == 10 and r.output["date"][4] == "-"
