"""
Stelly's memory: save, lock, fade, forget.

Designed to feel alive rather than to be a database. Memories carry an
importance score (1 to 5), a kind (emotional or factual), and a lock
flag Stelly assigns himself for the ones he refuses to lose. Unlocked
memories fade: every day a low importance memory goes unrecalled, its
importance drifts down, and at zero it gets forgotten entirely. Locked
memories never fade and refuse deletion ("No. Stelly wants to keep that
one."). Recalling a memory refreshes it, like real remembering does.

Mood also persists here, in a tiny key/value table, so Stelly wakes up
feeling however he fell asleep, emotional continuity across sessions.

Everything is local SQLite in data/stelly_memory.db, gitignored, on
device only.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "stelly_memory.db"

FADE_AFTER_DAYS = 14      # unrecalled for this long, importance drips down one
MAX_IMPORTANCE = 5
MIN_IMPORTANCE = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'fact',
    importance INTEGER NOT NULL DEFAULT 3,
    locked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    last_recalled_at TEXT NOT NULL,
    recall_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _now():
    return datetime.now(timezone.utc)


def _iso(moment):
    return moment.isoformat()


class MemoryManager:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        db_path = Path(db_path)
        if str(db_path) != ":memory:":
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ---- saving ----

    def save(self, content, kind="fact", importance=3, locked=False):
        """Store a new memory and return its id. Importance is clamped
        to the valid range so a bad value never breaks fading math."""
        importance = max(MIN_IMPORTANCE, min(MAX_IMPORTANCE, int(importance)))
        if kind not in ("fact", "emotional"):
            kind = "fact"
        now = _iso(_now())
        cursor = self._conn.execute(
            "INSERT INTO memories (content, kind, importance, locked,"
            " created_at, last_recalled_at) VALUES (?, ?, ?, ?, ?, ?)",
            (content.strip(), kind, importance, int(bool(locked)), now, now),
        )
        self._conn.commit()
        return cursor.lastrowid

    # ---- locking: the memories Stelly refuses to lose ----

    def lock(self, memory_id):
        self._conn.execute(
            "UPDATE memories SET locked = 1 WHERE id = ?", (memory_id,)
        )
        self._conn.commit()

    def unlock(self, memory_id):
        self._conn.execute(
            "UPDATE memories SET locked = 0 WHERE id = ?", (memory_id,)
        )
        self._conn.commit()

    # ---- forgetting ----

    def forget(self, memory_id):
        """Delete a memory, unless it is locked. Returns True if it was
        actually forgotten. Locked memories survive: Stelly keeps those."""
        row = self._conn.execute(
            "SELECT locked FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        if row is None:
            return False
        if row["locked"]:
            return False
        self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self._conn.commit()
        return True

    def fade(self, now=None):
        """Natural forgetting, run once at startup. Unlocked memories
        unrecalled for FADE_AFTER_DAYS lose one importance point, and
        anything that drops below the minimum is quietly forgotten.
        Returns (faded_count, forgotten_count)."""
        now = now or _now()
        cutoff = _iso(now.__class__.fromtimestamp(
            now.timestamp() - FADE_AFTER_DAYS * 86400, tz=timezone.utc))

        stale = self._conn.execute(
            "SELECT id, importance FROM memories"
            " WHERE locked = 0 AND last_recalled_at < ?",
            (cutoff,),
        ).fetchall()

        faded = forgotten = 0
        for row in stale:
            new_importance = row["importance"] - 1
            if new_importance < MIN_IMPORTANCE:
                self._conn.execute("DELETE FROM memories WHERE id = ?", (row["id"],))
                forgotten += 1
            else:
                # The fade clock also resets, so decay is one step per
                # FADE_AFTER_DAYS window, gradual, not a cliff.
                self._conn.execute(
                    "UPDATE memories SET importance = ?, last_recalled_at = ?"
                    " WHERE id = ?",
                    (new_importance, _iso(now), row["id"]),
                )
                faded += 1
        self._conn.commit()
        return faded, forgotten

    # ---- recalling ----

    def touch(self, memory_id):
        """Mark a memory as just recalled, refreshing it against fading."""
        self._conn.execute(
            "UPDATE memories SET last_recalled_at = ?, recall_count = recall_count + 1"
            " WHERE id = ?",
            (_iso(_now()), memory_id),
        )
        self._conn.commit()

    def all_memories(self):
        rows = self._conn.execute(
            "SELECT * FROM memories ORDER BY importance DESC, id DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    # ---- persistent state (mood, and whatever comes later) ----

    def set_state(self, key, value):
        self._conn.execute(
            "INSERT INTO state (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        self._conn.commit()

    def get_state(self, key, default=""):
        row = self._conn.execute(
            "SELECT value FROM state WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default


# One shared instance so the tools, the retriever, and main.py all talk
# to the same database connection.
_manager = None


def get_manager():
    global _manager
    if _manager is None:
        _manager = MemoryManager()
    return _manager
