"""
Unit tests for UserService - TDD RED phase.

Tests CRUD operations for user management:
- create_user: Create new users with validation
- get_user: Retrieve user by ID
- get_all_users: List all users
- update_user: Modify user details
- delete_user: Remove user and cascade deletions
"""

import pytest
from sqlalchemy.orm import Session

from src.web.services.user_service import (
    create_user,
    get_user,
    get_all_users,
    update_user,
    delete_user,
    UserNotFoundError,
    UserValidationError,
)
from src.web.database import get_test_db


@pytest.fixture
def db():
    """Provide test database session."""
    yield from get_test_db()


class TestCreateUser:
    """Tests for create_user function."""

    def test_create_user_success(self, db: Session):
        """Should create user with valid first_name."""
        user = create_user(db, first_name="Alice")

        assert user.id is not None
        assert user.first_name == "Alice"
        assert user.avatar_path is None
        assert user.created_at is not None

    def test_create_user_with_avatar(self, db: Session):
        """Should create user with avatar path."""
        user = create_user(db, first_name="Bob", avatar_path="bob_avatar.png")

        assert user.id is not None
        assert user.first_name == "Bob"
        assert user.avatar_path == "bob_avatar.png"

    def test_create_user_empty_name_fails(self, db: Session):
        """Should raise ValidationError for empty name."""
        with pytest.raises(UserValidationError, match="First name cannot be empty"):
            create_user(db, first_name="")

    def test_create_user_whitespace_only_name_fails(self, db: Session):
        """Should raise ValidationError for whitespace-only name."""
        with pytest.raises(UserValidationError, match="First name cannot be empty"):
            create_user(db, first_name="   ")

    def test_create_user_none_name_fails(self, db: Session):
        """Should raise ValidationError for None name."""
        with pytest.raises(UserValidationError, match="First name is required"):
            create_user(db, first_name=None)

    def test_create_user_too_long_name_fails(self, db: Session):
        """Should raise ValidationError for name exceeding 100 characters."""
        long_name = "A" * 101
        with pytest.raises(
            UserValidationError, match="First name cannot exceed 100 characters"
        ):
            create_user(db, first_name=long_name)

    def test_create_multiple_users(self, db: Session):
        """Should create multiple users with unique IDs."""
        user1 = create_user(db, first_name="Alice")
        user2 = create_user(db, first_name="Bob")
        user3 = create_user(db, first_name="Charlie")

        assert user1.id != user2.id != user3.id
        assert get_all_users(db) == [user1, user2, user3]


class TestGetUser:
    """Tests for get_user function."""

    def test_get_user_success(self, db: Session):
        """Should retrieve existing user by ID."""
        user = create_user(db, first_name="Alice")

        retrieved = get_user(db, user.id)

        assert retrieved.id == user.id
        assert retrieved.first_name == "Alice"

    def test_get_user_not_found(self, db: Session):
        """Should raise UserNotFoundError for non-existent ID."""
        with pytest.raises(UserNotFoundError, match="User with ID 999 not found"):
            get_user(db, user_id=999)

    def test_get_user_invalid_id_type(self, db: Session):
        """Should raise ValidationError for invalid ID type."""
        with pytest.raises(UserValidationError, match="User ID must be an integer"):
            get_user(db, user_id="invalid")


class TestGetAllUsers:
    """Tests for get_all_users function."""

    def test_get_all_users_empty(self, db: Session):
        """Should return empty list when no users exist."""
        users = get_all_users(db)

        assert users == []

    def test_get_all_users_multiple(self, db: Session):
        """Should return all users ordered by creation time."""
        user1 = create_user(db, first_name="Alice")
        user2 = create_user(db, first_name="Bob")
        user3 = create_user(db, first_name="Charlie")

        users = get_all_users(db)

        assert len(users) == 3
        assert users[0].id == user1.id
        assert users[1].id == user2.id
        assert users[2].id == user3.id


class TestUpdateUser:
    """Tests for update_user function."""

    def test_update_user_first_name(self, db: Session):
        """Should update user's first name."""
        user = create_user(db, first_name="Alice")

        updated = update_user(db, user.id, first_name="Alicia")

        assert updated.id == user.id
        assert updated.first_name == "Alicia"
        assert updated.avatar_path is None

    def test_update_user_avatar_path(self, db: Session):
        """Should update user's avatar path."""
        user = create_user(db, first_name="Bob")

        updated = update_user(db, user.id, avatar_path="new_avatar.png")

        assert updated.id == user.id
        assert updated.first_name == "Bob"
        assert updated.avatar_path == "new_avatar.png"

    def test_update_user_both_fields(self, db: Session):
        """Should update both first name and avatar."""
        user = create_user(db, first_name="Charlie")

        updated = update_user(
            db, user.id, first_name="Charles", avatar_path="charlie.png"
        )

        assert updated.first_name == "Charles"
        assert updated.avatar_path == "charlie.png"

    def test_update_user_not_found(self, db: Session):
        """Should raise UserNotFoundError for non-existent user."""
        with pytest.raises(UserNotFoundError, match="User with ID 999 not found"):
            update_user(db, user_id=999, first_name="Nobody")

    def test_update_user_empty_name_fails(self, db: Session):
        """Should raise ValidationError for empty name."""
        user = create_user(db, first_name="Alice")

        with pytest.raises(UserValidationError, match="First name cannot be empty"):
            update_user(db, user.id, first_name="")

    def test_update_user_no_changes(self, db: Session):
        """Should return user unchanged when no fields provided."""
        user = create_user(db, first_name="Alice", avatar_path="alice.png")

        updated = update_user(db, user.id)

        assert updated.first_name == "Alice"
        assert updated.avatar_path == "alice.png"


class TestDeleteUser:
    """Tests for delete_user function."""

    def test_delete_user_success(self, db: Session):
        """Should delete user and return True."""
        user = create_user(db, first_name="Alice")

        result = delete_user(db, user.id)

        assert result is True
        with pytest.raises(UserNotFoundError):
            get_user(db, user.id)

    def test_delete_user_not_found(self, db: Session):
        """Should raise UserNotFoundError for non-existent user."""
        with pytest.raises(UserNotFoundError, match="User with ID 999 not found"):
            delete_user(db, user_id=999)

    def test_delete_user_cascades_to_interests(self, db: Session):
        """Should cascade delete to user_interests table."""
        from src.web.services.interest_service import (
            add_user_interest,
            get_user_interests,
        )

        user = create_user(db, first_name="Alice")
        add_user_interest(db, user.id, "AI", is_predefined=True)
        add_user_interest(db, user.id, "rust", is_predefined=True)

        # Verify interests exist
        interests = get_user_interests(db, user.id)
        assert len(interests) == 2

        delete_user(db, user.id)

        # Verify user was deleted
        with pytest.raises(UserNotFoundError):
            get_user(db, user.id)

        # Verify interests were cascade deleted
        # Query directly since user doesn't exist anymore
        from src.web.models import UserInterest

        remaining_interests = (
            db.query(UserInterest).filter(UserInterest.user_id == user.id).all()
        )
        assert len(remaining_interests) == 0

    def test_delete_user_cascades_to_newsletters(self, db: Session):
        """Should cascade delete to newsletters table."""
        from src.web.services.newsletter_service import (
            create_pending_newsletter,
            get_newsletter_count,
        )
        from datetime import date

        user = create_user(db, first_name="Bob")
        _newsletter = create_pending_newsletter(db, user.id, date.today())

        # Verify newsletter exists
        assert get_newsletter_count(db, user.id) == 1

        delete_user(db, user.id)

        # Verify user was deleted
        with pytest.raises(UserNotFoundError):
            get_user(db, user.id)

        # Verify newsletters were cascade deleted
        # Query directly since user doesn't exist anymore
        from src.web.models import Newsletter

        remaining_newsletters = (
            db.query(Newsletter).filter(Newsletter.user_id == user.id).all()
        )
        assert len(remaining_newsletters) == 0
        assert get_all_users(db) == []

    def test_delete_user_removes_avatar_file(self, db: Session, tmp_path):
        """Should delete avatar file from disk when user is deleted."""
        from pathlib import Path

        # Create a test avatar file
        avatars_dir = tmp_path / "avatars"
        avatars_dir.mkdir()
        avatar_filename = "test-avatar.jpg"
        avatar_path = avatars_dir / avatar_filename
        avatar_path.write_text("fake avatar data")

        # Create user with avatar
        user = create_user(db, first_name="AvatarUser", avatar_path=avatar_filename)

        # Verify avatar file exists
        assert avatar_path.exists()

        # Mock the avatars directory to use tmp_path
        import src.web.services.user_service as user_service_module

        original_avatars_path = getattr(
            user_service_module, "AVATARS_DIR", Path("src/web/static/avatars")
        )

        try:
            # Temporarily override the avatars directory
            user_service_module.AVATARS_DIR = avatars_dir

            # Delete user
            delete_user(db, user.id)

            # Verify avatar file was deleted
            assert not avatar_path.exists()
        finally:
            # Restore original path
            if hasattr(user_service_module, "AVATARS_DIR"):
                user_service_module.AVATARS_DIR = original_avatars_path

    def test_delete_user_without_avatar_succeeds(self, db: Session):
        """Should successfully delete user even if they have no avatar."""
        user = create_user(db, first_name="NoAvatar", avatar_path=None)

        # Should not raise exception
        delete_user(db, user.id)

        # Verify user was deleted
        with pytest.raises(UserNotFoundError):
            get_user(db, user.id)

    def test_delete_user_removes_newsletter_files(self, db: Session, tmp_path):
        """Should delete newsletter HTML files from disk when user is deleted."""
        from src.web.models import Newsletter
        from datetime import datetime

        # Create output directory
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create user and newsletters with files
        user = create_user(db, first_name="NewsletterUser")

        newsletter1_path = output_dir / "news-2025-01-01-guid1.html"
        newsletter1_path.write_text("<html>Newsletter 1</html>")

        newsletter2_path = output_dir / "news-2025-01-02-guid2.html"
        newsletter2_path.write_text("<html>Newsletter 2</html>")

        # Create newsletter records
        newsletter1 = Newsletter(
            user_id=user.id,
            date="2025-01-01",
            guid="guid1",
            file_path=str(newsletter1_path),
            status="completed",
            generated_at=datetime.now().isoformat(),
        )
        newsletter2 = Newsletter(
            user_id=user.id,
            date="2025-01-02",
            guid="guid2",
            file_path=str(newsletter2_path),
            status="completed",
            generated_at=datetime.now().isoformat(),
        )
        db.add(newsletter1)
        db.add(newsletter2)
        db.commit()

        # Verify files exist
        assert newsletter1_path.exists()
        assert newsletter2_path.exists()

        # Delete user
        delete_user(db, user.id)

        # Verify newsletter files were deleted
        assert not newsletter1_path.exists()
        assert not newsletter2_path.exists()

    def test_delete_user_handles_missing_newsletter_files(self, db: Session):
        """Should gracefully handle newsletter records with missing files."""
        from src.web.models import Newsletter
        from datetime import datetime

        # Create user and newsletter record WITHOUT creating the file
        user = create_user(db, first_name="MissingFile")

        newsletter = Newsletter(
            user_id=user.id,
            date="2025-01-01",
            guid="guid-missing",
            file_path="/nonexistent/path/news.html",
            status="completed",
            generated_at=datetime.now().isoformat(),
        )
        db.add(newsletter)
        db.commit()

        # Should not raise exception even though file doesn't exist
        delete_user(db, user.id)

        # Verify user was deleted
        with pytest.raises(UserNotFoundError):
            get_user(db, user.id)
