"""Tests for reviewer recommendation."""

from src.analysis.reviewer_rec import (
    ReviewerRecommendation, recommend_reviewers, render_reviewer_section,
)
from src.core.types import FileChange


def _file(path):
    return FileChange(path=path, status="modified", language="python", diff="x", additions=1, deletions=0)


class TestReviewerRecommendation:
    def test_fields(self):
        r = ReviewerRecommendation(user="alice", reason="CODEOWNERS", expertise_area="auth")
        assert r.user == "alice"


class TestRecommendReviewers:
    def test_codeowners_match(self):
        owners = "src/auth/* @alice\n*.md @bob\n"
        fc = _file("src/auth/login.py")
        recs = recommend_reviewers([fc], owners)
        assert len(recs) == 1
        assert recs[0].user == "alice"

    def test_no_codeowners(self):
        fc = _file("src/app.py")
        recs = recommend_reviewers([fc], "")
        assert recs == []

    def test_wildcard_match(self):
        owners = "* @admin\n"
        fc = _file("random.py")
        recs = recommend_reviewers([fc], owners)
        assert any(r.user == "admin" for r in recs)

    def test_multiple_files_same_owner(self):
        owners = "src/* @alice\n"
        recs = recommend_reviewers([_file("src/a.py"), _file("src/b.py")], owners)
        assert len(recs) == 1  # deduplicated


class TestRenderSection:
    def test_no_recs(self):
        section = render_reviewer_section([])
        assert "CODEOWNERS" in section

    def test_with_recs(self):
        r = ReviewerRecommendation(user="alice", reason="CODEOWNERS: src/*", expertise_area="src")
        section = render_reviewer_section([r])
        assert "@alice" in section
