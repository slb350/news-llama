"""
Newsletter generation service for News Llama web application.

Orchestrates newsletter generation by integrating NewsLlama engine with
web application database and file management.
"""

from sqlalchemy.orm import Session
from datetime import date
import logging
import asyncio
import time

from src.web.services import user_service, interest_service, newsletter_service
from src.web.models import Newsletter
from src.web.services.llama_wrapper import (
    generate_newsletter_for_interests as generate_news_digest,
)

logger = logging.getLogger(__name__)

# Configuration constants
RETRY_BASE_DELAY_SECONDS = 300  # 5 minutes
MAX_RETRIES = 3


# Custom Exceptions
class GenerationServiceError(Exception):
    """Base exception for generation service errors."""

    pass


class NewsletterAlreadyExistsError(GenerationServiceError):
    """Raised when newsletter already exists for user/date."""

    pass


class NewsletterGenerationError(GenerationServiceError):
    """Raised when newsletter generation fails."""

    pass


def queue_newsletter_generation(db: Session, user_id: int, newsletter_date: date):
    """
    Create pending newsletter and queue for generation.

    Args:
        db: Database session
        user_id: User ID
        newsletter_date: Date for newsletter

    Returns:
        Created Newsletter object

    Raises:
        NewsletterAlreadyExistsError: If newsletter exists for user/date
        GenerationServiceError: If user not found
    """
    # Validate user exists
    try:
        user_service.get_user(db, user_id)
    except user_service.UserNotFoundError:
        raise GenerationServiceError(f"User with ID {user_id} not found")

    # Try to create pending newsletter
    try:
        newsletter = newsletter_service.create_pending_newsletter(
            db, user_id, newsletter_date
        )
        return newsletter
    except newsletter_service.DuplicateNewsletterError as e:
        raise NewsletterAlreadyExistsError(str(e))


def process_newsletter_generation(db: Session, newsletter_id: int):
    """
    Process newsletter generation using NewsLlama engine.

    Args:
        db: Database session
        newsletter_id: Newsletter ID

    Returns:
        Updated Newsletter object

    Raises:
        NewsletterGenerationError: If generation fails
        GenerationServiceError: If newsletter not found
    """
    # Get newsletter
    try:
        newsletter = db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()
        if not newsletter:
            raise GenerationServiceError(
                f"Newsletter with ID {newsletter_id} not found"
            )
    except Exception:
        raise GenerationServiceError(f"Newsletter with ID {newsletter_id} not found")

    # Mark as generating
    newsletter_service.mark_newsletter_generating(db, newsletter_id)

    try:
        # Get user's interests
        interests_objs = interest_service.get_user_interests(db, newsletter.user_id)
        interests = [i.interest_name for i in interests_objs]

        # Generate newsletter using NewsLlama engine
        output_date = date.fromisoformat(newsletter.date)
        file_path = generate_news_digest(interests=interests, output_date=output_date)

        # Mark as completed
        updated_newsletter = newsletter_service.mark_newsletter_completed(
            db, newsletter_id, file_path
        )

        logger.info(
            f"Successfully generated newsletter {newsletter_id} for user {newsletter.user_id}"
        )
        return updated_newsletter

    except Exception as e:
        # Handle generation failure
        logger.error(
            f"Failed to generate newsletter {newsletter_id}: {str(e)}", exc_info=True
        )
        handle_generation_error(db, newsletter_id, str(e))
        raise NewsletterGenerationError(f"Failed to generate newsletter: {str(e)}")


def get_generation_status(db: Session, newsletter_id: int):
    """
    Get current generation status of newsletter.

    Args:
        db: Database session
        newsletter_id: Newsletter ID

    Returns:
        Dict with status, file_path, generated_at, retry_count

    Raises:
        GenerationServiceError: If newsletter not found
    """
    # Get newsletter
    newsletter = db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()
    if not newsletter:
        raise GenerationServiceError(f"Newsletter with ID {newsletter_id} not found")

    return {
        "status": newsletter.status,
        "file_path": newsletter.file_path,
        "generated_at": newsletter.generated_at,
        "retry_count": newsletter.retry_count,
    }


def handle_generation_error(db: Session, newsletter_id: int, error_message: str):
    """
    Handle generation error by marking newsletter as failed.

    Args:
        db: Database session
        newsletter_id: Newsletter ID
        error_message: Error description for logging

    Raises:
        GenerationServiceError: If newsletter not found
    """
    # Verify newsletter exists
    newsletter = db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()
    if not newsletter:
        raise GenerationServiceError(f"Newsletter with ID {newsletter_id} not found")

    # Log error
    logger.error(
        f"Newsletter {newsletter_id} generation failed: {error_message}",
        extra={
            "newsletter_id": newsletter_id,
            "user_id": newsletter.user_id,
            "date": newsletter.date,
            "retry_count": newsletter.retry_count,
        },
    )

    # Mark as failed and increment retry count
    newsletter_service.mark_newsletter_failed(db, newsletter_id)


class GenerationMetrics:
    """Track generation performance metrics."""

    def __init__(self):
        self.total_generated = 0
        self.total_failed = 0
        self.average_duration = 0.0
        self.queue_depth = 0

    def record_success(self, duration_seconds: float):
        """Record successful generation with duration."""
        self.total_generated += 1
        # Calculate new average: ((old_avg * old_count) + new_value) / new_count
        self.average_duration = (
            self.average_duration * (self.total_generated - 1) + duration_seconds
        ) / self.total_generated

    def record_failure(self):
        """Record failed generation."""
        self.total_failed += 1

    def get_stats(self):
        """Get current metrics as dictionary."""
        total_attempts = self.total_generated + self.total_failed
        success_rate = (
            self.total_generated / total_attempts if total_attempts > 0 else 0
        )

        return {
            "total_generated": self.total_generated,
            "total_failed": self.total_failed,
            "success_rate": success_rate,
            "average_duration_seconds": self.average_duration,
            "queue_depth": self.queue_depth,
        }


# Global metrics instance
metrics = GenerationMetrics()


async def process_newsletter_with_retry(
    db: Session, newsletter_id: int, max_retries: int = MAX_RETRIES
):
    """
    Process newsletter generation with automatic retries and exponential backoff.

    Args:
        db: Database session
        newsletter_id: Newsletter ID to process
        max_retries: Maximum number of retry attempts (default 3)

    Raises:
        Exception: If all retry attempts fail
    """
    newsletter = db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()
    if not newsletter:
        raise GenerationServiceError(f"Newsletter with ID {newsletter_id} not found")

    start_time = time.time()

    for attempt in range(max_retries):
        try:
            # Attempt generation
            process_newsletter_generation(db, newsletter_id)

            # Record success
            duration = time.time() - start_time
            metrics.record_success(duration)

            logger.info(
                f"Newsletter {newsletter_id} generated successfully on attempt {attempt + 1}"
            )
            return

        except Exception as e:
            logger.warning(
                f"Newsletter {newsletter_id} failed on attempt {attempt + 1}: {e}"
            )

            if attempt < max_retries - 1:
                # Exponential backoff: 5 min, 10 min, 20 min
                backoff_seconds = RETRY_BASE_DELAY_SECONDS * (2**attempt)
                logger.info(f"Retrying in {backoff_seconds} seconds...")
                await asyncio.sleep(backoff_seconds)
            else:
                # Max retries exceeded
                logger.error(
                    f"Newsletter {newsletter_id} failed after {max_retries} attempts"
                )
                handle_generation_error(
                    db, newsletter_id, f"Max retries exceeded: {str(e)}"
                )
                metrics.record_failure()
                raise


def requeue_newsletter_for_today(db: Session, user_id: int) -> bool:
    """
    Delete existing newsletter for today (if pending/generating) and queue a new one.

    This is used when user updates their interests and we want to regenerate
    today's newsletter with the new interests.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        True if newsletter was requeued, False if no action taken

    Raises:
        GenerationServiceError: If user not found or generation fails
    """
    # Validate user exists
    try:
        user_service.get_user(db, user_id)
    except user_service.UserNotFoundError:
        raise GenerationServiceError(f"User with ID {user_id} not found")

    today = date.today()

    # Check if newsletter already exists for today
    try:
        newsletters = newsletter_service.get_newsletters_by_month(
            db, user_id, today.year, today.month
        )
        today_str = today.isoformat()
        existing = next((n for n in newsletters if n.date == today_str), None)

        if existing:
            # Only delete and requeue if pending or generating
            # If completed, we let it be (user can manually regenerate later)
            if existing.status in ["pending", "generating"]:
                logger.info(
                    f"Deleting existing {existing.status} newsletter {existing.id} for regeneration"
                )
                newsletter_service.delete_newsletter(db, existing.id)

                # Check again after delete - another thread might have queued one
                # (prevents race condition when rapidly adding/removing interests)
                newsletters_after_delete = newsletter_service.get_newsletters_by_month(
                    db, user_id, today.year, today.month
                )
                existing_after_delete = next(
                    (n for n in newsletters_after_delete if n.date == today_str), None
                )
                if existing_after_delete:
                    logger.info(
                        f"Newsletter {existing_after_delete.id} already queued by another request, skipping"
                    )
                    return True
            elif existing.status == "completed":
                # Don't regenerate completed newsletters automatically
                logger.info(
                    f"Newsletter {existing.id} already completed, skipping regeneration"
                )
                return False
            # If failed, we'll delete and retry

        # Queue new newsletter
        newsletter = queue_newsletter_generation(db, user_id, today)

        # Queue for immediate background processing
        from src.web.services import scheduler_service

        scheduler_service.queue_immediate_generation(newsletter.id)

        return True

    except Exception as e:
        logger.error(f"Failed to requeue newsletter for user {user_id}: {str(e)}")
        # Don't raise - we don't want interest updates to fail if newsletter fails
        return False
