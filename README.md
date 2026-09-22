# SARATHI

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
.\scripts\setup.ps1

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
