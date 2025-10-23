"""
Unit tests for NewsletterService - TDD RED phase.

Tests newsletter lifecycle management:
- create_pending_newsletter: Queue newsletter for generation
- get_newsletters_by_month: Calendar view queries
- get_newsletter_by_guid: Retrieve for display
- mark_generating/completed/failed: Status transitions
- get_newsletter_count: Statistics
"""

import pytest
from datetime import date
from sqlalchemy.orm import Session

from src.web.services.newsletter_service import (
    create_pending_newsletter,
    get_newsletters_by_month,
    get_newsletter_by_guid,
    mark_newsletter_generating,
    mark_newsletter_completed,
    mark_newsletter_failed,
    get_newsletter_count,
    NewsletterNotFoundError,
    DuplicateNewsletterError,
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


class TestCreatePendingNewsletter:
    """Tests for create_pending_newsletter."""

    def test_create_pending_newsletter(self, db: Session, user):
        """Should create newsletter with pending status."""
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))

        assert newsletter.id is not None
        assert newsletter.user_id == user.id
        assert newsletter.date == "2025-10-22"
        assert newsletter.guid is not None
        assert newsletter.file_path is None
        assert newsletter.status == "pending"
        assert newsletter.generated_at is None
        assert newsletter.retry_count == 0

    def test_create_pending_generates_unique_guid(self, db: Session, user):
        """Should generate unique GUIDs."""
        n1 = create_pending_newsletter(db, user.id, date(2025, 10, 22))
        n2 = create_pending_newsletter(db, user.id, date(2025, 10, 23))

        assert n1.guid != n2.guid

    def test_create_duplicate_date_fails(self, db: Session, user):
        """Should prevent duplicate newsletters for same user/date."""
        create_pending_newsletter(db, user.id, date(2025, 10, 22))

        with pytest.raises(DuplicateNewsletterError, match="Newsletter already exists"):
            create_pending_newsletter(db, user.id, date(2025, 10, 22))


class TestGetNewslettersByMonth:
    """Tests for get_newsletters_by_month."""

    def test_get_newsletters_by_month_empty(self, db: Session, user):
        """Should return empty list for month with no newsletters."""
        newsletters = get_newsletters_by_month(db, user.id, 2025, 10)

        assert newsletters == []

    def test_get_newsletters_by_month(self, db: Session, user):
        """Should return all newsletters for given month."""
        n1 = create_pending_newsletter(db, user.id, date(2025, 10, 15))
        n2 = create_pending_newsletter(db, user.id, date(2025, 10, 20))
        create_pending_newsletter(db, user.id, date(2025, 11, 1))  # Different month

        newsletters = get_newsletters_by_month(db, user.id, 2025, 10)

        assert len(newsletters) == 2
        assert newsletters[0].id == n1.id
        assert newsletters[1].id == n2.id

    def test_get_newsletters_isolates_users(self, db: Session):
        """Should only return newsletters for specified user."""
        user1 = create_user(db, first_name="User1")
        user2 = create_user(db, first_name="User2")

        create_pending_newsletter(db, user1.id, date(2025, 10, 15))
        create_pending_newsletter(db, user2.id, date(2025, 10, 15))

        newsletters = get_newsletters_by_month(db, user1.id, 2025, 10)

        assert len(newsletters) == 1
        assert newsletters[0].user_id == user1.id


class TestGetNewsletterByGuid:
    """Tests for get_newsletter_by_guid."""

    def test_get_newsletter_by_guid(self, db: Session, user):
        """Should retrieve newsletter by GUID."""
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))

        retrieved = get_newsletter_by_guid(db, newsletter.guid)

        assert retrieved.id == newsletter.id
        assert retrieved.guid == newsletter.guid

    def test_get_newsletter_by_guid_not_found(self, db: Session):
        """Should raise NewsletterNotFoundError for invalid GUID."""
        with pytest.raises(NewsletterNotFoundError, match="Newsletter with GUID"):
            get_newsletter_by_guid(db, "invalid-guid")


class TestMarkNewsletterStatus:
    """Tests for newsletter status transitions."""

    def test_mark_newsletter_generating(self, db: Session, user):
        """Should transition to generating status."""
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))

        updated = mark_newsletter_generating(db, newsletter.id)

        assert updated.status == "generating"
        assert updated.generated_at is None

    def test_mark_newsletter_completed(self, db: Session, user):
        """Should transition to completed status with timestamp."""
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))

        updated = mark_newsletter_completed(db, newsletter.id, "output/test.html")

        assert updated.status == "completed"
        assert updated.file_path == "output/test.html"
        assert updated.generated_at is not None

    def test_mark_newsletter_failed(self, db: Session, user):
        """Should transition to failed status and increment retry count."""
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))

        updated = mark_newsletter_failed(db, newsletter.id)

        assert updated.status == "failed"
        assert updated.retry_count == 1

    def test_mark_newsletter_failed_increments_retry(self, db: Session, user):
        """Should increment retry count on each failure."""
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))

        mark_newsletter_failed(db, newsletter.id)
        updated = mark_newsletter_failed(db, newsletter.id)

        assert updated.retry_count == 2


class TestGetNewsletterCount:
    """Tests for get_newsletter_count."""

    def test_get_newsletter_count_by_status(self, db: Session, user):
        """Should count newsletters by status."""
        n1 = create_pending_newsletter(db, user.id, date(2025, 10, 20))
        n2 = create_pending_newsletter(db, user.id, date(2025, 10, 21))
        create_pending_newsletter(db, user.id, date(2025, 10, 22))

        mark_newsletter_completed(db, n1.id, "output/1.html")
        mark_newsletter_failed(db, n2.id)
        # n3 stays pending

        assert get_newsletter_count(db, user.id, "pending") == 1
        assert get_newsletter_count(db, user.id, "completed") == 1
        assert get_newsletter_count(db, user.id, "failed") == 1

    def test_get_newsletter_count_all(self, db: Session, user):
        """Should count all newsletters when status not specified."""
        create_pending_newsletter(db, user.id, date(2025, 10, 20))
        create_pending_newsletter(db, user.id, date(2025, 10, 21))

        assert get_newsletter_count(db, user.id) == 2
