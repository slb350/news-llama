"""
Newsletter service for News Llama web application.

Manages newsletter lifecycle:
pending → generating → completed/failed
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, extract
from datetime import date, datetime
import uuid

from src.web.models import Newsletter


# Custom Exceptions
class NewsletterServiceError(Exception):
    """Base exception for newsletter service errors."""
    pass


class NewsletterNotFoundError(NewsletterServiceError):
    """Raised when newsletter is not found."""
    pass


class NewsletterValidationError(NewsletterServiceError):
    """Raised when newsletter data validation fails."""
    pass


class DuplicateNewsletterError(NewsletterServiceError):
    """Raised when attempting to create duplicate newsletter."""
    pass


def create_pending_newsletter(
    db: Session,
    user_id: int,
    newsletter_date: date
) -> Newsletter:
    """
    Create pending newsletter for user on given date.

    Generates unique GUID and sets initial status to 'pending'.

    Args:
        db: Database session
        user_id: User ID
        newsletter_date: Date for newsletter

    Returns:
        Created Newsletter object

    Raises:
        DuplicateNewsletterError: If newsletter already exists for user/date
    """
    date_str = newsletter_date.strftime("%Y-%m-%d")

    # Check for existing newsletter
    existing = db.query(Newsletter).filter(
        Newsletter.user_id == user_id,
        Newsletter.date == date_str
    ).first()

    if existing:
        raise DuplicateNewsletterError(
            f"Newsletter already exists for user {user_id} on {date_str}"
        )

    # Create newsletter
    newsletter = Newsletter(
        user_id=user_id,
        date=date_str,
        guid=str(uuid.uuid4()),
        file_path=None,
        status="pending",
        generated_at=None,
        retry_count=0
    )

    db.add(newsletter)
    db.commit()
    db.refresh(newsletter)

    return newsletter


def get_newsletters_by_month(
    db: Session,
    user_id: int,
    year: int,
    month: int
) -> list[Newsletter]:
    """
    Get all newsletters for user in given month.

    Used for calendar view.

    Args:
        db: Database session
        user_id: User ID
        year: Year (e.g., 2025)
        month: Month (1-12)

    Returns:
        List of Newsletter objects (empty if none)
    """
    # Query newsletters matching year and month
    # SQLite stores dates as TEXT "YYYY-MM-DD"
    month_prefix = f"{year}-{month:02d}"

    newsletters = db.query(Newsletter).filter(
        Newsletter.user_id == user_id,
        Newsletter.date.like(f"{month_prefix}%")
    ).order_by(Newsletter.date).all()

    return newsletters


def get_newsletter_by_guid(
    db: Session,
    guid: str
) -> Newsletter:
    """
    Get newsletter by GUID.

    Args:
        db: Database session
        guid: Newsletter GUID

    Returns:
        Newsletter object

    Raises:
        NewsletterNotFoundError: If newsletter doesn't exist
    """
    newsletter = db.query(Newsletter).filter(
        Newsletter.guid == guid
    ).first()

    if not newsletter:
        raise NewsletterNotFoundError(f"Newsletter with GUID {guid} not found")

    return newsletter


def mark_newsletter_generating(
    db: Session,
    newsletter_id: int
) -> Newsletter:
    """
    Mark newsletter as generating.

    Transitions from 'pending' to 'generating'.

    Args:
        db: Database session
        newsletter_id: Newsletter ID

    Returns:
        Updated Newsletter object

    Raises:
        NewsletterNotFoundError: If newsletter doesn't exist
    """
    newsletter = db.query(Newsletter).filter(
        Newsletter.id == newsletter_id
    ).first()

    if not newsletter:
        raise NewsletterNotFoundError(f"Newsletter with ID {newsletter_id} not found")

    newsletter.status = "generating"

    db.commit()
    db.refresh(newsletter)

    return newsletter


def mark_newsletter_completed(
    db: Session,
    newsletter_id: int,
    file_path: str
) -> Newsletter:
    """
    Mark newsletter as completed.

    Sets file path and generation timestamp.

    Args:
        db: Database session
        newsletter_id: Newsletter ID
        file_path: Path to generated HTML file

    Returns:
        Updated Newsletter object

    Raises:
        NewsletterNotFoundError: If newsletter doesn't exist
    """
    newsletter = db.query(Newsletter).filter(
        Newsletter.id == newsletter_id
    ).first()

    if not newsletter:
        raise NewsletterNotFoundError(f"Newsletter with ID {newsletter_id} not found")

    newsletter.status = "completed"
    newsletter.file_path = file_path
    newsletter.generated_at = datetime.now().isoformat()

    db.commit()
    db.refresh(newsletter)

    return newsletter


def mark_newsletter_failed(
    db: Session,
    newsletter_id: int
) -> Newsletter:
    """
    Mark newsletter as failed.

    Increments retry count.

    Args:
        db: Database session
        newsletter_id: Newsletter ID

    Returns:
        Updated Newsletter object

    Raises:
        NewsletterNotFoundError: If newsletter doesn't exist
    """
    newsletter = db.query(Newsletter).filter(
        Newsletter.id == newsletter_id
    ).first()

    if not newsletter:
        raise NewsletterNotFoundError(f"Newsletter with ID {newsletter_id} not found")

    newsletter.status = "failed"
    newsletter.retry_count += 1

    db.commit()
    db.refresh(newsletter)

    return newsletter


def get_newsletter_count(
    db: Session,
    user_id: int,
    status: Optional[str] = None
) -> int:
    """
    Get count of newsletters for user.

    Args:
        db: Database session
        user_id: User ID
        status: Optional status filter (pending, generating, completed, failed)

    Returns:
        Count of newsletters
    """
    query = db.query(Newsletter).filter(Newsletter.user_id == user_id)

    if status:
        query = query.filter(Newsletter.status == status)

    return query.count()
