"""Build a ToolRegistry from settings."""

from __future__ import annotations

from pathlib import Path

from core.config.settings import ToolsConfig
from core.logging.logger import get_logger
from core.memory.vault import MemoryVault
from tools.filesystem.list import FileListTool
from tools.filesystem.mkdir import MakeDirTool
from tools.filesystem.read import FileReadTool
from tools.filesystem.write import FileWriteTool
from tools.registry import ToolRegistry
from tools.system.app_launch import AppLaunchTool
from tools.system.system_info import SystemInfoTool
from tools.system.time_date import TimeDateTool
from tools.terminal.safe_command import SafeCommandTool
from tools.web.search import WebSearchTool

log = get_logger("tools.factory")


def build_registry(cfg: ToolsConfig, vault: MemoryVault | None = None) -> ToolRegistry:
    """Build the default tool registry based on configuration."""
    registry = ToolRegistry()
    if not cfg.enabled:
        log.info("Tools disabled by configuration.")
        return registry

    roots: list[Path] = [Path(r).expanduser() for r in cfg.allowed_roots]

    registry.register(SystemInfoTool())
    registry.register(TimeDateTool())
    registry.register(AppLaunchTool())

    read_tool = FileReadTool(roots)
    registry.register(read_tool)
    registry.register_alias("fs.read", read_tool)

    list_tool = FileListTool(roots)
    registry.register(list_tool)
    registry.register_alias("filesystem_list", list_tool)

    write_tool = FileWriteTool(roots)
    registry.register(write_tool)
    registry.register_alias("fs.write", write_tool)

    mkdir_tool = MakeDirTool(roots)
    registry.register(mkdir_tool)
    registry.register_alias("fs.mkdir", mkdir_tool)

    registry.register(SafeCommandTool())

    if cfg.web_search_enabled:
        search_tool = WebSearchTool()
        registry.register(search_tool)
        registry.register_alias("web.search", search_tool)
    else:
        log.info("Web search disabled by configuration.")

    if vault is not None:
        from tools.memory.list import MemoryListTool
        from tools.memory.read import MemoryReadTool
        from tools.memory.save import MemorySaveTool
        from tools.memory.search import MemorySearchTool

        save_m = MemorySaveTool(vault)
        registry.register(save_m)
        registry.register_alias("memory.save", save_m)

        read_m = MemoryReadTool(vault)
        registry.register(read_m)
        registry.register_alias("memory.read", read_m)

        search_m = MemorySearchTool(vault)
        registry.register(search_m)
        registry.register_alias("memory.search", search_m)

        list_m = MemoryListTool(vault)
        registry.register(list_m)
        registry.register_alias("memory.list", list_m)

    try:
        from tools.google.calendar_read import CalendarReadTool
        from tools.google.gmail_read import GmailReadTool
        registry.register(GmailReadTool())
        registry.register(CalendarReadTool())
    except Exception as e:
        log.debug("Failed to register Google tools: %s", e)

    log.info("Registered %d tools: %s", len(registry), ", ".join(registry.names()))
    return registry
