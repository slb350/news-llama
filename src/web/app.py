"""FastAPI application for News Llama web interface.

Phase 2: Frontend mockup with static data.
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

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
async def profile_select(request: Request):
    """Profile selection page."""
    return templates.TemplateResponse(
        "profile_select.html", {"request": request, "users": MOCK_USERS}
    )


@app.get("/profile/new", response_class=HTMLResponse)
async def profile_create(request: Request):
    """Profile creation page."""
    return templates.TemplateResponse(
        "profile_create.html", {"request": request, "interests": MOCK_INTERESTS}
    )


@app.get("/calendar", response_class=HTMLResponse)
async def calendar_view(request: Request):
    """Calendar view page."""
    # Default to current month (October 2025 for mockup)
    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "user": MOCK_USERS[0],
            "newsletters": MOCK_NEWSLETTERS,
            "current_month": "October 2025",
            "year": 2025,
            "month": 10,
        },
    )


@app.get("/profile/settings", response_class=HTMLResponse)
async def profile_settings(request: Request):
    """Profile settings page."""
    # Mock selected interests for the user
    user_interests = ["AI", "rust", "LocalLLM", "startups", "technology"]
    return templates.TemplateResponse(
        "profile_settings.html",
        {
            "request": request,
            "user": MOCK_USERS[0],
            "user_interests": user_interests,
            "available_interests": MOCK_INTERESTS,
        },
    )


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
async def calendar_month(request: Request, year: int, month: int):
    """Calendar view for specific month (HTMX partial)."""
    # For mockup, just return the same data with different month name
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

    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "user": MOCK_USERS[0],
            "newsletters": MOCK_NEWSLETTERS if month == 10 else [],  # Only October has data
            "current_month": current_month,
            "year": year,
            "month": month,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
