from github import Github

from src.core.types import PullRequest, FileChange
from src.context.diff_parser import parse_unified_diff


class GitHubClient:
    def __init__(self, token: str):
        # requests library auto-respects HTTPS_PROXY/HTTP_PROXY env vars
        self._gh = Github(token)

    def fetch_pr(self, owner: str, repo: str, number: int) -> PullRequest:
        pr = self._gh.get_repo(f"{owner}/{repo}").get_pull(number)
        return PullRequest(
            owner=owner,
            repo=repo,
            number=number,
            title=pr.title,
            description=pr.body or "",
            url=pr.html_url,
            base_branch=pr.base.ref,
            head_branch=pr.head.ref,
            base_sha=pr.base.sha,
            head_sha=pr.head.sha,
            author=pr.user.login,
        )

    def fetch_files(self, owner: str, repo: str, number: int) -> list[FileChange]:
        pr = self._gh.get_repo(f"{owner}/{repo}").get_pull(number)
        files: list[FileChange] = []
        for f in pr.get_files():
            fc = _file_to_change(f)
            if fc is not None:
                files.append(fc)
        return files


def _file_to_change(f) -> FileChange | None:
    patch: str = f.patch or ""
    if not patch and f.status not in ("added", "modified", "removed", "renamed"):
        return None

    # Parse individual file patch for hunk info
    if patch:
        parsed = parse_unified_diff(patch)
        if parsed:
            fc = parsed[0]
            fc.path = f.filename
            fc.status = f.status
            fc.additions = f.additions
            fc.deletions = f.deletions
            if f.previous_filename:
                fc.old_path = f.previous_filename
            return fc

    # Fallback: no parseable patch (binary / empty)
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    return FileChange(
        path=f.filename,
        status=f.status,
        language=ext,
        diff="",
        additions=f.additions,
        deletions=f.deletions,
        old_path=f.previous_filename or None,
    )
