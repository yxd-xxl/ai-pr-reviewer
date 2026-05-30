"""PR comment thread management — scan, detect replies, handle interactions."""

import json
import re
import urllib.request
from dataclasses import dataclass, field

from src.core.types import PullRequest

_FINGERPRINT_RE = re.compile(r'<!-- ai-pr-reviewer fp=([a-f0-9]{12}) -->')
_INSTRUCTION_RE = re.compile(r'@ai-pr-reviewer\s+(fix\s+this|false\s+positive|why|fixed|wont.?fix|duplicate|low.?priority)(?:\s+(.+))?', re.IGNORECASE)


@dataclass
class CommentThread:
    finding_fingerprint: str
    comments: list[dict] = field(default_factory=list)

    @property
    def last_comment(self) -> dict | None:
        return self.comments[-1] if self.comments else None


def scan_existing_comments(token: str, pr: PullRequest) -> list[CommentThread]:
    """Scan all comments on a PR and group by AI reviewer fingerprint."""
    url = (f"https://api.github.com/repos/{pr.owner}/{pr.repo}"
           f"/pulls/{pr.number}/comments?per_page=100")
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-pr-reviewer",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            comments = json.loads(resp.read())
    except Exception:
        return []

    threads: dict[str, CommentThread] = {}
    for c in comments:
        body = c.get("body", "")
        match = _FINGERPRINT_RE.search(body)
        if match:
            fp = match.group(1)
            if fp not in threads:
                threads[fp] = CommentThread(finding_fingerprint=fp)
            threads[fp].comments.append({
                "id": c.get("id"),
                "author": c.get("user", {}).get("login", "unknown"),
                "body": body,
                "created_at": c.get("created_at", ""),
            })
    return list(threads.values())


def detect_user_reply(comment_body: str) -> dict | None:
    """Parse a user comment for @ai-pr-reviewer instructions.
    Returns dict with action and parsed args, or None if no instruction found.
    """
    match = _INSTRUCTION_RE.search(comment_body)
    if not match:
        return None

    action_raw = match.group(1).lower().replace(" ", "_")
    extra = (match.group(2) or "").strip()

    action_map = {
        "fix_this": "fix",
        "false_positive": "mark_fp",
        "why": "followup",
        "fixed": "mark_fixed",
        "wont_fix": "wont_fix",
        "wont.fix": "wont_fix",
        "duplicate": "duplicate",
        "low_priority": "low_pri",
        "low.priority": "low_pri",
    }
    action = action_map.get(action_raw, action_raw)

    result: dict = {"action": action}
    if action == "mark_fp":
        result["reason"] = extra or "User marked as false positive"
    elif action == "followup":
        result["question"] = extra or comment_body
    elif action == "wont_fix":
        result["reason"] = extra or "User declined to fix"
    return result


def handle_comment_reply(token: str, pr: PullRequest,
                         comment: dict) -> dict:
    """Process a user comment reply. Returns result dict with action taken."""
    body = comment.get("body", "")
    instruction = detect_user_reply(body)
    if not instruction:
        return {"status": "skipped", "message": "No AI instruction found"}

    # Find the parent AI comment by looking at reply_to / in_reply_to_id
    parent_id = comment.get("in_reply_to_id")
    finding_fp = None

    if parent_id:
        threads = scan_existing_comments(token, pr)
        for thread in threads:
            for c in thread.comments:
                if c.get("id") == parent_id:
                    finding_fp = thread.finding_fingerprint
                    break

    result = {
        "status": "ok",
        "action": instruction["action"],
        "finding_fingerprint": finding_fp,
    }

    if instruction["action"] == "mark_fp":
        from src.feedback.tracker import FeedbackTracker
        # We don't have the full Finding object, just the fingerprint
        result["message"] = f"FP marked for {finding_fp}: {instruction.get('reason', '')}"

    elif instruction["action"] == "followup":
        result["message"] = f"Follow-up question: {instruction.get('question', '')}"

    elif instruction["action"] == "mark_fixed":
        result["message"] = f"Finding {finding_fp} marked as fixed by user"

    return result
