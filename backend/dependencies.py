"""FastAPI dependencies — token extraction, user resolution, DB sessions."""

import os
from fastapi import Depends, HTTPException, Header
from backend.models import UserResponse


def get_token(authorization: str = Header(None)) -> str:
    """Extract Bearer token from Authorization header."""
    if not authorization:
        # Fallback to env GITHUB_TOKEN for local/CLI use
        token = os.getenv("GITHUB_TOKEN", "")
        if token:
            return token
        raise HTTPException(401, "Authorization header or GITHUB_TOKEN required")
    if authorization.startswith("Bearer "):
        return authorization[7:]
    return authorization


def get_current_user(token: str = Depends(get_token)) -> UserResponse:
    """Resolve the current user from their GitHub token."""
    try:
        from src.context.user_profile import get_user_profile
        profile = get_user_profile(token)
        if not profile:
            raise HTTPException(401, "Invalid token")
        return UserResponse(
            login=profile.get("login", "unknown"),
            name=profile.get("name"),
            avatar_url=profile.get("avatar_url"),
        )
    except Exception as e:
        raise HTTPException(401, f"Failed to resolve user: {e}")
