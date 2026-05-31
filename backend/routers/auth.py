"""Auth router — register, login, OAuth callback, JWT, token refresh."""

import os
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.dependencies import get_token, get_current_user
from backend.models import UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str = ""
    phone: str = ""
    password: str = ""
    name: str = ""


class LoginRequest(BaseModel):
    email: str = ""
    phone: str = ""
    password: str = ""


@router.post("/register")
def register(req: RegisterRequest):
    """Register a new account by email or phone."""
    from src.store.db import UserRepo
    from backend.auth import issue_jwt
    db = UserRepo()
    try:
        if req.email:
            user = db.register_by_email(req.email, req.password, req.name)
        elif req.phone:
            user = db.register_by_phone(req.phone, req.password, req.name)
        else:
            return {"error": "Email or phone required"}
        if not user:
            return {"error": "Account already exists"}
        jwt = issue_jwt(user["id"], user["login"], 0)
        return {"access_token": jwt, "token_type": "bearer", "user": user}
    finally:
        db.close()


@router.post("/login")
def login(req: LoginRequest):
    """Login by email or phone with password."""
    from src.store.db import UserRepo
    from backend.auth import issue_jwt
    db = UserRepo()
    try:
        if req.email:
            user = db.authenticate_by_email(req.email, req.password)
        elif req.phone:
            user = db.authenticate_by_phone(req.phone, req.password)
        else:
            return {"error": "Email or phone required"}
        if not user:
            return {"error": "Invalid credentials"}
        github_id = user.get("github_id") or 0
        jwt = issue_jwt(user["id"], user["login"], github_id)
        return {"access_token": jwt, "token_type": "bearer", "user": {"id": user["id"], "login": user["login"], "email": user.get("email"), "phone": user.get("phone")}}
    finally:
        db.close()


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
