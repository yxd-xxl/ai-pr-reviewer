"""GitHub OAuth authentication flow."""

import json
import os
import urllib.request
import urllib.parse
from dataclasses import dataclass


@dataclass
class OAuthUser:
    login: str
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    organizations: list[str] | None = None


def get_oauth_url(client_id: str, redirect_uri: str = "http://localhost:8000/callback",
                  scope: str = "read:user read:org") -> str:
    """Generate GitHub OAuth authorization URL."""
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
    })
    return f"https://github.com/login/oauth/authorize?{params}"


def exchange_code_for_token(code: str, client_id: str,
                            client_secret: str) -> str | None:
    """Exchange OAuth code for access token."""
    url = "https://github.com/login/oauth/access_token"
    import urllib.parse
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
    }).encode()

    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return result.get("access_token")
    except Exception as e:
        import sys
        print(f"OAuth exchange error: {e}", file=sys.stderr)
        return None


def get_oauth_user(token: str) -> OAuthUser | None:
    """Fetch authenticated user info from GitHub API."""
    req = urllib.request.Request("https://api.github.com/user", headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-pr-reviewer",
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        # Fetch organizations
        orgs_req = urllib.request.Request(
            "https://api.github.com/user/orgs", headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "ai-pr-reviewer",
            })
        orgs = []
        try:
            with urllib.request.urlopen(orgs_req, timeout=10) as org_resp:
                orgs = [o["login"] for o in json.loads(org_resp.read())]
        except Exception:
            pass

        return OAuthUser(
            login=data.get("login", ""),
            name=data.get("name"),
            email=data.get("email"),
            avatar_url=data.get("avatar_url"),
            organizations=orgs,
        )
    except Exception:
        return None
