"""GitHub App authentication — installation token management."""

import json
import time
import urllib.request
from pathlib import Path

try:
    import jwt  # PyJWT — install with: pip install PyJWT
except ImportError:
    jwt = None  # GitHub App features require PyJWT


def create_installation_token(installation_id: int, app_id: str,
                              private_key: str) -> dict:
    """Generate an installation access token for a GitHub App.
    Returns dict with: token, expires_at, repository_selection.
    Requires PyJWT: pip install PyJWT
    """
    if jwt is None:
        raise RuntimeError("PyJWT is required for GitHub App authentication. "
                          "Install with: pip install PyJWT")
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 600,  # 10 minutes max
        "iss": app_id,
    }
    try:
        # Read private key from file path or raw string
        if Path(private_key).exists():
            private_key = Path(private_key).read_text()
        encoded = jwt.encode(payload, private_key, algorithm="RS256")
    except Exception as e:
        raise RuntimeError(f"Failed to sign JWT: {e}") from e

    url = (f"https://api.github.com/app/installations/{installation_id}"
           f"/access_tokens")
    req = urllib.request.Request(url, method="POST", headers={
        "Authorization": f"Bearer {encoded}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-pr-reviewer",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        raise RuntimeError(f"Failed to create installation token: {e}") from e


class GitHubAppClient:
    """GitHub API client that authenticates as a GitHub App installation."""

    def __init__(self, installation_id: int, app_id: str,
                 private_key_path: str):
        self._installation_id = installation_id
        self._app_id = app_id
        self._private_key_path = private_key_path
        self._token: str | None = None
        self._token_expires: int = 0

    def _ensure_token(self):
        now = int(time.time())
        if self._token and now < self._token_expires - 60:
            return
        result = create_installation_token(
            self._installation_id, self._app_id, self._private_key_path)
        self._token = result["token"]
        expires_str = result.get("expires_at", "")
        if expires_str:
            from datetime import datetime, timezone
            try:
                dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                self._token_expires = int(dt.timestamp())
            except (ValueError, TypeError):
                self._token_expires = now + 3600
        else:
            self._token_expires = now + 3600

    @property
    def token(self) -> str:
        self._ensure_token()
        return self._token or ""

    def get_installation_repos(self) -> list[dict]:
        """List repositories accessible to this installation."""
        url = "https://api.github.com/installation/repositories?per_page=100"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "ai-pr-reviewer",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return data.get("repositories", [])
