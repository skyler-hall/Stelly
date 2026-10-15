"""
SQLite storage for job listing alerts: just enough state to make repeated
runs idempotent.

notified_jobs remembers every listing id Skyler has actually been texted
about, from either source, so a posting that already went out never
triggers a second text. Deliberately its own database file rather than a
table bolted onto tracker.db: tracker.db is the Gmail application-status
tracker, a different concern (following up on applications already sent)
from this one (surfacing brand new postings), and the two shouldn't share
a schema just because both happen to be about jobs.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "job_alerts.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notified_jobs (
    job_id TEXT PRIMARY KEY,
    notified_at TEXT NOT NULL
);
"""


class JobAlertStore:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        db_path = Path(db_path)
        if str(db_path) != ":memory:":
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self):
        self._conn.close()

    def is_notified(self, job_id):
        row = self._conn.execute(
            "SELECT 1 FROM notified_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return row is not None

    def mark_notified(self, job_id):
        self._conn.execute(
            "INSERT OR IGNORE INTO notified_jobs (job_id, notified_at) VALUES (?, ?)",
            (job_id, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()
