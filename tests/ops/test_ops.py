"""Tests for ops modules: audit, cost tracking, A/B testing."""

import json
import tempfile
from pathlib import Path
from src.ops.audit import AuditLogger, AuditEvent
from src.ops.cost_tracker import estimate_cost
from src.ops.ab_test import compare_metrics, ABTest, ABTestResult


class TestAuditLogger:
    def test_log_and_retrieve(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "audit.jsonl"
            logger = AuditLogger(str(path))
            logger.log("alice", "review_started", "pr:1", "Test review")
            logger.log("bob", "feedback_marked", "fp:abc", "Marked FP")
            trail = logger.get_trail()
            assert len(trail) == 2
            assert trail[0].user == "alice"

    def test_filter_by_resource(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "audit.jsonl"
            logger = AuditLogger(str(path))
            logger.log("alice", "review_started", "pr:1")
            logger.log("bob", "review_started", "pr:2")
            trail = logger.get_trail(resource="pr:1")
            assert len(trail) == 1

    def test_empty_log(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "nonexistent.jsonl"
            logger = AuditLogger(str(path))
            assert logger.get_trail() == []


class TestCostTracker:
    def test_deepseek_pricing(self):
        cost = estimate_cost("deepseek-chat", 1000000, 500000)
        assert cost > 0
        # ~$0.27 + $0.55 = ~$0.82 per 1M in + 500k out

    def test_unknown_model_fallback(self):
        cost = estimate_cost("unknown-model", 1000, 100)
        assert cost >= 0


class TestABTest:
    def test_treatment_wins(self):
        result = compare_metrics(0.80, 0.50, 0.85, 0.60)
        assert result.winner == "treatment"

    def test_control_wins(self):
        result = compare_metrics(0.90, 0.70, 0.80, 0.50)
        assert result.winner == "control"

    def test_tie(self):
        result = compare_metrics(0.85, 0.60, 0.85, 0.61)
        assert result.winner in ("tie", "treatment")
