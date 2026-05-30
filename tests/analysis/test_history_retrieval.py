"""Tests for historical similar issue retrieval."""

from src.analysis.history_retrieval import (
    SimilarFinding, find_similar_findings, generate_history_context,
)


class TestSimilarFinding:
    def test_fields(self):
        s = SimilarFinding(title="Null check", file="a.py", severity="high",
                          category="bug", similarity_score=0.85)
        assert s.similarity_score == 0.85


class TestFindSimilarFindings:
    def test_exact_match(self):
        history = [{"title": "Null check missing", "file": "a.py", "severity": "high", "category": "bug"}]
        results = find_similar_findings("Null check missing", history)
        assert len(results) == 1
        assert results[0].similarity_score == 1.0

    def test_partial_match(self):
        history = [{"title": "Add null check for input validation", "file": "b.py", "severity": "medium", "category": "bug"}]
        results = find_similar_findings("Add null check for input", history)
        assert len(results) >= 1
        assert results[0].similarity_score >= 0.6

    def test_no_match(self):
        history = [{"title": "SQL injection risk", "file": "a.py", "severity": "high", "category": "security"}]
        results = find_similar_findings("Memory leak in loop", history)
        assert results == []

    def test_respects_limit(self):
        history = [{"title": f"Issue {i}"} for i in range(10)]
        results = find_similar_findings("Issue", history, min_score=0.0, limit=3)
        assert len(results) <= 3

    def test_sorted_by_score(self):
        history = [
            {"title": "Null check bug"},
            {"title": "Null safety issue"},
            {"title": "Memory leak"},
        ]
        results = find_similar_findings("Null check", history)
        if len(results) >= 2:
            assert results[0].similarity_score >= results[1].similarity_score


class TestGenerateContext:
    def test_empty(self):
        assert generate_history_context([]) == ""

    def test_with_similar(self):
        similar = [SimilarFinding(title="Null check", file="a.py", severity="high",
                                  category="bug", similarity_score=0.9, resolution="Added null guard")]
        ctx = generate_history_context(similar)
        assert "Null check" in ctx
        assert "null guard" in ctx
