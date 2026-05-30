"""ReviewApplicationService — unified entry point for all review operations.

CLI, Streamlit, GitHub Action, and Webhook should all route through this service
rather than calling pipeline.py directly.
"""

import time
from dataclasses import dataclass, field

from src.core.types import PullRequest, FileChange, ReviewResult, Finding
from src.core.config import ReviewConfig, load_config
from src.llm import create_adapter, LLMAdapter


@dataclass
class ReviewRunResult:
    pr: PullRequest | None = None
    files: list[FileChange] = field(default_factory=list)
    result: ReviewResult | None = None
    timing: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class ReviewApplicationService:
    """Central service for review operations. Encapsulates pipeline orchestration."""

    def __init__(self, token: str, config: ReviewConfig | None = None,
                 llm_config: dict | None = None):
        self._token = token
        self._config = config or load_config()
        self._llm_config = llm_config or {}

    def review_pr(self, pr_url: str, categories: str = "all") -> ReviewRunResult:
        """Run a full review on a single PR."""
        from src.pipeline import run_review
        t0 = time.time()
        try:
            pr, files, result = run_review(
                pr_url, self._token,
                config=self._config,
                llm_config=self._llm_config or None,
                categories=categories,
            )
            timing = result.metadata.get("timing", {})
            timing["service_total"] = round(time.time() - t0, 2)
            return ReviewRunResult(pr=pr, files=files, result=result, timing=timing)
        except Exception as e:
            return ReviewRunResult(
                errors=[str(e)],
                timing={"service_total": round(time.time() - t0, 2)},
            )

    def check_changes(self, owner: str, repo: str) -> dict:
        """Check for unreviewed changes in a repository."""
        from src.pipeline import check_changes
        return check_changes(owner, repo, self._token)

    def generate_pr_proposal(self, owner: str, repo: str,
                             diff_text: str, commit_count: int) -> dict:
        """Generate PR title/description from changes."""
        from src.pipeline import generate_pr_proposal
        return generate_pr_proposal(owner, repo, self._token, diff_text, commit_count)

    def create_pr(self, owner: str, repo: str, title: str,
                  description: str, head_sha: str) -> dict:
        """Create a PR from detected changes."""
        from src.pipeline import create_pr_from_changes
        return create_pr_from_changes(owner, repo, self._token, title, description, head_sha)

    def request_fix_pr(self, result: ReviewResult, pr: PullRequest,
                       finding_indices: list[int] | None = None,
                       dry_run: bool = True) -> list[str]:
        """Generate a fix PR from reviewed findings."""
        from src.delivery.pr_generator import generate_fix_pr
        return generate_fix_pr(result, pr, self._token,
                              finding_indices=finding_indices, dry_run=dry_run)

    def deliver_review(self, result: ReviewResult, pr: PullRequest,
                       dry_run: bool = True) -> list[str]:
        """Deliver review results to GitHub."""
        from src.delivery.github_delivery import GitHubDelivery
        delivery = GitHubDelivery(token=self._token, dry_run=dry_run)
        return delivery.deliver(result, pr)

    def get_history(self, repo: str = "", limit: int = 20) -> list[dict]:
        """Get review history from the database."""
        from src.store.db import ReviewRepo
        db = ReviewRepo()
        try:
            return db.get_history(repo=repo, limit=limit)
        finally:
            db.close()

    @property
    def config(self) -> ReviewConfig:
        return self._config
