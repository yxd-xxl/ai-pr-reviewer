"""Auth router — login, callback, user profile."""

import os
from fastapi import APIRouter, Depends
from backend.dependencies import get_token, get_current_user
from backend.models import UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
def me(user: UserResponse = Depends(get_current_user)):
    return user


@router.get("/login")
def login_url(redirect_uri: str = "http://localhost:5174/callback"):
    """Get GitHub OAuth login URL."""
    client_id = os.getenv("GITHUB_CLIENT_ID", "")
    if not client_id:
        return {"url": None, "message": "GITHUB_CLIENT_ID not configured. Use personal token instead."}
    return {
        "url": (f"https://github.com/login/oauth/authorize"
                f"?client_id={client_id}"
                f"&redirect_uri={redirect_uri}"
                f"&scope=read:user,read:org,repo")
    }


@router.post("/callback")
def callback(code: str, state: str = ""):
    """Exchange OAuth code for access token."""
    from src.auth.github_oauth import exchange_code_for_token, get_oauth_user

    client_id = os.getenv("GITHUB_CLIENT_ID", "")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return {"error": "GitHub OAuth not configured"}

    token = exchange_code_for_token(code, client_id, client_secret)
    if not token:
        return {"error": "Failed to exchange code"}

    user = get_oauth_user(token)
    if not user:
        return {"error": "Failed to fetch user"}

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "login": user.login,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "organizations": user.organizations,
        }
    }
