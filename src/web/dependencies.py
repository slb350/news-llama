"""
FastAPI dependencies for News Llama web application.

Provides dependency injection for database sessions and user context.
"""

from typing import Optional
from fastapi import Cookie, HTTPException, status, Depends
from sqlalchemy.orm import Session

from src.web.database import get_db
from src.web.models import User


def get_current_user(
    user_id: Optional[str] = Cookie(None), db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from cookie.

    Simple cookie-based session management for multi-user profiles.
    No password authentication - just profile selection.

    Args:
        user_id: User ID from cookie
        db: Database session

    Returns:
        User object if valid cookie, None otherwise

    Example:
        @app.get("/calendar")
        def calendar(user: User = Depends(get_current_user)):
            if not user:
                return RedirectResponse("/")
            ...
    """
    if not user_id:
        return None

    try:
        user_id_int = int(user_id)
    except ValueError:
        return None

    user = db.query(User).filter(User.id == user_id_int).first()
    return user


def require_user(
    user_id: Optional[str] = Cookie(None), db: Session = Depends(get_db)
) -> User:
    """
    Require authenticated user (raises 401 if not found).

    Use this for API endpoints that require a user context.

    Args:
        user_id: User ID from cookie
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: 401 if no valid user session

    Example:
        @app.post("/profile/settings")
        def update_settings(user: User = Depends(require_user)):
            ...
    """
    user = get_current_user(user_id, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active user session. Please select a profile.",
        )

    return user


# Re-export get_db for convenience
__all__ = ["get_db", "get_current_user", "require_user"]
