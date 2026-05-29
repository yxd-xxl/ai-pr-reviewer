import json
import tempfile
from pathlib import Path
import pytest
from src.context.review_state import ReviewState, _now_iso


@pytest.fixture
def tmp_state_file():
    d = tempfile.mkdtemp()
    path = Path(d) / "state.json"
    yield str(path)
    # cleanup
    if path.exists():
        path.unlink()
    Path(d).rmdir()


class TestReviewState:
    def test_is_not_reviewed_initially(self, tmp_state_file):
        state = ReviewState(tmp_state_file)
        assert not state.is_reviewed(pr_number=7, head_sha="abc123")

    def test_mark_and_check_reviewed(self, tmp_state_file):
        state = ReviewState(tmp_state_file)
        state.mark_reviewed(pr_number=7, head_sha="abc123",
                            findings_count=3)
        assert state.is_reviewed(pr_number=7, head_sha="abc123")

    def test_different_sha_not_reviewed(self, tmp_state_file):
        state = ReviewState(tmp_state_file)
        state.mark_reviewed(pr_number=7, head_sha="abc123", findings_count=3)
        # Different SHA for same PR
        assert not state.is_reviewed(pr_number=7, head_sha="def456")

    def test_different_pr_not_reviewed(self, tmp_state_file):
        state = ReviewState(tmp_state_file)
        state.mark_reviewed(pr_number=7, head_sha="abc123", findings_count=3)
        assert not state.is_reviewed(pr_number=8, head_sha="abc123")

    def test_persistence_across_instances(self, tmp_state_file):
        s1 = ReviewState(tmp_state_file)
        s1.mark_reviewed(pr_number=7, head_sha="abc", findings_count=3)

        s2 = ReviewState(tmp_state_file)
        assert s2.is_reviewed(pr_number=7, head_sha="abc")

    def test_last_reviewed_sha(self, tmp_state_file):
        state = ReviewState(tmp_state_file)
        state.mark_reviewed(pr_number=7, head_sha="old-sha", findings_count=1)
        state.mark_reviewed(pr_number=7, head_sha="new-sha", findings_count=2)
        assert state.last_reviewed_sha(7) == "new-sha"

    def test_empty_file_no_error(self, tmp_state_file):
        Path(tmp_state_file).write_text("")
        state = ReviewState(tmp_state_file)
        assert not state.is_reviewed(7, "abc")

    def test_corrupt_file_no_error(self, tmp_state_file):
        Path(tmp_state_file).write_text("not json")
        state = ReviewState(tmp_state_file)
        assert not state.is_reviewed(7, "abc")
