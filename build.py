import os

files = {
    'pyproject.toml': '''[project]
name = "sarathi"
version = "0.1.0"
description = "SARATHI — Personal AI Operating Companion (V0.1 Core Brain)"
requires-python = ">=3.11"
readme = "README.md"
license = { text = "MIT" }
authors = [{ name = "SARATHI Project" }]

dependencies = [
    "httpx>=0.27",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "typer>=0.12",
    "rich>=13.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
    "ruff>=0.5",
    "mypy>=1.10",
]

[project.scripts]
sarathi = "apps.cli.main:app"

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = [
    "apps*", "core*", "models*", "tools*", "memory*",
    "voice*", "vision*", "ui*", "security*",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "W", "B", "UP", "ASYNC"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-ra"

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
''',

    '.gitignore': '''# Python
__pycache__/
*.py[cod]
*.egg-info/
.eggs/
build/
dist/

# Virtual envs
.venv/
venv/
env/

# Tooling caches
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Logs / runtime
logs/
*.log

# Secrets / local config
.env
.env.local
config/local.toml

# IDE
.vscode/
.idea/
*.swp
.DS_Store
''',

    '.env.example': '''# SARATHI environment configuration (V0.1)
# Copy to .env and edit. .env is gitignored.

# Nested values use double underscore.
SARATHI_MODEL__PROVIDER=ollama
SARATHI_MODEL__NAME=llama3.1:8b
SARATHI_MODEL__BASE_URL=http://localhost:11434
SARATHI_MODEL__TEMPERATURE=0.2
SARATHI_MODEL__REQUEST_TIMEOUT=120

SARATHI_AGENT__MAX_HISTORY_MESSAGES=40

SARATHI_LOGGING__LEVEL=INFO
SARATHI_LOGGING__FILE=logs/sarathi.log
''',

    'config/default.toml': '''# Default SARATHI configuration.
# Priority (highest → lowest): CLI args > SARATHI_* env vars > .env > this file > built-in defaults.

[model]
provider = "ollama"
name = "llama3.1:8b"
base_url = "http://localhost:11434"
temperature = 0.2
request_timeout = 120.0

[agent]
max_history_messages = 40

[logging]
level = "INFO"
file = "logs/sarathi.log"
''',

    'README.md': '''# SARATHI

**Personal AI Operating Companion — V0.1 (Core Brain)**

SARATHI is a local-first, agent-oriented AI companion for Windows laptops.
V0.1 provides a working CLI brain: text input → model → streamed response.

## Status

- Version: **0.1.0**
- Scope: CLI brain only. No tools, memory, voice, vision, or GUI yet.
- Roadmap: see `docs/ROADMAP.md`.

## Requirements

- Windows (tested) / Linux / macOS
- Python 3.11+
- [Ollama](https://ollama.com/) running locally for the default provider

## Quick start (PowerShell)

```powershell
# 1. Clone / enter the project
cd SARATHI

# 2. Create venv and install
.\\scripts\\setup.ps1

# 3. Pull a model (once)
ollama pull llama3.1:8b

# 4. Make sure Ollama is running
ollama serve

# 5. Run
sarathi chat
```

See `docs/SETUP.md` for details and troubleshooting.

## Commands

| Command | Purpose |
|---|---|
| `sarathi chat` | Interactive chat with SARATHI |
| `sarathi doctor` | Check config + provider health |
| `sarathi version` | Print version |

Inside `chat`:

- `/exit` or `/quit` — leave
- `/reset` — clear conversation history (keeps system prompt)

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/SECURITY.md`
- `docs/SETUP.md`
- `docs/DEVELOPMENT.md`
- `docs/CHANGELOG.md`
''',

    'scripts/setup.ps1': '''# SARATHI setup (Windows / PowerShell)
# Creates a virtual environment and installs SARATHI with dev dependencies.

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}

Write-Host "Activating venv..." -ForegroundColor Cyan
. .\\.venv\\Scripts\\Activate.ps1

Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

Write-Host "Installing SARATHI (editable, with dev deps)..." -ForegroundColor Cyan
pip install -e ".[dev]"

Write-Host ""
Write-Host "Done. Activate with: .\\.venv\\Scripts\\Activate.ps1" -ForegroundColor Green
Write-Host "Then run: sarathi chat" -ForegroundColor Green
''',

    'scripts/run.ps1': '''$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

. .\\.venv\\Scripts\\Activate.ps1
sarathi chat @args
''',

    'scripts/test.ps1': '''$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

. .\\.venv\\Scripts\\Activate.ps1

Write-Host "Ruff..." -ForegroundColor Cyan
ruff check .

Write-Host "MyPy..." -ForegroundColor Cyan
mypy core models apps

Write-Host "Pytest..." -ForegroundColor Cyan
pytest
''',

    'apps/__init__.py': '',
    'apps/cli/__init__.py': '',
    'core/__init__.py': '',
    'core/agent/__init__.py': '',
    'core/config/__init__.py': '',
    'core/errors/__init__.py': '',
    'core/logging/__init__.py': '',
    'core/prompts/__init__.py': '',
    'core/types/__init__.py': '',
    'models/__init__.py': '',
    'models/providers/__init__.py': '',
    'tests/__init__.py': '',
    'tests/unit/__init__.py': '',
    'tests/integration/__init__.py': '',

    'tools/__init__.py': '"""SARATHI tool system — implemented in V0.2. Intentionally empty in V0.1."""\n',
    'memory/__init__.py': '"""SARATHI memory system — implemented in V0.6. Intentionally empty in V0.1."""\n',
    'voice/__init__.py': '"""SARATHI voice pipeline — implemented in V0.5. Intentionally empty in V0.1."""\n',
    'vision/__init__.py': '"""SARATHI vision pipeline — implemented in V0.8. Intentionally empty in V0.1."""\n',
    'ui/__init__.py': '"""SARATHI desktop UI — implemented in V1.0+. Intentionally empty in V0.1."""\n',
    'security/__init__.py': '"""SARATHI security & permission system — implemented in V0.4. Intentionally empty in V0.1."""\n',

    'core/errors/exceptions.py': '''"""SARATHI exception hierarchy.

Rule: every error SARATHI can raise deliberately should be a subclass of
``SarathiError``. This lets the CLI render friendly messages for expected
failures while still allowing unexpected exceptions to surface.
"""

from __future__ import annotations


class SarathiError(Exception):
    """Base class for all SARATHI-raised errors."""


class ConfigurationError(SarathiError):
    """Configuration is missing, malformed, or contradictory."""


class ModelError(SarathiError):
    """Base class for model/provider related failures."""


class ModelUnavailableError(ModelError):
    """The requested model or provider is unavailable or not installed."""


class ModelResponseError(ModelError):
    """The provider returned a response SARATHI could not interpret."""


class ProviderConnectionError(ModelError):
    """SARATHI could not establish a connection to the provider."""
''',

    'core/types/messages.py': '''"""Conversation and message primitives used across SARATHI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(slots=True)
class Message:
    """A single message in a conversation."""

    role: Role
    content: str
    name: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Minimal wire-format representation for LLM providers."""
        payload: dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.name is not None:
            payload["name"] = self.name
        return payload


@dataclass(slots=True)
class Conversation:
    """Ordered message history with helpers."""

    messages: list[Message] = field(default_factory=list)

    def add(self, message: Message) -> None:
        self.messages.append(message)

    def add_system(self, content: str) -> Message:
        msg = Message(role=Role.SYSTEM, content=content)
        self.add(msg)
        return msg

    def add_user(self, content: str) -> Message:
        msg = Message(role=Role.USER, content=content)
        self.add(msg)
        return msg

    def add_assistant(self, content: str) -> Message:
        msg = Message(role=Role.ASSISTANT, content=content)
        self.add(msg)
        return msg

    def to_payload(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self.messages]

    def clear(self) -> None:
        self.messages.clear()

    def __len__(self) -> int:
        return len(self.messages)
''',

    'core/prompts/system.py': '''"""SARATHI's system identity.

This is deliberately close to the identity defined in the project brief.
As capabilities are added (tools, verification, memory), this prompt will
be expanded, but the non-negotiable rules must remain.
"""

from __future__ import annotations

SARATHI_SYSTEM_PROMPT = """\\
You are SARATHI, a personal AI operating companion.

Your purpose is to help the user understand information, solve problems,
create things, operate approved computer tools, and automate tasks safely.

You distinguish between thinking, planning, executing, and verifying.
You never claim an action succeeded unless it has been verified.
You respect permission boundaries and ask for confirmation before sensitive
or destructive actions.

Personality:
- Intelligent, calm, concise, useful, respectful, technically capable.
- Proactive when appropriate, never overstepping.
- Transparent about uncertainty.

Hard rules — never violate these:
- Never pretend to have performed an action you did not perform.
- Never pretend to have access to information you do not have.
- Never claim success without verification.
- Never make unauthorized decisions.
- Never hide failures.

If you cannot do something, say so plainly and, when possible, suggest a
concrete alternative.

You are currently running in V0.1 (Core Brain). You have no tools, no memory
persistence, no voice, no vision, and no computer control. If the user asks
for something that requires these, say so honestly and explain that it will
arrive in a future version. Do not simulate any capability you do not have.
"""
''',

    'core/logging/logger.py': '''"""Structured logging configuration for SARATHI."""

from __future__ import annotations

import logging
from pathlib import Path

from rich.logging import RichHandler

_ROOT_NAME = "sarathi"
_CONFIGURED = False


def configure_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    *,
    force: bool = False,
) -> logging.Logger:
    """Configure the ``sarathi`` logger tree.

    Idempotent unless ``force=True``. Attaches a Rich console handler and,
    optionally, a file handler.
    """
    global _CONFIGURED
    root = logging.getLogger(_ROOT_NAME)

    if _CONFIGURED and not force:
        return root

    root.handlers.clear()
    root.setLevel(level)
    root.propagate = False

    console = RichHandler(
        rich_tracebacks=True,
        show_time=False,
        show_path=False,
        markup=False,
    )
    console.setLevel(level)
    root.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root.addHandler(fh)

    _CONFIGURED = True
    return root


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``sarathi`` namespace."""
    return logging.getLogger(f"{_ROOT_NAME}.{name}")
''',

    'core/config/settings.py': '''"""Configuration loading for SARATHI.

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
''',

    'models/base.py': '''"""Abstract AI provider interface.

Every concrete provider (Ollama, OpenAI, Gemini, ...) implements this ABC.
The agent core must never import a concrete provider directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from core.types.messages import Message


class AIProvider(ABC):
    """Provider contract used by the agent core."""

    name: str = "base"

    @abstractmethod
    async def chat(
        self, messages: list[Message], *, model: str | None = None
    ) -> str:
        """Return a single non-streamed assistant response."""

    @abstractmethod
    def stream(
        self, messages: list[Message], *, model: str | None = None
    ) -> AsyncIterator[str]:
        """Return an async iterator yielding text chunks."""

    async def health(self) -> bool:
        """Return True if the provider is reachable. Default: True."""
        return True

    async def close(self) -> None:
        """Release resources. Default: no-op."""
        return None
''',

    'models/providers/ollama_provider.py': '''"""Ollama provider (local models).

Uses the /api/chat endpoint:
    POST {base_url}/api/chat
with stream=False for chat() and stream=True for stream().
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from core.errors.exceptions import (
    ModelResponseError,
    ModelUnavailableError,
    ProviderConnectionError,
)
from core.logging.logger import get_logger
from core.types.messages import Message
from models.base import AIProvider

log = get_logger("models.ollama")


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3.1:8b",
        temperature: float = 0.2,
        request_timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.temperature = temperature
        self.request_timeout = request_timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(request_timeout, connect=5.0),
            headers={"Content-Type": "application/json"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def health(self) -> bool:
        try:
            r = await self._client.get("/api/tags", timeout=5.0)
            return r.status_code == 200
        except httpx.HTTPError as e:
            log.debug("Ollama health check failed: %s", e)
            return False

    def _payload(
        self, messages: list[Message], model: str, stream: bool
    ) -> dict[str, object]:
        return {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "stream": stream,
            "options": {"temperature": self.temperature},
        }

    async def chat(
        self, messages: list[Message], *, model: str | None = None
    ) -> str:
        model_name = model or self.default_model
        payload = self._payload(messages, model_name, stream=False)
        try:
            r = await self._client.post("/api/chat", json=payload)
        except httpx.ConnectError as e:
            raise ProviderConnectionError(
                f"Cannot reach Ollama at {self.base_url}. Is `ollama serve` running?"
            ) from e
        except httpx.HTTPError as e:
            raise ModelUnavailableError(f"Ollama request failed: {e}") from e

        if r.status_code == 404:
            raise ModelUnavailableError(
                f"Model '{model_name}' not found in Ollama. Try: ollama pull {model_name}"
            )
        if r.status_code >= 400:
            raise ModelResponseError(
                f"Ollama returned HTTP {r.status_code}: {r.text[:200]}"
            )

        try:
            data = r.json()
        except ValueError as e:
            raise ModelResponseError(
                f"Ollama returned non-JSON response: {r.text[:200]}"
            ) from e

        try:
            return data["message"]["content"]
        except (KeyError, TypeError) as e:
            raise ModelResponseError(
                f"Malformed Ollama chat response: {json.dumps(data)[:200]}"
            ) from e

    async def stream(
        self, messages: list[Message], *, model: str | None = None
    ) -> AsyncIterator[str]:
        model_name = model or self.default_model
        payload = self._payload(messages, model_name, stream=True)
        try:
            async with self._client.stream("POST", "/api/chat", json=payload) as r:
                if r.status_code == 404:
                    raise ModelUnavailableError(
                        f"Model '{model_name}' not found in Ollama. "
                        f"Try: ollama pull {model_name}"
                    )
                if r.status_code >= 400:
                    body = await r.aread()
                    raise ModelResponseError(
                        f"Ollama stream HTTP {r.status_code}: {body[:200]!r}"
                    )
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        log.debug("Skipping non-JSON stream line: %r", line[:80])
                        continue
                    if chunk.get("done"):
                        break
                    content = (chunk.get("message") or {}).get("content")
                    if content:
                        yield content
        except httpx.ConnectError as e:
            raise ProviderConnectionError(
                f"Cannot reach Ollama at {self.base_url}. Is `ollama serve` running?"
            ) from e
        except httpx.HTTPError as e:
            raise ModelUnavailableError(f"Ollama stream failed: {e}") from e
''',

    'models/registry.py': '''"""Provider factory. Keeps the agent core decoupled from concrete providers."""

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
''',

    'core/agent/agent.py': '''"""SARATHI V0.1 Core Brain.

Responsibilities:
- Hold conversation state (system prompt + history).
- Invoke the configured AI provider.
- Enforce a bounded history window.
- Never fabricate a response: if the provider fails, the user message is
  rolled back and the exception propagates.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from core.config.settings import SarathiSettings
from core.logging.logger import get_logger
from core.prompts.system import SARATHI_SYSTEM_PROMPT
from core.types.messages import Conversation, Role
from models.base import AIProvider

log = get_logger("agent")


class Agent:
    def __init__(self, provider: AIProvider, settings: SarathiSettings) -> None:
        self.provider = provider
        self.settings = settings
        self.conversation = Conversation()
        self._seed_system_prompt()

    def _seed_system_prompt(self) -> None:
        self.conversation.add_system(SARATHI_SYSTEM_PROMPT)

    def _trim_history(self) -> None:
        """Keep system prompt + the most recent N-1 messages."""
        max_messages = self.settings.agent.max_history_messages
        messages = self.conversation.messages
        if len(messages) <= max_messages:
            return
        system = messages[0]
        if system.role is not Role.SYSTEM:
            # Defensive: if somehow the system prompt isn't first, rebuild.
            log.warning("System prompt was not at index 0; rebuilding.")
            self.conversation.messages = messages[-(max_messages):]
            return
        tail = messages[-(max_messages - 1):]
        self.conversation.messages = [system, *tail]

    async def ask(self, user_input: str) -> str:
        """Single-shot request; returns the full assistant response."""
        self.conversation.add_user(user_input)
        self._trim_history()
        log.debug("chat() with %d messages", len(self.conversation.messages))
        try:
            reply = await self.provider.chat(
                self.conversation.messages, model=self.settings.model.name
            )
        except Exception:
            # Roll back the user turn so the conversation isn't left dangling.
            self.conversation.messages.pop()
            raise
        self.conversation.add_assistant(reply)
        return reply

    async def stream(self, user_input: str) -> AsyncIterator[str]:
        """Streamed request; yields chunks, commits assistant turn on success."""
        self.conversation.add_user(user_input)
        self._trim_history()
        log.debug("stream() with %d messages", len(self.conversation.messages))

        buffer: list[str] = []
        try:
            async for chunk in self.provider.stream(
                self.conversation.messages, model=self.settings.model.name
            ):
                buffer.append(chunk)
                yield chunk
        except Exception:
            self.conversation.messages.pop()
            raise

        self.conversation.add_assistant("".join(buffer))

    def reset(self) -> None:
        """Clear conversation history but keep the system prompt."""
        self.conversation.clear()
        self._seed_system_prompt()
''',

    'apps/cli/main.py': '''"""SARATHI CLI entry point (V0.1)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from core.agent.agent import Agent
from core.config.settings import SarathiSettings
from core.errors.exceptions import SarathiError
from core.logging.logger import configure_logging
from models.registry import create_provider

app = typer.Typer(
    name="sarathi",
    help="SARATHI — Personal AI Operating Companion (V0.1 Core Brain)",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()
err_console = Console(stderr=True)


async def _chat_loop(settings: SarathiSettings) -> None:
    provider = create_provider(settings.model)
    agent = Agent(provider, settings)

    healthy = await provider.health()
    if not healthy:
        console.print(
            Panel(
                f"[red]Cannot reach {settings.model.provider} at "
                f"{settings.model.base_url}.[/red]\\n\\n"
                "Checklist:\\n"
                "  1. Start Ollama:      [bold]ollama serve[/bold]\\n"
                f"  2. Pull the model:   [bold]ollama pull {settings.model.name}[/bold]\\n"
                "  3. Re-run:            [bold]sarathi chat[/bold]",
                title="Provider unavailable",
                border_style="red",
            )
        )
        await provider.close()
        raise typer.Exit(code=2)

    console.print(
        Panel(
            "[bold cyan]SARATHI V0.1 — Core Brain[/bold cyan]\\n"
            f"provider: [green]{settings.model.provider}[/green]   "
            f"model: [green]{settings.model.name}[/green]\\n"
            "Commands: [bold]/reset[/bold] clear history   "
            "[bold]/exit[/bold] quit",
            border_style="cyan",
        )
    )

    try:
        while True:
            try:
                user = Prompt.ask("[bold blue]you[/bold blue]")
            except (EOFError, KeyboardInterrupt):
                console.print()
                break

            text = user.strip()
            if not text:
                continue
            if text.lower() in {"/exit", "/quit"}:
                break
            if text.lower() == "/reset":
                agent.reset()
                console.print("[yellow]Conversation reset.[/yellow]")
                continue

            console.print("[bold magenta]sarathi[/bold magenta] ", end="")
            try:
                async for chunk in agent.stream(text):
                    console.print(chunk, end="", soft_wrap=True, highlight=False)
                console.print()
            except SarathiError as e:
                console.print(f"\\n[red]Error:[/red] {e}")
            except Exception as e:  # noqa: BLE001
                console.print(f"\\n[red]Unexpected error:[/red] {type(e).__name__}: {e}")
    finally:
        await provider.close()


@app.command()
def chat(
    config: Path = typer.Option(
        Path("config/default.toml"),
        "--config",
        "-c",
        help="Path to TOML config file.",
        show_default=True,
    ),
    log_level: str | None = typer.Option(
        None, "--log-level", help="Override log level (DEBUG/INFO/WARNING/ERROR)."
    ),
) -> None:
    """Start an interactive chat session with SARATHI."""
    try:
        settings = SarathiSettings.load(config)
    except Exception as e:  # noqa: BLE001
        err_console.print(f"[red]Failed to load settings:[/red] {e}")
        raise typer.Exit(code=1) from e

    if log_level:
        settings.logging.level = log_level  # type: ignore[assignment]

    configure_logging(settings.logging.level, settings.logging.file, force=True)

    try:
        asyncio.run(_chat_loop(settings))
    except KeyboardInterrupt:
        console.print("\\n[dim]Interrupted.[/dim]")


@app.command()
def version() -> None:
    """Print SARATHI version."""
    console.print("SARATHI v0.1.0 — Core Brain")


@app.command()
def doctor(
    config: Path = typer.Option(
        Path("config/default.toml"), "--config", "-c", show_default=True
    ),
) -> None:
    """Check configuration and provider health."""
    try:
        settings = SarathiSettings.load(config)
    except Exception as e:  # noqa: BLE001
        err_console.print(f"[red]Failed to load settings:[/red] {e}")
        raise typer.Exit(code=1) from e

    console.print("[bold]SARATHI doctor[/bold]")
    console.print(f"  provider: {settings.model.provider}")
    console.print(f"  model:    {settings.model.name}")
    console.print(f"  base_url: {settings.model.base_url}")
    console.print(f"  timeout:  {settings.model.request_timeout}s")
    console.print(f"  log file: {settings.logging.file}")

    async def _check() -> bool:
        provider = create_provider(settings.model)
        try:
            return await provider.health()
        finally:
            await provider.close()

    ok = asyncio.run(_check())
    if ok:
        console.print("[green]Provider reachable.[/green]")
    else:
        console.print("[red]Provider unreachable.[/red]")
        raise typer.Exit(code=2)


if __name__ == "__main__":
    app()
''',

    'tests/conftest.py': '''from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from core.types.messages import Message
from models.base import AIProvider


class FakeProvider(AIProvider):
    """Deterministic in-memory provider for unit tests."""

    name = "fake"

    def __init__(self, response: str = "ok") -> None:
        self.response = response
        self.chat_calls: list[list[Message]] = []
        self.stream_calls: list[list[Message]] = []
        self.fail_chat = False
        self.fail_stream = False

    async def chat(self, messages, *, model=None):  # type: ignore[override]
        self.chat_calls.append(list(messages))
        if self.fail_chat:
            raise RuntimeError("fake chat failure")
        return self.response

    async def stream(self, messages, *, model=None) -> AsyncIterator[str]:  # type: ignore[override]
        self.stream_calls.append(list(messages))
        if self.fail_stream:
            raise RuntimeError("fake stream failure")
        for token in self.response.split():
            yield token + " "


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()
''',

    'tests/unit/test_messages.py': '''from __future__ import annotations

from core.types.messages import Conversation, Message, Role


def test_message_to_dict_minimal():
    m = Message(role=Role.USER, content="hello")
    assert m.to_dict() == {"role": "user", "content": "hello"}


def test_message_to_dict_includes_name_when_set():
    m = Message(role=Role.TOOL, content="x", name="system_info")
    d = m.to_dict()
    assert d["name"] == "system_info"


def test_conversation_helpers():
    c = Conversation()
    c.add_system("sys")
    c.add_user("hi")
    c.add_assistant("hello")
    assert len(c) == 3
    assert [m.role for m in c.messages] == [Role.SYSTEM, Role.USER, Role.ASSISTANT]
    assert c.to_payload()[0] == {"role": "system", "content": "sys"}


def test_conversation_clear():
    c = Conversation()
    c.add_user("hi")
    c.clear()
    assert len(c) == 0
''',

    'tests/unit/test_config.py': '''from __future__ import annotations

from pathlib import Path

import pytest

from core.config.settings import SarathiSettings


def test_defaults_when_no_file():
    s = SarathiSettings.load(Path("does-not-exist.toml"))
    assert s.model.provider == "ollama"
    assert s.model.name == "llama3.1:8b"
    assert s.agent.max_history_messages >= 4


def test_toml_overrides_defaults(tmp_path: Path):
    cfg = tmp_path / "c.toml"
    cfg.write_text(
        "[model]\\n"
        'name = "qwen2.5:7b"\\n'
        "temperature = 0.7\\n"
        "[agent]\\n"
        "max_history_messages = 12\\n"
    )
    s = SarathiSettings.load(cfg)
    assert s.model.name == "qwen2.5:7b"
    assert s.model.temperature == 0.7
    assert s.agent.max_history_messages == 12


def test_env_overrides_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cfg = tmp_path / "c.toml"
    cfg.write_text('[model]\\nname = "from-toml"\\n')
    monkeypatch.setenv("SARATHI_MODEL__NAME", "from-env")
    s = SarathiSettings.load(cfg)
    assert s.model.name == "from-env"


def test_invalid_temperature_rejected(tmp_path: Path):
    cfg = tmp_path / "c.toml"
    cfg.write_text('[model]\\ntemperature = 5.0\\n')
    with pytest.raises(Exception):
        SarathiSettings.load(cfg)
''',

    'tests/unit/test_agent.py': '''from __future__ import annotations

from pathlib import Path

import pytest

from core.agent.agent import Agent
from core.config.settings import SarathiSettings
from core.types.messages import Role


@pytest.fixture
def settings() -> SarathiSettings:
    return SarathiSettings.load(Path("does-not-exist.toml"))


@pytest.mark.asyncio
async def test_ask_appends_user_and_assistant(fake_provider, settings):
    fake_provider.response = "hello world"
    agent = Agent(fake_provider, settings)

    reply = await agent.ask("hi")
    assert reply == "hello world"

    roles = [m.role for m in agent.conversation.messages]
    assert roles[0] is Role.SYSTEM
    assert roles[-2] is Role.USER
    assert roles[-1] is Role.ASSISTANT


@pytest.mark.asyncio
async def test_stream_appends_after_completion(fake_provider, settings):
    fake_provider.response = "one two three"
    agent = Agent(fake_provider, settings)

    chunks: list[str] = []
    async for c in agent.stream("go"):
        chunks.append(c)

    assert "".join(chunks).strip() == "one two three"
    assert agent.conversation.messages[-1].role is Role.ASSISTANT
    assert agent.conversation.messages[-1].content.strip() == "one two three"


@pytest.mark.asyncio
async def test_failed_chat_rolls_back_user_message(fake_provider, settings):
    fake_provider.fail_chat = True
    agent = Agent(fake_provider, settings)

    before = len(agent.conversation)
    with pytest.raises(RuntimeError):
        await agent.ask("boom")
    assert len(agent.conversation) == before


@pytest.mark.asyncio
async def test_history_is_trimmed(fake_provider, settings):
    settings.agent.max_history_messages = 4
    agent = Agent(fake_provider, settings)
    for i in range(10):
        await agent.ask(f"msg {i}")
    # system + at most 3 others
    assert len(agent.conversation.messages) <= 4
    assert agent.conversation.messages[0].role is Role.SYSTEM


def test_reset_keeps_system_prompt(fake_provider, settings):
    agent = Agent(fake_provider, settings)
    agent.conversation.add_user("x")
    agent.reset()
    assert len(agent.conversation.messages) == 1
    assert agent.conversation.messages[0].role is Role.SYSTEM
''',

    'tests/integration/test_ollama_provider.py': '''from __future__ import annotations

import httpx
import pytest
import respx

from core.errors.exceptions import (
    ModelResponseError,
    ModelUnavailableError,
    ProviderConnectionError,
)
from core.types.messages import Message, Role
from models.providers.ollama_provider import OllamaProvider

BASE = "http://localhost:11434"


def _user(content: str = "hi") -> Message:
    return Message(role=Role.USER, content=content)


@pytest.mark.asyncio
@respx.mock
async def test_health_ok():
    respx.get(f"{BASE}/api/tags").mock(return_value=httpx.Response(200, json={}))
    p = OllamaProvider(base_url=BASE)
    try:
        assert await p.health() is True
    finally:
        await p.close()


@pytest.mark.asyncio
@respx.mock
async def test_health_failure():
    respx.get(f"{BASE}/api/tags").mock(side_effect=httpx.ConnectError("no"))
    p = OllamaProvider(base_url=BASE)
    try:
        assert await p.health() is False
    finally:
        await p.close()


@pytest.mark.asyncio
@respx.mock
async def test_chat_success():
    respx.post(f"{BASE}/api/chat").mock(
        return_value=httpx.Response(200, json={"message": {"content": "hi there"}})
    )
    p = OllamaProvider(base_url=BASE)
    try:
        reply = await p.chat([_user()])
        assert reply == "hi there"
    finally:
        await p.close()


@pytest.mark.asyncio
@respx.mock
async def test_chat_model_not_found():
    respx.post(f"{BASE}/api/chat").mock(
        return_value=httpx.Response(404, json={"error": "model not found"})
    )
    p = OllamaProvider(base_url=BASE)
    try:
        with pytest.raises(ModelUnavailableError):
            await p.chat([_user()])
    finally:
        await p.close()


@pytest.mark.asyncio
@respx.mock
async def test_chat_malformed_body():
    respx.post(f"{BASE}/api/chat").mock(
        return_value=httpx.Response(200, json={"weird": True})
    )
    p = OllamaProvider(base_url=BASE)
    try:
        with pytest.raises(ModelResponseError):
            await p.chat([_user()])
    finally:
        await p.close()


@pytest.mark.asyncio
@respx.mock
async def test_chat_connection_error():
    respx.post(f"{BASE}/api/chat").mock(side_effect=httpx.ConnectError("no"))
    p = OllamaProvider(base_url=BASE)
    try:
        with pytest.raises(ProviderConnectionError):
            await p.chat([_user()])
    finally:
        await p.close()


@pytest.mark.asyncio
@respx.mock
async def test_stream_chunks():
    body = (
        b'{"message":{"content":"Hel"},"done":false}\\n'
        b'{"message":{"content":"lo"},"done":false}\\n'
        b'{"message":{"content":""},"done":true}\\n'
    )
    respx.post(f"{BASE}/api/chat").mock(
        return_value=httpx.Response(200, content=body)
    )
    p = OllamaProvider(base_url=BASE)
    try:
        chunks = [c async for c in p.stream([_user()])]
        assert "".join(chunks) == "Hello"
    finally:
        await p.close()
''',

    'docs/ARCHITECTURE.md': '''# SARATHI Architecture

This document describes the architecture of SARATHI. It is expected to
grow with each version. Sections marked **[V0.1]** are implemented; others
are planned.

## Layers

```
Input → Agent Core → AI Router → Providers → Tools / Memory / Vision
```

### [V0.1] Agent Core

- File: `core/agent/agent.py`
- Holds conversation state (system prompt + bounded history).
- Calls an `AIProvider`.
- Never fabricates a response.
- Rolls back failed turns.

### [V0.1] AI Provider Abstraction

- File: `models/base.py`
- Interface: `chat`, `stream`, `health`, `close`.
- Concrete: `OllamaProvider` (`models/providers/ollama_provider.py`).
- Factory: `models/registry.py` maps `ModelConfig.provider` to an instance.

### [V0.1] Configuration

- File: `core/config/settings.py`
- Priority: init kwargs > env (`SARATHI_*`) > `.env` > TOML > defaults.
- Nested env keys use `__` (e.g. `SARATHI_MODEL__NAME`).

### [V0.1] Logging

- File: `core/logging/logger.py`
- Logger namespace `sarathi.*`.
- Console (Rich) + optional rotating-safe file handler.

### [V0.1] CLI

- File: `apps/cli/main.py`
- Commands: `chat`, `doctor`, `version`.
- Streaming output with Rich.

## Reserved packages (planned)

- `tools/` — V0.2
- `security/` — V0.4
- `voice/` — V0.5
- `memory/` — V0.6
- `vision/` — V0.8
- `ui/` — V1.0+
''',

    'docs/ROADMAP.md': '''# SARATHI Roadmap

Each version is independently runnable, tested, and documented. No version
starts until the previous one is working.

| Version | Objective | Status |
|---|---|---|
| V0.1 | Core Brain (CLI + provider abstraction) | **in progress** |
| V0.2 | Tool system | planned |
| V0.3 | Planner + verifier | planned |
| V0.4 | Security & permissions (T0–T3) | planned |
| V0.5 | Voice (push-to-talk STT/TTS) | planned |
| V0.6 | Memory layers | planned |
| V0.7 | Web intelligence | planned |
| V0.8 | Vision | planned |
| V0.9 | Computer control | planned |
| V1.0 | Desktop app | planned |
| V1.1 | Futuristic HUD | planned |
| V1.2 | Multi-modal agent | planned |
| V1.3 | Advanced automation | planned |
| V1.4 | Pluggable tools | planned |
| V1.5 | Local-first optimization | planned |
| V2.0 | Personal AI OS | planned |
''',

    'docs/SECURITY.md': '''# SARATHI Security Model

**V0.1 status: no tools, no shell, no filesystem writes.**

V0.1 does not execute any user- or model-controlled action beyond sending
text to a configured local or cloud LLM. There is no shell access, no file
mutation, no network calls beyond the configured provider endpoint.

## Forward-looking principles (enforced from V0.4 onward)

- Permission tiers T0–T3; see the project brief.
- LLM never gets unrestricted shell access.
- Secrets only via env vars / OS keyring; never in source.
- Audit log for all T1+ actions.
- Global emergency STOP.

## V0.1 secret handling

- No API keys are used by V0.1 (Ollama is local).
- `.env` and `config/local.toml` are gitignored.
- Logs must not include secrets.
''',

    'docs/SETUP.md': '''# SARATHI Setup (V0.1)

## Prerequisites

- Windows 10/11, Linux, or macOS
- Python 3.11 or newer
- [Ollama](https://ollama.com/) installed
- ~5 GB free disk for a 7B quantized model

## Steps (Windows PowerShell)

```powershell
cd SARATHI
.\\scripts\\setup.ps1
ollama pull llama3.1:8b
ollama serve        # in a separate terminal
sarathi doctor
sarathi chat
```

## Common issues

| Symptom | Fix |
|---|---|
| `Cannot reach Ollama` | Start `ollama serve` |
| `Model 'x' not found` | `ollama pull x` |
| Slow responses | Use a smaller model in `config/default.toml` |
| `python: command not found` | Install Python 3.11+ and add to PATH |

## Configuration priority

CLI args → `SARATHI_*` env vars → `.env` → TOML (`-c`) → defaults.
''',

    'docs/DEVELOPMENT.md': '''# Development Guide

## Environment

```powershell
.\\scripts\\setup.ps1     # creates .venv, installs editable + dev deps
```

## Checks

```powershell
.\\scripts\\test.ps1      # ruff + mypy + pytest
```

Or individually:

```powershell
ruff check .
mypy core models apps
pytest -q
```

## Conventions

- Type hints on public functions.
- Errors inherit from `SarathiError`.
- No provider imported directly by `core/`.
- No secrets in source.
- Small, focused commits (conventional commits).

## Adding a provider

1. Create `models/providers/<name>_provider.py` subclassing `AIProvider`.
2. Register it in `models/registry.py`.
3. Extend `ModelConfig.provider` Literal in `core/config/settings.py`.
4. Add tests under `tests/integration/`.
''',

    'docs/CHANGELOG.md': '''# Changelog

All notable changes are recorded here. Format: Keep a Changelog.
Versioning: Semantic-ish (MAJOR.MINOR.PATCH).

## [0.1.0] — V0.1 Core Brain

### Added
- CLI (`chat`, `doctor`, `version`) built on Typer + Rich.
- AI provider abstraction (`AIProvider`).
- First concrete provider: Ollama (`OllamaProvider`).
- Provider factory (`create_provider`).
- Configuration loader with TOML + env + `.env`.
- Structured logging.
- Conversation state with bounded history.
- Graceful error hierarchy (`SarathiError` and subclasses).
- Unit tests for config, messages, agent.
- Integration tests for the Ollama provider (respx).
- Windows PowerShell scripts: setup, run, test.
- Documentation: architecture, roadmap, security, setup, dev.

### Not included (by design)
- Tools, planner, memory, voice, vision, UI, computer control.
'''
}

for path, content in files.items():
    full_path = os.path.join(r"d:\SARATHI", path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)

print("Files created successfully.")
