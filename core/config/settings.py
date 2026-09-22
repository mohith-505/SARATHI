"""Configuration loading for SARATHI.

Priority (highest to lowest):
    1. Explicit init kwargs (not used by the CLI in V0.1)
    2. Environment variables prefixed with ``SARATHI_`` (nested via ``__``)
    3. ``.env`` file
    4. TOML file passed to ``SarathiSettings.load(path)``
    5. Built-in defaults
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class ModelConfig(BaseModel):
    provider: Literal["ollama"] = "ollama"
    name: str = "llama3.1:8b"
    base_url: str = "http://localhost:11434"
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    request_timeout: float = Field(default=120.0, gt=0.0)


class AgentConfig(BaseModel):
    max_history_messages: int = Field(default=40, ge=4)


class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    file: Path | None = Path("logs/sarathi.log")


class _TomlSource(PydanticBaseSettingsSource):
    """Loads settings from a TOML file. Lowest meaningful priority."""

    def __init__(self, settings_cls: type[BaseSettings], path: Path | None) -> None:
        super().__init__(settings_cls)
        self._data: dict[str, Any] = {}
        if path is not None and path.exists():
            with path.open("rb") as fh:
                self._data = tomllib.load(fh)

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:  # noqa: ARG002
        return self._data.get(field_name), field_name, False

    def __call__(self) -> dict[str, Any]:
        return self._data


_TOML_PATH: Path | None = None


class SarathiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SARATHI_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    model: ModelConfig = Field(default_factory=ModelConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            _TomlSource(settings_cls, _TOML_PATH),
            file_secret_settings,
        )

    @classmethod
    def load(cls, config_path: Path | None = None) -> "SarathiSettings":
        """Load settings, optionally seeding defaults from a TOML file."""
        global _TOML_PATH
        _TOML_PATH = config_path
        return cls()
