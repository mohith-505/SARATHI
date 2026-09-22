# SARATHI Architecture

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
