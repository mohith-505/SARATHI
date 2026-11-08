"""Tests for SARATHI Transparent Markdown Memory Vault and Tools."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.daemon.rpc import RPCConnection
from core.config.settings import SarathiSettings
from core.memory.vault import MemoryVault
from core.prompts.system import build_system_prompt
from core.storage.sqlite import SQLiteStore
from tools.memory.list import MemoryListTool
from tools.memory.read import MemoryReadTool
from tools.memory.save import MemorySaveTool
from tools.memory.search import MemorySearchTool


@pytest.mark.asyncio
async def test_memory_vault_bootstrap(tmp_path: Path):
    vault_dir = tmp_path / "memory_vault"
    db_file = tmp_path / "test.db"
    store = SQLiteStore(db_file)
    await store.connect()

    vault = MemoryVault(vault_dir, store)
    await vault.bootstrap()

    # Check files created
    assert vault_dir.exists()
    assert (vault_dir / ".obsidian" / "app.json").exists()
    assert (vault_dir / "README.md").exists()
    assert (vault_dir / "user_profile.md").exists()
    assert (vault_dir / "preferences.md").exists()
    assert (vault_dir / "facts.md").exists()
    assert (vault_dir / "projects.md").exists()

    await store.close()


@pytest.mark.asyncio
async def test_memory_vault_save_and_retrieve(tmp_path: Path):
    vault_dir = tmp_path / "memory_vault"
    db_file = tmp_path / "test.db"
    store = SQLiteStore(db_file)
    await store.connect()

    vault = MemoryVault(vault_dir, store)
    await vault.bootstrap()

    # Save preference
    saved = await vault.save_entry("theme", "cyberpunk neon", category="preference")
    assert saved["key"] == "theme"
    assert saved["content"] == "cyberpunk neon"
    assert saved["category"] == "preference"

    # Check markdown file updated
    pref_file = vault_dir / "preferences.md"
    content = pref_file.read_text(encoding="utf-8")
    assert "- **theme**: cyberpunk neon" in content

    # Check SQLite entry
    entry = await vault.get_entry("theme")
    assert entry is not None
    assert entry["content"] == "cyberpunk neon"

    # Update existing key without duplication
    await vault.save_entry("theme", "midnight dark", category="preference")
    content_updated = pref_file.read_text(encoding="utf-8")
    assert content_updated.count("- **theme**:") == 1
    assert "- **theme**: midnight dark" in content_updated

    await store.close()


@pytest.mark.asyncio
async def test_memory_vault_invalid_keys(tmp_path: Path):
    vault_dir = tmp_path / "memory_vault"
    db_file = tmp_path / "test.db"
    store = SQLiteStore(db_file)
    await store.connect()

    vault = MemoryVault(vault_dir, store)
    await vault.bootstrap()

    # Reject path traversal keys
    with pytest.raises(ValueError, match="Invalid memory key"):
        await vault.save_entry("../../escape", "hacked")

    with pytest.raises(ValueError, match="Invalid memory key"):
        await vault.save_entry("key with spaces", "invalid")

    await store.close()


@pytest.mark.asyncio
async def test_memory_vault_search_and_list(tmp_path: Path):
    vault_dir = tmp_path / "memory_vault"
    db_file = tmp_path / "test.db"
    store = SQLiteStore(db_file)
    await store.connect()

    vault = MemoryVault(vault_dir, store)
    await vault.bootstrap()

    await vault.save_entry("user_name", "Mohith", category="profile")
    await vault.save_entry("favorite_lang", "Python", category="preference")
    await vault.save_entry("architecture", "Local-first AI", category="fact")

    # Search
    results = await vault.search_entries("Python")
    assert len(results) == 1
    assert results[0]["key"] == "favorite_lang"

    # List all
    all_entries = await vault.list_entries()
    assert len(all_entries) == 3

    # List by category
    pref_entries = await vault.list_entries("preference")
    assert len(pref_entries) == 1
    assert pref_entries[0]["key"] == "favorite_lang"

    await store.close()


@pytest.mark.asyncio
async def test_memory_vault_delete(tmp_path: Path):
    vault_dir = tmp_path / "memory_vault"
    db_file = tmp_path / "test.db"
    store = SQLiteStore(db_file)
    await store.connect()

    vault = MemoryVault(vault_dir, store)
    await vault.bootstrap()

    await vault.save_entry("temp_fact", "Temporary knowledge", category="fact")
    assert await vault.get_entry("temp_fact") is not None

    deleted = await vault.delete_entry("temp_fact")
    assert deleted is True
    assert await vault.get_entry("temp_fact") is None

    # Check removed from markdown
    facts_file = vault_dir / "facts.md"
    assert "temp_fact" not in facts_file.read_text(encoding="utf-8")

    await store.close()


@pytest.mark.asyncio
async def test_memory_context_summary_injection(tmp_path: Path):
    vault_dir = tmp_path / "memory_vault"
    db_file = tmp_path / "test.db"
    store = SQLiteStore(db_file)
    await store.connect()

    vault = MemoryVault(vault_dir, store)
    await vault.bootstrap()

    await vault.save_entry("user_name", "Mohith", category="profile")
    await vault.save_entry("ide", "VS Code", category="preference")

    summary = await vault.get_context_summary()
    assert "### Profile" in summary
    assert "- **user_name**: Mohith" in summary
    assert "### Preference" in summary
    assert "- **ide**: VS Code" in summary

    # Verify build_system_prompt includes memory context
    prompt = build_system_prompt(None, memory_context=summary)
    assert "# Memory & User Context:" in prompt
    assert "- **user_name**: Mohith" in prompt

    await store.close()


@pytest.mark.asyncio
async def test_memory_tools_execution(tmp_path: Path):
    vault_dir = tmp_path / "memory_vault"
    db_file = tmp_path / "test.db"
    store = SQLiteStore(db_file)
    await store.connect()

    vault = MemoryVault(vault_dir, store)
    await vault.bootstrap()

    save_tool = MemorySaveTool(vault)
    read_tool = MemoryReadTool(vault)
    search_tool = MemorySearchTool(vault)
    list_tool = MemoryListTool(vault)

    # 1. Save
    s_args = save_tool.input_schema.model_validate({
        "key": "os_target",
        "content": "Windows 11",
        "category": "fact",
    })
    s_res = await save_tool.execute(s_args)
    assert s_res.success is True
    assert s_res.verified is True

    # 2. Read
    r_args = read_tool.input_schema.model_validate({"key": "os_target"})
    r_res = await read_tool.execute(r_args)
    assert r_res.success is True
    assert r_res.output["content"] == "Windows 11"

    # 3. Search
    sr_args = search_tool.input_schema.model_validate({"query": "Windows"})
    sr_res = await search_tool.execute(sr_args)
    assert sr_res.success is True
    assert sr_res.output["count"] == 1

    # 4. List
    l_args = list_tool.input_schema.model_validate({})
    l_res = await list_tool.execute(l_args)
    assert l_res.success is True
    assert l_res.output["count"] == 1

    await store.close()


@pytest.mark.asyncio
async def test_rpc_memory_methods(tmp_path: Path):
    db_file = tmp_path / "rpc_mem.db"
    store = SQLiteStore(db_file)
    await store.connect()

    settings = SarathiSettings.load(Path("config/default.toml"))
    settings.memory.vault_path = tmp_path / "vault"

    mock_ws = MagicMock()
    mock_ws.send_text = AsyncMock()

    rpc = RPCConnection(mock_ws, store, settings)
    await rpc.vault.bootstrap()

    # 1. memory.save
    save_req = {
        "jsonrpc": "2.0",
        "method": "memory.save",
        "params": {
            "key": "preferred_model",
            "content": "qwen3:4b",
            "category": "preference",
        },
        "id": 1,
    }
    await rpc.handle_message(json.dumps(save_req))
    resp = json.loads(mock_ws.send_text.call_args[0][0])
    assert resp["result"]["status"] == "ok"
    assert resp["result"]["entry"]["key"] == "preferred_model"

    # 2. memory.list
    mock_ws.send_text.reset_mock()
    list_req = {"jsonrpc": "2.0", "method": "memory.list", "params": {}, "id": 2}
    await rpc.handle_message(json.dumps(list_req))
    resp = json.loads(mock_ws.send_text.call_args[0][0])
    assert resp["result"]["count"] == 1
    assert resp["result"]["entries"][0]["key"] == "preferred_model"

    # 3. memory.search
    mock_ws.send_text.reset_mock()
    search_req = {
        "jsonrpc": "2.0",
        "method": "memory.search",
        "params": {"query": "qwen"},
        "id": 3,
    }
    await rpc.handle_message(json.dumps(search_req))
    resp = json.loads(mock_ws.send_text.call_args[0][0])
    assert resp["result"]["count"] == 1
    assert resp["result"]["results"][0]["key"] == "preferred_model"

    await store.close()
