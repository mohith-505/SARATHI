"""Provider factory. Keeps the agent core decoupled from concrete providers."""

from __future__ import annotations

from core.config.settings import ModelConfig
from core.errors.exceptions import ConfigurationError
from models.base import AIProvider
from models.providers.ollama_provider import OllamaProvider


def create_provider(cfg: ModelConfig) -> AIProvider:
    """Instantiate the provider described by ``cfg``."""
    if cfg.provider == "ollama":
        return OllamaProvider(
            base_url=cfg.base_url,
            default_model=cfg.name,
            temperature=cfg.temperature,
            request_timeout=cfg.request_timeout,
        )
    raise ConfigurationError(f"Unknown provider: {cfg.provider!r}")
