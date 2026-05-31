"""Settings router — save/load user preferences."""

from fastapi import APIRouter
from pydantic import BaseModel

from backend.dependencies import get_github_token
from backend.middleware import require_permission

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    min_confidence: float = 0.0
    max_inline_comments: int = 0
    review_mode: str = ""


@router.get("")
def get_settings(token: str = Depends(get_github_token)):
    """Return current user's settings from DB."""
    from src.store.db import _DEFAULT_PATH
    import sqlite3
    from backend.dependencies import get_current_user

    try:
        user = get_current_user(token)
        # Try to get user_id from JWT
        from backend.auth import verify_jwt
        jwt_user = verify_jwt(token)
        user_id = jwt_user.id if jwt_user else None
    except Exception:
        user_id = None

    if not user_id:
        return {"status": "ok", "settings": {}}

    conn = sqlite3.connect(_DEFAULT_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM user_settings WHERE user_id=?", (user_id,)).fetchone()
        if row:
            return {"status": "ok", "settings": dict(row)}
        return {"status": "ok", "settings": {"llm_provider": "deepseek", "llm_model": "deepseek-chat", "min_confidence": 0.65, "max_inline_comments": 10, "review_mode": "balanced"}}
    finally:
        conn.close()


@router.post("")
def save_settings(req: SettingsUpdate, token: str = Depends(get_github_token)):
    """Save user settings to DB."""
    import sqlite3
    from src.store.db import _DEFAULT_PATH

    try:
        from backend.auth import verify_jwt
        jwt_user = verify_jwt(token)
        user_id = jwt_user.id if jwt_user else None
    except Exception:
        user_id = None

    if not user_id:
        return {"status": "error", "message": "Authentication required"}

    conn = sqlite3.connect(_DEFAULT_PATH)
    try:
        conn.execute(
            """INSERT INTO user_settings (user_id, llm_provider, llm_api_key, llm_model,
               min_confidence, max_inline_comments, review_mode)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET
               llm_provider=excluded.llm_provider,
               llm_api_key=excluded.llm_api_key,
               llm_model=excluded.llm_model,
               min_confidence=excluded.min_confidence,
               max_inline_comments=excluded.max_inline_comments,
               review_mode=excluded.review_mode,
               updated_at=datetime('now')""",
            (user_id, req.llm_provider, req.llm_api_key, req.llm_model,
             req.min_confidence or 0.65, req.max_inline_comments or 10, req.review_mode or "balanced")
        )
        conn.commit()
    finally:
        conn.close()

    return {"status": "ok", "message": "Settings saved"}
