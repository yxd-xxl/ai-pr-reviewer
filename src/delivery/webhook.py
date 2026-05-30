"""GitHub webhook handler for automated PR review."""

import json
import os
import hashlib
import hmac
from http.server import HTTPServer, BaseHTTPRequestHandler


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
        from src.pipeline import run_review
        pr, files, result = run_review(pr_url, token)
    except Exception as e:
        return {"status": "error", "message": str(e)}

    # Deliver findings
    from src.delivery.github_delivery import GitHubDelivery
    delivery = GitHubDelivery(token=token, dry_run=False)
    actions = delivery.deliver(result, pr)

    return {
        "status": "ok",
        "pr_url": pr_url,
        "findings": len(result.findings),
        "actions": actions,
    }


class _WebhookHandler(BaseHTTPRequestHandler):
    _secret: str = ""
    _token: str = ""

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(content_length)
        signature = self.headers.get("X-Hub-Signature-256", "")

        result = handle_webhook(payload, signature, self._secret, self._token)

        self.send_response(200 if result["status"] == "ok" else 400)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def log_message(self, format, *args):
        # Suppress default logging
        pass


def start_webhook_server(host: str = "0.0.0.0", port: int = 8080,
                         secret: str = "", token: str = ""):
    """Start a lightweight HTTP server for GitHub webhook events.
    Trigger: pull_request opened/synchronize/reopened -> auto review.
    """
    _WebhookHandler._secret = secret
    _WebhookHandler._token = token

    server = HTTPServer((host, port), _WebhookHandler)
    print(f"Webhook server listening on {host}:{port}")
    print(f"Add webhook URL: http://<your-server>:{port}/")
    print("Events: Pull Request — opened, synchronize, reopened")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
