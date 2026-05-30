"""Tests for ReviewApplicationService."""

from unittest.mock import patch, MagicMock
import pytest
from src.service.review_service import ReviewApplicationService, ReviewRunResult
from src.core.config import ReviewConfig


class TestReviewRunResult:
    def test_defaults(self):
        r = ReviewRunResult()
        assert r.pr is None
        assert r.files == []
        assert r.result is None
        assert r.errors == []

    def test_with_errors(self):
        r = ReviewRunResult(errors=["Something went wrong"])
        assert len(r.errors) == 1


class TestReviewApplicationService:
    def test_init_sets_fields(self):
        svc = ReviewApplicationService("test-token")
        assert svc._token == "test-token"
        assert isinstance(svc._config, ReviewConfig)

    def test_review_pr_delegates(self):
        svc = ReviewApplicationService("token")
        with patch("src.pipeline.run_review") as mock_run:
            mock_pr = MagicMock()
            mock_result = MagicMock()
            mock_result.metadata = {"timing": {}}
            mock_run.return_value = (mock_pr, [], mock_result)
            result = svc.review_pr("https://github.com/o/r/pull/1")
            assert result.errors == []
            mock_run.assert_called_once()

    def test_review_pr_captures_errors(self):
        svc = ReviewApplicationService("token")
        with patch("src.pipeline.run_review", side_effect=ValueError("Bad URL")):
            result = svc.review_pr("bad-url")
            assert len(result.errors) == 1

    def test_deliver_review_delegates(self):
        svc = ReviewApplicationService("token")
        with patch("src.delivery.github_delivery.GitHubDelivery") as mock_del:
            mock_del.return_value.deliver.return_value = ["[DRY-RUN] test"]
            result = svc.deliver_review(MagicMock(), MagicMock(), dry_run=True)
            assert len(result) == 1

    def test_get_history_delegates(self):
        svc = ReviewApplicationService("token")
        with patch("src.store.db.ReviewRepo") as mock_repo:
            mock_repo.return_value.get_history.return_value = [
                {"id": 1, "pr_title": "Test"}
            ]
            result = svc.get_history(repo="o/r", limit=5)
            assert len(result) == 1
            assert result[0]["pr_title"] == "Test"

    def test_config_property(self):
        cfg = ReviewConfig(mode="fast")
        svc = ReviewApplicationService("token", config=cfg)
        assert svc.config.mode == "fast"
