"""Repos router — list repos, list PRs."""

from fastapi import APIRouter, Depends, Query
from backend.dependencies import get_token, get_github_token

router = APIRouter(prefix="/api/v1/repos", tags=["repos"])


@router.get("")
def list_repos(token: str = Depends(get_github_token), per_page: int = Query(30, le=100)):
    """List repositories accessible to the authenticated user."""
    from src.context.user_profile import list_user_repos
    repos = list_user_repos(token, per_page=per_page)
    return {
        "status": "ok",
        "repos": [
            {
                "full_name": r.get("full_name"),
                "private": r.get("private", False),
                "language": r.get("language"),
                "open_issues_count": r.get("open_issues_count", 0),
                "description": r.get("description"),
            }
            for r in repos
        ]
    }


@router.get("/{owner}/{repo}/prs")
def list_prs(owner: str, repo: str, token: str = Depends(get_github_token),
             state: str = Query("open"), limit: int = Query(20, le=50)):
    """List pull requests for a repository."""
    import json, urllib.request
    url = (f"https://api.github.com/repos/{owner}/{repo}/pulls"
           f"?state={state}&per_page={limit}&sort=updated&direction=desc")
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-pr-reviewer",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            prs = json.loads(resp.read())
        return {
            "status": "ok",
            "prs": [
                {
                    "number": pr.get("number"),
                    "title": pr.get("title"),
                    "html_url": pr.get("html_url"),
                    "user": {"login": pr.get("user", {}).get("login", "")},
                    "state": pr.get("state"),
                    "draft": pr.get("draft", False),
                    "additions": pr.get("additions", 0),
                    "deletions": pr.get("deletions", 0),
                    "changed_files": pr.get("changed_files", 0),
                    "comments": pr.get("comments", 0),
                    "created_at": pr.get("created_at", ""),
                }
                for pr in prs
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
