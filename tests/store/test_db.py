"""Tests for SQLite persistence layer."""

import json
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.store.db import ReviewRepo, FeedbackRepo, migrate_from_json
from src.core.types import Finding, Location


@pytest.fixture
def tmp_db_path():
    td = tempfile.mkdtemp()
    p = Path(td) / "test_reviews.db"
    yield p
    # Clean up
    try:
        p.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        Path(td).rmdir()
    except Exception:
        pass


@pytest.fixture
def repo(tmp_db_path):
    r = ReviewRepo(path=str(tmp_db_path))
    yield r
    r.close()
    # Ensure file is released
    try:
        tmp_db_path.unlink(missing_ok=True)
    except Exception:
        pass


@pytest.fixture
def sample_findings():
    return [
        Finding(
            severity="high", category="security",
            location=Location(file="auth.py", line=42),
            title="SQL injection risk", description="Unsanitized input in query.",
            suggestion="Use parameterized queries.", confidence=0.9,
            evidence='query = f"SELECT * FROM users WHERE id={user_id}"',
            analyzer="security", classification="new",
        ),
        Finding(
            severity="medium", category="bug",
            location=Location(file="utils.py", line=15),
            title="Possible None reference", description="Variable may be None.",
            suggestion="Add null check.", confidence=0.7,
            evidence="result = data.process()",
            analyzer="llm", classification="new",
        ),
    ]


class TestReviewRepo:
    def test_creates_tables_on_init(self, tmp_db_path):
        r = ReviewRepo(path=str(tmp_db_path))
        tables = r._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {t[0] for t in tables}
        assert "review_runs" in table_names
        assert "findings" in table_names
        r.close()

    def test_save_review_returns_run_id(self, repo, sample_findings):
        run_id = repo.save_review(
            "https://github.com/owner/repo/pull/42",
            "Test PR", "owner/repo", sample_findings,
            risk_score=45, mode="balanced", categories="all",
        )
        assert run_id > 0

    def test_save_and_retrieve_history(self, repo, sample_findings):
        repo.save_review(
            "https://github.com/owner/repo/pull/1",
            "PR One", "owner/repo", sample_findings,
            risk_score=30, mode="fast", categories="security",
        )
        repo.save_review(
            "https://github.com/owner/repo/pull/2",
            "PR Two", "owner/repo", sample_findings[:1],
            risk_score=60, mode="deep", categories="all",
        )
        rows = repo.get_history(repo="owner/repo", limit=10)
        assert len(rows) == 2
        assert rows[0]["pr_title"] == "PR Two"  # most recent first
        assert rows[1]["pr_title"] == "PR One"

    def test_history_filter_by_repo(self, repo, sample_findings):
        repo.save_review(
            "https://github.com/a/b/pull/1", "A", "a/b", sample_findings)
        repo.save_review(
            "https://github.com/x/y/pull/2", "B", "x/y", sample_findings[:1])
        rows_a = repo.get_history(repo="a/b", limit=10)
        rows_x = repo.get_history(repo="x/y", limit=10)
        assert len(rows_a) == 1
        assert len(rows_x) == 1

    def test_history_limit(self, repo, sample_findings):
        for i in range(5):
            repo.save_review(
                f"https://github.com/o/r/pull/{i}", f"PR {i}",
                "o/r", sample_findings[:1])
        rows = repo.get_history(limit=3)
        assert len(rows) == 3

    def test_get_findings(self, repo, sample_findings):
        run_id = repo.save_review(
            "https://github.com/o/r/pull/1", "PR", "o/r", sample_findings)
        findings = repo.get_findings(run_id)
        assert len(findings) == len(sample_findings)
        assert findings[0]["severity"] == "high"
        assert findings[0]["category"] == "security"

    def test_empty_history(self, repo):
        rows = repo.get_history()
        assert rows == []


class TestFeedbackRepo:
    def test_save_and_retrieve_feedback(self, tmp_db_path):
        r = FeedbackRepo(path=str(tmp_db_path))
        r.mark("abc123", "tp", "alice", "Confirmed real bug")
        import time
        time.sleep(0.01)
        r.mark("abc123", "fp", "bob", "Actually a false positive")
        history = r.get_history("abc123")
        assert len(history) == 2
        # most recent first
        states = {h["state"] for h in history}
        assert "tp" in states
        assert "fp" in states
        r.close()

    def test_get_state_returns_latest(self, tmp_db_path):
        r = FeedbackRepo(path=str(tmp_db_path))
        r.mark("fp1", "tp", "alice", "")
        r.mark("fp1", "wont_fix", "bob", "Not worth fixing")
        assert r.get_state("fp1") == "wont_fix"
        r.close()

    def test_get_state_unknown_returns_unmarked(self, tmp_db_path):
        r = FeedbackRepo(path=str(tmp_db_path))
        assert r.get_state("unknown_fp") == "unmarked"
        r.close()

    def test_is_known_fp(self, tmp_db_path):
        r = FeedbackRepo(path=str(tmp_db_path))
        r.mark("fp_x", "fp", "alice", "")
        assert r.is_known_fp("fp_x") is True
        assert r.is_known_fp("fp_y") is False
        r.close()

    def test_is_known_fp_only_for_fp_state(self, tmp_db_path):
        r = FeedbackRepo(path=str(tmp_db_path))
        r.mark("fp_z", "tp", "alice", "")
        assert r.is_known_fp("fp_z") is False
        r.close()


class TestMigrateFromJson:
    def test_migrate_empty_state(self, tmp_db_path):
        state_dir = tmp_db_path.parent / ".ai-pr-reviewer"
        state_dir.mkdir(exist_ok=True)
        state_file = state_dir / "state.json"
        state_file.write_text(json.dumps({}), encoding="utf-8")

        result = migrate_from_json(str(state_file), str(tmp_db_path))
        assert "no data" in result.lower() or "migrated 0" in result.lower()

    def test_migrate_with_data(self, tmp_db_path):
        state_dir = tmp_db_path.parent / ".ai-pr-reviewer"
        state_dir.mkdir(exist_ok=True)
        state_file = state_dir / "state.json"
        data = {
            "42": {"sha": "abc123", "findings": 5, "reviewed_at": "2025-01-01T00:00:00Z"},
            "99": {"sha": "def456", "findings": 3, "reviewed_at": "2025-01-02T00:00:00Z"},
        }
        state_file.write_text(json.dumps(data), encoding="utf-8")

        result = migrate_from_json(str(state_file), str(tmp_db_path))
        assert "migrated" in result.lower()

    def test_migrate_missing_file(self, tmp_db_path):
        result = migrate_from_json("/nonexistent/state.json", str(tmp_db_path))
        assert "not found" in result.lower() or "0" in result.lower()
