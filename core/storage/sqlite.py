"""SQLite persistence for SARATHI (Phase 1 Lean: SQLite first, vector memory deferred)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

from core.logging.logger import get_logger
from core.types.messages import Message, Role

log = get_logger("storage.sqlite")

# MIGRATIONS
MIGRATIONS = [
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        name TEXT,
        timestamp TEXT NOT NULL,
        metadata TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages (session_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS memory_entries (
        key TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        content TEXT NOT NULL,
        source_file TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_memory_category ON memory_entries (category);
    """
]


class SQLiteStore:
    """Manages persistent sessions and messages."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Initialize the database connection and run migrations."""
        if self._conn is not None:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        # Enable foreign keys
        await self._conn.execute("PRAGMA foreign_keys = ON;")
        await self._run_migrations()

    async def _ensure_connected(self) -> None:
        """Ensure connection is established even if startup handler wasn't invoked."""
        if self._conn is None:
            await self.connect()

    async def _run_migrations(self) -> None:
        if not self._conn:
            return
        try:
            for stmt in MIGRATIONS:
                await self._conn.execute(stmt)
            await self._conn.commit()
            log.info("Database migrations applied successfully.")
        except Exception as e:
            log.exception("Failed to run migrations.")
            raise e

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def ensure_session(self, session_id: str, title: str | None = None) -> None:
        """Ensure a session exists before inserting messages."""
        await self._ensure_connected()
        assert self._conn is not None
        now_str = datetime.now(UTC).isoformat()
        default_title = "Default Session" if session_id == "default" else "New Session"
        stmt = (
            "INSERT OR IGNORE INTO sessions (id, title, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)"
        )
        await self._conn.execute(
            stmt,
            (session_id, title or default_title, now_str, now_str),
        )
        await self._conn.commit()

    async def create_session(self, session_id: str, title: str = "New Session") -> None:
        await self._ensure_connected()
        assert self._conn is not None
        now_str = datetime.now(UTC).isoformat()
        stmt = (
            "INSERT INTO sessions (id, title, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)"
        )
        await self._conn.execute(
            stmt,
            (session_id, title, now_str, now_str),
        )
        await self._conn.commit()

    async def save_message(self, session_id: str, message: Message) -> None:
        await self._ensure_connected()
        assert self._conn is not None

        await self.ensure_session(session_id)

        metadata_str = json.dumps(message.metadata, ensure_ascii=False)
        timestamp_str = message.timestamp.isoformat()
        await self._conn.execute(
            """
            INSERT INTO messages (session_id, role, content, name, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                message.role.value,
                message.content,
                message.name,
                timestamp_str,
                metadata_str,
            ),
        )
        await self._conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (timestamp_str, session_id),
        )
        await self._conn.commit()

    async def get_messages(self, session_id: str) -> list[Message]:
        await self._ensure_connected()
        assert self._conn is not None

        query = (
            "SELECT role, content, name, timestamp, metadata FROM messages "
            "WHERE session_id = ? ORDER BY id ASC"
        )
        async with self._conn.execute(query, (session_id,)) as cursor:
            rows = await cursor.fetchall()

        messages = []
        for role_val, content, name, ts, metadata_str in rows:
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    ts = datetime.now(UTC)
            elif isinstance(ts, datetime):
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)

            messages.append(
                Message(
                    role=Role(role_val),
                    content=content,
                    name=name,
                    timestamp=ts,
                    metadata=json.loads(metadata_str),
                )
            )
        return messages

    async def list_sessions(self) -> list[dict[str, Any]]:
        await self._ensure_connected()
        assert self._conn is not None

        async with self._conn.execute(
            "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()

        return [
            {"id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3]}
            for r in rows
        ]

    # --- Memory Store Operations ---

    async def save_memory_entry(
        self, key: str, category: str, content: str, source_file: str
    ) -> None:
        """Upsert a memory entry into SQLite."""
        await self._ensure_connected()
        assert self._conn is not None
        now_str = datetime.now(UTC).isoformat()
        stmt = """
        INSERT INTO memory_entries (key, category, content, source_file, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            category = excluded.category,
            content = excluded.content,
            source_file = excluded.source_file,
            updated_at = excluded.updated_at
        """
        await self._conn.execute(stmt, (key, category, content, source_file, now_str))
        await self._conn.commit()

    async def get_memory_entry(self, key: str) -> dict[str, Any] | None:
        """Retrieve a memory entry by key."""
        await self._ensure_connected()
        assert self._conn is not None
        stmt = (
            "SELECT key, category, content, source_file, updated_at "
            "FROM memory_entries WHERE key = ?"
        )
        async with self._conn.execute(stmt, (key,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            return None
        return {
            "key": row[0],
            "category": row[1],
            "content": row[2],
            "source_file": row[3],
            "updated_at": row[4],
        }

    async def list_memory_entries(self, category: str | None = None) -> list[dict[str, Any]]:
        """List memory entries, optionally filtered by category."""
        await self._ensure_connected()
        assert self._conn is not None
        if category:
            stmt = (
                "SELECT key, category, content, source_file, updated_at "
                "FROM memory_entries WHERE category = ? ORDER BY key ASC"
            )
            params: tuple[Any, ...] = (category,)
        else:
            stmt = (
                "SELECT key, category, content, source_file, updated_at "
                "FROM memory_entries ORDER BY category ASC, key ASC"
            )
            params = ()
        async with self._conn.execute(stmt, params) as cursor:
            rows = await cursor.fetchall()
        return [
            {
                "key": r[0],
                "category": r[1],
                "content": r[2],
                "source_file": r[3],
                "updated_at": r[4],
            }
            for r in rows
        ]

    async def search_memory_entries(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search memory entries by key or content substring."""
        await self._ensure_connected()
        assert self._conn is not None
        search_pattern = f"%{query}%"
        stmt = """
        SELECT key, category, content, source_file, updated_at FROM memory_entries
        WHERE key LIKE ? OR content LIKE ?
        ORDER BY updated_at DESC
        LIMIT ?
        """
        async with self._conn.execute(stmt, (search_pattern, search_pattern, limit)) as cursor:
            rows = await cursor.fetchall()
        return [
            {
                "key": r[0],
                "category": r[1],
                "content": r[2],
                "source_file": r[3],
                "updated_at": r[4],
            }
            for r in rows
        ]

    async def delete_memory_entry(self, key: str) -> bool:
        """Delete a memory entry by key."""
        await self._ensure_connected()
        assert self._conn is not None
        stmt = "DELETE FROM memory_entries WHERE key = ?"
        cursor = await self._conn.execute(stmt, (key,))
        await self._conn.commit()
        return cursor.rowcount > 0
