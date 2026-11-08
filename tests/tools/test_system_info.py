from __future__ import annotations

import pytest

from tools.system.system_info import SystemInfoTool, _Args


@pytest.mark.asyncio
async def test_system_info_basic_shape():
    t = SystemInfoTool()
    r = await t.execute(_Args(include_gpu=False, include_disk=False, include_processes=False))
    assert r.success
    assert "os" in r.output
    assert "cpu" in r.output
    assert "memory" in r.output
    assert "gpu" not in r.output
    assert isinstance(r.output["memory"]["total_mb"], (int, float))
