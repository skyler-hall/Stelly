"""
The job tracker's SQLite storage layer.

Implements the locked data model: applications keyed by company name for
lookup, role captured at creation time but never used for matching, a
seen set of Gmail message IDs so no email is ever processed twice, and a
needs_review flag for the ambiguous cases that get kicked to Skyler
instead of guessed at.

Everything here is plain sqlite3 from the standard library, one file on
disk, local only, matching the project's local first principle.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tracker.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL COLLATE NOCASE,
    role TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'applied',
    needs_review INTEGER NOT NULL DEFAULT 0,
    review_reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER REFERENCES applications(id),
    message_id TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'email',
    subject TEXT NOT NULL DEFAULT '',
    sender TEXT NOT NULL DEFAULT '',
    occurred_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS seen_messages (
    message_id TEXT PRIMARY KEY
);
"""


def _now():
    return datetime.now(timezone.utc).isoformat()


class TrackerStore:
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

    # ---- seen set: the dedup guarantee ----

    def is_seen(self, message_id):
        row = self._conn.execute(
            "SELECT 1 FROM seen_messages WHERE message_id = ?", (message_id,)
        ).fetchone()
        return row is not None

    def mark_seen(self, message_id):
        self._conn.execute(
            "INSERT OR IGNORE INTO seen_messages (message_id) VALUES (?)",
            (message_id,),
        )
        self._conn.commit()

    # ---- applications ----

    def add_application(self, company, role="", status="applied"):
        """Create a new application row and return its id. Role is stored
        now because this is the only moment it is reliably known, but per
        the locked model it is never used as a matching key later."""
        now = _now()
        cursor = self._conn.execute(
            "INSERT INTO applications (company, role, status, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (company, role, status, now, now),
        )
        self._conn.commit()
        return cursor.lastrowid

    def find_by_company(self, company):
        """All applications for a company, case insensitive, newest first.
        Company name is the primary lookup key of the whole tracker."""
        rows = self._conn.execute(
            "SELECT * FROM applications WHERE company = ? ORDER BY id DESC",
            (company,),
        ).fetchall()
        return [dict(row) for row in rows]

    def update_status(self, application_id, status):
        self._conn.execute(
            "UPDATE applications SET status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), application_id),
        )
        self._conn.commit()

    def flag_for_review(self, application_id, reason):
        """Mark an application as needing Skyler's manual eyes instead of
        an automatic guess. Ambiguity gets flagged, never resolved by code."""
        self._conn.execute(
            "UPDATE applications SET needs_review = 1, review_reason = ?,"
            " updated_at = ? WHERE id = ?",
            (reason, _now(), application_id),
        )
        self._conn.commit()

    def needing_review(self):
        rows = self._conn.execute(
            "SELECT * FROM applications WHERE needs_review = 1 ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]

    def all_applications(self):
        rows = self._conn.execute(
            "SELECT * FROM applications ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    # ---- events: the paper trail ----

    def add_event(self, application_id, message_id="", kind="email",
                  subject="", sender=""):
        cursor = self._conn.execute(
            "INSERT INTO events (application_id, message_id, kind, subject,"
            " sender, occurred_at) VALUES (?, ?, ?, ?, ?, ?)",
            (application_id, message_id, kind, subject, sender, _now()),
        )
        self._conn.commit()
        return cursor.lastrowid

    def events_for(self, application_id):
        rows = self._conn.execute(
            "SELECT * FROM events WHERE application_id = ? ORDER BY id",
            (application_id,),
        ).fetchall()
        return [dict(row) for row in rows]
