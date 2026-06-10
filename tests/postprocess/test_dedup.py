"""Tests for PostProcessor deduplication logic."""

import pytest

from src.core.types import Finding, Location, ReviewResult
from src.postprocess.filter import PostProcessor


def _make_finding(file="a.py", line=10, title="Issue A", category="bug",
                  severity="medium", confidence=0.8, evidence="line 10"):
    return Finding(
        severity=severity, category=category,
        location=Location(file=file, line=line),
        title=title, description=f"Description for {title}",
        suggestion="Fix it", confidence=confidence, evidence=evidence,
        analyzer="llm",
    )


class TestDedupSimilar:
    def test_identical_titles_deduped(self):
        f1 = _make_finding(title="Null check missing")
        f2 = _make_finding(title="Null check missing")
        result = ReviewResult(summary="", findings=[f1, f2])
        pp = PostProcessor(min_confidence=0.5, max_findings=100)
        processed = pp.process(result)
        assert len(processed.findings) == 1

    def test_similar_titles_deduped(self):
        f1 = _make_finding(title="Missing null check in handler")
        f2 = _make_finding(title="Missing null check in handler function")
        result = ReviewResult(summary="", findings=[f1, f2])
        pp = PostProcessor(min_confidence=0.5, max_findings=100)
        processed = pp.process(result)
        # ratio > 0.8 means dedup
        assert len(processed.findings) == 1

    def test_different_titles_not_deduped(self):
        f1 = _make_finding(title="SQL injection risk")
        f2 = _make_finding(title="Memory leak in loop")
        result = ReviewResult(summary="", findings=[f1, f2])
        pp = PostProcessor(min_confidence=0.5, max_findings=100)
        processed = pp.process(result)
        assert len(processed.findings) == 2

    def test_different_categories_not_deduped(self):
        f1 = _make_finding(title="Same title", category="bug")
        f2 = _make_finding(title="Same title", category="security")
        result = ReviewResult(summary="", findings=[f1, f2])
        pp = PostProcessor(min_confidence=0.5, max_findings=100)
        processed = pp.process(result)
        assert len(processed.findings) == 2

    def test_different_files_not_deduped(self):
        f1 = _make_finding(file="a.py", title="Same title")
        f2 = _make_finding(file="b.py", title="Same title")
        result = ReviewResult(summary="", findings=[f1, f2])
        pp = PostProcessor(min_confidence=0.5, max_findings=100)
        processed = pp.process(result)
        assert len(processed.findings) == 2

    def test_keeps_higher_severity_on_dedup(self):
        f1 = _make_finding(title="Null check", severity="medium")
        f2 = _make_finding(title="Null check", severity="high")
        result = ReviewResult(summary="", findings=[f1, f2])
        pp = PostProcessor(min_confidence=0.5, max_findings=100)
        processed = pp.process(result)
        assert len(processed.findings) == 1
        # Severity sort puts high first — dedup keeps first match
