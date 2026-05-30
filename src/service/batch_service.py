"""Batch review service — manage multi-PR review jobs."""

from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


@dataclass
class BatchReviewJob:
    job_id: str
    owner: str
    repo: str
    pr_urls: list[str] = field(default_factory=list)
    status: str = "pending"  # pending|running|completed|failed
    results: list = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    completed: int = 0
    failed: int = 0
    total: int = 0


class BatchReviewService:
    """Manages batch review jobs with parallel execution."""

    def __init__(self, token: str, max_workers: int = 4):
        self._token = token
        self._max_workers = max_workers
        self._jobs: dict[str, BatchReviewJob] = {}
        self._lock = threading.Lock()

    def create_job(self, owner: str, repo: str,
                   pr_urls: list[str]) -> BatchReviewJob:
        import uuid
        job_id = uuid.uuid4().hex[:8]
        job = BatchReviewJob(
            job_id=job_id, owner=owner, repo=repo,
            pr_urls=pr_urls, total=len(pr_urls),
        )
        with self._lock:
            self._jobs[job_id] = job
        return job

    def run_job(self, job_id: str, categories: str = "all"):
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"Job {job_id} not found")
        job.status = "running"

        from src.service.review_service import ReviewApplicationService
        svc = ReviewApplicationService(token=self._token)

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {
                pool.submit(svc.review_pr, url, categories): url
                for url in job.pr_urls
            }
            for fut in as_completed(futures):
                url = futures[fut]
                try:
                    result = fut.result()
                    if result.errors:
                        job.failed += 1
                        job.errors.append(f"{url}: {result.errors[0]}")
                    else:
                        job.completed += 1
                        job.results.append({
                            "url": url,
                            "findings": len(result.result.findings) if result.result else 0,
                            "timing": result.timing,
                        })
                except Exception as e:
                    job.failed += 1
                    job.errors.append(f"{url}: {e}")

        job.status = "completed" if job.failed == 0 else "completed"

    def get_progress(self, job_id: str) -> dict:
        job = self._jobs.get(job_id)
        if job is None:
            return {}
        return {
            "status": job.status,
            "completed": job.completed,
            "failed": job.failed,
            "total": job.total,
            "pending": job.total - job.completed - job.failed,
        }

    def get_results(self, job_id: str) -> list:
        job = self._jobs.get(job_id)
        return job.results if job else []

    def get_job(self, job_id: str) -> BatchReviewJob | None:
        return self._jobs.get(job_id)
