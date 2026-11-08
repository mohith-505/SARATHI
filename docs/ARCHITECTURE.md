# SARATHI Architecture

This document describes the architecture of SARATHI. Sections marked **[V0.1]** / **[V0.2]** are implemented; others are planned.

## Core Layers

```
HUD / Client → JSON-RPC 2.0 (WebSocket 127.0.0.1) → Daemon Core Runtime → Agent Core → AI Providers (Ollama) → Tools (Bounded)
                                                                       ↓
                                                                SQLite Persistence
```

## Permanent Architectural Rules

1. **Policy Immobility**: The model can NEVER modify, loosen, or reconfigure its own security policy, permission tiers, allowed roots, or tool whitelists.
2. **No Self-Approval**: The model cannot approve its own privileged actions or bypass server confirmation gates.
3. **Unbypassable Emergency Stop**: The emergency stop halts all tool execution and agent processing immediately. It cannot be cleared by the model or untrusted requests.
4. **Lean Persistence (Phase 1)**: SQLite first via `aiosqlite`. Vector memory and `sqlite-vec` are deferred to later phases.
5. **Localhost Isolation**: The daemon binds strictly to `127.0.0.1`.

## Subsystems

### Daemon Core Runtime (`apps/daemon/core_runtime.py`, `apps/daemon/rpc.py`, `apps/daemon/main.py`)
- Exposes JSON-RPC 2.0 WebSocket endpoint at `/ws` on `127.0.0.1:8000`.
- Streams tokens using `chat.delta` notifications for real-time frontend HUD display.
- Persists user messages and completed assistant responses to SQLite.
- Fails cleanly on provider errors without corrupting the conversation history.

### Persistence (`core/storage/sqlite.py`)
- Single-file relational storage with automated schema migrations.
- Tracks sessions, messages, timestamps, and metadata.
- Enforces foreign keys (`PRAGMA foreign_keys = ON`) with automatic session creation.

### Tool Registry & Authorization (`tools/`)
- Phase 1 read-only whitelist:
  - `fs.list`: Directory listing bounded by allowed workspace roots.
  - `fs.read`: UTF-8 file reading bounded by size limits (default 200 KB) and workspace roots.
  - `web.search`: Search provider adapter via DuckDuckGo.
- Server-side authorization checks `call_tool()` before every execution.

### Agent Core (`core/agent/agent.py`)
- Bounded tool execution loop with configurable iteration limit (`max_tool_iterations`).
- Detects JSON tool calls, executes through server-authorized tools, feeds back results.
- Rolls back on unhandled provider failures.

### AI Provider (`models/`)
- Asynchronous streaming and chat interface to local Ollama (`/api/chat`).
- Health checks and structured error recovery.
