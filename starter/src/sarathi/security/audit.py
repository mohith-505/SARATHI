"""Append-only record of every tool call and every decision. Never deleted."""
from __future__ import annotations
import json, sqlite3, time
from pathlib import Path


class Audit:
    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS audit(
            id INTEGER PRIMARY KEY, ts REAL, session_id TEXT, tool TEXT,
            args TEXT, decision TEXT, reason TEXT)""")
        self.db.commit()

    def log(self, ctx, call, decision: str, reason: str) -> None:
        self.db.execute(
            "INSERT INTO audit(ts,session_id,tool,args,decision,reason) VALUES(?,?,?,?,?,?)",
            (time.time(), ctx.session_id, call.name,
             json.dumps(call.args)[:4000], decision, reason))
        self.db.commit()

    def recent(self, n: int = 20):
        return self.db.execute(
            "SELECT ts,tool,decision,reason FROM audit ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
