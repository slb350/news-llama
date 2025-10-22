"""Unit tests for SQLAlchemy ORM models.

Following TDD methodology: These tests are written BEFORE implementation.
Expected to FAIL until models are implemented.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# These imports will fail until we create the models - that's expected (RED phase)
from src.web.models import Base, User, Newsletter, UserInterest


@pytest.fixture
def engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()

    # Enable foreign keys for SQLite (SQLAlchemy 2.0 requires text())
    session.execute(text("PRAGMA foreign_keys=ON"))

    yield session
    session.close()


class TestUserModel:
    """Test User ORM model."""

    def test_user_creation_with_required_fields(self, session):
        """Test creating user with only required fields."""
        user = User(first_name="Alice")
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.first_name == "Alice"
        assert user.avatar_path is None
        assert user.created_at is not None
        assert isinstance(user.created_at, str)

    def test_user_creation_with_all_fields(self, session):
        """Test creating user with all fields."""
        user = User(first_name="Bob", avatar_path="avatars/bob.png")
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.first_name == "Bob"
        assert user.avatar_path == "avatars/bob.png"
        assert user.created_at is not None

    def test_user_first_name_required(self, session):
        """Test that first_name is required."""
        user = User()
        session.add(user)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_user_has_relationships(self, session):
        """Test that User has newsletters and interests relationships."""
        user = User(first_name="Charlie")
        session.add(user)
        session.commit()

        # Should have empty collections
        assert hasattr(user, "newsletters")
        assert hasattr(user, "interests")
        assert len(user.newsletters) == 0
        assert len(user.interests) == 0


class TestNewsletterModel:
    """Test Newsletter ORM model."""

    def test_newsletter_creation_with_required_fields(self, session):
        """Test creating newsletter with required fields."""
        user = User(first_name="Alice")
        session.add(user)
        session.commit()

        newsletter = Newsletter(
            user_id=user.id,
            date="2025-10-22",
            guid="550e8400-e29b-41d4-a716-446655440000",
            file_path="output/550e8400.html",
        )
        session.add(newsletter)
        session.commit()

        assert newsletter.id is not None
        assert newsletter.user_id == user.id
        assert newsletter.date == "2025-10-22"
        assert newsletter.guid == "550e8400-e29b-41d4-a716-446655440000"
        assert newsletter.file_path == "output/550e8400.html"
        assert newsletter.status == "pending"  # default
        assert newsletter.generated_at is None
        assert newsletter.retry_count == 0  # default

    def test_newsletter_status_constraint(self, session):
        """Test that status must be one of allowed values."""
        user = User(first_name="Bob")
        session.add(user)
        session.commit()

        newsletter = Newsletter(
            user_id=user.id,
            date="2025-10-22",
            guid="550e8400-e29b-41d4-a716-446655440001",
            file_path="output/test.html",
            status="invalid_status",
        )
        session.add(newsletter)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_newsletter_guid_unique(self, session):
        """Test that guid must be unique."""
        user = User(first_name="Charlie")
        session.add(user)
        session.commit()

        newsletter1 = Newsletter(
            user_id=user.id,
            date="2025-10-22",
            guid="same-guid",
            file_path="output/1.html",
        )
        session.add(newsletter1)
        session.commit()

        newsletter2 = Newsletter(
            user_id=user.id,
            date="2025-10-23",
            guid="same-guid",  # duplicate
            file_path="output/2.html",
        )
        session.add(newsletter2)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_newsletter_cascade_delete(self, session):
        """Test that newsletters are deleted when user is deleted."""
        user = User(first_name="David")
        session.add(user)
        session.commit()

        newsletter = Newsletter(
            user_id=user.id,
            date="2025-10-22",
            guid="cascade-test",
            file_path="output/cascade.html",
        )
        session.add(newsletter)
        session.commit()

        newsletter_id = newsletter.id

        # Delete user
        session.delete(user)
        session.commit()

        # Newsletter should be gone
        assert session.query(Newsletter).filter_by(id=newsletter_id).first() is None

    def test_newsletter_has_user_relationship(self, session):
        """Test that Newsletter has user relationship."""
        user = User(first_name="Eve")
        session.add(user)
        session.commit()

        newsletter = Newsletter(
            user_id=user.id,
            date="2025-10-22",
            guid="relationship-test",
            file_path="output/rel.html",
        )
        session.add(newsletter)
        session.commit()

        # Should be able to access user through relationship
        assert hasattr(newsletter, "user")
        assert newsletter.user.first_name == "Eve"


class TestUserInterestModel:
    """Test UserInterest ORM model."""

    def test_user_interest_creation(self, session):
        """Test creating user interest."""
        user = User(first_name="Frank")
        session.add(user)
        session.commit()

        interest = UserInterest(user_id=user.id, interest_name="AI")
        session.add(interest)
        session.commit()

        assert interest.id is not None
        assert interest.user_id == user.id
        assert interest.interest_name == "AI"
        assert interest.is_predefined is False  # default
        assert interest.added_at is not None

    def test_user_interest_predefined_flag(self, session):
        """Test creating predefined interest."""
        user = User(first_name="Grace")
        session.add(user)
        session.commit()

        interest = UserInterest(
            user_id=user.id, interest_name="rust", is_predefined=True
        )
        session.add(interest)
        session.commit()

        assert interest.is_predefined is True

    def test_user_interest_unique_constraint(self, session):
        """Test that user can't have duplicate interests."""
        user = User(first_name="Henry")
        session.add(user)
        session.commit()

        interest1 = UserInterest(user_id=user.id, interest_name="AI")
        session.add(interest1)
        session.commit()

        interest2 = UserInterest(
            user_id=user.id,
            interest_name="AI",  # duplicate
        )
        session.add(interest2)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_user_interest_cascade_delete(self, session):
        """Test that interests are deleted when user is deleted."""
        user = User(first_name="Iris")
        session.add(user)
        session.commit()

        interest = UserInterest(user_id=user.id, interest_name="technology")
        session.add(interest)
        session.commit()

        interest_id = interest.id

        # Delete user
        session.delete(user)
        session.commit()

        # Interest should be gone
        assert session.query(UserInterest).filter_by(id=interest_id).first() is None

    def test_user_interest_has_user_relationship(self, session):
        """Test that UserInterest has user relationship."""
        user = User(first_name="Jack")
        session.add(user)
        session.commit()

        interest = UserInterest(user_id=user.id, interest_name="programming")
        session.add(interest)
        session.commit()

        # Should be able to access user through relationship
        assert hasattr(interest, "user")
        assert interest.user.first_name == "Jack"
