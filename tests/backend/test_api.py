"""Tests for FastAPI REST API server."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.main import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


class TestReviewEndpoint:
    def test_review_missing_token(self, client):
        with patch.dict("os.environ", {}, clear=True):
            resp = client.post("/api/v1/review", json={
                "pr_url": "https://github.com/o/r/pull/1",
            })
            assert resp.status_code == 400

    def test_review_with_token(self, client):
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test"}, clear=True), \
             patch("src.pipeline.run_review") as mock_run:
            mock_pr = MagicMock()
            mock_pr.title = "Test"
            mock_pr.url = "url"
            mock_pr.author = "dev"
            mock_result = MagicMock()
            mock_result.findings = []
            mock_result.warnings = []
            mock_result.metadata = {"timing": {}}
            mock_run.return_value = (mock_pr, [], mock_result)

            resp = client.post("/api/v1/review", json={
                "pr_url": "https://github.com/o/r/pull/1",
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"


class TestFeedbackEndpoint:
    def test_submit_feedback(self, client):
        resp = client.post("/api/v1/feedback", json={
            "fingerprint": "abc123",
            "state": "fp",
            "reason": "Not a real bug",
        })
        assert resp.status_code == 200


class TestReviewsEndpoint:
    def test_list_reviews(self, client):
        with patch("src.store.db.ReviewRepo") as mock_repo:
            mock_repo.return_value.get_history.return_value = []
            resp = client.get("/api/v1/reviews?repo=test/repo&limit=10")
            assert resp.status_code == 200


class TestEvalEndpoint:
    def test_get_eval(self, client):
        resp = client.get("/api/v1/eval")
        assert resp.status_code == 200
        data = resp.json()
        assert "baseline" in data
