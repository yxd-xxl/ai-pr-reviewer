"""Tests for Finding lifecycle state machine."""

from src.core.types import Finding, FindingEvent, Location, FindingState


def make_finding():
    return Finding(
        severity="high", category="bug",
        location=Location(file="a.py", line=10),
        title="Test", description="", suggestion="",
        confidence=0.8, evidence="code", analyzer="test",
    )


class TestFindingState:
    def test_all_states_defined(self):
        states = [s.value for s in FindingState]
        assert "detected" in states
        assert "verified" in states
        assert "published" in states
        assert "marked_fp" in states
        assert "fixed" in states


class TestFindingLifecycle:
    def test_default_state_is_detected(self):
        f = make_finding()
        assert f.lifecycle_state == "detected"

    def test_lifecycle_history_starts_empty(self):
        f = make_finding()
        assert f.lifecycle_history == []

    def test_can_transition_state(self):
        f = make_finding()
        f.lifecycle_state = "verified"
        f.lifecycle_history.append(FindingEvent(
            finding_fingerprint="abc123",
            from_state="detected", to_state="verified",
            user="test", reason="Test transition",
        ).__dict__)
        assert f.lifecycle_state == "verified"
        assert len(f.lifecycle_history) == 1
        assert f.lifecycle_history[0]["from_state"] == "detected"


class TestFindingEvent:
    def test_dataclass_fields(self):
        e = FindingEvent(
            finding_fingerprint="abc",
            from_state="detected", to_state="verified",
            user="system", reason="Auto transition",
        )
        assert e.finding_fingerprint == "abc"
        assert e.from_state == "detected"
        assert e.to_state == "verified"
