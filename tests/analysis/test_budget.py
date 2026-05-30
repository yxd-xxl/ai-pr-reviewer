"""Tests for analysis budget system."""

import pytest
from src.analysis.budget import (
    AnalysisBudget, BudgetTracker, BudgetExceeded,
    estimate_tokens, rank_files_by_risk,
)
from src.core.types import FileChange


class TestAnalysisBudget:
    def test_default_values(self):
        b = AnalysisBudget()
        assert b.max_files == 20
        assert b.max_llm_calls == 60
        assert b.large_pr_threshold == 30

    def test_custom_values(self):
        b = AnalysisBudget(max_files=10, max_llm_calls=20,
                          max_tokens_estimate=10000, large_pr_threshold=15)
        assert b.max_files == 10
        assert b.large_pr_threshold == 15

    def test_is_large_pr(self):
        small = AnalysisBudget(large_pr_threshold=30)
        assert small.is_large_pr(25) is False
        assert small.is_large_pr(35) is True


class TestBudgetTracker:
    def test_tracks_consumption(self):
        t = BudgetTracker(AnalysisBudget(max_llm_calls=10, max_files=10))
        assert t.llm_calls_used == 0
        t.record_llm_call()
        t.record_llm_call()
        assert t.llm_calls_used == 2
        assert t.remaining_llm_calls == 8

    def test_exceeded_detection(self):
        t = BudgetTracker(AnalysisBudget(max_llm_calls=2))
        t.record_llm_call()
        t.record_llm_call()
        assert t.is_exceeded() is True

    def test_files_tracking(self):
        t = BudgetTracker(AnalysisBudget(max_files=5))
        t.record_files_analyzed(3)
        assert t.files_analyzed == 3
        assert t.remaining_files == 2

    def test_not_exceeded_initially(self):
        t = BudgetTracker(AnalysisBudget(max_llm_calls=100))
        assert t.is_exceeded() is False


class TestEstimateTokens:
    def test_empty_files(self):
        assert estimate_tokens([]) == 0

    def test_estimates_from_diff(self):
        fc = FileChange(path="a.py", status="modified", language="python",
                        diff="x" * 4000, additions=10, deletions=5)
        tokens = estimate_tokens([fc])
        assert tokens > 0

    def test_scales_with_file_count(self):
        fc = FileChange(path="a.py", status="modified", language="python",
                        diff="x" * 1000, additions=10, deletions=5)
        t1 = estimate_tokens([fc])
        t3 = estimate_tokens([fc, fc, fc])
        assert t3 > t1


class TestRankFilesByRisk:
    def test_returns_all_files(self):
        files = [
            FileChange(path="src/auth.py", status="modified", language="python",
                       diff="x" * 100, additions=20, deletions=10),
            FileChange(path="README.md", status="modified", language="text",
                       diff="x" * 10, additions=2, deletions=1),
        ]
        ranked = rank_files_by_risk(files, "Test PR")
        assert len(ranked) == 2

    def test_security_files_ranked_higher(self):
        files = [
            FileChange(path="README.md", status="modified", language="text",
                       diff="x" * 100, additions=20, deletions=10),
            FileChange(path="src/auth.py", status="modified", language="python",
                       diff="x" * 100, additions=20, deletions=10),
        ]
        ranked = rank_files_by_risk(files, "Test PR")
        # auth.py should appear before README.md
        auth_idx = next(i for i, f in enumerate(ranked) if "auth" in f.path)
        readme_idx = next(i for i, f in enumerate(ranked) if "README" in f.path)
        assert auth_idx < readme_idx
