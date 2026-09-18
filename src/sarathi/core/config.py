from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sarathi.core.types import ModelSpec

class Secrets(BaseSettings):
    """Loaded exclusively from .env and environment variables.
    NO secrets should ever be hardcoded in Python files or YAML config.
    """
    openrouter_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

class PathsConfig(BaseModel):
    workspace: str = "~/sarathi/workspace"
    profile: str = "~/sarathi/profile.md"
    db: str = "data/memory.db"
    
    def expand(self, path_str: str) -> Path:
        return Path(path_str).expanduser().resolve()

class AppConfig(BaseModel):
    """Loaded from config.yaml."""
    paths: PathsConfig = Field(default_factory=PathsConfig)
    
    # Raw dict for now, can be parsed into ModelSpec later
    models: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def load(cls, path: str = "config.yaml") -> "AppConfig":
        p = Path(path).expanduser()
        if not p.exists():
            # Return defaults if no config.yaml is found
            return cls()
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)

# Global instances for easy access
secrets = Secrets()
config = AppConfig.load()
