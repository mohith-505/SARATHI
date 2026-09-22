# SARATHI Setup (V0.1)

## Prerequisites

- Windows 10/11, Linux, or macOS
- Python 3.11 or newer
- [Ollama](https://ollama.com/) installed
- ~5 GB free disk for a 7B quantized model

## Steps (Windows PowerShell)

```powershell
cd SARATHI
.\scripts\setup.ps1
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
