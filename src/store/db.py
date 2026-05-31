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
        from src.store.schema import SCHEMA_SQL
        self._conn.executescript(SCHEMA_SQL)
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


# ── User & Auth Repos ────────────────────────

class UserRepo:
    """User account management — linked to GitHub identity."""

    def __init__(self, path: str = _DEFAULT_PATH):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row

    def find_or_create_by_github(self, github_id: int, login: str,
                                  name: str | None = None,
                                  email: str | None = None,
                                  avatar_url: str | None = None) -> dict:
        row = self._conn.execute(
            "SELECT * FROM users WHERE github_id=?", (github_id,)
        ).fetchone()
        if row:
            return dict(row)

        cur = self._conn.execute(
            "INSERT INTO users (github_id, login, name, email, avatar_url) VALUES (?,?,?,?,?)",
            (github_id, login, name, email, avatar_url)
        )
        self._conn.commit()
        return {"id": cur.lastrowid, "github_id": github_id, "login": login,
                "name": name, "email": email, "avatar_url": avatar_url}

    def find_by_id(self, user_id: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None

    def find_by_github_id(self, github_id: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM users WHERE github_id=?", (github_id,)).fetchone()
        return dict(row) if row else None

    def save_github_token(self, user_id: int, access_token: str,
                          scopes: str = "", expires_at: str | None = None):
        self._conn.execute(
            "INSERT OR REPLACE INTO github_tokens (user_id, access_token, scopes, expires_at) VALUES (?,?,?,?)",
            (user_id, access_token, scopes, expires_at)
        )
        self._conn.commit()

    def get_github_token(self, user_id: int) -> str | None:
        row = self._conn.execute(
            "SELECT access_token FROM github_tokens WHERE user_id=?", (user_id,)
        ).fetchone()
        return row["access_token"] if row else None

    def register_by_email(self, email: str, password: str, name: str = "") -> dict | None:
        import hashlib
        existing = self._conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            return None
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        cur = self._conn.execute(
            "INSERT INTO users (login, name, email, password_hash) VALUES (?,?,?,?)",
            (name or email.split("@")[0], name, email, pw_hash)
        )
        self._conn.commit()
        return {"id": cur.lastrowid, "login": name or email.split("@")[0], "email": email}

    def register_by_phone(self, phone: str, password: str, name: str = "") -> dict | None:
        import hashlib
        existing = self._conn.execute("SELECT id FROM users WHERE phone=?", (phone,)).fetchone()
        if existing:
            return None
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        cur = self._conn.execute(
            "INSERT INTO users (login, name, phone, password_hash) VALUES (?,?,?,?)",
            (name or phone, name, phone, pw_hash)
        )
        self._conn.commit()
        return {"id": cur.lastrowid, "login": name or phone, "phone": phone}

    def authenticate_by_email(self, email: str, password: str) -> dict | None:
        import hashlib
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        row = self._conn.execute(
            "SELECT * FROM users WHERE email=? AND password_hash=?", (email, pw_hash)
        ).fetchone()
        return dict(row) if row else None

    def authenticate_by_phone(self, phone: str, password: str) -> dict | None:
        import hashlib
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        row = self._conn.execute(
            "SELECT * FROM users WHERE phone=? AND password_hash=?", (phone, pw_hash)
        ).fetchone()
        return dict(row) if row else None

    def close(self):
        self._conn.close()


class SessionRepo:
    """JWT refresh token storage."""

    def __init__(self, path: str = _DEFAULT_PATH):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row

    def create(self, user_id: int, token_hash: str, expires_at: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO sessions (user_id, token_hash, expires_at) VALUES (?,?,?)",
            (user_id, token_hash, expires_at)
        )
        self._conn.commit()
        return cur.lastrowid

    def find_valid(self, token_hash: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE token_hash=? AND expires_at > datetime('now')",
            (token_hash,)
        ).fetchone()
        return dict(row) if row else None

    def revoke(self, token_hash: str):
        self._conn.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))
        self._conn.commit()

    def revoke_all_for_user(self, user_id: int):
        self._conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        self._conn.commit()

    def close(self):
        self._conn.close()


class AuditRepo:
    """Audit log for compliance and debugging."""

    def __init__(self, path: str = _DEFAULT_PATH):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row

    def log(self, user_id: int | None, action: str, resource: str = "",
            details: str = "", org_id: int | None = None):
        self._conn.execute(
            "INSERT INTO audit_logs (user_id, org_id, action, resource, details) VALUES (?,?,?,?,?)",
            (user_id, org_id, action, resource, details)
        )
        self._conn.commit()

    def get_trail(self, user_id: int | None = None, action: str = "",
                  limit: int = 100) -> list[dict]:
        q = "SELECT * FROM audit_logs WHERE 1=1"
        params = []
        if user_id:
            q += " AND user_id=?"
            params.append(user_id)
        if action:
            q += " AND action=?"
            params.append(action)
        q += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self._conn.execute(q, params).fetchall()]

    def close(self):
        self._conn.close()



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
