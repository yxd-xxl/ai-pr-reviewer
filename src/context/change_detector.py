import urllib.request
import json

from src.context.review_state import ReviewState

# Thresholds for auto-triggering a review
MIN_COMMITS = 3
MIN_LINES = 20


class ChangeDetector:
    def __init__(self, state: ReviewState | None = None):
        self._state = state or ReviewState()

    def check(self, owner: str, repo: str, token: str,
              pr_number: int = 0) -> tuple[bool, str, int]:
        """Check if enough changes have accumulated since last review.
        Returns (should_review, current_sha, commit_count).
        Uses PR number as key when available, else uses repo-level tracking."""
        key = pr_number if pr_number else 0
        last_sha = self._state.last_reviewed_sha(key)

        # Get current HEAD SHA
        current_sha = self._get_head_sha(owner, repo, token)
        if not current_sha:
            return False, "", 0

        if last_sha == current_sha:
            return False, current_sha, 0

        # Count commits between last review and HEAD
        commit_count = self._count_commits(owner, repo, token, last_sha, current_sha)
        changed_lines = self._count_changes(owner, repo, token, last_sha, current_sha)

        should = commit_count >= MIN_COMMITS or changed_lines >= MIN_LINES
        return should, current_sha, commit_count

    def _get_head_sha(self, owner: str, repo: str, token: str) -> str:
        url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/main"
        data = self._api_get(url, token)
        if isinstance(data, dict):
            return data.get("object", {}).get("sha", "")
        return ""

    def _count_commits(self, owner, repo, token, last_sha, current_sha) -> int:
        if not last_sha:
            return MIN_COMMITS  # first review, always trigger
        url = (f"https://api.github.com/repos/{owner}/{repo}"
               f"/compare/{last_sha}...{current_sha}")
        data = self._api_get(url, token)
        if isinstance(data, dict):
            return data.get("total_commits", 0)
        return 0

    def _count_changes(self, owner, repo, token, last_sha, current_sha) -> int:
        if not last_sha:
            return MIN_LINES
        url = (f"https://api.github.com/repos/{owner}/{repo}"
               f"/compare/{last_sha}...{current_sha}")
        data = self._api_get(url, token)
        if isinstance(data, dict):
            files = data.get("files", [])
            return sum(f.get("changes", 0) for f in files)
        return 0

    def _api_get(self, url: str, token: str):
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "ai-pr-reviewer",
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except Exception:
            return None
