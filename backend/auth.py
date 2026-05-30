"""JWT authentication — issue, verify, refresh tokens."""

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_EXPIRY = 3600 * 24  # 24 hours
REFRESH_EXPIRY = 3600 * 24 * 30  # 30 days


@dataclass
class AuthUser:
    id: int
    login: str
    github_id: int
    name: str | None = None
    avatar_url: str | None = None


def _b64url(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    import base64
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def issue_jwt(user_id: int, login: str, github_id: int) -> str:
    """Issue a signed JWT for the given user."""
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps({
        "sub": str(user_id),
        "login": login,
        "github_id": github_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRY,
    }).encode())
    signature = _b64url(hmac.new(
        JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256
    ).digest())
    return f"{header}.{payload}.{signature}"


def verify_jwt(token: str) -> AuthUser | None:
    """Verify a JWT and return the user if valid."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, signature = parts

        expected_sig = _b64url(hmac.new(
            JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256
        ).digest())
        if not hmac.compare_digest(signature, expected_sig):
            return None

        data = json.loads(_b64url_decode(payload))
        if data.get("exp", 0) < time.time():
            return None

        return AuthUser(
            id=int(data["sub"]),
            login=data["login"],
            github_id=data["github_id"],
        )
    except Exception:
        return None


def issue_refresh_token(user_id: int) -> str:
    """Issue a refresh token and store in DB."""
    token = os.urandom(32).hex()
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time() + REFRESH_EXPIRY))

    from src.store.db import SessionRepo
    repo = SessionRepo()
    try:
        repo.create(user_id, token_hash, expires)
    finally:
        repo.close()
    return token


def refresh_access_token(refresh_token: str) -> str | None:
    """Exchange a refresh token for a new JWT."""
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    from src.store.db import SessionRepo
    repo = SessionRepo()
    try:
        session = repo.find_valid(token_hash)
        if not session:
            return None
        repo.revoke(token_hash)
    finally:
        repo.close()

    from src.store.db import UserRepo
    user_repo = UserRepo()
    try:
        user = user_repo.find_by_id(session["user_id"])
        if not user:
            return None
        return issue_jwt(user["id"], user["login"], user["github_id"])
    finally:
        user_repo.close()
