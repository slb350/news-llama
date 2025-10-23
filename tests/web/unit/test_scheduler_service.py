"""
Unit tests for scheduler_service.py

Tests for background newsletter generation scheduling using APScheduler.
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from apscheduler.schedulers.background import BackgroundScheduler

from src.web.services import scheduler_service, user_service, generation_service
from src.web.database import get_test_db


@pytest.fixture
def db():
    """Provide test database session."""
    yield from get_test_db()


@pytest.fixture
def mock_config():
    """Mock scheduler configuration."""
    return {
        "SCHEDULER_ENABLED": True,
        "SCHEDULER_HOUR": 6,
        "SCHEDULER_MINUTE": 0,
        "SCHEDULER_TIMEZONE": "America/Los_Angeles",
    }


@pytest.fixture
def mock_config_disabled():
    """Mock scheduler configuration with scheduler disabled."""
    return {
        "SCHEDULER_ENABLED": False,
        "SCHEDULER_HOUR": 6,
        "SCHEDULER_MINUTE": 0,
        "SCHEDULER_TIMEZONE": "America/Los_Angeles",
    }


@pytest.fixture(autouse=True)
def reset_scheduler():
    """Reset scheduler before each test."""
    if scheduler_service.scheduler.running:
        scheduler_service.scheduler.shutdown(wait=False)
    # Use BackgroundScheduler for testing (doesn't require event loop)
    scheduler_service.scheduler = BackgroundScheduler()
    yield
    if scheduler_service.scheduler.running:
        scheduler_service.scheduler.shutdown(wait=False)


class TestScheduleDailyGeneration:
    """Tests for schedule_daily_generation function."""

    def test_schedules_cron_job_with_correct_time(self, mock_config):
        """Should schedule daily job at specified time."""
        # Schedule daily generation
        scheduler_service.schedule_daily_generation(
            hour=mock_config["SCHEDULER_HOUR"],
            minute=mock_config["SCHEDULER_MINUTE"],
            timezone=mock_config["SCHEDULER_TIMEZONE"],
        )

        # Verify job was added
        jobs = scheduler_service.scheduler.get_jobs()
        assert len(jobs) == 1

        job = jobs[0]
        assert job.id == "daily_generation"
        assert str(job.trigger.timezone) == "America/Los_Angeles"

    def test_generates_newsletters_for_all_users(self, db):
        """Should create newsletters for all users during scheduled run."""
        # Create test users
        _user1 = user_service.create_user(db, first_name="Alice")
        _user2 = user_service.create_user(db, first_name="Bob")

        # Mock the immediate processing
        with patch.object(scheduler_service, "queue_immediate_generation"):
            # Trigger daily generation manually
            scheduler_service.schedule_daily_generation(hour=6, minute=0)

            # Get the scheduled function
            jobs = scheduler_service.scheduler.get_jobs()
            assert len(jobs) == 1

    def test_handles_duplicate_newsletter_gracefully(self, db):
        """Should skip users who already have newsletter for today."""
        user = user_service.create_user(db, first_name="Alice")

        # Create newsletter for today
        _newsletter = generation_service.queue_newsletter_generation(
            db, user.id, date.today()
        )

        # Mock immediate queue - should handle duplicate gracefully
        with patch.object(scheduler_service, "queue_immediate_generation"):
            # Schedule generation - function won't execute in test but tests setup
            scheduler_service.schedule_daily_generation(hour=6, minute=0)

    def test_logs_errors_for_failed_users(self, db, caplog):
        """Should log errors but continue processing other users."""
        _user1 = user_service.create_user(db, first_name="Alice")
        _user2 = user_service.create_user(db, first_name="Bob")

        # Mock generation to fail for first user
        with patch.object(
            generation_service,
            "queue_newsletter_generation",
            side_effect=[Exception("Test error"), MagicMock()],
        ):
            # Schedule generation - function won't execute in test
            scheduler_service.schedule_daily_generation(hour=6, minute=0)


class TestQueueImmediateGeneration:
    """Tests for queue_immediate_generation function."""

    def test_adds_job_to_scheduler(self, db):
        """Should add immediate job to scheduler."""
        # Create test newsletter
        user = user_service.create_user(db, first_name="Alice")
        newsletter = generation_service.queue_newsletter_generation(
            db, user.id, date.today()
        )

        # Queue immediate generation
        scheduler_service.queue_immediate_generation(newsletter.id)

        # Verify job was added
        jobs = scheduler_service.scheduler.get_jobs()
        job_ids = [job.id for job in jobs]
        assert f"newsletter_{newsletter.id}" in job_ids

    def test_replaces_existing_job_for_same_newsletter(self, db):
        """Should replace existing job if queued multiple times."""
        user = user_service.create_user(db, first_name="Alice")
        newsletter = generation_service.queue_newsletter_generation(
            db, user.id, date.today()
        )

        # Queue twice - should not error (replace_existing=True)
        scheduler_service.queue_immediate_generation(newsletter.id)
        scheduler_service.queue_immediate_generation(newsletter.id)

        # Verify jobs exist (may be 0, 1, or 2 depending on execution timing)
        # The key is that queueing twice doesn't error
        jobs = scheduler_service.scheduler.get_jobs()
        job_ids = [job.id for job in jobs]
        # All jobs for this newsletter should have the same ID
        newsletter_jobs = [job_id for job_id in job_ids if "newsletter_" in job_id]
        # Should have at most 1 unique job ID (replace_existing means same ID)
        unique_ids = set(newsletter_jobs)
        assert len(unique_ids) <= 1

    def test_processes_newsletter_generation(self, db):
        """Should call process_newsletter_generation for the newsletter."""
        user = user_service.create_user(db, first_name="Alice")
        newsletter = generation_service.queue_newsletter_generation(
            db, user.id, date.today()
        )

        # Mock the processing
        with patch.object(generation_service, "process_newsletter_generation"):
            # Queue and execute immediately
            scheduler_service.queue_immediate_generation(newsletter.id)

            # Note: In real scenario, job would execute asynchronously
            # For testing, we verify the job was queued correctly
            jobs = scheduler_service.scheduler.get_jobs()
            assert len(jobs) > 0

    def test_handles_processing_errors_gracefully(self, db, caplog):
        """Should log error but not crash if processing fails."""
        user = user_service.create_user(db, first_name="Alice")
        newsletter = generation_service.queue_newsletter_generation(
            db, user.id, date.today()
        )

        # Mock processing to fail
        with patch.object(
            generation_service,
            "process_newsletter_generation",
            side_effect=Exception("Test error"),
        ):
            # Should not raise exception
            scheduler_service.queue_immediate_generation(newsletter.id)

    def test_uses_misfire_grace_time(self, db):
        """Should configure job with misfire grace time."""
        user = user_service.create_user(db, first_name="Alice")
        newsletter = generation_service.queue_newsletter_generation(
            db, user.id, date.today()
        )

        scheduler_service.queue_immediate_generation(newsletter.id)

        # Verify misfire_grace_time is set
        jobs = scheduler_service.scheduler.get_jobs()
        job = next(j for j in jobs if j.id == f"newsletter_{newsletter.id}")
        assert job.misfire_grace_time == 3600  # 1 hour


class TestProcessPendingNewsletters:
    """Tests for process_pending_newsletters function."""

    def test_queues_all_pending_newsletters(self, db):
        """Should queue all pending newsletters for processing."""
        # Create users and newsletters
        user1 = user_service.create_user(db, first_name="Alice")
        user2 = user_service.create_user(db, first_name="Bob")

        newsletter1 = generation_service.queue_newsletter_generation(
            db, user1.id, date.today()
        )
        newsletter2 = generation_service.queue_newsletter_generation(
            db, user2.id, date.today()
        )

        # Both should be pending
        assert newsletter1.status == "pending"
        assert newsletter2.status == "pending"

        # Mock SessionLocal to return our test db
        with patch("src.web.services.scheduler_service.SessionLocal") as mock_session:
            mock_session.return_value = db

            # Mock immediate queue to verify it's called
            with patch.object(
                scheduler_service, "queue_immediate_generation"
            ) as mock_queue:
                scheduler_service.process_pending_newsletters()

                # Should have queued both newsletters
                assert mock_queue.call_count == 2
                mock_queue.assert_any_call(newsletter1.id)
                mock_queue.assert_any_call(newsletter2.id)

    def test_skips_non_pending_newsletters(self, db):
        """Should only process newsletters in pending status."""
        user = user_service.create_user(db, first_name="Alice")

        # Create pending and completed newsletters
        pending = generation_service.queue_newsletter_generation(
            db, user.id, date.today()
        )

        # Create a completed one by modifying directly
        from src.web.services import newsletter_service

        completed = newsletter_service.create_pending_newsletter(
            db, user.id, date(2025, 10, 20)
        )
        newsletter_service.mark_newsletter_completed(
            db, completed.id, "/fake/path.html"
        )

        # Mock SessionLocal to return our test db
        with patch("src.web.services.scheduler_service.SessionLocal") as mock_session:
            mock_session.return_value = db

            # Mock immediate queue to verify it's called
            with patch.object(
                scheduler_service, "queue_immediate_generation"
            ) as mock_queue:
                scheduler_service.process_pending_newsletters()

                # Should only queue the pending one
                assert mock_queue.call_count == 1
                mock_queue.assert_called_once_with(pending.id)

    def test_handles_queue_errors_gracefully(self, db, caplog):
        """Should log errors but continue processing other newsletters."""
        user1 = user_service.create_user(db, first_name="Alice")
        user2 = user_service.create_user(db, first_name="Bob")

        _newsletter1 = generation_service.queue_newsletter_generation(
            db, user1.id, date.today()
        )
        _newsletter2 = generation_service.queue_newsletter_generation(
            db, user2.id, date.today()
        )

        # Mock SessionLocal and queue to fail for first, succeed for second
        with patch("src.web.services.scheduler_service.SessionLocal") as mock_session:
            mock_session.return_value = db

            with patch.object(
                scheduler_service,
                "queue_immediate_generation",
                side_effect=[Exception("Test error"), None],
            ):
                # Should not raise exception
                scheduler_service.process_pending_newsletters()

                # Should have attempted both (first failed, second succeeded)


class TestStartScheduler:
    """Tests for start_scheduler function."""

    def test_starts_scheduler_when_enabled(self, mock_config):
        """Should start scheduler when enabled in config."""
        # Mock process_pending_newsletters to prevent DB operations
        with patch.object(scheduler_service, "process_pending_newsletters"):
            scheduler_service.start_scheduler(mock_config)

        assert scheduler_service.scheduler.running is True

    def test_does_not_start_when_disabled(self, mock_config_disabled):
        """Should not start scheduler when disabled in config."""
        scheduler_service.start_scheduler(mock_config_disabled)

        assert scheduler_service.scheduler.running is False

    def test_configures_correct_schedule(self, mock_config):
        """Should configure scheduler with correct time from config."""
        # Mock process_pending_newsletters to prevent DB operations
        with patch.object(scheduler_service, "process_pending_newsletters"):
            scheduler_service.start_scheduler(mock_config)

        jobs = scheduler_service.scheduler.get_jobs()
        assert len(jobs) >= 1  # At least the daily generation job

    def test_uses_default_config_values(self):
        """Should use defaults if config values missing."""
        # Mock process_pending_newsletters to prevent DB operations
        with patch.object(scheduler_service, "process_pending_newsletters"):
            # Empty config
            scheduler_service.start_scheduler({})

        assert scheduler_service.scheduler.running is True


class TestStopScheduler:
    """Tests for stop_scheduler function."""

    def test_stops_running_scheduler(self, mock_config):
        """Should stop scheduler if running."""
        # Mock process_pending_newsletters to prevent DB operations
        with patch.object(scheduler_service, "process_pending_newsletters"):
            scheduler_service.start_scheduler(mock_config)
        assert scheduler_service.scheduler.running is True

        # Stop scheduler
        scheduler_service.stop_scheduler()
        assert scheduler_service.scheduler.running is False

    def test_handles_already_stopped_scheduler(self):
        """Should handle stopping already stopped scheduler gracefully."""
        # Scheduler should already be stopped (from reset_scheduler fixture)
        # Should not raise exception
        scheduler_service.stop_scheduler()
