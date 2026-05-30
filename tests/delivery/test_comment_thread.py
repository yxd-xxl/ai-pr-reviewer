"""Tests for PR comment thread management."""

import pytest
from unittest.mock import patch, MagicMock
from src.delivery.comment_thread import (
    CommentThread, scan_existing_comments, detect_user_reply, handle_comment_reply,
)
from src.core.types import PullRequest


@pytest.fixture
def sample_pr():
    return PullRequest(
        owner="o", repo="r", number=1, title="T", description="",
        url="https://github.com/o/r/pull/1",
        base_branch="main", head_branch="f", base_sha="a", head_sha="b",
    )


class TestCommentThread:
    def test_empty_thread(self):
        t = CommentThread(finding_fingerprint="abc123")
        assert t.finding_fingerprint == "abc123"
        assert t.comments == []
        assert t.last_comment is None

    def test_with_comments(self):
        t = CommentThread(finding_fingerprint="fp1", comments=[
            {"id": 1, "author": "bot", "body": "test"},
            {"id": 2, "author": "user", "body": "@ai-pr-reviewer fix this"},
        ])
        assert len(t.comments) == 2
        assert t.last_comment["id"] == 2


class TestDetectUserReply:
    def test_fix_this(self):
        r = detect_user_reply("@ai-pr-reviewer fix this")
        assert r is not None
        assert r["action"] == "fix"

    def test_false_positive(self):
        r = detect_user_reply("@ai-pr-reviewer false positive")
        assert r is not None
        assert r["action"] == "mark_fp"

    def test_false_positive_with_reason(self):
        r = detect_user_reply("@ai-pr-reviewer false positive Not a real bug, this is debug code")
        assert r is not None
        assert r["action"] == "mark_fp"
        assert "debug" in r.get("reason", "")

    def test_why(self):
        r = detect_user_reply("@ai-pr-reviewer why")
        assert r is not None
        assert r["action"] == "followup"

    def test_fixed(self):
        r = detect_user_reply("@ai-pr-reviewer fixed")
        assert r is not None
        assert r["action"] == "mark_fixed"

    def test_no_instruction(self):
        r = detect_user_reply("Just a regular comment")
        assert r is None

    def test_wont_fix(self):
        r = detect_user_reply("@ai-pr-reviewer wont fix")
        assert r is not None
        assert r["action"] == "wont_fix"

    def test_duplicate(self):
        r = detect_user_reply("@ai-pr-reviewer duplicate")
        assert r is not None
        assert r["action"] == "duplicate"


class TestHandleCommentReply:
    def test_no_instruction_skipped(self, sample_pr):
        result = handle_comment_reply("token", sample_pr, {
            "body": "Nice catch!", "id": 1,
        })
        assert result["status"] == "skipped"

    def test_mark_fp_reply(self, sample_pr):
        result = handle_comment_reply("token", sample_pr, {
            "body": "@ai-pr-reviewer false positive Debug code",
            "id": 2, "in_reply_to_id": 1,
        })
        assert result["status"] == "ok"
        assert result["action"] == "mark_fp"
