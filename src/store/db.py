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
                pr_author TEXT,
                base_sha TEXT,
                head_sha TEXT,
                files_count INTEGER DEFAULT 0,
                lines_added INTEGER DEFAULT 0,
                lines_deleted INTEGER DEFAULT 0,
                findings_count INTEGER DEFAULT 0,
                risk_score INTEGER DEFAULT 0,
                llm_provider TEXT,
                llm_model TEXT,
                prompt_version TEXT,
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
                lifecycle_state TEXT DEFAULT 'detected',
                FOREIGN KEY (review_run_id) REFERENCES review_runs(id)
            );
            CREATE TABLE IF NOT EXISTS review_run_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_run_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                status TEXT,
                language TEXT,
                additions INTEGER DEFAULT 0,
                deletions INTEGER DEFAULT 0,
                is_binary BOOLEAN DEFAULT FALSE,
                analyzed BOOLEAN DEFAULT TRUE,
                skip_reason TEXT,
                FOREIGN KEY (review_run_id) REFERENCES review_runs(id)
            );
            CREATE TABLE IF NOT EXISTS prompt_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                version TEXT NOT NULL,
                system_prompt_hash TEXT,
                created_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            );
            CREATE TABLE IF NOT EXISTS model_usages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_run_id INTEGER NOT NULL,
                model TEXT,
                provider TEXT,
                call_count INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                total_latency_ms INTEGER DEFAULT 0,
                cost_estimate REAL DEFAULT 0.0,
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

    def save_run_files(self, run_id: int, files: list):
        """Record per-file metadata for a review run."""
        for fc in files:
            self._conn.execute(
                "INSERT INTO review_run_files (review_run_id, path, status, language, additions, deletions, is_binary, analyzed) VALUES (?,?,?,?,?,?,?,?)",
                (run_id, fc.path, fc.status, fc.language or "",
                 fc.additions, fc.deletions, fc.is_binary, not fc.is_binary)
            )
        self._conn.commit()

    def save_model_usage(self, run_id: int, model: str, provider: str,
                         call_count: int = 0, total_tokens: int = 0,
                         total_latency_ms: int = 0):
        """Record LLM usage for a review run."""
        self._conn.execute(
            "INSERT INTO model_usages (review_run_id, model, provider, call_count, total_tokens, total_latency_ms) VALUES (?,?,?,?,?,?)",
            (run_id, model, provider, call_count, total_tokens, total_latency_ms)
        )
        self._conn.commit()

    def get_run_files(self, run_id: int) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM review_run_files WHERE review_run_id=?",
            (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_model_usage(self, run_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM model_usages WHERE review_run_id=?",
            (run_id,)
        ).fetchone()
        return dict(row) if row else None

    def close(self):
        self._conn.close()


def _make_fingerprint(finding) -> str:
    import hashlib
    key = f"{finding.location.file}:{finding.location.line}:{finding.title}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]
