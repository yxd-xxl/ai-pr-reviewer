"""Fetch user profile and accessible repos via GitHub API."""

import json
import urllib.request


def get_user_profile(token: str) -> dict:
    url = "https://api.github.com/user"
    return _api_get(url, token) or {}


def list_user_repos(token: str, per_page: int = 30) -> list[dict]:
    url = f"https://api.github.com/user/repos?per_page={per_page}&sort=updated"
    data = _api_get(url, token)
    if isinstance(data, list):
        return data
    return []


def _api_get(url: str, token: str):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-pr-reviewer",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return None
