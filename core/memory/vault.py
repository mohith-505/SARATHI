"""Transparent Markdown Memory Vault with SQLite Index for SARATHI.

Features:
- Pure Markdown vault compatible with Obsidian (.obsidian/app.json included).
- SQLite-backed full-text and key-based indexing for fast retrieval.
- Categorized storage: 'profile', 'preference', 'fact', 'project'.
- Strict path containment: model cannot target or mutate outside vault_path.
- Injects user profile & preferences dynamically into system prompts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.logging.logger import get_logger
from core.storage.sqlite import SQLiteStore

log = get_logger("memory.vault")

_SAFE_KEY_RE = re.compile(r"^[a-zA-Z0-9_\-\.]{1,64}$")

CATEGORY_FILES: dict[str, str] = {
    "profile": "user_profile.md",
    "preference": "preferences.md",
    "fact": "facts.md",
    "project": "projects.md",
}


class MemoryVault:
    def __init__(self, vault_path: Path, store: SQLiteStore):
        self.vault_path = vault_path.resolve()
        self.store = store

    async def bootstrap(self) -> None:
        """Create vault structure, Obsidian configuration, and default notes if absent."""
        self.vault_path.mkdir(parents=True, exist_ok=True)

        # Obsidian compatibility
        obsidian_dir = self.vault_path / ".obsidian"
        obsidian_dir.mkdir(exist_ok=True)
        app_json = obsidian_dir / "app.json"
        if not app_json.exists():
            app_json.write_text(
                json.dumps(
                    {
                        "alwaysUpdateLinks": True,
                        "newFileLocation": "root",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

        # Vault README
        readme = self.vault_path / "README.md"
        if not readme.exists():
            readme.write_text(
                "# SARATHI Knowledge Vault\n\n"
                "This directory contains transparent, human-auditable markdown memory.\n"
                "SARATHI reads and updates files here to remember user preferences, facts, "
                "and project context across sessions.\n\n"
                "You can open this folder directly as an Obsidian vault.\n",
                encoding="utf-8",
            )

        # Default markdown files
        defaults = {
            "user_profile.md": (
                "# User Profile\n\n"
                "Information about the user, role, and goals.\n\n"
            ),
            "preferences.md": (
                "# User Preferences\n\n"
                "User preferences for interaction, coding style, and workflow.\n\n"
            ),
            "facts.md": (
                "# Facts & Knowledge\n\n"
                "Verified facts and knowledge SARATHI has learned.\n\n"
            ),
            "projects.md": (
                "# Active Projects\n\n"
                "Current projects, directories, and development notes.\n\n"
            ),
        }

        for filename, template in defaults.items():
            fpath = self.vault_path / filename
            if not fpath.exists():
                fpath.write_text(template, encoding="utf-8")

        # Sync existing files into SQLite store
        await self._sync_markdown_to_sqlite()
        log.info("Memory vault bootstrapped at %s", self.vault_path)

    def _resolve_file_for_category(self, category: str) -> Path:
        cat = category.lower().strip()
        filename = CATEGORY_FILES.get(cat, "facts.md")
        target = (self.vault_path / filename).resolve()
        if not target.is_relative_to(self.vault_path):
            raise PermissionError("Access outside memory vault boundary is forbidden.")
        return target

    async def _sync_markdown_to_sqlite(self) -> None:
        """Parse structured sections from markdown files into SQLite store."""
        for cat, filename in CATEGORY_FILES.items():
            fpath = self.vault_path / filename
            if not fpath.exists():
                continue
            content = fpath.read_text(encoding="utf-8")
            # Parse sections: "### <key>\n<content>" or "- **<key>**: <content>"
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("- **") and "**:" in line:
                    parts = line[4:].split("**:", 1)
                    if len(parts) == 2:
                        k = parts[0].strip()
                        v = parts[1].strip()
                        if _SAFE_KEY_RE.match(k):
                            await self.store.save_memory_entry(k, cat, v, filename)

    async def save_entry(
        self, key: str, content: str, category: str = "fact"
    ) -> dict[str, Any]:
        """Save or update a memory entry in both Markdown and SQLite."""
        clean_key = key.strip()
        if not _SAFE_KEY_RE.match(clean_key):
            raise ValueError(
                f"Invalid memory key {key!r}. "
                "Must be alphanumeric, dashes, or underscores (1-64 chars)."
            )

        clean_cat = category.lower().strip()
        if clean_cat not in CATEGORY_FILES:
            clean_cat = "fact"

        clean_content = content.strip()
        if not clean_content:
            raise ValueError("Memory content cannot be empty.")

        target_file = self._resolve_file_for_category(clean_cat)
        rel_path = target_file.name

        # Update or append in markdown file
        existing_text = target_file.read_text(encoding="utf-8") if target_file.exists() else ""
        bullet_prefix = f"- **{clean_key}**:"
        new_bullet = f"- **{clean_key}**: {clean_content}"

        lines = existing_text.splitlines()
        found = False
        new_lines: list[str] = []
        for line in lines:
            if line.strip().startswith(bullet_prefix):
                new_lines.append(new_bullet)
                found = True
            else:
                new_lines.append(line)

        if not found:
            new_lines.append(new_bullet)

        target_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

        # Upsert in SQLite
        await self.store.save_memory_entry(clean_key, clean_cat, clean_content, rel_path)

        log.info("Saved memory entry [%s] under %s", clean_key, clean_cat)
        return {
            "key": clean_key,
            "category": clean_cat,
            "content": clean_content,
            "source_file": rel_path,
        }

    async def get_entry(self, key: str) -> dict[str, Any] | None:
        """Fetch a single memory entry by key."""
        clean_key = key.strip()
        return await self.store.get_memory_entry(clean_key)

    async def list_entries(self, category: str | None = None) -> list[dict[str, Any]]:
        """List all remembered entries, optionally filtered by category."""
        return await self.store.list_memory_entries(category)

    async def search_entries(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search remembered facts and preferences by keyword."""
        return await self.store.search_memory_entries(query, limit=limit)

    async def delete_entry(self, key: str) -> bool:
        """Delete an entry from SQLite and remove from its markdown file."""
        entry = await self.get_entry(key)
        if not entry:
            return False

        # Remove from SQLite
        await self.store.delete_memory_entry(key)

        # Remove bullet from markdown file
        fpath = self.vault_path / entry["source_file"]
        if fpath.exists():
            bullet_prefix = f"- **{key}**:"
            lines = [
                line
                for line in fpath.read_text(encoding="utf-8").splitlines()
                if not line.strip().startswith(bullet_prefix)
            ]
            fpath.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return True

    async def get_context_summary(self, max_chars: int = 1500) -> str:
        """Build a concise markdown summary of remembered context for system prompt injection."""
        entries = await self.store.list_memory_entries()
        if not entries:
            return ""

        by_cat: dict[str, list[dict[str, Any]]] = {}
        for e in entries:
            by_cat.setdefault(e["category"], []).append(e)

        parts: list[str] = []
        for cat in ("profile", "preference", "project", "fact"):
            items = by_cat.get(cat, [])
            if not items:
                continue
            cat_title = cat.capitalize()
            bullets = "\n".join(f"- **{it['key']}**: {it['content']}" for it in items)
            parts.append(f"### {cat_title}\n{bullets}")

        summary = "\n\n".join(parts)
        if len(summary) > max_chars:
            return summary[:max_chars] + "\n...[truncated]"
        return summary
