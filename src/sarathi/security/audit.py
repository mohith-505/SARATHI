import sqlite3
import time
from sarathi.core.types import Context, ToolCall

class AuditLogger:
    def __init__(self, db_conn: sqlite3.Connection):
        self.db_conn = db_conn
        self._init_db()

    def _init_db(self):
        self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY,
                ts REAL,
                session_id TEXT,
                tool_name TEXT,
                args_json TEXT,
                decision TEXT,
                reason TEXT
            )
        """)
        self.db_conn.commit()

    def log(self, ctx: Context, call: ToolCall, decision: str, reason: str):
        import json
        args_str = json.dumps(call.args)
        self.db_conn.execute(
            """INSERT INTO audit_log (ts, session_id, tool_name, args_json, decision, reason)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (time.time(), ctx.session_id, call.name, args_str, decision, reason)
        )
        self.db_conn.commit()
