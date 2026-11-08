from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from core.config.settings import SarathiSettings


def test_defaults_when_no_file():
    s = SarathiSettings.load(Path("does-not-exist.toml"))
    assert s.model.provider == "ollama"
    assert s.model.name == "qwen3:4b"
    assert s.agent.max_history_messages >= 4


def test_toml_overrides_defaults(tmp_path: Path):
    cfg = tmp_path / "c.toml"
    cfg.write_text(
        "[model]\n"
        'name = "qwen2.5:7b"\n'
        "temperature = 0.7\n"
        "[agent]\n"
        "max_history_messages = 12\n"
    )
    s = SarathiSettings.load(cfg)
    assert s.model.name == "qwen2.5:7b"
    assert s.model.temperature == 0.7
    assert s.agent.max_history_messages == 12


def test_env_overrides_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cfg = tmp_path / "c.toml"
    cfg.write_text('[model]\nname = "from-toml"\n')
    monkeypatch.setenv("SARATHI_MODEL__NAME", "from-env")
    s = SarathiSettings.load(cfg)
    assert s.model.name == "from-env"


def test_invalid_temperature_rejected(tmp_path: Path):
    cfg = tmp_path / "c.toml"
    cfg.write_text('[model]\ntemperature = 5.0\n')
    with pytest.raises(ValidationError):
        SarathiSettings.load(cfg)
