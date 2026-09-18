PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY, started_at REAL, title TEXT
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY, session_id TEXT, ordinal INTEGER,
  role TEXT, content TEXT, trust TEXT, created_at REAL
);

-- Facts get provenance and validity intervals from day one. Retrofitting
-- these is painful; adding them now costs you four extra columns.
CREATE TABLE IF NOT EXISTS facts (
  id INTEGER PRIMARY KEY,
  subject TEXT NOT NULL, predicate TEXT NOT NULL, object TEXT NOT NULL,
  confidence REAL DEFAULT 0.5,
  source_type TEXT NOT NULL,          -- user_stated | inferred | document | web
  trust TEXT NOT NULL DEFAULT 'trusted',
  valid_from REAL NOT NULL, valid_to REAL,
  superseded_by INTEGER REFERENCES facts(id),
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_facts_subj ON facts(subject) WHERE valid_to IS NULL;

CREATE TABLE IF NOT EXISTS usage_log (
  id INTEGER PRIMARY KEY, ts REAL, session_id TEXT, model TEXT,
  task_type TEXT, tokens_in INTEGER, tokens_out INTEGER,
  cost_inr REAL, latency_ms INTEGER, ok INTEGER
);
