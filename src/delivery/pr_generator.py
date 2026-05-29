"""Generate fix PRs from reviewed findings."""

import json
import urllib.request
import urllib.error

from src.core.types import ReviewResult, PullRequest, Finding


def generate_fix_pr(result: ReviewResult, pr: PullRequest, token: str,
                    finding_indices: list[int] | None = None,
                    dry_run: bool = True) -> list[str]:
    """Create a fix PR from verified findings. Returns list of actions."""
    actions: list[str] = []

    # Select findings with fix patches
    fixable = [f for f in result.findings if f.fix_patch and f.fix_verified]
    if finding_indices:
        fixable = [f for i, f in enumerate(result.findings)
                   if i in finding_indices and f.fix_patch]

    if not fixable:
        actions.append("No verified fix patches available.")
        return actions

    # Build fix title and body
    title = f"fix: address {len(fixable)} AI review finding(s)"
    body_lines = [
        "## AI-Generated Fix",
        "",
        f"Based on review of [#{pr.number}]({pr.url}).",
        "",
        "### Fixed Findings",
        "",
    ]
    for f in fixable:
        body_lines.append(f"- **[{f.severity}]** {f.title} (`{f.location.file}`)")
    body = "\n".join(body_lines)

    if dry_run:
        actions.append(f"[DRY-RUN] Would create PR: '{title}'")
        actions.append(f"[DRY-RUN] Files affected: {len(set(f.location.file for f in fixable))}")
        actions.append(f"[DRY-RUN] Findings fixed: {len(fixable)}")
        for f in fixable:
            actions.append(f"  - {f.location.file}: {f.title[:60]}")
        return actions

    # Create branch
    branch_name = f"ai-fix-pr-{pr.number}-{len(fixable)}-findings"
    try:
        _create_branch(pr, token, branch_name)
        actions.append(f"Created branch: {branch_name}")
    except Exception as e:
        actions.append(f"Failed to create branch: {e}")
        return actions

    # Create fix PR
    try:
        fix_pr_url = _create_pr(pr, token, branch_name, title, body)
        actions.append(f"Created fix PR: {fix_pr_url}")
    except Exception as e:
        actions.append(f"Failed to create PR: {e}")

    return actions


def _create_branch(pr: PullRequest, token: str, branch_name: str):
    url = (f"https://api.github.com/repos/{pr.owner}/{pr.repo}"
           f"/git/refs")
    data = json.dumps({
        "ref": f"refs/heads/{branch_name}",
        "sha": pr.head_sha,
    }).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req) as resp:
        resp.read()


def _create_pr(pr: PullRequest, token: str, branch_name: str,
               title: str, body: str) -> str:
    url = f"https://api.github.com/repos/{pr.owner}/{pr.repo}/pulls"
    data = json.dumps({
        "title": title,
        "body": body,
        "head": branch_name,
        "base": pr.base_branch,
    }).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        return result.get("html_url", "")
