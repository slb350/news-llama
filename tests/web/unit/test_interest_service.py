"""
Unit tests for InterestService - TDD RED phase.

Tests interest management operations:
- get_all_predefined: List pre-configured interest categories
- search_interests: Fuzzy search for interests by query
- add_user_interest: Add interest to user profile
- remove_user_interest: Remove interest from user
- get_user_interests: Get all interests for a user
- get_predefined_interests: Get list of standard interests
"""

import pytest
from sqlalchemy.orm import Session

from src.web.services.interest_service import (
    get_predefined_interests,
    search_interests,
    add_user_interest,
    remove_user_interest,
    get_user_interests,
    InterestNotFoundError,
    InterestValidationError,
    DuplicateInterestError,
)
from src.web.services.user_service import create_user
from src.web.database import get_test_db


@pytest.fixture
def db():
    """Provide test database session."""
    yield from get_test_db()


@pytest.fixture
def user(db: Session):
    """Create test user."""
    return create_user(db, first_name="TestUser")


# Predefined interests that should be available
EXPECTED_PREDEFINED_INTERESTS = [
    "AI",
    "rust",
    "LocalLLM",
    "LocalLlama",
    "strix halo",
    "startups",
    "technology",
    "programming",
    "machine learning",
    "web development",
    "databases",
    "devops",
    "security",
    "python",
    "javascript",
    "go",
    "systems programming",
]


class TestGetPredefinedInterests:
    """Tests for get_predefined_interests function."""

    def test_get_predefined_interests_returns_list(self, db: Session):
        """Should return list of predefined interest strings."""
        interests = get_predefined_interests()

        assert isinstance(interests, list)
        assert len(interests) > 0
        assert all(isinstance(i, str) for i in interests)

    def test_get_predefined_interests_includes_expected(self, db: Session):
        """Should include expected interests from mockup."""
        interests = get_predefined_interests()

        # Check that key interests from mockup are present
        assert "AI" in interests
        assert "rust" in interests
        assert "LocalLLM" in interests
        assert "startups" in interests
        assert "technology" in interests

    def test_get_predefined_interests_alphabetically_sorted(self, db: Session):
        """Should return interests in alphabetical order."""
        interests = get_predefined_interests()

        assert interests == sorted(interests)


class TestSearchInterests:
    """Tests for search_interests function."""

    def test_search_interests_exact_match(self, db: Session):
        """Should find exact match."""
        results = search_interests("AI")

        assert "AI" in results

    def test_search_interests_case_insensitive(self, db: Session):
        """Should match regardless of case."""
        results_lower = search_interests("ai")
        results_upper = search_interests("AI")
        results_mixed = search_interests("Ai")

        assert "AI" in results_lower
        assert "AI" in results_upper
        assert "AI" in results_mixed

    def test_search_interests_partial_match(self, db: Session):
        """Should find partial matches."""
        results = search_interests("prog")

        # Should match "programming" and "systems programming"
        matching = [i for i in results if "prog" in i.lower()]
        assert len(matching) > 0

    def test_search_interests_empty_query(self, db: Session):
        """Should return all interests for empty query."""
        results = search_interests("")

        predefined = get_predefined_interests()
        assert len(results) == len(predefined)

    def test_search_interests_no_matches(self, db: Session):
        """Should return empty list for no matches."""
        results = search_interests("xyznonexistent")

        assert results == []

    def test_search_interests_with_spaces(self, db: Session):
        """Should handle multi-word queries."""
        results = search_interests("machine learn")

        # Should match "machine learning"
        assert any("machine learning" in i.lower() for i in results)


class TestAddUserInterest:
    """Tests for add_user_interest function."""

    def test_add_user_interest_predefined(self, db: Session, user):
        """Should add predefined interest to user."""
        interest = add_user_interest(db, user.id, "AI", is_predefined=True)

        assert interest.id is not None
        assert interest.user_id == user.id
        assert interest.interest_name == "AI"
        assert interest.is_predefined is True
        assert interest.added_at is not None

    def test_add_user_interest_custom(self, db: Session, user):
        """Should add custom interest to user."""
        interest = add_user_interest(
            db, user.id, "Custom Interest", is_predefined=False
        )

        assert interest.user_id == user.id
        assert interest.interest_name == "Custom Interest"
        assert interest.is_predefined is False

    def test_add_user_interest_multiple(self, db: Session, user):
        """Should add multiple interests to same user."""
        add_user_interest(db, user.id, "AI", is_predefined=True)
        add_user_interest(db, user.id, "rust", is_predefined=True)
        add_user_interest(db, user.id, "Custom", is_predefined=False)

        interests = get_user_interests(db, user.id)
        assert len(interests) == 3

    def test_add_user_interest_duplicate_fails(self, db: Session, user):
        """Should raise DuplicateInterestError for duplicate."""
        add_user_interest(db, user.id, "AI", is_predefined=True)

        with pytest.raises(
            DuplicateInterestError, match="User already has interest 'AI'"
        ):
            add_user_interest(db, user.id, "AI", is_predefined=True)

    def test_add_user_interest_case_insensitive_duplicate(self, db: Session, user):
        """Should detect duplicates regardless of case."""
        add_user_interest(db, user.id, "AI", is_predefined=True)

        with pytest.raises(DuplicateInterestError):
            add_user_interest(db, user.id, "ai", is_predefined=True)

    def test_add_user_interest_empty_name_fails(self, db: Session, user):
        """Should raise ValidationError for empty name."""
        with pytest.raises(
            InterestValidationError, match="Interest name cannot be empty"
        ):
            add_user_interest(db, user.id, "", is_predefined=True)

    def test_add_user_interest_whitespace_only_fails(self, db: Session, user):
        """Should raise ValidationError for whitespace-only name."""
        with pytest.raises(
            InterestValidationError, match="Interest name cannot be empty"
        ):
            add_user_interest(db, user.id, "   ", is_predefined=True)

    def test_add_user_interest_too_long_fails(self, db: Session, user):
        """Should raise ValidationError for name exceeding 200 characters."""
        long_name = "A" * 201
        with pytest.raises(
            InterestValidationError, match="Interest name cannot exceed 200 characters"
        ):
            add_user_interest(db, user.id, long_name, is_predefined=False)

    def test_add_user_interest_invalid_user_id(self, db: Session):
        """Should raise error for non-existent user."""
        with pytest.raises(Exception):  # Will raise foreign key or user not found error
            add_user_interest(db, 999, "AI", is_predefined=True)


class TestRemoveUserInterest:
    """Tests for remove_user_interest function."""

    def test_remove_user_interest_success(self, db: Session, user):
        """Should remove interest from user."""
        add_user_interest(db, user.id, "AI", is_predefined=True)

        result = remove_user_interest(db, user.id, "AI")

        assert result is True
        interests = get_user_interests(db, user.id)
        assert len(interests) == 0

    def test_remove_user_interest_case_insensitive(self, db: Session, user):
        """Should remove interest regardless of case."""
        add_user_interest(db, user.id, "AI", is_predefined=True)

        result = remove_user_interest(db, user.id, "ai")

        assert result is True
        interests = get_user_interests(db, user.id)
        assert len(interests) == 0

    def test_remove_user_interest_not_found(self, db: Session, user):
        """Should raise InterestNotFoundError for non-existent interest."""
        with pytest.raises(
            InterestNotFoundError, match="Interest 'NonExistent' not found for user"
        ):
            remove_user_interest(db, user.id, "NonExistent")

    def test_remove_user_interest_leaves_others(self, db: Session, user):
        """Should only remove specified interest."""
        add_user_interest(db, user.id, "AI", is_predefined=True)
        add_user_interest(db, user.id, "rust", is_predefined=True)
        add_user_interest(db, user.id, "python", is_predefined=True)

        remove_user_interest(db, user.id, "rust")

        interests = get_user_interests(db, user.id)
        interest_names = [i.interest_name for i in interests]
        assert len(interests) == 2
        assert "AI" in interest_names
        assert "python" in interest_names
        assert "rust" not in interest_names


class TestGetUserInterests:
    """Tests for get_user_interests function."""

    def test_get_user_interests_empty(self, db: Session, user):
        """Should return empty list for user with no interests."""
        interests = get_user_interests(db, user.id)

        assert interests == []

    def test_get_user_interests_multiple(self, db: Session, user):
        """Should return all interests for user."""
        add_user_interest(db, user.id, "AI", is_predefined=True)
        add_user_interest(db, user.id, "rust", is_predefined=True)
        add_user_interest(db, user.id, "Custom", is_predefined=False)

        interests = get_user_interests(db, user.id)

        assert len(interests) == 3
        interest_names = [i.interest_name for i in interests]
        assert "AI" in interest_names
        assert "rust" in interest_names
        assert "Custom" in interest_names

    def test_get_user_interests_ordered_by_added_at(self, db: Session, user):
        """Should return interests in order they were added."""
        add_user_interest(db, user.id, "First", is_predefined=True)
        add_user_interest(db, user.id, "Second", is_predefined=True)
        add_user_interest(db, user.id, "Third", is_predefined=False)

        interests = get_user_interests(db, user.id)

        assert interests[0].interest_name == "First"
        assert interests[1].interest_name == "Second"
        assert interests[2].interest_name == "Third"

    def test_get_user_interests_different_users(self, db: Session):
        """Should isolate interests between users."""
        user1 = create_user(db, first_name="User1")
        user2 = create_user(db, first_name="User2")

        add_user_interest(db, user1.id, "AI", is_predefined=True)
        add_user_interest(db, user1.id, "rust", is_predefined=True)
        add_user_interest(db, user2.id, "python", is_predefined=True)

        interests1 = get_user_interests(db, user1.id)
        interests2 = get_user_interests(db, user2.id)

        assert len(interests1) == 2
        assert len(interests2) == 1
        assert interests1[0].user_id == user1.id
        assert interests2[0].user_id == user2.id

    def test_get_user_interests_includes_metadata(self, db: Session, user):
        """Should include all interest metadata."""
        add_user_interest(db, user.id, "AI", is_predefined=True)

        interests = get_user_interests(db, user.id)
        interest = interests[0]

        assert hasattr(interest, "id")
        assert hasattr(interest, "user_id")
        assert hasattr(interest, "interest_name")
        assert hasattr(interest, "is_predefined")
        assert hasattr(interest, "added_at")
        assert interest.is_predefined is True
