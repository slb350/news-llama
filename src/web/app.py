"""FastAPI application for News Llama web interface.

Phase 6: Background scheduler integration.
"""

import os
import sys
import logging
from contextlib import asynccontextmanager

# Configure logging to show INFO level messages
logging.basicConfig(
    level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s"
)

# Fix libmagic path on macOS (python-magic needs help finding Homebrew's libmagic)
if sys.platform == "darwin":  # macOS
    os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/lib")

import magic
import io
from typing import Optional
from PIL import Image
from fastapi import FastAPI, Request, Depends, Response, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import date

from src.web.database import get_db
from src.web.dependencies import get_current_user, require_user
from src.web.schemas import (
    ProfileCreateRequest,
    ProfileUpdateRequest,
    InterestAdd,
    NewsletterCreate,
    NewsletterResponse,
)
from src.web.models import User
from src.web.services import (
    user_service,
    interest_service,
    newsletter_service,
    generation_service,
    scheduler_service,
)
from src.web.error_handlers import (
    global_exception_handler,
    validation_exception_handler,
    get_friendly_message,
)
from src.web import file_cache

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle (startup/shutdown)."""
    # Startup
    logger.info("Starting News Llama web application")

    # Disable scheduler during tests to avoid interference with test fixtures
    is_testing = os.getenv("TESTING", "false").lower() == "true"

    if not is_testing:
        # Load scheduler configuration from environment
        config = {
            "SCHEDULER_ENABLED": os.getenv("SCHEDULER_ENABLED", "true").lower()
            == "true",
            "SCHEDULER_HOUR": int(os.getenv("SCHEDULER_HOUR", "6")),
            "SCHEDULER_MINUTE": int(os.getenv("SCHEDULER_MINUTE", "0")),
            "SCHEDULER_TIMEZONE": os.getenv(
                "SCHEDULER_TIMEZONE", "America/Los_Angeles"
            ),
        }

        # Start scheduler
        scheduler_service.start_scheduler(config)

    yield

    # Shutdown
    if not is_testing:
        logger.info("Shutting down News Llama web application")
        scheduler_service.stop_scheduler()


# Initialize FastAPI app with lifespan
app = FastAPI(title="News Llama", lifespan=lifespan)

# Register global exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Mount static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Favicon shortcut route (browsers request /favicon.ico directly)
@app.get("/favicon.ico")
async def favicon():
    """Serve favicon from static directory."""
    from fastapi.responses import FileResponse
    return FileResponse(static_path / "favicon.ico")

# Output path reference (for file serving via routes, not static mount)
output_path = Path(__file__).parent.parent.parent / "output"

# Templates
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))


# Mock data for frontend testing
MOCK_USERS = [
    {"id": 1, "first_name": "Alice", "avatar_path": None},
    {"id": 2, "first_name": "Bob", "avatar_path": None},
    {"id": 3, "first_name": "Charlie", "avatar_path": None},
]

MOCK_INTERESTS = [
    "AI",
    "rust",
    "LocalLLM",
    "LocalLlama",
    "strix halo",
    "startups",
    "technology",
    "programming",
    "machine learning",
    "web development",
]

MOCK_NEWSLETTERS = [
    {
        "id": 1,
        "user_id": 1,
        "date": "2025-10-22",
        "guid": "news-2025-10-22",  # Maps to actual file in output/
        "status": "completed",
    },
    {
        "id": 2,
        "user_id": 1,
        "date": "2025-10-21",
        "guid": "news-2025-10-22",  # Reuse same file for demo
        "status": "completed",
    },
    {
        "id": 3,
        "user_id": 1,
        "date": "2025-10-20",
        "guid": "news-2025-10-22",  # Reuse same file for demo
        "status": "pending",
    },
]


@app.get("/", response_class=HTMLResponse)
async def profile_select(request: Request, db: Session = Depends(get_db)):
    """Profile selection page with real users from database."""
    users = user_service.get_all_users(db)
    return templates.TemplateResponse(request, "profile_select.html", {"users": users})


@app.get("/profile/new", response_class=HTMLResponse)
async def profile_create_page(request: Request):
    """Profile creation page with grouped interests."""
    interests_grouped = interest_service.get_predefined_interests_grouped()
    return templates.TemplateResponse(
        request, "profile_create.html", {"interests_grouped": interests_grouped}
    )


@app.post("/profile/create")
async def profile_create(
    profile_data: ProfileCreateRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Create new profile with interests and set session cookie."""
    # Create user
    user = user_service.create_user(db, first_name=profile_data.first_name)

    # Get predefined interests for comparison
    predefined_interests = interest_service.get_predefined_interests()
    predefined_set = {i.lower() for i in predefined_interests}

    # Deduplicate interests (case-insensitive)
    seen = set()
    unique_interests = []
    for interest in profile_data.interests:
        interest_lower = interest.lower()
        if interest_lower not in seen:
            seen.add(interest_lower)
            unique_interests.append(interest)

    # Add interests
    for interest_name in unique_interests:
        is_predefined = interest_name.lower() in predefined_set
        interest_service.add_user_interest(
            db,
            user_id=user.id,
            interest_name=interest_name,
            is_predefined=is_predefined,
        )

    # Queue newsletter generation for today
    newsletter_queued = False
    try:
        newsletter = generation_service.queue_newsletter_generation(
            db, user.id, date.today()
        )
        scheduler_service.queue_immediate_generation(newsletter.id)
        newsletter_queued = True
    except generation_service.NewsletterAlreadyExistsError:
        # Newsletter already exists for today - this is fine, continue
        pass
    except Exception:
        # Log error but don't block profile creation
        # Newsletter generation failures shouldn't prevent user onboarding
        pass

    # Return JSON response with redirect URL and set cookie
    if newsletter_queued:
        redirect_url = "/calendar?toast=Generating your first newsletter! This may take 10-15 minutes depending on your interests.&toast_type=info"
    else:
        redirect_url = "/calendar"

    response_data = {
        "status": "success",
        "redirect_url": redirect_url,
        "user_id": user.id,
    }
    response = JSONResponse(content=response_data)
    response.set_cookie(key="user_id", value=str(user.id))
    return response


@app.post("/profile/avatar")
async def upload_avatar(
    avatar: UploadFile = File(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Upload profile avatar image."""
    # Validate file size (500KB max)
    contents = await avatar.read()
    if len(contents) > 500 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 500KB")

    # Validate actual file content (magic bytes) to prevent spoofing
    try:
        mime_type = magic.from_buffer(contents, mime=True)
        if not mime_type.startswith("image/"):
            raise HTTPException(
                status_code=400, detail=f"File must be an image (detected: {mime_type})"
            )
    except Exception as e:
        logger.error(f"Magic byte validation failed: {e}")
        raise HTTPException(
            status_code=400,
            detail="Unable to validate file type. Please upload a valid image.",
        )

    # Validate file extension against whitelist
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}

    if avatar.filename:
        file_extension = avatar.filename.rsplit(".", 1)[-1].lower()
        # Sanitize extension to prevent path traversal
        file_extension = (
            file_extension.replace("/", "").replace("\\", "").replace("..", "")
        )
    else:
        file_extension = "jpg"

    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    if len(file_extension) > 10:  # Prevent absurdly long extensions
        raise HTTPException(status_code=400, detail="Invalid file extension")

    # Create avatars directory if it doesn't exist
    avatars_dir = Path(__file__).parent / "static" / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)

    # Save file with user ID as filename
    avatar_filename = f"{user.id}.{file_extension}"
    avatar_path = (avatars_dir / avatar_filename).resolve()

    # Verify final path is within avatars_dir (prevent path traversal)
    if not str(avatar_path).startswith(str(avatars_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")

    # Open and compress image
    try:
        image = Image.open(io.BytesIO(contents))

        # Resize to max 512x512 (preserve aspect ratio)
        image.thumbnail((512, 512), Image.Resampling.LANCZOS)

        # Convert to RGB if necessary (for PNG with transparency, etc.)
        if image.mode in ("RGBA", "LA", "P"):
            # Create white background
            background = Image.new("RGB", image.size, (255, 255, 255))
            # Convert to RGBA if palette mode
            if image.mode == "P":
                image = image.convert("RGBA")
            # Paste with alpha channel as mask
            if "A" in image.mode:
                background.paste(image, mask=image.split()[-1])
            else:
                background.paste(image)
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")

        # Save compressed JPEG
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=85, optimize=True)
        compressed_contents = output.getvalue()

        # Always save as .jpg regardless of original extension
        avatar_filename = f"{user.id}.jpg"
        avatar_path = (avatars_dir / avatar_filename).resolve()

        # Verify path again after modification
        if not str(avatar_path).startswith(str(avatars_dir.resolve())):
            raise HTTPException(status_code=400, detail="Invalid file path")

        with open(avatar_path, "wb") as f:
            f.write(compressed_contents)

    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        raise HTTPException(
            status_code=400,
            detail="Failed to process image. Please upload a valid image file.",
        )

    # Update user's avatar_path in database
    user_service.update_user(db, user.id, avatar_path=avatar_filename)

    return {"status": "success", "avatar_path": avatar_filename}


@app.get("/calendar", response_class=HTMLResponse)
async def calendar_view(
    request: Request,
    user_id: Optional[int] = None,  # Query parameter for profile selection
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calendar view page with user session check."""
    # If user_id provided in query param, set cookie and redirect
    if user_id is not None:
        # Validate user exists
        selected_user = db.query(User).filter(User.id == user_id).first()
        if selected_user:
            response = RedirectResponse(url="/calendar", status_code=303)
            response.set_cookie(key="user_id", value=str(user_id))
            return response
        # Invalid user_id, redirect to home
        return RedirectResponse(url="/", status_code=303)

    # Redirect to profile select if no user session
    if not user:
        return RedirectResponse(url="/", status_code=303)

    # Default to current month/year
    from datetime import date

    today = date.today()
    year = today.year
    month = today.month
    month_names = [
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    current_month = f"{month_names[month]} {year}"

    # Get newsletters for current month
    newsletters = newsletter_service.get_newsletters_by_month(db, user.id, year, month)

    # Check if any newsletters are pending/generating
    has_active = any(n.status in ["pending", "generating"] for n in newsletters)

    return templates.TemplateResponse(
        request,
        "calendar.html",
        {
            "user": user,
            "newsletters": newsletters,
            "current_month": current_month,
            "year": year,
            "month": month,
            "has_active": has_active,
            "today": today,
        },
    )


@app.get("/profile/settings", response_class=HTMLResponse)
async def profile_settings(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Profile settings page with user session check."""
    # Redirect to profile select if no user session
    if not user:
        return RedirectResponse(url="/", status_code=303)

    # Get user's interests
    user_interests_objs = interest_service.get_user_interests(db, user.id)
    user_interests = [i.interest_name for i in user_interests_objs]

    # Get grouped predefined interests
    interests_grouped = interest_service.get_predefined_interests_grouped()

    # Calculate real stats
    today = date.today()
    newsletters_this_month = newsletter_service.get_newsletters_by_month(
        db, user.id, today.year, today.month
    )
    this_month_completed = len(
        [n for n in newsletters_this_month if n.status == "completed"]
    )

    # Get total completed newsletters (all time)
    total_completed = newsletter_service.get_newsletter_count(
        db, user.id, status="completed"
    )

    stats = {
        "interests_count": len(user_interests),
        "this_month": this_month_completed,
        "total": total_completed,
        "retention_days": 365,
    }

    return templates.TemplateResponse(
        request,
        "profile_settings.html",
        {
            "user": user,
            "user_interests": user_interests,
            "interests_grouped": interests_grouped,
            "stats": stats,
        },
    )


@app.post("/profile/settings")
async def profile_settings_update(
    update_data: ProfileUpdateRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Update profile settings (first name and interests)."""

    # Update first name if provided
    if update_data.first_name is not None:
        user_service.update_user(db, user.id, first_name=update_data.first_name)

    # Update interests if provided
    interests_changed = False
    if update_data.interests is not None:
        # Get predefined interests for comparison
        predefined_interests = interest_service.get_predefined_interests()
        predefined_set = {i.lower() for i in predefined_interests}

        # Deduplicate interests (case-insensitive)
        seen = set()
        unique_interests = []
        for interest in update_data.interests:
            interest_lower = interest.lower()
            if interest_lower not in seen:
                seen.add(interest_lower)
                unique_interests.append(interest)

        # Calculate diff (what changed) - only modify what's different
        existing_interests = interest_service.get_user_interests(db, user.id)
        existing_set = {i.interest_name for i in existing_interests}
        new_set = set(unique_interests)

        to_remove = existing_set - new_set
        to_add = new_set - existing_set

        # Only remove interests that were deleted
        for interest_name in to_remove:
            interest_service.remove_user_interest(db, user.id, interest_name)
            interests_changed = True

        # Only add interests that are new
        for interest_name in to_add:
            is_predefined = interest_name.lower() in predefined_set
            interest_service.add_user_interest(
                db,
                user_id=user.id,
                interest_name=interest_name,
                is_predefined=is_predefined,
            )
            interests_changed = True

        # Trigger newsletter regeneration if interests changed
        if interests_changed:
            logger.info(
                f"Interests changed for user {user.id}, triggering newsletter regeneration"
            )
            generation_service.requeue_newsletter_for_today(db, user.id)
        else:
            logger.info(
                f"No interest changes for user {user.id}, skipping regeneration"
            )

    return {"status": "success"}


@app.delete("/profile/{user_id}")
async def delete_profile(
    user_id: int,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Delete user profile and all associated data.

    Cascades to user_interests and newsletters tables.
    Clears session cookie to prevent stale session errors.
    """
    try:
        # Delete the user (service handles cascade via foreign keys + file cleanup)
        user_service.delete_user(db, user_id)

        # Clear the session cookie to prevent "user not found" errors
        response.delete_cookie("user_id")

        return {
            "status": "success",
            "message": "Profile deleted successfully",
        }
    except user_service.UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=get_friendly_message(e))
    except user_service.UserServiceError as e:
        raise HTTPException(status_code=500, detail=get_friendly_message(e))


@app.post("/profile/settings/interests/add")
async def add_interest_route(
    interest_data: InterestAdd,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Add interest to user's profile and trigger newsletter regeneration."""

    try:
        interest = interest_service.add_user_interest(
            db,
            user_id=user.id,
            interest_name=interest_data.interest_name,
            is_predefined=interest_data.is_predefined,
        )

        # Trigger newsletter regeneration for today
        newsletter_regenerated = generation_service.requeue_newsletter_for_today(
            db, user.id
        )

        return {
            "status": "success",
            "interest": interest.interest_name,
            "newsletter_regenerated": newsletter_regenerated,
        }
    except interest_service.DuplicateInterestError as e:
        raise HTTPException(status_code=409, detail=get_friendly_message(e))
    except interest_service.InterestValidationError as e:
        raise HTTPException(status_code=422, detail=get_friendly_message(e))


@app.post("/profile/settings/interests/remove")
async def remove_interest_route(
    interest_data: InterestAdd,  # Reuse schema, only need interest_name
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Remove interest from user's profile and trigger newsletter regeneration."""

    try:
        interest_service.remove_user_interest(db, user.id, interest_data.interest_name)

        # Trigger newsletter regeneration for today
        newsletter_regenerated = generation_service.requeue_newsletter_for_today(
            db, user.id
        )

        return {
            "status": "success",
            "newsletter_regenerated": newsletter_regenerated,
        }
    except interest_service.InterestNotFoundError:
        raise HTTPException(status_code=404, detail="Interest not found")


@app.post("/newsletters/generate", response_model=NewsletterResponse)
async def generate_newsletter(
    newsletter_data: NewsletterCreate,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Generate newsletter for specified date with rate limiting."""

    # Apply rate limiting only for authenticated users
    from src.web.rate_limiter import newsletter_rate_limiter

    is_allowed, remaining = newsletter_rate_limiter.is_allowed(str(user.id))
    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before making another request.",
        )

    try:
        # Parse date from validated input
        newsletter_date = date.fromisoformat(newsletter_data.date)

        # Queue newsletter generation
        newsletter = generation_service.queue_newsletter_generation(
            db, user.id, newsletter_date
        )
        scheduler_service.queue_immediate_generation(newsletter.id)

        # Return newsletter response
        return NewsletterResponse(
            id=newsletter.id,
            user_id=newsletter.user_id,
            date=newsletter.date,
            guid=newsletter.guid,
            file_path=newsletter.file_path,
            status=newsletter.status,
            generated_at=newsletter.generated_at,
            retry_count=newsletter.retry_count,
        )

    except generation_service.NewsletterAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=get_friendly_message(e))
    except generation_service.GenerationServiceError as e:
        raise HTTPException(status_code=500, detail=get_friendly_message(e))


@app.get("/newsletters/logo.png")
async def serve_newsletter_logo():
    """Serve logo for newsletter HTML files (backwards compatibility)."""
    logo_path = static_path / "logo.png"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return Response(content=f.read(), media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo not found")


@app.get("/newsletters/{guid}")
async def view_newsletter(guid: str, db: Session = Depends(get_db)):
    """View a newsletter by GUID - database-backed retrieval."""
    try:
        # Look up newsletter in database
        newsletter = newsletter_service.get_newsletter_by_guid(db, guid)

        # If newsletter is completed and file exists, serve the file
        if newsletter.status == "completed" and newsletter.file_path:
            # Use cached file reading to reduce disk I/O
            content = file_cache.read_newsletter_file(newsletter.file_path)
            if content is not None:
                return Response(content=content, media_type="text/html")
            else:
                # File missing despite completed status
                raise HTTPException(
                    status_code=500, detail="Newsletter file not found on disk"
                )

        # For pending/generating/failed, return status information
        return JSONResponse(
            content={
                "guid": newsletter.guid,
                "date": newsletter.date,
                "status": newsletter.status,
                "file_path": newsletter.file_path,
                "generated_at": newsletter.generated_at,
                "retry_count": newsletter.retry_count,
            }
        )

    except newsletter_service.NewsletterNotFoundError:
        raise HTTPException(status_code=404, detail="Newsletter not found")


@app.post("/newsletters/{guid}/retry")
async def retry_newsletter_route(
    guid: str, user: User = Depends(require_user), db: Session = Depends(get_db)
):
    """Retry a failed newsletter by resetting it to pending status."""

    try:
        # Retry the newsletter
        newsletter = newsletter_service.retry_newsletter(db, guid)

        return {
            "status": "success",
            "guid": newsletter.guid,
            "newsletter_status": newsletter.status,
            "retry_count": newsletter.retry_count,
        }

    except newsletter_service.NewsletterNotFoundError as e:
        raise HTTPException(status_code=404, detail=get_friendly_message(e))
    except newsletter_service.NewsletterValidationError as e:
        raise HTTPException(status_code=400, detail=get_friendly_message(e))


@app.get("/calendar/{year}/{month}", response_class=HTMLResponse)
async def calendar_month(
    request: Request,
    year: int,
    month: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calendar view for specific month (HTMX partial) with validation."""
    # Redirect to profile select if no user session
    if not user:
        return RedirectResponse(url="/", status_code=303)

    # Validate month range
    if month < 1 or month > 12:
        return HTMLResponse("<h1>Invalid month</h1>", status_code=404)

    # Month names for display
    month_names = [
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    current_month = f"{month_names[month]} {year}"

    # Get newsletters for specified month
    newsletters = newsletter_service.get_newsletters_by_month(db, user.id, year, month)

    # Check if any newsletters are pending/generating
    has_active = any(n.status in ["pending", "generating"] for n in newsletters)

    # Get today's date for highlighting in calendar
    from datetime import date

    today = date.today()

    return templates.TemplateResponse(
        request,
        "calendar.html",
        {
            "user": user,
            "newsletters": newsletters,
            "current_month": current_month,
            "year": year,
            "month": month,
            "has_active": has_active,
            "today": today,
        },
    )


@app.get("/metrics", response_class=HTMLResponse)
async def metrics_page(request: Request, db: Session = Depends(get_db)):
    """
    Public metrics page - no authentication required.

    Shows discovery system performance stats and scheduler status.
    """
    from src.web.services.discovery_metrics_service import get_all_metrics
    from datetime import datetime, timezone

    metrics = get_all_metrics(db)

    # Get scheduler status
    scheduler_info = {
        "running": scheduler_service.scheduler.running,
        "jobs": []
    }

    if scheduler_service.scheduler.running:
        for job in scheduler_service.scheduler.get_jobs():
            job_info = {
                "id": job.id,
                "function": job.func.__name__,
                "next_run": None,
                "next_run_formatted": None,
                "hours_until": None
            }

            if job.next_run_time:
                # Get timezone if available (APScheduler stores timezone object)
                if hasattr(job.trigger, "timezone"):
                    tz = job.trigger.timezone
                    next_run_local = job.next_run_time.astimezone(tz)
                    tz_name = str(tz)
                else:
                    next_run_local = job.next_run_time.astimezone(timezone.utc)
                    tz_name = "UTC"

                job_info["next_run"] = next_run_local.isoformat()
                job_info["next_run_formatted"] = next_run_local.strftime("%Y-%m-%d %I:%M %p %Z")

                # Calculate hours until
                now = datetime.now(timezone.utc)
                time_until = next_run_local - now
                job_info["hours_until"] = time_until.total_seconds() / 3600

                # Get schedule description
                if job.id == "daily_generation" and hasattr(job.trigger, "hour"):
                    job_info["schedule"] = f"Daily at {job.trigger.hour:02d}:{job.trigger.minute:02d} {tz_name}"
                elif job.id == "weekly_discovery" and hasattr(job.trigger, "day_of_week"):
                    job_info["schedule"] = f"Weekly on {job.trigger.day_of_week} at {job.trigger.hour:02d}:{job.trigger.minute:02d} {tz_name}"
                elif job.id == "rate_limiter_cleanup" and hasattr(job.trigger, "interval"):
                    job_info["schedule"] = f"Every {job.trigger.interval}"
                else:
                    job_info["schedule"] = "Custom schedule"

            scheduler_info["jobs"].append(job_info)

    return templates.TemplateResponse(request, "metrics.html", {
        "metrics": metrics,
        "scheduler": scheduler_info
    })


@app.get("/health/scheduler")
async def scheduler_health():
    """
    Check scheduler status and jobs.

    Returns scheduler running status and list of scheduled jobs with their next run times.
    """
    jobs_info = []
    for job in scheduler_service.scheduler.get_jobs():
        jobs_info.append(
            {
                "id": job.id,
                "next_run": job.next_run_time.isoformat()
                if job.next_run_time
                else None,
                "name": str(job.func),
            }
        )

    return {
        "running": scheduler_service.scheduler.running,
        "jobs": jobs_info,
        "job_count": len(jobs_info),
    }


@app.get("/health/generation")
async def generation_health():
    """
    Check generation metrics and performance.

    Returns generation stats including success/failure counts, success rate, and average duration.
    """
    return generation_service.metrics.get_stats()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
