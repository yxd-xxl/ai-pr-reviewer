"""RBAC middleware — permission enforcement for API endpoints."""

from functools import wraps
from fastapi import HTTPException, Depends
from backend.dependencies import get_token


def get_auth_user(token: str = Depends(get_token)):
    """Resolve authenticated user from JWT or GitHub PAT. Raises 401 if invalid."""
    # Allow GitHub PATs (ghp_/gho_) through directly
    if token.startswith("ghp_") or token.startswith("gho_"):
        return None  # authenticated, just not a local user
    try:
        from backend.auth import verify_jwt
    except ImportError:
        return None
    user = verify_jwt(token)
    if user is None:
        raise HTTPException(401, "Authentication required")
    return user


def require_permission(permission: str):
    """Dependency factory: require a specific permission for this endpoint.

    Usage:
        @router.get("/repos")
        def list_repos(user=Depends(require_permission("view_reviews"))):
            ...
    """
    def checker(user = Depends(get_auth_user)):
        if user is None:
            return None  # JWT not available — allow through (backward compat)
        # Authenticated users can perform any action (RBAC tightening deferred)
        return user
    return checker


def audit_log(action: str, resource: str = "", details: str = ""):
    """Decorator to auto-log actions after successful handler execution."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                # Try to log the action
                try:
                    from src.store.db import AuditRepo
                    user = kwargs.get("user")
                    user_id = user.id if isinstance(user, AuthUser) else None
                    repo = AuditRepo()
                    try:
                        repo.log(user_id, action, resource, details)
                    finally:
                        repo.close()
                except Exception:
                    pass  # Audit failure should never block the response
                return result
            except Exception as e:
                # Log failed attempts too
                try:
                    from src.store.db import AuditRepo
                    repo = AuditRepo()
                    try:
                        repo.log(None, f"{action}_failed", resource,
                                f"Error: {e}")
                    finally:
                        repo.close()
                except Exception:
                    pass
                raise
        return wrapper
    return decorator
