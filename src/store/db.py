"""SQLite persistence for review results."""

import sqlite3
import json
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


def _make_fingerprint(finding) -> str:
    import hashlib
    key = f"{finding.location.file}:{finding.location.line}:{finding.title}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]
