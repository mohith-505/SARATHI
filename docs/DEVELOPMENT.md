# Development Guide

## Environment

```powershell
.\scripts\setup.ps1     # creates .venv, installs editable + dev deps
```

## Checks

```powershell
.\scripts\test.ps1      # ruff + mypy + pytest
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
