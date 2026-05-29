import tempfile
from pathlib import Path
from src.feedback.tracker import FeedbackTracker, fingerprint
from src.core.types import Finding, Location


def make_finding(title="Test", file="a.py", line=1):
    return Finding(
        severity="medium", category="bug",
        location=Location(file=file, line=line),
        title=title, description="", suggestion="", confidence=0.8,
    )


class TestFeedbackTracker:
    def test_mark_and_check_fp(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "feedback.json"
            t = FeedbackTracker(str(path))
            f = make_finding()
            t.mark_fp(f)
            assert t.is_known_fp(f)

    def test_different_finding_not_fp(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "feedback.json"
            t = FeedbackTracker(str(path))
            f1 = make_finding(title="A")
            f2 = make_finding(title="B")
            t.mark_fp(f1)
            assert not t.is_known_fp(f2)

    def test_fingerprint_stable(self):
        f1 = make_finding(title="Null check", file="auth.py", line=42)
        f2 = make_finding(title="Null check", file="auth.py", line=42)
        assert fingerprint(f1) == fingerprint(f2)

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "feedback.json"
            t1 = FeedbackTracker(str(path))
            t1.mark_fp(make_finding())
            t2 = FeedbackTracker(str(path))
            assert t2.is_known_fp(make_finding())
