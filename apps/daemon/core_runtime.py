"""SARATHI Core Runtime (Phase 2 Interactive Agent & Controlled Tools).

Permanent Invariants:
1. The model must NEVER be able to modify its own security policy, approve its
   own privileged actions, or bypass the emergency stop.
2. Authorization and granted permissions are strictly server-side authoritative;
   client or model requests can NEVER supply trusted permission sets.
3. Privileged tools (T2/T3) require interactive user confirmation.
4. Host binding is strictly 127.0.0.1 (localhost).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
from fastapi import WebSocket

from core.config.settings import SarathiSettings
from core.logging.logger import get_logger
from core.storage.sqlite import SQLiteStore
from core.types.messages import Message, Role
from models.providers.ollama_provider import OllamaProvider

log = get_logger("daemon.core_runtime")

# Workspace root for file boundaries
WORKSPACE = Path.cwd().resolve()

# Permanent server-side security policy
ALLOWED_TOOLS: set[str] = {
    "fs.list", "fs.read", "fs.write", "fs.mkdir",
    "web.search", "system_information", "current_time",
    "terminal_safe", "application_launch",
    "filesystem_list", "filesystem_read", "filesystem_write", "directory_create", "web_search",
    "memory.save", "memory.read", "memory.search", "memory.list",
    "memory_save", "memory_read", "memory_search", "memory_list",
}
_SERVER_POLICY: set[str] = {
    "fs.list", "fs.read", "fs.write", "fs.mkdir",
    "web.search", "system_information", "current_time",
    "terminal_safe", "application_launch",
    "memory.save", "memory.read", "memory.search", "memory.list",
}
_EMERGENCY_STOP: bool = False

# Global database store
DEFAULT_DB_PATH = Path("data/sarathi.db")
store = SQLiteStore(DEFAULT_DB_PATH)


# --- Emergency Stop Controls ---

def trigger_emergency_stop() -> None:
    """Trigger global emergency stop circuit-breaker."""
    global _EMERGENCY_STOP
    _EMERGENCY_STOP = True
    log.warning("EMERGENCY STOP TRIGGERED. All tool executions and operations halted.")


def reset_emergency_stop() -> None:
    """Reset emergency stop (strictly operator/server action, never callable by LLM)."""
    global _EMERGENCY_STOP
    _EMERGENCY_STOP = False
    log.info("Emergency stop reset by host operator.")


def is_emergency_stop_active() -> bool:
    """Check if emergency stop is currently active."""
    return _EMERGENCY_STOP


def get_server_policy() -> set[str]:
    """Get the active server-side permission set."""
    return set(_SERVER_POLICY)


# --- Path & File Security Boundary ---

def safe_path(path: str | Path, workspace: Path | None = None) -> Path:
    """Resolve `path` and guarantee it resides strictly under `workspace`.

    - Relative paths resolve against `workspace`.
    - Symlinks are resolved completely to avoid symlink traversal escapes.
    - Any path escaping `workspace` raises PermissionError.
    """
    ws = (workspace or WORKSPACE).resolve()
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = ws / p

    try:
        resolved = p.resolve(strict=False)
    except OSError as e:
        raise PermissionError(f"Cannot resolve path {path!r}: {e}") from e

    try:
        resolved.relative_to(ws)
    except ValueError as e:
        raise PermissionError(f"Path outside workspace boundary: {path!r} -> {resolved}") from e

    return resolved


# --- Tool Execution with Strict Server-Side Authorization ---

async def call_tool(
    tool_name: str,
    args: dict[str, Any],
    granted_permissions: set[str] | None = None,
    *,
    workspace: Path | None = None,
) -> dict[str, Any]:
    """Execute a restricted tool with strict server-side policy enforcement.

    Permanent security rules:
    - If emergency stop is active, immediate PermissionError.
    - If tool_name is not in ALLOWED_TOOLS, immediate PermissionError.
    - If tool_name is not in granted_permissions (or server policy), PermissionError.
    """
    if is_emergency_stop_active():
        raise PermissionError("Emergency stop is active. Tool execution blocked.")

    if tool_name not in ALLOWED_TOOLS:
        raise PermissionError(f"Unauthorized or unknown tool: {tool_name!r}")

    # Canonicalize tool name
    canonical_name = {
        "filesystem_read": "fs.read",
        "filesystem_list": "fs.list",
        "filesystem_write": "fs.write",
        "directory_create": "fs.mkdir",
        "web_search": "web.search",
        "memory.save": "memory_save",
        "memory.read": "memory_read",
        "memory.search": "memory_search",
        "memory.list": "memory_list",
    }.get(tool_name, tool_name)

    # Server policy check
    effective_permissions = (
        granted_permissions if granted_permissions is not None else get_server_policy()
    )
    if canonical_name not in effective_permissions and tool_name not in effective_permissions:
        raise PermissionError(f"Permission denied for tool: {tool_name!r}")

    ws = workspace or WORKSPACE

    if canonical_name == "fs.read":
        path_str = args.get("path")
        if not path_str:
            raise ValueError("Argument 'path' is required for fs.read")
        p = safe_path(path_str, workspace=ws)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")
        if not p.is_file():
            raise IsADirectoryError(f"Path is not a regular file: {p}")
        max_bytes = int(args.get("max_bytes", 200_000))
        size = p.stat().st_size
        if size > max_bytes:
            raise ValueError(f"File too large: {size} bytes exceeds limit of {max_bytes} bytes")
        try:
            content = p.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raise ValueError("File content is not valid UTF-8 text") from e
        return {"path": str(p), "size_bytes": size, "content": content}

    elif canonical_name == "fs.write":
        path_str = args.get("path")
        content = str(args.get("content", ""))
        overwrite = bool(args.get("overwrite", False))
        if not path_str:
            raise ValueError("Argument 'path' is required for fs.write")
        p = safe_path(path_str, workspace=ws)
        if p.exists():
            if not p.is_file():
                raise IsADirectoryError(f"Path is not a regular file: {p}")
            if not overwrite:
                raise FileExistsError(f"File exists (overwrite=False): {p}")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        if p.read_text(encoding="utf-8") != content:
            raise OSError("Post-write verification mismatch")
        return {"path": str(p), "bytes": len(content.encode("utf-8")), "verified": True}

    elif canonical_name == "fs.mkdir":
        path_str = args.get("path")
        if not path_str:
            raise ValueError("Argument 'path' is required for fs.mkdir")
        p = safe_path(path_str, workspace=ws)
        created = False
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created = True
        return {"path": str(p), "created": created}

    elif canonical_name == "fs.list":
        path_str = args.get("path", ".")
        p = safe_path(path_str, workspace=ws)
        if not p.exists():
            raise FileNotFoundError(f"Directory not found: {p}")
        if not p.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {p}")
        max_entries = int(args.get("max_entries", 100))
        entries: list[dict[str, Any]] = []
        for item in sorted(p.iterdir()):
            if len(entries) >= max_entries:
                break
            try:
                is_dir = item.is_dir()
                size = 0 if is_dir else item.stat().st_size
                entries.append({"name": item.name, "is_dir": is_dir, "size_bytes": size})
            except OSError:
                continue
        return {"path": str(p), "count": len(entries), "entries": entries}

    elif canonical_name == "web.search":
        query = args.get("query")
        if not query:
            raise ValueError("Argument 'query' is required for web.search")
        max_results = int(args.get("max_results", 5))
        try:
            from tools.web.search import _run_search
            results = await asyncio.to_thread(_run_search, query, max_results)
        except Exception as e:
            log.warning("Web search provider failed: %s", e)
            results = []
        return {"query": query, "results": results}

    elif canonical_name in {
        "system_information",
        "current_time",
        "terminal_safe",
        "application_launch",
        "memory_save",
        "memory_read",
        "memory_search",
        "memory_list",
    }:
        from core.config.settings import ToolsConfig
        from core.memory.vault import MemoryVault
        from tools.factory import build_registry

        vault = MemoryVault(Path("data/memory"), store)
        await vault.bootstrap()
        t_reg = build_registry(ToolsConfig(), vault=vault)
        tool = t_reg.get(canonical_name)
        v_args = tool.input_schema.model_validate(args)
        t_res = await tool.execute(v_args)
        if not t_res.success:
            raise RuntimeError(t_res.error or "Tool execution failed")
        return t_res.output

    raise PermissionError(f"Tool implementation missing: {tool_name}")


# --- Persistence Helpers ---

async def save_message(
    session_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
    db_store: SQLiteStore | None = None,
) -> None:
    """Save a message to SQLite storage, ensuring session foreign key exists."""
    target_store = db_store or store
    msg = Message(
        role=Role(role),
        content=content,
        metadata=metadata or {},
    )
    await target_store.save_message(session_id, msg)


async def get_messages(
    session_id: str,
    db_store: SQLiteStore | None = None,
) -> list[Message]:
    """Retrieve message history for a session from SQLite storage."""
    target_store = db_store or store
    return await target_store.get_messages(session_id)


# --- JSON-RPC 2.0 Helpers ---

def rpc_result(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def rpc_error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def rpc_notification(method: str, params: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "method": method, "params": params}


# --- Streaming Chat to Ollama ---

async def chat_stream(
    websocket: WebSocket,
    request_id: Any,
    session_id: str,
    user_text: str,
    settings: SarathiSettings,
    db_store: SQLiteStore | None = None,
) -> None:
    """Send chat messages to Ollama asynchronously, stream chunks to client, and persist."""
    if is_emergency_stop_active():
        await websocket.send_json(
            rpc_error(request_id, -32000, "Emergency stop is active. Operations halted.")
        )
        return

    target_store = db_store or store

    # Save user message first
    await save_message(session_id, "user", user_text, db_store=target_store)

    # Fetch history for context
    history = await get_messages(session_id, db_store=target_store)

    provider = OllamaProvider(
        base_url=settings.model.base_url,
        default_model=settings.model.name,
        temperature=settings.model.temperature,
        request_timeout=settings.model.request_timeout,
    )

    answer_parts: list[str] = []

    try:
        async for chunk in provider.stream(history, model=settings.model.name):
            if is_emergency_stop_active():
                await websocket.send_json(
                    rpc_error(request_id, -32000, "Emergency stop triggered during generation.")
                )
                return
            if chunk:
                answer_parts.append(chunk)
                await websocket.send_json({
                    "jsonrpc": "2.0",
                    "method": "chat.delta",
                    "params": {
                        "id": request_id,
                        "text": chunk,
                    },
                })

        answer = "".join(answer_parts)
        # Only persist once complete
        await save_message(session_id, "assistant", answer, db_store=target_store)
        await websocket.send_json({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "session_id": session_id,
                "content": answer,
                "reply": answer,
                "done": True,
            },
        })
    except (httpx.HTTPError, json.JSONDecodeError, Exception) as exc:
        log.exception("Model error during streaming: %s", exc)
        # Do not store a failed/incomplete answer as a completed one.
        await websocket.send_json(
            rpc_error(request_id, -32000, f"Model error: {exc}")
        )
    finally:
        await provider.close()
