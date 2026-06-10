"""Tests for evaluate_result() in eval/runner.py."""

import pytest

from src.eval.metrics import EvalCase, EvalResult
from src.eval.runner import evaluate_result
from src.core.types import Finding, Location, ReviewResult


def _make_result(findings=None):
    return ReviewResult(
        summary="Test", findings=findings or [],
        metadata={"analyzer": "test"},
    )


def _case(expected=None, forbidden=None, category="bug"):
    return EvalCase(
        pr_url="https://github.com/o/r/pull/1",
        expected_titles=expected or [],
        forbidden_titles=forbidden or [],
        category=category,
    )


class TestEvaluateResult:
    def test_all_expected_matched(self):
        result = _make_result([
            Finding(severity="high", category="bug",
                    location=Location(file="a.py"), title="Null check",
                    description="", suggestion="", confidence=0.9,
                    evidence="code", analyzer="llm"),
            Finding(severity="medium", category="bug",
                    location=Location(file="b.py"), title="Memory leak",
                    description="", suggestion="", confidence=0.7,
                    evidence="code", analyzer="llm"),
        ])
        case = _case(expected=["Null check", "Memory leak"])
        er = evaluate_result(case, result)
        assert len(er.matched_expected) == 2
        assert er.false_positives == []
        assert er.false_negatives == []

    def test_partial_match(self):
        result = _make_result([
            Finding(severity="high", category="bug",
                    location=Location(file="a.py"), title="Null check",
                    description="", suggestion="", confidence=0.9,
                    evidence="code", analyzer="llm"),
        ])
        case = _case(expected=["Null check", "Memory leak"])
        er = evaluate_result(case, result)
        assert len(er.matched_expected) == 1
        assert er.false_negatives == ["Memory leak"]
        assert er.false_positives == []

    def test_substring_match(self):
        result = _make_result([
            Finding(severity="high", category="bug",
                    location=Location(file="a.py"),
                    title="Add null check for user input validation",
                    description="", suggestion="", confidence=0.9,
                    evidence="code", analyzer="llm"),
        ])
        case = _case(expected=["null check"])
        er = evaluate_result(case, result)
        assert len(er.matched_expected) == 1

    def test_forbidden_title_is_false_positive(self):
        result = _make_result([
            Finding(severity="low", category="style",
                    location=Location(file="a.py"), title="Import order",
                    description="", suggestion="", confidence=0.5,
                    evidence="code", analyzer="llm"),
        ])
        case = _case(forbidden=["Import order"])
        er = evaluate_result(case, result)
        assert er.false_positives == ["Import order"]

    def test_no_findings_no_expected(self):
        result = _make_result([])
        case = _case(expected=[])
        er = evaluate_result(case, result)
        assert len(er.matched_expected) == 0
        assert er.false_positives == []
        assert er.false_negatives == []

    def test_case_insensitive_match(self):
        result = _make_result([
            Finding(severity="high", category="bug",
                    location=Location(file="a.py"), title="SQL INJECTION risk",
                    description="", suggestion="", confidence=0.9,
                    evidence="code", analyzer="llm"),
        ])
        case = _case(expected=["sql injection"])
        er = evaluate_result(case, result)
        assert len(er.matched_expected) == 1
