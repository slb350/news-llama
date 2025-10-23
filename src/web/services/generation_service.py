"""
Newsletter generation service for News Llama web application.

Orchestrates newsletter generation by integrating NewsLlama engine with
web application database and file management.
"""

from sqlalchemy.orm import Session
from datetime import date
import logging

from src.web.services import user_service, interest_service, newsletter_service
from src.web.models import Newsletter
from src.web.services.llama_wrapper import (
    generate_newsletter_for_interests as generate_news_digest,
)

logger = logging.getLogger(__name__)


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
