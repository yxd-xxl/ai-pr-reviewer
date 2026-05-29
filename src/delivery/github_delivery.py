import hashlib
import json
import urllib.request
import urllib.error

from src.core.types import ReviewResult, Finding, PullRequest
from src.delivery.interface import Delivery


def _fingerprint(f: Finding) -> str:
    key = f"{f.location.file}:{f.location.line}:{f.title}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


class GitHubDelivery(Delivery):
    def __init__(self, token: str, dry_run: bool = True):
        self._token = token
        self.dry_run = dry_run
        self._comments_posted = 0
        self._summary_posted = False

    def deliver(self, result: ReviewResult, pr: PullRequest) -> list[str]:
        """Deliver findings as GitHub comments. Returns list of actions taken."""
        actions: list[str] = []
        inline_findings = []
        summary_items = []

        for f in result.findings:
            # Skip findings from removed files ======================
            # We detect removed files by checking if the finding
            # references a file that was removed in the PR.
            # For MVP, we use a conservative approach: if line is
            # None, treat as summary; if line is present, try inline.

            if f.location.line is None:
                summary_items.append(f)
                continue

            inline_findings.append(f)

        # Post inline comments =====================================
        for f in inline_findings:
            fp = _fingerprint(f)
            marker = f"<!-- ai-pr-reviewer fp={fp} -->"
            body = (
                f"**{f.severity.upper()}** `{f.category}` — {f.title}\n\n"
                f"{f.description}\n\n"
                f"> **Suggestion:** {f.suggestion}\n\n"
                f"{marker}"
            )

            if f.evidence:
                body = (
                    f"**{f.severity.upper()}** `{f.category}` — {f.title}\n\n"
                    f"{f.description}\n\n"
                    f"```\n{f.evidence}\n```\n\n"
                    f"> **Suggestion:** {f.suggestion}\n\n"
                    f"{marker}"
                )

            if self.dry_run:
                actions.append(
                    f"[DRY-RUN] Inline: {f.location.file}:{f.location.line} "
                    f"({f.severity} {f.category}) — {f.title}"
                )
            else:
                self._post_inline(pr, f.location.file, f.location.line,
                                  f.location.side, body)
                actions.append(
                    f"Posted: {f.location.file}:{f.location.line} — {f.title}"
                )
                self._comments_posted += 1

        # Post summary comment =====================================
        if summary_items:
            lines = ["## AI Review Summary", "", result.summary, "",
                     "### Additional Notes", ""]
            for f in summary_items:
                lines.append(f"- **[{f.severity}]** {f.title}: {f.description}")

            body = "\n".join(lines)
            marker = "<!-- ai-pr-reviewer-summary -->"
            body += f"\n\n{marker}"

            if self.dry_run:
                actions.append(
                    f"[DRY-RUN] Summary: {len(summary_items)} item(s) "
                    f"on PR #{pr.number}"
                )
            else:
                self._post_issue_comment(pr, body)
                actions.append(f"Posted summary on PR #{pr.number}")
                self._summary_posted = True

        return actions

    def _post_inline(self, pr: PullRequest, path: str, line: int,
                     side: str, body: str):
        url = (f"https://api.github.com/repos/{pr.owner}/{pr.repo}"
               f"/pulls/{pr.number}/comments")
        data = json.dumps({
            "body": body,
            "commit_id": pr.head_sha,
            "path": path,
            "line": line,
            "side": side,
        }).encode()
        req = urllib.request.Request(url, data=data, headers={
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        })
        with urllib.request.urlopen(req) as resp:
            resp.read()

    def _post_issue_comment(self, pr: PullRequest, body: str):
        url = (f"https://api.github.com/repos/{pr.owner}/{pr.repo}"
               f"/issues/{pr.number}/comments")
        data = json.dumps({"body": body}).encode()
        req = urllib.request.Request(url, data=data, headers={
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        })
        with urllib.request.urlopen(req) as resp:
            resp.read()
