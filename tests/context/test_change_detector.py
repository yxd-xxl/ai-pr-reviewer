import pytest
from unittest.mock import patch, MagicMock
from src.context.change_detector import ChangeDetector, MIN_COMMITS, MIN_LINES


class TestChangeDetector:
    def test_no_last_sha_triggers_review(self, mocker):
        mocker.patch.object(ChangeDetector, '_get_head_sha', return_value="abc123")
        mocker.patch.object(ChangeDetector, '_count_commits', return_value=MIN_COMMITS)
        mocker.patch.object(ChangeDetector, '_count_changes', return_value=0)
        d = ChangeDetector()
        should, sha, count = d.check("o", "r", "token")
        assert should is True

    def test_same_sha_skips(self, mocker):
        state = MagicMock()
        state.last_reviewed_sha.return_value = "abc123"
        mocker.patch.object(ChangeDetector, '_get_head_sha', return_value="abc123")
        d = ChangeDetector(state)
        should, sha, count = d.check("o", "r", "token")
        assert should is False

    def test_enough_commits_triggers(self, mocker):
        state = MagicMock()
        state.last_reviewed_sha.return_value = "old"
        mocker.patch.object(ChangeDetector, '_get_head_sha', return_value="new")
        mocker.patch.object(ChangeDetector, '_count_commits', return_value=5)
        mocker.patch.object(ChangeDetector, '_count_changes', return_value=0)
        d = ChangeDetector(state)
        should, sha, count = d.check("o", "r", "token")
        assert should is True

    def test_below_threshold_skips(self, mocker):
        state = MagicMock()
        state.last_reviewed_sha.return_value = "old"
        mocker.patch.object(ChangeDetector, '_get_head_sha', return_value="new")
        mocker.patch.object(ChangeDetector, '_count_commits', return_value=1)
        mocker.patch.object(ChangeDetector, '_count_changes', return_value=10)
        d = ChangeDetector(state)
        should, sha, count = d.check("o", "r", "token")
        assert should is False
