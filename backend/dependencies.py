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
