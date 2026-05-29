"""GitLab API client — mirrors GitHubClient interface."""

import json
import urllib.request
import urllib.error

from src.core.types import PullRequest, FileChange
from src.context.diff_parser import parse_unified_diff
from src.context.pr_url import parse_pr_url, PRUrl


class GitLabClient:
    def __init__(self, token: str, base_url: str = "https://gitlab.com"):
        self._token = token
        self._base = base_url.rstrip("/")

    def fetch_pr(self, owner: str, repo: str, number: int) -> PullRequest:
        # GitLab MR endpoint
        encoded = f"{owner}%2F{repo}"
        url = f"{self._base}/api/v4/projects/{encoded}/merge_requests/{number}"
        data = self._get(url)
        return PullRequest(
            owner=owner, repo=repo, number=number,
            title=data.get("title", ""),
            description=data.get("description", "") or "",
            url=data.get("web_url", ""),
            base_branch=data.get("target_branch", "main"),
            head_branch=data.get("source_branch", ""),
            base_sha=data.get("diff_refs", {}).get("base_sha", ""),
            head_sha=data.get("diff_refs", {}).get("head_sha", ""),
            author=data.get("author", {}).get("username", ""),
        )

    def fetch_files(self, owner: str, repo: str, number: int) -> list[FileChange]:
        encoded = f"{owner}%2F{repo}"
        url = (f"{self._base}/api/v4/projects/{encoded}"
               f"/merge_requests/{number}/changes")
        data = self._get(url)
        changes = data.get("changes", [])
        files: list[FileChange] = []
        for c in changes:
            diff = c.get("diff", "")
            parsed = parse_unified_diff(diff)
            fc = parsed[0] if parsed else FileChange(
                path=c.get("new_path", ""), status="modified",
                language="", diff=diff, additions=0, deletions=0,
            )
            fc.path = c.get("new_path", "")
            fc.status = _map_status(c)
            fc.additions = c.get("added_lines", c.get("additions", 0))
            fc.deletions = c.get("removed_lines", c.get("deletions", 0))
            if c.get("old_path") and c["old_path"] != c["new_path"]:
                fc.old_path = c["old_path"]
            files.append(fc)
        return files

    def _get(self, url: str) -> dict:
        req = urllib.request.Request(url, headers={
            "PRIVATE-TOKEN": self._token,
            "Accept": "application/json",
            "User-Agent": "ai-pr-reviewer",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"GitLab API error: {e.code}") from e


def _map_status(change: dict) -> str:
    if change.get("new_file"):
        return "added"
    if change.get("deleted_file"):
        return "removed"
    if change.get("renamed_file"):
        return "renamed"
    return "modified"
