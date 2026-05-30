"""Auth router — OAuth callback, JWT login, token refresh, user profile."""

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
    """Exchange OAuth code → find/create user → issue JWT."""
    from src.auth.github_oauth import exchange_code_for_token, get_oauth_user
    from src.store.db import UserRepo
    from backend.auth import issue_jwt

    client_id = os.getenv("GITHUB_CLIENT_ID", "")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return {"error": "GitHub OAuth not configured"}

    token = exchange_code_for_token(code, client_id, client_secret)
    if not token:
        return {"error": "Failed to exchange code"}

    gh_user = get_oauth_user(token)
    if not gh_user:
        return {"error": "Failed to fetch user"}

    # Find or create local user
    db = UserRepo()
    try:
        github_id = int(gh_user.login.encode().hex(), 16) % (10**12)  # derive stable ID from login
        user = db.find_or_create_by_github(
            github_id=github_id,
            login=gh_user.login,
            name=gh_user.name,
            email=gh_user.email,
            avatar_url=gh_user.avatar_url,
        )
        # Store GitHub token for later API calls
        db.save_github_token(user["id"], token,
                            scopes="read:user,read:org,repo")
    finally:
        db.close()

    jwt = issue_jwt(user["id"], user["login"], user["github_id"])

    return {
        "access_token": jwt,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "login": user["login"],
            "name": user.get("name"),
            "avatar_url": user.get("avatar_url"),
        }
    }


@router.post("/token")
def token_login(token: str):
    """Login with GitHub personal access token — find/create user + issue JWT."""
    from src.context.user_profile import get_user_profile
    from src.store.db import UserRepo
    from backend.auth import issue_jwt

    profile = get_user_profile(token)
    if not profile:
        return {"error": "Invalid token"}

    db = UserRepo()
    try:
        github_login = profile.get("login", "unknown")
        github_id = profile.get("id", 0)
        if not github_id:
            github_id = int(github_login.encode().hex(), 16) % (10**12)

        user = db.find_or_create_by_github(
            github_id=github_id,
            login=github_login,
            name=profile.get("name"),
            email=profile.get("email"),
            avatar_url=profile.get("avatar_url"),
        )
        db.save_github_token(user["id"], token,
                            scopes="read:user,read:org,repo")
    finally:
        db.close()

    jwt = issue_jwt(user["id"], user["login"], user["github_id"])

    return {
        "access_token": jwt,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "login": user["login"],
            "name": user.get("name"),
            "avatar_url": user.get("avatar_url"),
        }
    }


@router.post("/refresh")
def refresh(refresh_token: str):
    """Exchange refresh token for new JWT."""
    from backend.auth import refresh_access_token
    new_jwt = refresh_access_token(refresh_token)
    if not new_jwt:
        return {"error": "Invalid or expired refresh token"}
    return {"access_token": new_jwt, "token_type": "bearer"}
