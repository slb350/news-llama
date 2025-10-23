"""
User service for News Llama web application.

Provides CRUD operations for user management with validation and error handling.
Follows TDD approach with comprehensive test coverage.
"""

from typing import Optional
from pathlib import Path
from sqlalchemy.orm import Session

from src.web.models import User, Newsletter

# Directory paths for file cleanup
AVATARS_DIR = Path("src/web/static/avatars")


# Custom Exceptions
class UserServiceError(Exception):
    """Base exception for user service errors."""

    pass


class UserNotFoundError(UserServiceError):
    """Raised when user is not found."""

    pass


class UserValidationError(UserServiceError):
    """Raised when user data validation fails."""

    pass


def create_user(
    db: Session, first_name: Optional[str], avatar_path: Optional[str] = None
) -> User:
    """
    Create a new user.

    Args:
        db: Database session
        first_name: User's first name (required, 1-100 chars)
        avatar_path: Optional path to avatar image

    Returns:
        Created User object with generated ID

    Raises:
        UserValidationError: If validation fails
    """
    # Validation
    if first_name is None:
        raise UserValidationError("First name is required")

    first_name = first_name.strip()

    if not first_name:
        raise UserValidationError("First name cannot be empty")

    if len(first_name) > 100:
        raise UserValidationError("First name cannot exceed 100 characters")

    # Create user - let database handle created_at default
    user = User(first_name=first_name, avatar_path=avatar_path)

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_user(db: Session, user_id: int) -> User:
    """
    Retrieve user by ID.

    Args:
        db: Database session
        user_id: User ID to retrieve

    Returns:
        User object

    Raises:
        UserNotFoundError: If user doesn't exist
        UserValidationError: If user_id is invalid type
    """
    # Validate ID type
    if not isinstance(user_id, int):
        raise UserValidationError("User ID must be an integer")

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise UserNotFoundError(f"User with ID {user_id} not found")

    return user


def get_all_users(db: Session) -> list[User]:
    """
    Retrieve all users ordered by creation time.

    Args:
        db: Database session

    Returns:
        List of User objects (empty list if none exist)
    """
    return db.query(User).order_by(User.created_at).all()


def update_user(
    db: Session,
    user_id: int,
    first_name: Optional[str] = None,
    avatar_path: Optional[str] = None,
) -> User:
    """
    Update user details.

    Args:
        db: Database session
        user_id: User ID to update
        first_name: New first name (optional)
        avatar_path: New avatar path (optional)

    Returns:
        Updated User object

    Raises:
        UserNotFoundError: If user doesn't exist
        UserValidationError: If validation fails
    """
    user = get_user(db, user_id)

    # Update first_name if provided
    if first_name is not None:
        first_name = first_name.strip()

        if not first_name:
            raise UserValidationError("First name cannot be empty")

        if len(first_name) > 100:
            raise UserValidationError("First name cannot exceed 100 characters")

        user.first_name = first_name

    # Update avatar_path if provided
    if avatar_path is not None:
        user.avatar_path = avatar_path

    db.commit()
    db.refresh(user)

    return user


def delete_user(db: Session, user_id: int) -> bool:
    """
    Delete user by ID.

    Cascades to user_interests and newsletters tables due to foreign key constraints.
    Also cleans up avatar and newsletter files from disk.

    Args:
        db: Database session
        user_id: User ID to delete

    Returns:
        True if user was deleted

    Raises:
        UserNotFoundError: If user doesn't exist
    """
    user = get_user(db, user_id)

    # Clean up avatar file if exists
    if user.avatar_path:
        avatar_full_path = AVATARS_DIR / user.avatar_path
        if avatar_full_path.exists():
            try:
                avatar_full_path.unlink()
            except OSError:
                # Log error but don't fail deletion if file cleanup fails
                pass

    # Clean up newsletter files
    newsletters = db.query(Newsletter).filter(Newsletter.user_id == user_id).all()
    for newsletter in newsletters:
        if newsletter.file_path:
            newsletter_path = Path(newsletter.file_path)
            if newsletter_path.exists():
                try:
                    newsletter_path.unlink()
                except OSError:
                    # Log error but don't fail deletion if file cleanup fails
                    pass

    # Delete user from database (cascades to interests and newsletters)
    db.delete(user)
    db.commit()

    return True
