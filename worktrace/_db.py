"""
SQLite connection and schema management.
DB lives at ~/.worktrace/worktrace.db, WAL mode for safe concurrent writes.
"""

import sqlite3
from pathlib import Path

_DB_PATH = Path.home() / ".worktrace" / "worktrace.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'running',
    started_at  TEXT NOT NULL,
    ended_at    TEXT,
    tags        TEXT NOT NULL DEFAULT '[]',
    metadata    TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS events (
    id           TEXT PRIMARY KEY,
    run_id       TEXT,
    type         TEXT NOT NULL,
    resource_uri TEXT,
    timestamp    TEXT NOT NULL,
    data         TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE TABLE IF NOT EXISTS snapshots (
    id           TEXT PRIMARY KEY,
    run_id       TEXT,
    resource_uri TEXT NOT NULL,
    kind         TEXT NOT NULL,
    data         TEXT NOT NULL DEFAULT '{}',
    timestamp    TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE INDEX IF NOT EXISTS idx_events_run_id       ON events(run_id);
CREATE INDEX IF NOT EXISTS idx_events_resource_uri  ON events(resource_uri);
CREATE INDEX IF NOT EXISTS idx_events_type          ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp     ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_snapshots_resource   ON snapshots(resource_uri);
"""


def get_conn() -> sqlite3.Connection:
    """Return a WAL-mode connection to the worktrace database."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA)
    return conn
