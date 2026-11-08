"""Tests for SARATHI Core Runtime and Security Invariants.

Validates:
- Workspace path boundary enforcement and safe_path
- Symlink traversal escape prevention
- Relative traversal (../) prevention
- Tool authorization and refusal of unauthorized tools (e.g. shell.exec)
- Permission checking (T0 read-only subset)
- Missing file and oversized file handling
- Emergency stop invariant and unbypassability
- SQLite persistence round-trip
- JSON-RPC 2.0 message handling and error recovery
- Ollama connection failure handling
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from apps.daemon.core_runtime import (
    WORKSPACE,
    call_tool,
    chat_stream,
    get_messages,
    is_emergency_stop_active,
    reset_emergency_stop,
    safe_path,
    save_message,
    trigger_emergency_stop,
)
from apps.daemon.rpc import RPCConnection
from core.config.settings import SarathiSettings
from core.storage.sqlite import SQLiteStore


def test_workspace_path_is_allowed():
    path = safe_path("notes.txt")
    assert path.is_relative_to(WORKSPACE)


def test_absolute_path_outside_workspace_is_rejected():
    with pytest.raises(PermissionError):
        safe_path("C:/Windows/win.ini")


@pytest.mark.asyncio
async def test_unknown_tool_is_rejected():
    with pytest.raises(PermissionError):
        await call_tool(
            "shell.exec",
            {"command": "whoami"},
            {"shell.exec"},
        )


@pytest.mark.asyncio
async def test_missing_permission_is_rejected():
    with pytest.raises(PermissionError):
        await call_tool(
            "fs.read",
            {"path": "notes.txt"},
            {"fs.list"},
        )


def test_path_traversal_dotdot_is_rejected(tmp_path: Path):
    outside = tmp_path.parent
    with pytest.raises(PermissionError):
        safe_path(f"../../{outside.name}/secret.txt", workspace=tmp_path)


def test_symlink_escape_is_rejected(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    target_file = outside_dir / "secret.txt"
    target_file.write_text("classified")

    symlink_path = ws / "leak.txt"
    try:
        symlink_path.symlink_to(target_file)
    except OSError:
        pytest.skip("Symlinks not permitted by OS in this context")

    with pytest.raises(PermissionError):
        safe_path("leak.txt", workspace=ws)


@pytest.mark.asyncio
async def test_fs_read_success_and_missing(tmp_path: Path):
    ws = tmp_path
    sample = ws / "hello.txt"
    sample.write_text("Hello World", encoding="utf-8")

    # Success
    res = await call_tool("fs.read", {"path": "hello.txt"}, {"fs.read"}, workspace=ws)
    assert res["content"] == "Hello World"
    assert res["size_bytes"] == 11

    # Missing file
    with pytest.raises(FileNotFoundError):
        await call_tool("fs.read", {"path": "does_not_exist.txt"}, {"fs.read"}, workspace=ws)


@pytest.mark.asyncio
async def test_oversized_file_is_rejected(tmp_path: Path):
    ws = tmp_path
    big_file = ws / "big.bin"
    big_file.write_text("x" * 1000, encoding="utf-8")

    with pytest.raises(ValueError, match="exceeds limit"):
        await call_tool("fs.read", {"path": "big.bin", "max_bytes": 100}, {"fs.read"}, workspace=ws)


@pytest.mark.asyncio
async def test_fs_list(tmp_path: Path):
    ws = tmp_path
    (ws / "file1.txt").write_text("1")
    (ws / "subdir").mkdir()

    res = await call_tool("fs.list", {"path": "."}, {"fs.list"}, workspace=ws)
    names = {e["name"] for e in res["entries"]}
    assert "file1.txt" in names
    assert "subdir" in names


@pytest.mark.asyncio
async def test_emergency_stop_invariant():
    try:
        trigger_emergency_stop()
        assert is_emergency_stop_active() is True

        # Any tool call MUST be immediately rejected
        with pytest.raises(PermissionError, match="Emergency stop is active"):
            await call_tool("fs.read", {"path": "notes.txt"}, {"fs.read"})

    finally:
        reset_emergency_stop()
        assert is_emergency_stop_active() is False


@pytest.mark.asyncio
async def test_sqlite_persistence_roundtrip(tmp_path: Path):
    db_file = tmp_path / "test_sarathi.db"
    store = SQLiteStore(db_file)
    await store.connect()

    session_id = "test_session_1"
    await save_message(session_id, "user", "Hello daemon", db_store=store)
    await save_message(session_id, "assistant", "Hello human", db_store=store)

    msgs = await get_messages(session_id, db_store=store)
    assert len(msgs) == 2
    assert msgs[0].role.value == "user"
    assert msgs[0].content == "Hello daemon"
    assert msgs[1].role.value == "assistant"
    assert msgs[1].content == "Hello human"

    await store.close()


@pytest.mark.asyncio
async def test_malformed_json_rpc_messages(tmp_path: Path):
    db_file = tmp_path / "rpc_test.db"
    store = SQLiteStore(db_file)
    await store.connect()
    settings = SarathiSettings.load(Path("config/default.toml"))

    mock_ws = MagicMock()
    mock_ws.send_text = AsyncMock()

    rpc = RPCConnection(mock_ws, store, settings)

    # 1. Parse error
    await rpc.handle_message("NOT A VALID JSON")
    sent = json.loads(mock_ws.send_text.call_args[0][0])
    assert sent["error"]["code"] == -32700

    # 2. Invalid Request (not 2.0)
    mock_ws.send_text.reset_mock()
    await rpc.handle_message(json.dumps({"jsonrpc": "1.0", "method": "chat.send", "id": 1}))
    sent = json.loads(mock_ws.send_text.call_args[0][0])
    assert sent["error"]["code"] == -32600

    # 3. Method not found
    mock_ws.send_text.reset_mock()
    await rpc.handle_message(json.dumps({"jsonrpc": "2.0", "method": "unknown.method", "id": 2}))
    sent = json.loads(mock_ws.send_text.call_args[0][0])
    assert sent["error"]["code"] == -32601

    # 4. Missing params
    mock_ws.send_text.reset_mock()
    msg_payload = {"jsonrpc": "2.0", "method": "chat.send", "params": {}, "id": 3}
    await rpc.handle_message(json.dumps(msg_payload))
    sent = json.loads(mock_ws.send_text.call_args[0][0])
    assert sent["error"]["code"] == -32602

    await store.close()


@pytest.mark.asyncio
async def test_failed_ollama_streaming_does_not_persist(tmp_path: Path):
    db_file = tmp_path / "stream_test.db"
    store = SQLiteStore(db_file)
    await store.connect()
    settings = SarathiSettings.load(Path("config/default.toml"))

    mock_ws = MagicMock()
    mock_ws.send_json = AsyncMock()

    # Simulate network error from Ollama
    with patch("models.providers.ollama_provider.OllamaProvider.stream") as mock_stream:
        async def failing_stream(*args, **kwargs):
            raise httpx.ConnectError("Ollama daemon unreachable")
            yield "partial"  # pragma: no cover

        mock_stream.side_effect = failing_stream

        await chat_stream(
            mock_ws,
            request_id=123,
            session_id="err_session",
            user_text="What is the time?",
            settings=settings,
            db_store=store,
        )

    # Check error message sent to client
    sent_calls = [c[0][0] for c in mock_ws.send_json.call_args_list]
    error_response = next(c for c in sent_calls if "error" in c)
    assert error_response["error"]["code"] == -32000
    assert "Ollama daemon unreachable" in error_response["error"]["message"]

    # Verify that no assistant message was persisted
    history = await get_messages("err_session", db_store=store)
    assert len(history) == 1
    assert history[0].role.value == "user"

    await store.close()


@pytest.mark.asyncio
async def test_privileged_tool_triggers_approval_and_executes_on_approval(tmp_path: Path):
    db_file = tmp_path / "approval_test.db"
    store = SQLiteStore(db_file)
    await store.connect()

    settings = SarathiSettings.load(Path("config/default.toml"))
    settings.tools.allowed_roots = [str(tmp_path)]

    mock_ws = MagicMock()
    mock_ws.send_text = AsyncMock()

    rpc = RPCConnection(mock_ws, store, settings)

    target_file = tmp_path / "created.txt"

    call_count = 0

    async def mock_stream_gen(messages, model=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            yield json.dumps({
                "tool": "fs.write",
                "arguments": {"path": str(target_file), "content": "approved content"},
            })
        else:
            yield "File created."

    with patch.object(rpc.provider, "stream", side_effect=mock_stream_gen):
        chat_req = {
            "jsonrpc": "2.0",
            "method": "chat.send",
            "params": {"session_id": "appr_sess", "message": "create created.txt"},
            "id": 1,
        }
        chat_task = asyncio.create_task(rpc.handle_message(json.dumps(chat_req)))

        for _ in range(50):
            if rpc.pending_approvals:
                break
            await asyncio.sleep(0.01)

        assert len(rpc.pending_approvals) == 1
        approval_id = next(iter(rpc.pending_approvals.keys()))

        sent_messages = [json.loads(c[0][0]) for c in mock_ws.send_text.call_args_list]
        appr_notif = next(m for m in sent_messages if m.get("method") == "chat.approval_request")
        assert appr_notif["params"]["approval_id"] == approval_id
        assert appr_notif["params"]["tool"] == "fs.write"
        assert appr_notif["params"]["permission_level"] == "T2"

        appr_resp = {
            "jsonrpc": "2.0",
            "method": "chat.approval_response",
            "params": {"approval_id": approval_id, "approved": True},
            "id": 2,
        }
        await rpc.handle_message(json.dumps(appr_resp))
        await chat_task

    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == "approved content"

    await store.close()


@pytest.mark.asyncio
async def test_privileged_tool_denied_by_user(tmp_path: Path):
    db_file = tmp_path / "denial_test.db"
    store = SQLiteStore(db_file)
    await store.connect()

    settings = SarathiSettings.load(Path("config/default.toml"))
    settings.tools.allowed_roots = [str(tmp_path)]

    mock_ws = MagicMock()
    mock_ws.send_text = AsyncMock()

    rpc = RPCConnection(mock_ws, store, settings)

    target_file = tmp_path / "unwanted.txt"

    call_count = 0

    async def mock_stream_gen(messages, model=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            yield json.dumps({
                "tool": "fs.write",
                "arguments": {"path": str(target_file), "content": "should not exist"},
            })
        else:
            yield "Okay, did not write file."

    with patch.object(rpc.provider, "stream", side_effect=mock_stream_gen):
        chat_req = {
            "jsonrpc": "2.0",
            "method": "chat.send",
            "params": {"session_id": "deny_sess", "message": "create unwanted.txt"},
            "id": 1,
        }
        chat_task = asyncio.create_task(rpc.handle_message(json.dumps(chat_req)))

        for _ in range(50):
            if rpc.pending_approvals:
                break
            await asyncio.sleep(0.01)

        approval_id = next(iter(rpc.pending_approvals.keys()))

        appr_resp = {
            "jsonrpc": "2.0",
            "method": "chat.approval_response",
            "params": {"approval_id": approval_id, "approved": False},
            "id": 2,
        }
        await rpc.handle_message(json.dumps(appr_resp))
        await chat_task

    assert not target_file.exists()

    msgs = await store.get_messages("deny_sess")
    tool_msg = next((m for m in msgs if m.role.value == "tool"), None)
    assert tool_msg is not None
    assert "User denied execution." in tool_msg.content

    await store.close()


@pytest.mark.asyncio
async def test_emergency_stop_cancels_pending_approval(tmp_path: Path):
    db_file = tmp_path / "estop_test.db"
    store = SQLiteStore(db_file)
    await store.connect()

    settings = SarathiSettings.load(Path("config/default.toml"))
    settings.tools.allowed_roots = [str(tmp_path)]

    mock_ws = MagicMock()
    mock_ws.send_text = AsyncMock()

    rpc = RPCConnection(mock_ws, store, settings)

    target_file = tmp_path / "estop_file.txt"

    call_count = 0

    async def mock_stream_gen(messages, model=None):
        nonlocal call_count
        call_count += 1
        yield json.dumps({
            "tool": "fs.write",
            "arguments": {"path": str(target_file), "content": "should be aborted"},
        })

    with patch.object(rpc.provider, "stream", side_effect=mock_stream_gen):
        chat_req = {
            "jsonrpc": "2.0",
            "method": "chat.send",
            "params": {"session_id": "estop_sess", "message": "create estop_file.txt"},
            "id": 1,
        }
        chat_task = asyncio.create_task(rpc.handle_message(json.dumps(chat_req)))

        for _ in range(50):
            if rpc.pending_approvals:
                break
            await asyncio.sleep(0.01)

        assert len(rpc.pending_approvals) == 1

        stop_req = {
            "jsonrpc": "2.0",
            "method": "emergency_stop.trigger",
            "id": 99,
        }
        await rpc.handle_message(json.dumps(stop_req))
        await chat_task

    assert not target_file.exists()
    assert is_emergency_stop_active() is True
    reset_emergency_stop()

    await store.close()


@pytest.mark.asyncio
async def test_chat_approval_response_invalid_id(tmp_path: Path):
    db_file = tmp_path / "invalid_appr.db"
    store = SQLiteStore(db_file)
    await store.connect()

    settings = SarathiSettings.load(Path("config/default.toml"))
    mock_ws = MagicMock()
    mock_ws.send_text = AsyncMock()

    rpc = RPCConnection(mock_ws, store, settings)

    appr_resp = {
        "jsonrpc": "2.0",
        "method": "chat.approval_response",
        "params": {"approval_id": "non-existent-uuid", "approved": True},
        "id": 1,
    }
    await rpc.handle_message(json.dumps(appr_resp))

    sent = json.loads(mock_ws.send_text.call_args[0][0])
    assert sent["error"]["code"] == -32602
    assert "Approval request not found or expired" in sent["error"]["message"]

    await store.close()
