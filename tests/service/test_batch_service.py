"""Tests for BatchReviewService."""

import pytest
from src.service.batch_service import BatchReviewService, BatchReviewJob


class TestBatchReviewJob:
    def test_defaults(self):
        job = BatchReviewJob(job_id="test", owner="o", repo="r")
        assert job.status == "pending"
        assert job.total == 0
        assert job.pr_urls == []

    def test_with_urls(self):
        job = BatchReviewJob(
            job_id="j1", owner="o", repo="r",
            pr_urls=["url1", "url2"], total=2,
        )
        assert job.total == 2


class TestBatchReviewService:
    def test_create_job(self):
        svc = BatchReviewService("token")
        job = svc.create_job("o", "r", ["url1", "url2"])
        assert job.total == 2
        assert job.status == "pending"
        assert job.job_id in svc._jobs

    def test_get_progress(self):
        svc = BatchReviewService("token")
        job = svc.create_job("o", "r", ["u1", "u2", "u3"])
        job.completed = 2
        job.failed = 1
        p = svc.get_progress(job.job_id)
        assert p["completed"] == 2
        assert p["failed"] == 1
        assert p["pending"] == 0

    def test_unknown_job(self):
        svc = BatchReviewService("token")
        assert svc.get_job("nonexistent") is None
        assert svc.get_progress("nonexistent") == {}

    def test_run_job_not_found(self):
        svc = BatchReviewService("token")
        with pytest.raises(ValueError, match="not found"):
            svc.run_job("nonexistent")
