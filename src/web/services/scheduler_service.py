"""
Background scheduler for automated newsletter generation.

Handles both scheduled (daily cron) and immediate (user-triggered) background tasks
using APScheduler. Optimized for family-sized deployment (10-50 users) without
requiring Redis or Celery.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import date

from src.web.database import SessionLocal
from src.web.services import user_service, generation_service
from src.web.models import Newsletter

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


def schedule_daily_generation(
    hour: int = 6, minute: int = 0, timezone: str = "America/Los_Angeles"
):
    """
    Schedule daily newsletter generation for all users.

    Creates a cron job that runs at the specified time daily, generating
    newsletters for all users in the system.

    Args:
        hour: Hour to run (0-23), default 6 AM
        minute: Minute to run (0-59), default 0
        timezone: Timezone string, default "America/Los_Angeles"
    """

    def generate_daily_newsletters():
        """Generate newsletters for all users at scheduled time."""
        logger.info("Starting daily newsletter generation")

        db = SessionLocal()
        try:
            users = user_service.get_all_users(db)
            today = date.today()

            success_count = 0
            error_count = 0

            for user in users:
                try:
                    # Queue newsletter generation
                    newsletter = generation_service.queue_newsletter_generation(
                        db, user.id, today
                    )
                    logger.info(
                        f"Queued newsletter {newsletter.guid} for user {user.id}"
                    )

                    # Trigger immediate background processing (non-blocking)
                    queue_immediate_generation(newsletter.id)
                    success_count += 1

                except generation_service.NewsletterAlreadyExistsError:
                    logger.debug(f"Newsletter already exists for user {user.id}")
                except Exception as e:
                    logger.error(f"Failed to queue newsletter for user {user.id}: {e}")
                    error_count += 1

            logger.info(
                f"Daily generation complete: {success_count} queued, {error_count} errors"
            )

        finally:
            db.close()

    # Add scheduled job
    scheduler.add_job(
        func=generate_daily_newsletters,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=timezone),
        id="daily_generation",
        replace_existing=True,
    )


def queue_immediate_generation(newsletter_id: int):
    """
    Queue newsletter generation to run immediately in background.

    Used for user-triggered generation (profile creation, manual generation,
    interest updates, retries) to prevent blocking the request thread.

    APScheduler handles both scheduled (daily) AND immediate (user-triggered)
    background tasks - no Redis/Celery needed for family-sized deployment.

    Args:
        newsletter_id: Newsletter ID to process
    """

    def _process_with_db():
        """Internal function to process newsletter with fresh DB session."""
        db = SessionLocal()
        try:
            generation_service.process_newsletter_generation(db, newsletter_id)
            logger.info(
                f"Background generation completed for newsletter {newsletter_id}"
            )
        except Exception as e:
            logger.error(
                f"Background generation failed for newsletter {newsletter_id}: {e}"
            )
        finally:
            db.close()

    # Add immediate job
    scheduler.add_job(
        func=_process_with_db,
        id=f"newsletter_{newsletter_id}",
        replace_existing=True,
        misfire_grace_time=3600,  # Allow 1 hour grace period if scheduler is busy
    )
    logger.info(
        f"Queued immediate background generation for newsletter {newsletter_id}"
    )


def process_pending_newsletters():
    """
    Process all pending newsletters (background worker).

    This can be called on startup to process any newsletters that were
    pending when the application last shut down.
    """
    db = SessionLocal()
    try:
        pending = db.query(Newsletter).filter(Newsletter.status == "pending").all()

        if not pending:
            logger.info("No pending newsletters to process")
            return

        logger.info(f"Processing {len(pending)} pending newsletters")

        for newsletter in pending:
            try:
                # Use immediate queue to prevent blocking
                queue_immediate_generation(newsletter.id)
            except Exception as e:
                logger.error(f"Failed to queue newsletter {newsletter.id}: {e}")

        logger.info(f"Queued {len(pending)} pending newsletters for processing")

    finally:
        db.close()


def start_scheduler(config: dict):
    """
    Start scheduler with configuration.

    Args:
        config: Configuration dictionary with keys:
            - SCHEDULER_ENABLED: bool (default True)
            - SCHEDULER_HOUR: int (default 6)
            - SCHEDULER_MINUTE: int (default 0)
            - SCHEDULER_TIMEZONE: str (default "America/Los_Angeles")
    """
    if not config.get("SCHEDULER_ENABLED", True):
        logger.info("Scheduler disabled via configuration")
        return

    hour = config.get("SCHEDULER_HOUR", 6)
    minute = config.get("SCHEDULER_MINUTE", 0)
    timezone = config.get("SCHEDULER_TIMEZONE", "America/Los_Angeles")

    # Schedule daily generation
    schedule_daily_generation(hour, minute, timezone)

    # Start scheduler
    scheduler.start()
    logger.info(
        f"Scheduler started: daily generation at {hour:02d}:{minute:02d} {timezone}"
    )

    # Process any pending newsletters from previous shutdown
    process_pending_newsletters()


def stop_scheduler():
    """Stop scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")
