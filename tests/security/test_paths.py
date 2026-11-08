from __future__ import annotations

from pathlib import Path

import pytest

from core.errors.exceptions import PathAccessError
from security.paths import resolve_under_roots


def test_path_inside_root(tmp_path: Path):
    target = tmp_path / "sub" / "file.txt"
    target.parent.mkdir()
    target.write_text("hi")
    resolved = resolve_under_roots(str(target), [tmp_path])
    assert resolved == target.resolve()


def test_relative_path_inside_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    p = resolve_under_roots("foo.txt", [tmp_path])
    assert p == (tmp_path / "foo.txt").resolve()


def test_path_outside_root_rejected(tmp_path: Path):
    outside = tmp_path.parent
    with pytest.raises(PathAccessError):
        resolve_under_roots(str(outside / "somewhere"), [tmp_path])


def test_no_allowed_roots_rejected(tmp_path: Path):
    with pytest.raises(PathAccessError):
        resolve_under_roots(str(tmp_path / "x"), [])


def test_tilde_expands(tmp_path: Path):
    resolved = resolve_under_roots("~", [Path.home()])
    assert resolved == Path.home().resolve()
