"""Unit tests for the scheduler job summaries shown on the /metrics page."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from src.web.routes.status import _job_info, _job_schedule


def _job(job_id, trigger, next_run_time=None):
    def daily():
        pass

    return SimpleNamespace(id=job_id, func=daily, trigger=trigger, next_run_time=next_run_time)


class TestJobSchedule:
    def test_daily_generation(self):
        job = _job("daily_generation", SimpleNamespace(hour=6, minute=5))
        assert _job_schedule(job, "America/Los_Angeles") == "Daily at 06:05 America/Los_Angeles"

    def test_weekly_discovery(self):
        job = _job("weekly_discovery", SimpleNamespace(day_of_week="sun", hour=3, minute=0))
        assert _job_schedule(job, "UTC") == "Weekly on sun at 03:00 UTC"

    def test_rate_limiter_cleanup(self):
        job = _job("rate_limiter_cleanup", SimpleNamespace(interval=timedelta(minutes=5)))
        assert _job_schedule(job, "UTC") == "Every 0:05:00"

    def test_unknown_job(self):
        assert _job_schedule(_job("other", SimpleNamespace()), "UTC") == "Custom schedule"


class TestJobInfo:
    def test_job_without_next_run(self):
        info = _job_info(_job("daily_generation", SimpleNamespace(hour=6, minute=0)))

        assert info == {
            "id": "daily_generation",
            "function": "daily",
            "next_run": None,
            "next_run_formatted": None,
            "hours_until": None,
        }

    def test_next_run_uses_trigger_timezone(self):
        tz = ZoneInfo("America/Los_Angeles")
        next_run = datetime.now(timezone.utc) + timedelta(hours=2)
        trigger = SimpleNamespace(hour=6, minute=0, timezone=tz)

        info = _job_info(_job("daily_generation", trigger, next_run))

        assert info["next_run"] == next_run.astimezone(tz).isoformat()
        assert 1.9 < info["hours_until"] <= 2.0
        assert info["schedule"] == "Daily at 06:00 America/Los_Angeles"

    def test_next_run_without_trigger_timezone_is_utc(self):
        next_run = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)

        info = _job_info(_job("other", SimpleNamespace(), next_run))

        assert info["next_run"] == "2030-01-01T12:00:00+00:00"
        assert info["next_run_formatted"] == "2030-01-01 12:00 PM UTC"
        assert info["schedule"] == "Custom schedule"
