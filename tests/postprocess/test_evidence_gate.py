import pytest
from src.postprocess.filter import PostProcessor
from src.core.types import ReviewResult, Finding, Location


def make_finding(title="T", evidence="code", confidence=0.8, severity="medium"):
    return Finding(
        severity=severity, category="bug", title=title,
        location=Location(file="a.py", line=1),
        description="", suggestion="", confidence=confidence,
        evidence=evidence, analyzer="test",
    )


class TestEvidenceGate:
    def test_finding_with_evidence_unchanged(self):
        result = ReviewResult(summary="", findings=[
            make_finding(evidence="x = pickle.loads(data)", confidence=0.8),
        ])
        pp = PostProcessor()
        filtered = pp.process(result)
        assert len(filtered.findings) == 1
        assert filtered.findings[0].confidence == 0.8

    def test_finding_without_evidence_degraded(self):
        result = ReviewResult(summary="", findings=[
            make_finding(evidence=None, confidence=0.9),
        ])
        pp = PostProcessor()
        filtered = pp.process(result)
        f = filtered.findings[0]
        assert f.confidence < 0.9
        assert f.evidence is None

    def test_finding_without_evidence_filtered_if_below_threshold(self):
        result = ReviewResult(summary="", findings=[
            make_finding(evidence=None, confidence=0.5),
        ])
        pp = PostProcessor(min_confidence=0.5)
        filtered = pp.process(result)
        # 0.5 - 0.3 = 0.2 < 0.5 → filtered out
        assert len(filtered.findings) == 0

    def test_empty_evidence_treated_as_none(self):
        result = ReviewResult(summary="", findings=[
            make_finding(evidence="", confidence=0.8),
        ])
        pp = PostProcessor()
        filtered = pp.process(result)
        assert filtered.findings[0].confidence < 0.8
