"""
Unit tests for NewsletterGenerationService - TDD RED phase.

Tests newsletter generation lifecycle:
- queue_newsletter_generation: Create pending newsletter and queue for processing
- process_newsletter_generation: Execute actual generation with NewsLlama
- get_generation_status: Check status of newsletter generation
- handle_generation_error: Mark newsletter as failed and increment retry count
"""

import pytest
from datetime import date
from sqlalchemy.orm import Session
from unittest.mock import patch

from src.web.services.generation_service import (
    queue_newsletter_generation,
    process_newsletter_generation,
    get_generation_status,
    handle_generation_error,
    GenerationServiceError,
    NewsletterAlreadyExistsError,
    NewsletterGenerationError,
)
from src.web.services.user_service import create_user
from src.web.services.interest_service import add_user_interest
from src.web.services.newsletter_service import (
    get_newsletter_by_guid,
    create_pending_newsletter,
)
from src.web.database import get_test_db
from src.web.models import Newsletter


@pytest.fixture
def db():
    """Provide test database session."""
    yield from get_test_db()


@pytest.fixture
def user_with_interests(db: Session):
    """Create test user with interests."""
    user = create_user(db, first_name="GenerationUser")
    add_user_interest(db, user.id, "AI", is_predefined=True)
    add_user_interest(db, user.id, "rust", is_predefined=True)
    add_user_interest(db, user.id, "python", is_predefined=True)
    return user


class TestQueueNewsletterGeneration:
    """Tests for queue_newsletter_generation."""

    def test_queue_newsletter_creates_pending(self, db: Session, user_with_interests):
        """Should create newsletter with pending status."""
        newsletter = queue_newsletter_generation(
            db, user_with_interests.id, date(2025, 10, 22)
        )

        assert newsletter.id is not None
        assert newsletter.user_id == user_with_interests.id
        assert newsletter.date == "2025-10-22"
        assert newsletter.status == "pending"
        assert newsletter.file_path is None
        assert newsletter.generated_at is None
        assert newsletter.retry_count == 0

    def test_queue_newsletter_generates_guid(self, db: Session, user_with_interests):
        """Should generate unique GUID for newsletter."""
        newsletter = queue_newsletter_generation(
            db, user_with_interests.id, date(2025, 10, 22)
        )

        assert newsletter.guid is not None
        assert len(newsletter.guid) > 0

    def test_queue_newsletter_prevents_duplicates(
        self, db: Session, user_with_interests
    ):
        """Should prevent duplicate newsletters for same user/date."""
        queue_newsletter_generation(db, user_with_interests.id, date(2025, 10, 22))

        with pytest.raises(
            NewsletterAlreadyExistsError, match="Newsletter already exists"
        ):
            queue_newsletter_generation(db, user_with_interests.id, date(2025, 10, 22))

    def test_queue_newsletter_allows_different_dates(
        self, db: Session, user_with_interests
    ):
        """Should allow multiple newsletters for different dates."""
        n1 = queue_newsletter_generation(db, user_with_interests.id, date(2025, 10, 22))
        n2 = queue_newsletter_generation(db, user_with_interests.id, date(2025, 10, 23))

        assert n1.date != n2.date
        assert n1.guid != n2.guid

    def test_queue_newsletter_requires_valid_user(self, db: Session):
        """Should raise error for non-existent user."""
        with pytest.raises(GenerationServiceError, match="User.*not found"):
            queue_newsletter_generation(db, 99999, date(2025, 10, 22))


class TestProcessNewsletterGeneration:
    """Tests for process_newsletter_generation."""

    @patch("src.web.services.generation_service.generate_news_digest")
    def test_process_generation_success(
        self, mock_generate, db: Session, user_with_interests
    ):
        """Should generate newsletter and update status to completed."""
        newsletter = create_pending_newsletter(
            db, user_with_interests.id, date(2025, 10, 22)
        )

        # Mock successful generation
        mock_generate.return_value = "/output/newsletters/news-2025-10-22-guid.html"

        result = process_newsletter_generation(db, newsletter.id)

        assert result.status == "completed"
        assert result.file_path is not None
        assert result.generated_at is not None
        assert "/output/newsletters/" in result.file_path

    @patch("src.web.services.generation_service.generate_news_digest")
    def test_process_generation_marks_generating(
        self, mock_generate, db: Session, user_with_interests
    ):
        """Should mark newsletter as 'generating' before processing."""
        newsletter = create_pending_newsletter(
            db, user_with_interests.id, date(2025, 10, 22)
        )

        # Make generation slow to check intermediate status
        def slow_generate(*args, **kwargs):
            # Check status during generation
            n = db.query(Newsletter).filter(Newsletter.id == newsletter.id).first()
            assert n.status == "generating"
            return "/output/test.html"

        mock_generate.side_effect = slow_generate

        process_newsletter_generation(db, newsletter.id)

    @patch("src.web.services.generation_service.generate_news_digest")
    def test_process_generation_uses_user_interests(
        self, mock_generate, db: Session, user_with_interests
    ):
        """Should pass user's interests to generation function."""
        newsletter = create_pending_newsletter(
            db, user_with_interests.id, date(2025, 10, 22)
        )

        mock_generate.return_value = "/output/test.html"

        process_newsletter_generation(db, newsletter.id)

        # Verify generate was called with user's interests
        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args[1]
        assert "interests" in call_kwargs
        interests = call_kwargs["interests"]
        assert "AI" in interests
        assert "rust" in interests
        assert "python" in interests

    @patch("src.web.services.generation_service.generate_news_digest")
    def test_process_generation_handles_failure(
        self, mock_generate, db: Session, user_with_interests
    ):
        """Should mark newsletter as failed on generation error."""
        newsletter = create_pending_newsletter(
            db, user_with_interests.id, date(2025, 10, 22)
        )

        # Mock generation failure
        mock_generate.side_effect = Exception("LLM connection failed")

        with pytest.raises(NewsletterGenerationError, match="Failed to generate"):
            process_newsletter_generation(db, newsletter.id)

        # Newsletter should be marked as failed
        updated = get_newsletter_by_guid(db, newsletter.guid)
        assert updated.status == "failed"
        assert updated.retry_count == 1

    def test_process_generation_requires_valid_newsletter(self, db: Session):
        """Should raise error for non-existent newsletter."""
        with pytest.raises(GenerationServiceError, match="Newsletter.*not found"):
            process_newsletter_generation(db, 99999)

    @patch("src.web.services.generation_service.generate_news_digest")
    def test_process_generation_creates_output_directory(
        self, mock_generate, db: Session, user_with_interests
    ):
        """Should ensure output directory exists before generation."""
        newsletter = create_pending_newsletter(
            db, user_with_interests.id, date(2025, 10, 22)
        )

        mock_generate.return_value = "/output/newsletters/test.html"

        process_newsletter_generation(db, newsletter.id)

        # Verify output directory was checked/created
        # (Implementation should create it if missing)


class TestGetGenerationStatus:
    """Tests for get_generation_status."""

    def test_get_status_pending(self, db: Session, user_with_interests):
        """Should return 'pending' for newly queued newsletter."""
        newsletter = queue_newsletter_generation(
            db, user_with_interests.id, date(2025, 10, 22)
        )

        status = get_generation_status(db, newsletter.id)

        assert status["status"] == "pending"
        assert status["file_path"] is None
        assert status["generated_at"] is None
        assert status["retry_count"] == 0

    @patch("src.web.services.generation_service.generate_news_digest")
    def test_get_status_completed(
        self, mock_generate, db: Session, user_with_interests
    ):
        """Should return 'completed' with file path after generation."""
        newsletter = create_pending_newsletter(
            db, user_with_interests.id, date(2025, 10, 22)
        )

        mock_generate.return_value = "/output/newsletters/test.html"
        process_newsletter_generation(db, newsletter.id)

        status = get_generation_status(db, newsletter.id)

        assert status["status"] == "completed"
        assert status["file_path"] is not None
        assert status["generated_at"] is not None

    def test_get_status_failed(self, db: Session, user_with_interests):
        """Should return 'failed' with retry count for failed newsletter."""
        newsletter = create_pending_newsletter(
            db, user_with_interests.id, date(2025, 10, 22)
        )

        handle_generation_error(db, newsletter.id, "Test error")

        status = get_generation_status(db, newsletter.id)

        assert status["status"] == "failed"
        assert status["retry_count"] == 1

    def test_get_status_requires_valid_newsletter(self, db: Session):
        """Should raise error for non-existent newsletter."""
        with pytest.raises(GenerationServiceError, match="Newsletter.*not found"):
            get_generation_status(db, 99999)


class TestHandleGenerationError:
    """Tests for handle_generation_error."""

    def test_handle_error_marks_failed(self, db: Session, user_with_interests):
        """Should mark newsletter as failed."""
        newsletter = create_pending_newsletter(
            db, user_with_interests.id, date(2025, 10, 22)
        )

        handle_generation_error(db, newsletter.id, "Connection timeout")

        updated = get_newsletter_by_guid(db, newsletter.guid)
        assert updated.status == "failed"

    def test_handle_error_increments_retry_count(
        self, db: Session, user_with_interests
    ):
        """Should increment retry count on each error."""
        newsletter = create_pending_newsletter(
            db, user_with_interests.id, date(2025, 10, 22)
        )

        handle_generation_error(db, newsletter.id, "Error 1")
        updated = get_newsletter_by_guid(db, newsletter.guid)
        assert updated.retry_count == 1

        handle_generation_error(db, newsletter.id, "Error 2")
        updated = get_newsletter_by_guid(db, newsletter.guid)
        assert updated.retry_count == 2

    def test_handle_error_logs_error_message(self, db: Session, user_with_interests):
        """Should log error message for debugging."""
        newsletter = create_pending_newsletter(
            db, user_with_interests.id, date(2025, 10, 22)
        )

        error_msg = "LLM API timeout after 30 seconds"
        handle_generation_error(db, newsletter.id, error_msg)

        # Error message should be logged (check via logging assertion or return value)
        # Implementation should log the error for ops debugging

    def test_handle_error_requires_valid_newsletter(self, db: Session):
        """Should raise error for non-existent newsletter."""
        with pytest.raises(GenerationServiceError, match="Newsletter.*not found"):
            handle_generation_error(db, 99999, "Test error")
