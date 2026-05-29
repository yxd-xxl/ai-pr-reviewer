"""GitHub webhook handler for automated PR review."""

import json
import os
import hashlib
import hmac

from src.pipeline import run_review
from src.delivery.github_delivery import GitHubDelivery


def handle_webhook(payload: bytes, signature: str, secret: str,
                   token: str) -> dict:
    """Process a GitHub webhook event. Returns result dict."""
    # Verify signature
    if secret:
        expected = "sha256=" + hmac.new(
            secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return {"status": "error", "message": "Invalid signature"}

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid JSON"}

    event_type = os.environ.get("X_GITHUB_EVENT", data.get("action", "unknown"))

    # Only process PR events
    if "pull_request" not in data:
        return {"status": "skipped", "message": "Not a PR event"}

    action = data.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        return {"status": "skipped", "message": f"Ignored action: {action}"}

    pr_url = data["pull_request"]["html_url"]

    try:
        pr, files, result = run_review(pr_url, token)
    except Exception as e:
        return {"status": "error", "message": str(e)}

    # Deliver findings
    delivery = GitHubDelivery(token=token, dry_run=False)
    # Check config for delivery mode
    config = data.get("repository", {})
    actions = delivery.deliver(result, pr)

    return {
        "status": "ok",
        "pr_url": pr_url,
        "findings": len(result.findings),
        "actions": actions,
    }
