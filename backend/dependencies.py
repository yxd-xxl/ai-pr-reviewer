"""FastAPI dependencies — JWT + GitHub token auth, user resolution."""

import os
from fastapi import Depends, HTTPException, Header
from backend.models import UserResponse


def get_token(authorization: str = Header(None)) -> str:
    """Extract Bearer token (JWT or GitHub PAT) from Authorization header."""
    if not authorization:
        token = os.getenv("GITHUB_TOKEN", "")
        if token:
            return token
        raise HTTPException(401, "Authorization header or GITHUB_TOKEN required")
    if authorization.startswith("Bearer "):
        return authorization[7:]
    return authorization


def get_current_user(token: str = Depends(get_token)) -> UserResponse:
    """Resolve user from JWT (local) or GitHub token (legacy)."""
    # Try JWT first
    try:
        from backend.auth import verify_jwt
        jwt_user = verify_jwt(token)
        if jwt_user:
            from src.store.db import UserRepo
            db = UserRepo()
            try:
                u = db.find_by_id(jwt_user.id)
                if u:
                    return UserResponse(
                        login=u["login"],
                        name=u.get("name"),
                        avatar_url=u.get("avatar_url"),
                    )
            finally:
                db.close()
    except Exception:
        pass

    # Fallback: direct GitHub token
    try:
        from src.context.user_profile import get_user_profile
        profile = get_user_profile(token)
        if profile:
            return UserResponse(
                login=profile.get("login", "unknown"),
                name=profile.get("name"),
                avatar_url=profile.get("avatar_url"),
            )
    except Exception:
        pass

    raise HTTPException(401, "Invalid token")


def get_user_github_token(user_id: int) -> str | None:
    """Retrieve stored GitHub token for a user (for API calls)."""
    from src.store.db import UserRepo
    db = UserRepo()
    try:
        return db.get_github_token(user_id)
    finally:
        db.close()


def get_github_token(raw_token: str = Depends(get_token)) -> str:
    """Resolve the authorization header to a valid GitHub API token.

    If the token is a JWT, extracts user and returns their stored GitHub token.
    If it's already a GitHub PAT (ghp_/gho_), returns it directly.
    """
    # Already a GitHub PAT — use directly
    if raw_token.startswith("ghp_") or raw_token.startswith("gho_"):
        return raw_token

    # Try JWT — extract user, get stored GitHub token
    try:
        from backend.auth import verify_jwt
        jwt_user = verify_jwt(raw_token)
        if jwt_user:
            gh_token = get_user_github_token(jwt_user.id)
            if gh_token:
                return gh_token
    except Exception:
        pass

    # Fallback: might work as-is (env token, etc.)
    return raw_token
