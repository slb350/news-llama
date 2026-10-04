"""Public metrics page and health endpoints for the scheduler and generation."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from src.web.database import get_db
from src.web.services import generation_service, scheduler_service
from src.web.services.discovery_metrics_service import get_all_metrics
from src.web.templating import templates

router = APIRouter()


def _job_schedule(job, tz_name: str) -> str:
    """Human-readable schedule for the jobs the scheduler service registers."""
    trigger = job.trigger
    if job.id == "daily_generation" and hasattr(trigger, "hour"):
        return f"Daily at {trigger.hour:02d}:{trigger.minute:02d} {tz_name}"
    if job.id == "weekly_discovery" and hasattr(trigger, "day_of_week"):
        return f"Weekly on {trigger.day_of_week} at {trigger.hour:02d}:{trigger.minute:02d} {tz_name}"
    if job.id == "rate_limiter_cleanup" and hasattr(trigger, "interval"):
        return f"Every {trigger.interval}"
    return "Custom schedule"


def _job_info(job) -> dict:
    info = {
        "id": job.id,
        "function": job.func.__name__,
        "next_run": None,
        "next_run_formatted": None,
        "hours_until": None,
    }
    if job.next_run_time:
        # APScheduler cron triggers carry their timezone; fall back to UTC for others
        tz = getattr(job.trigger, "timezone", timezone.utc)
        next_run_local = job.next_run_time.astimezone(tz)
        info["next_run"] = next_run_local.isoformat()
        info["next_run_formatted"] = next_run_local.strftime("%Y-%m-%d %I:%M %p %Z")
        info["hours_until"] = (next_run_local - datetime.now(timezone.utc)).total_seconds() / 3600
        info["schedule"] = _job_schedule(job, str(tz))
    return info


@router.get("/metrics", response_class=HTMLResponse)
async def metrics_page(request: Request, db: Session = Depends(get_db)):
    """Public metrics page: discovery performance stats and scheduler status."""
    scheduler = scheduler_service.scheduler
    scheduler_info = {
        "running": scheduler.running,
        "jobs": [_job_info(job) for job in scheduler.get_jobs()] if scheduler.running else [],
    }
    return templates.TemplateResponse(
        request, "metrics.html", {"metrics": get_all_metrics(db), "scheduler": scheduler_info}
    )


@router.get("/health/scheduler")
async def scheduler_health():
    """Scheduler running status and each job's next run time."""
    jobs_info = [
        {
            "id": job.id,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "name": str(job.func),
        }
        for job in scheduler_service.scheduler.get_jobs()
    ]
    return {
        "running": scheduler_service.scheduler.running,
        "jobs": jobs_info,
        "job_count": len(jobs_info),
    }


@router.get("/health/generation")
async def generation_health():
    """Generation success/failure counts, success rate, and average duration."""
    return generation_service.metrics.get_stats()
