"""FastAPI application for News Llama web interface.

Phase 3: Backend integration with database services.
"""

from fastapi import FastAPI, Request, Depends, Response, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from src.web.database import get_db
from src.web.dependencies import get_current_user
from src.web.schemas import ProfileCreateRequest, ProfileUpdateRequest, InterestAdd
from src.web.models import User
from src.web.services import user_service, interest_service, newsletter_service

# Initialize FastAPI app
app = FastAPI(title="News Llama")

# Mount static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Mount output directory for newsletters
output_path = Path(__file__).parent.parent.parent / "output"
app.mount("/newsletters", StaticFiles(directory=str(output_path)), name="newsletters")

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

    # Set user_id cookie and redirect
    redirect = RedirectResponse(url="/calendar", status_code=303)
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
    """Add interest to user's profile."""
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
        return {"status": "success", "interest": interest.interest_name}
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
    """Remove interest from user's profile."""
    # Require user session
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        interest_service.remove_user_interest(db, user.id, interest_data.interest_name)
        return {"status": "success"}
    except interest_service.InterestNotFoundError:
        raise HTTPException(status_code=404, detail="Interest not found")


@app.get("/newsletter/{guid}")
async def view_newsletter(guid: str):
    """View a newsletter by GUID."""
    # In mockup, redirect to the static file
    # In production, this would look up the file_path from database
    newsletter_file = output_path / f"{guid}.html"
    if newsletter_file.exists():
        return FileResponse(newsletter_file)
    return HTMLResponse("<h1>Newsletter not found</h1>", status_code=404)


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
