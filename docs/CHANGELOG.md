# Changelog

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
