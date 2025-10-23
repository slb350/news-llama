"""FastAPI application for News Llama web interface.

Phase 3: Backend integration with database services.
"""

from fastapi import FastAPI, Request, Depends, Response, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import date

from src.web.database import get_db
from src.web.dependencies import get_current_user
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
)

# Initialize FastAPI app
app = FastAPI(title="News Llama")

# Mount static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

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
    return templates.TemplateResponse(
        "profile_select.html", {"request": request, "users": users}
    )


@app.get("/profile/new", response_class=HTMLResponse)
async def profile_create_page(request: Request):
    """Profile creation page with predefined interests."""
    interests = interest_service.get_predefined_interests()
    return templates.TemplateResponse(
        "profile_create.html", {"request": request, "interests": interests}
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
        generation_service.queue_newsletter_generation(db, user.id, date.today())
        newsletter_queued = True
    except generation_service.NewsletterAlreadyExistsError:
        # Newsletter already exists for today - this is fine, continue
        pass
    except Exception:
        # Log error but don't block profile creation
        # Newsletter generation failures shouldn't prevent user onboarding
        pass

    # Set user_id cookie and redirect with toast message
    if newsletter_queued:
        redirect_url = "/calendar?toast=Generating your first newsletter! This may take 10-15 minutes depending on your interests.&toast_type=info"
    else:
        redirect_url = "/calendar"

    redirect = RedirectResponse(url=redirect_url, status_code=303)
    redirect.set_cookie(key="user_id", value=str(user.id))
    return redirect


@app.get("/calendar", response_class=HTMLResponse)
async def calendar_view(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calendar view page with user session check."""
    # Redirect to profile select if no user session
    if not user:
        return RedirectResponse(url="/", status_code=303)

    # Default to October 2025 (matches mockup)
    year = 2025
    month = 10
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

    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "user": user,
            "newsletters": newsletters,
            "current_month": current_month,
            "year": year,
            "month": month,
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

    # Get available predefined interests
    available_interests = interest_service.get_predefined_interests()

    return templates.TemplateResponse(
        "profile_settings.html",
        {
            "request": request,
            "user": user,
            "user_interests": user_interests,
            "available_interests": available_interests,
        },
    )


@app.post("/profile/settings")
async def profile_settings_update(
    update_data: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update profile settings (first name)."""
    # Redirect to profile select if no user session
    if not user:
        return RedirectResponse(url="/", status_code=303)

    # Update first name if provided
    if update_data.first_name is not None:
        user_service.update_user(db, user.id, first_name=update_data.first_name)

    return {"status": "success"}


@app.post("/profile/settings/interests/add")
async def add_interest_route(
    interest_data: InterestAdd,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add interest to user's profile and trigger newsletter regeneration."""
    # Require user session
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

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
    except interest_service.DuplicateInterestError:
        raise HTTPException(status_code=409, detail="Interest already exists")
    except interest_service.InterestValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/profile/settings/interests/remove")
async def remove_interest_route(
    interest_data: InterestAdd,  # Reuse schema, only need interest_name
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove interest from user's profile and trigger newsletter regeneration."""
    # Require user session
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate newsletter for specified date."""
    # Require user session
    if not user:
        return RedirectResponse(url="/", status_code=303)

    try:
        # Parse date from validated input
        newsletter_date = date.fromisoformat(newsletter_data.date)

        # Queue newsletter generation
        newsletter = generation_service.queue_newsletter_generation(
            db, user.id, newsletter_date
        )

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
        raise HTTPException(status_code=409, detail=str(e))
    except generation_service.GenerationServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/newsletters/{guid}")
async def view_newsletter(guid: str, db: Session = Depends(get_db)):
    """View a newsletter by GUID - database-backed retrieval."""
    try:
        # Look up newsletter in database
        newsletter = newsletter_service.get_newsletter_by_guid(db, guid)

        # If newsletter is completed and file exists, serve the file
        if newsletter.status == "completed" and newsletter.file_path:
            file_path = Path(newsletter.file_path)
            if file_path.exists():
                return FileResponse(file_path, media_type="text/html")
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

    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "user": user,
            "newsletters": newsletters,
            "current_month": current_month,
            "year": year,
            "month": month,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
