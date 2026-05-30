"""SQLite persistence for review results, findings, and feedback."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_PATH = ".ai-pr-reviewer/reviews.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReviewRepo:
    def __init__(self, path: str = _DEFAULT_PATH):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS review_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pr_url TEXT NOT NULL,
                pr_title TEXT,
                repo TEXT,
                findings_count INTEGER DEFAULT 0,
                risk_score INTEGER DEFAULT 0,
                mode TEXT DEFAULT 'balanced',
                categories TEXT DEFAULT 'all',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_run_id INTEGER NOT NULL,
                severity TEXT,
                category TEXT,
                classification TEXT DEFAULT 'new',
                title TEXT,
                file TEXT,
                line INTEGER,
                confidence REAL,
                evidence TEXT,
                suggestion TEXT,
                fix_patch TEXT,
                fingerprint TEXT,
                FOREIGN KEY (review_run_id) REFERENCES review_runs(id)
            );
        """)
        self._conn.commit()

    def save_review(self, pr_url: str, pr_title: str, repo: str,
                    findings: list, risk_score: int = 0,
                    mode: str = "balanced",
                    categories: str = "all") -> int:
        cur = self._conn.execute(
            "INSERT INTO review_runs (pr_url, pr_title, repo, findings_count, risk_score, mode, categories, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (pr_url, pr_title, repo, len(findings), risk_score, mode, categories, _now())
        )
        run_id = cur.lastrowid
        for f in findings:
            self._conn.execute(
                "INSERT INTO findings (review_run_id, severity, category, classification, title, file, line, confidence, evidence, suggestion, fix_patch, fingerprint) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (run_id, f.severity, f.category, f.classification,
                 f.title, f.location.file, f.location.line,
                 f.confidence, f.evidence, f.suggestion, f.fix_patch,
                 _make_fingerprint(f))
            )
        self._conn.commit()
        return run_id

    def get_history(self, repo: str = "", limit: int = 20) -> list[dict]:
        if repo:
            rows = self._conn.execute(
                "SELECT * FROM review_runs WHERE repo=? ORDER BY created_at DESC LIMIT ?",
                (repo, limit)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM review_runs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_findings(self, run_id: int) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM findings WHERE review_run_id=? ORDER BY severity, confidence DESC",
            (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self._conn.close()


class FeedbackRepo:
    """Persistent storage for user feedback on review findings."""

    def __init__(self, path: str = _DEFAULT_PATH):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS feedback_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'unmarked',
                user TEXT DEFAULT 'unknown',
                reason TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_feedback_fp
                ON feedback_events(fingerprint, created_at DESC);
        """)
        self._conn.commit()

    def mark(self, fingerprint: str, state: str, user: str = "unknown",
             reason: str = ""):
        self._conn.execute(
            "INSERT INTO feedback_events (fingerprint, state, user, reason, created_at) VALUES (?,?,?,?,?)",
            (fingerprint, state, user, reason, _now())
        )
        self._conn.commit()

    def get_state(self, fingerprint: str) -> str:
        row = self._conn.execute(
            "SELECT state FROM feedback_events WHERE fingerprint=? "
            "ORDER BY created_at DESC LIMIT 1",
            (fingerprint,)
        ).fetchone()
        return row["state"] if row else "unmarked"

    def get_history(self, fingerprint: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM feedback_events WHERE fingerprint=? "
            "ORDER BY created_at DESC",
            (fingerprint,)
        ).fetchall()
        return [dict(r) for r in rows]

    def is_known_fp(self, fingerprint: str) -> bool:
        return self.get_state(fingerprint) == "fp"

    def close(self):
        self._conn.close()


def _make_fingerprint(finding) -> str:
    import hashlib
    key = f"{finding.location.file}:{finding.location.line}:{finding.title}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def migrate_from_json(state_path: str, db_path: str = _DEFAULT_PATH) -> str:
    """Migrate review state from JSON to SQLite. Returns status message."""
    state_file = Path(state_path)
    if not state_file.exists():
        return f"State file not found: {state_path} — migrated 0 entries."

    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return f"State file {state_path} could not be read — migrated 0 entries."

    if not isinstance(data, dict) or not data:
        return "No data in state file — migrated 0 entries."

    migrated = 0
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS review_states (
                pr_number TEXT PRIMARY KEY,
                sha TEXT,
                findings_count INTEGER DEFAULT 0,
                reviewed_at TEXT
            );
        """)
        conn.commit()

        for pr_key, entry in data.items():
            if not isinstance(entry, dict):
                continue
            sha = entry.get("sha", "")
            findings = entry.get("findings", 0) or entry.get("findings_count", 0)
            reviewed_at = entry.get("reviewed_at", _now())
            conn.execute(
                "INSERT OR REPLACE INTO review_states (pr_number, sha, findings_count, reviewed_at) VALUES (?,?,?,?)",
                (str(pr_key), sha, findings, reviewed_at)
            )
            migrated += 1
        conn.commit()
    finally:
        conn.close()

    return f"Migrated {migrated} entries from {state_path} to {db_path}"
