import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReviewState:
    """Track which PR commits have been reviewed to avoid duplicate reviews.
    Supports JSON file storage by default, with optional SQLite backend.
    """

    def __init__(self, path: str | None = None):
        if path is None:
            path = ".ai-pr-reviewer/state.json"
        self._path = Path(path)
        self._data: dict = self._load()

    def _load(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            text = self._path.read_text(encoding="utf-8")
            if not text.strip():
                return {}
            return json.loads(text)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def is_reviewed(self, pr_number: int, head_sha: str) -> bool:
        pr_key = str(pr_number)
        return self._data.get(pr_key, {}).get("sha") == head_sha

    def last_reviewed_sha(self, pr_number: int) -> str | None:
        pr_key = str(pr_number)
        entry = self._data.get(pr_key)
        return entry["sha"] if entry else None

    def mark_reviewed(self, pr_number: int, head_sha: str,
                      findings_count: int = 0):
        pr_key = str(pr_number)
        self._data[pr_key] = {
            "sha": head_sha,
            "findings": findings_count,
            "reviewed_at": _now_iso(),
        }
        self._save()


class ReviewStateSQLite:
    """SQLite-backed review state for team/shared deployments.

    Uses the same reviews.db as ReviewRepo for consistency.
    Falls back gracefully if SQLite is unavailable.
    """

    def __init__(self, db_path: str = ".ai-pr-reviewer/reviews.db"):
        import sqlite3
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn = sqlite3.connect(db_path)
            self._conn.row_factory = sqlite3.Row
            self._init_schema()
        except Exception:
            self._conn = None

    def _init_schema(self):
        if self._conn is None:
            return
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS review_states (
                pr_number TEXT PRIMARY KEY,
                sha TEXT NOT NULL,
                findings_count INTEGER DEFAULT 0,
                reviewed_at TEXT NOT NULL
            );
        """)
        self._conn.commit()

    def is_reviewed(self, pr_number: int, head_sha: str) -> bool:
        if self._conn is None:
            return False
        row = self._conn.execute(
            "SELECT sha FROM review_states WHERE pr_number=?",
            (str(pr_number),)
        ).fetchone()
        return row is not None and row["sha"] == head_sha

    def last_reviewed_sha(self, pr_number: int) -> str | None:
        if self._conn is None:
            return None
        row = self._conn.execute(
            "SELECT sha FROM review_states WHERE pr_number=?",
            (str(pr_number),)
        ).fetchone()
        return row["sha"] if row else None

    def mark_reviewed(self, pr_number: int, head_sha: str,
                      findings_count: int = 0):
        if self._conn is None:
            return
        self._conn.execute(
            "INSERT OR REPLACE INTO review_states (pr_number, sha, findings_count, reviewed_at) VALUES (?,?,?,?)",
            (str(pr_number), head_sha, findings_count, _now_iso())
        )
        self._conn.commit()

    def close(self):
        if self._conn is not None:
            self._conn.close()
