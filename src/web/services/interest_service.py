"""
Interest service for News Llama web application.

Provides interest management operations with fuzzy search and validation.
Supports both predefined categories and custom user interests.
"""

from sqlalchemy.orm import Session

from src.web.models import UserInterest


# Custom Exceptions
class InterestServiceError(Exception):
    """Base exception for interest service errors."""

    pass


class InterestNotFoundError(InterestServiceError):
    """Raised when interest is not found."""

    pass


class InterestValidationError(InterestServiceError):
    """Raised when interest data validation fails."""

    pass


class DuplicateInterestError(InterestServiceError):
    """Raised when attempting to add duplicate interest."""

    pass


# Predefined interests organized into family-friendly groups
# Balanced for tech/developer audience (40%) + family/general (60%)
PREDEFINED_INTERESTS_GROUPED = {
    "tech": {
        "name": "Tech & Development",
        "emoji": "🔧",
        "interests": [
            "AI & Machine Learning",
            "Rust",
            "Python",
            "JavaScript & Web Dev",
            "Linux",
            "Self-Hosting",
            "Homelab",
            "3D Printing",
            "Mechanical Keyboards",
            "Open Source",
            "Docker & Containers",
            "Raspberry Pi",
        ],
    },
    "creative": {
        "name": "Creative Arts",
        "emoji": "🎨",
        "interests": [
            "Digital Art & Procreate",
            "Photography",
            "Music Production",
            "Writing & Storytelling",
        ],
    },
    "home": {
        "name": "Home & Living",
        "emoji": "🏡",
        "interests": [
            "Gardening",
            "Interior Design & Aesthetics",
            "Cooking & Recipes",
            "DIY & Home Improvement",
        ],
    },
    "gaming": {
        "name": "Gaming",
        "emoji": "🎮",
        "interests": [
            "Minecraft",
            "Roblox",
            "Indie Games",
        ],
    },
    "lifestyle": {
        "name": "Lifestyle",
        "emoji": "💫",
        "interests": [
            "Fashion & Style",
            "Pets & Animals",
            "Fitness & Wellness",
            "Coffee & Tea Culture",
        ],
    },
    "learning": {
        "name": "Learning & Discovery",
        "emoji": "📚",
        "interests": [
            "Science & Space",
            "History",
            "Today I Learned",
        ],
    },
}


def get_predefined_interests_grouped() -> dict:
    """
    Get predefined interests organized by category groups.

    Returns:
        Dictionary with group keys containing name, emoji, and interests list
    """
    return PREDEFINED_INTERESTS_GROUPED


def get_predefined_interests() -> list[str]:
    """
    Get flat list of all predefined interest categories.

    Flattens grouped interests into alphabetically sorted list for backward compatibility.

    Returns:
        List of predefined interest strings
    """
    all_interests = []
    for group_data in PREDEFINED_INTERESTS_GROUPED.values():
        all_interests.extend(group_data["interests"])
    return sorted(all_interests)


def search_interests(query: str) -> list[str]:
    """
    Search interests with fuzzy matching.

    Performs case-insensitive substring search across predefined interests.
    Returns all interests if query is empty.

    Args:
        query: Search query string

    Returns:
        List of matching interest strings
    """
    if not query or query.strip() == "":
        return get_predefined_interests()

    query_lower = query.lower()
    all_interests = get_predefined_interests()
    matches = [interest for interest in all_interests if query_lower in interest.lower()]

    return sorted(matches)


def add_user_interest(
    db: Session, user_id: int, interest_name: str, is_predefined: bool
) -> UserInterest:
    """
    Add interest to user profile.

    Args:
        db: Database session
        user_id: User ID
        interest_name: Interest name (1-200 chars)
        is_predefined: Whether interest is from predefined list

    Returns:
        Created UserInterest object

    Raises:
        InterestValidationError: If validation fails
        DuplicateInterestError: If user already has this interest
    """
    # Validation
    if not interest_name or not interest_name.strip():
        raise InterestValidationError("Interest name cannot be empty")

    interest_name = interest_name.strip()

    if len(interest_name) > 200:
        raise InterestValidationError("Interest name cannot exceed 200 characters")

    # Check for duplicates (case-insensitive)
    existing = (
        db.query(UserInterest)
        .filter(
            UserInterest.user_id == user_id,
            UserInterest.interest_name.ilike(interest_name),
        )
        .first()
    )

    if existing:
        raise DuplicateInterestError(f"User already has interest '{interest_name}'")

    # Create interest - let database handle added_at default
    user_interest = UserInterest(
        user_id=user_id, interest_name=interest_name, is_predefined=is_predefined
    )

    db.add(user_interest)
    db.commit()
    db.refresh(user_interest)

    return user_interest


def remove_user_interest(db: Session, user_id: int, interest_name: str) -> bool:
    """
    Remove interest from user profile.

    Case-insensitive interest name matching.

    Args:
        db: Database session
        user_id: User ID
        interest_name: Interest name to remove

    Returns:
        True if interest was removed

    Raises:
        InterestNotFoundError: If interest doesn't exist for user
    """
    # Find interest (case-insensitive)
    interest = (
        db.query(UserInterest)
        .filter(
            UserInterest.user_id == user_id,
            UserInterest.interest_name.ilike(interest_name),
        )
        .first()
    )

    if not interest:
        raise InterestNotFoundError(
            f"Interest '{interest_name}' not found for user {user_id}"
        )

    db.delete(interest)
    db.commit()

    return True


def get_user_interests(db: Session, user_id: int) -> list[UserInterest]:
    """
    Get all interests for a user.

    Returns interests ordered by when they were added.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        List of UserInterest objects (empty list if none)
    """
    return (
        db.query(UserInterest)
        .filter(UserInterest.user_id == user_id)
        .order_by(UserInterest.added_at)
        .all()
    )
