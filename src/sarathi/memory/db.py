import sqlite3
from pathlib import Path

def init_db(db_path: str, schema_path: str) -> sqlite3.Connection:
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(p)
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = f.read()
    conn.executescript(schema)
    return conn
