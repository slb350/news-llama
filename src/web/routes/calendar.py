"""Calendar pages: the current month and any month navigated to."""

import calendar
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.web.database import get_db
from src.web.dependencies import get_current_user
from src.web.models import User
from src.web.services import newsletter_service
from src.web.templating import templates

router = APIRouter()


def calendar_context(db: Session, user: User, year: int, month: int) -> dict:
    """Template context for one month of a user's calendar in a Sunday-first grid."""
    newsletters = newsletter_service.get_newsletters_by_month(db, user.id, year, month)
    monday_based_first_weekday, days_in_month = calendar.monthrange(year, month)
    leading_padding = (monday_based_first_weekday + 1) % 7
    return {
        "user": user,
        "newsletters": newsletters,
        "has_any_newsletters": newsletter_service.get_newsletter_count(db, user.id) > 0,
        "current_month": f"{calendar.month_name[month]} {year}",
        "year": year,
        "month": month,
        "days_in_month": days_in_month,
        "leading_padding": leading_padding,
        "trailing_padding": -(leading_padding + days_in_month) % 7,
        "today": date.today(),
    }


@router.get("/calendar", response_class=HTMLResponse)
async def calendar_view(
    request: Request,
    user_id: Optional[int] = None,  # Query parameter for profile selection
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calendar for the current month; ?user_id= selects a profile and redirects."""
    if user_id is not None:
        if db.query(User).filter(User.id == user_id).first():
            response = RedirectResponse(url="/calendar", status_code=303)
            response.set_cookie(key="user_id", value=str(user_id))
            return response
        return RedirectResponse(url="/", status_code=303)

    if not user:
        return RedirectResponse(url="/", status_code=303)

    today = date.today()
    return templates.TemplateResponse(
        request, "calendar.html", calendar_context(db, user, today.year, today.month)
    )


@router.get("/calendar/{year}/{month}", response_class=HTMLResponse)
async def calendar_month(
    request: Request,
    year: int,
    month: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calendar for a specific month (HTMX navigation target)."""
    if not user:
        return RedirectResponse(url="/", status_code=303)

    if month < 1 or month > 12:
        return HTMLResponse("<h1>Invalid month</h1>", status_code=404)
    if year < 1 or year > 9999:
        return HTMLResponse("<h1>Invalid year</h1>", status_code=404)

    return templates.TemplateResponse(
        request, "calendar.html", calendar_context(db, user, year, month)
    )
