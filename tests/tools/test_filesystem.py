from __future__ import annotations

from pathlib import Path

import pytest

from tools.filesystem.mkdir import MakeDirTool
from tools.filesystem.mkdir import _Args as MkArgs
from tools.filesystem.read import FileReadTool
from tools.filesystem.read import _Args as ReadArgs
from tools.filesystem.write import FileWriteTool
from tools.filesystem.write import _Args as WriteArgs


@pytest.mark.asyncio
async def test_write_then_read_round_trip(tmp_path: Path):
    w = FileWriteTool([tmp_path])
    r = await w.execute(WriteArgs(path=str(tmp_path / "a.txt"), content="hello"))
    assert r.success and r.verified
    assert (tmp_path / "a.txt").read_text() == "hello"

    rd = FileReadTool([tmp_path])
    rr = await rd.execute(ReadArgs(path=str(tmp_path / "a.txt")))
    assert rr.success
    assert rr.output["content"] == "hello"


@pytest.mark.asyncio
async def test_write_refuses_overwrite_by_default(tmp_path: Path):
    f = tmp_path / "x.txt"
    f.write_text("old")
    w = FileWriteTool([tmp_path])
    r = await w.execute(WriteArgs(path=str(f), content="new"))
    assert not r.success
    assert f.read_text() == "old"


@pytest.mark.asyncio
async def test_write_outside_root_rejected(tmp_path: Path):
    w = FileWriteTool([tmp_path / "sub"])
    r = await w.execute(WriteArgs(path=str(tmp_path / "escape.txt"), content="x"))
    assert not r.success


@pytest.mark.asyncio
async def test_mkdir_creates_and_is_idempotent(tmp_path: Path):
    m = MakeDirTool([tmp_path])
    r1 = await m.execute(MkArgs(path=str(tmp_path / "a" / "b")))
    assert r1.success and r1.output["created"]
    r2 = await m.execute(MkArgs(path=str(tmp_path / "a" / "b")))
    assert r2.success and not r2.output["created"]


@pytest.mark.asyncio
async def test_read_too_large(tmp_path: Path):
    f = tmp_path / "big.txt"
    f.write_text("x" * 1000)
    t = FileReadTool([tmp_path])
    r = await t.execute(ReadArgs(path=str(f), max_bytes=100))
    assert not r.success
