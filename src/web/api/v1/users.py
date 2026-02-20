"""API v1 user endpoints for the News Llama native client."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.web.database import get_db
from src.web.services import user_service, interest_service, newsletter_service
from src.web.services.user_service import UserNotFoundError
from src.web.api.schemas import (
    InterestBrief,
    InterestFull,
    NewsletterBrief,
    UserBrief,
    UserDetailResponse,
    UserListResponse,
    UserNewslettersResponse,
)

router = APIRouter()


@router.get("/", response_model=UserListResponse)
def list_users(db: Session = Depends(get_db)):
    """List all users with their interests and newsletter counts."""
    users = user_service.get_all_users(db)

    user_briefs = []
    for user in users:
        interests = interest_service.get_user_interests(db, user.id)
        count = newsletter_service.get_newsletter_count(db, user.id)
        user_briefs.append(
            UserBrief(
                id=user.id,
                first_name=user.first_name,
                avatar_path=user.avatar_path,
                created_at=user.created_at,
                interests=[InterestBrief.model_validate(i) for i in interests],
                newsletter_count=count,
            )
        )

    return UserListResponse(users=user_briefs, count=len(user_briefs))


@router.get("/{user_id}", response_model=UserDetailResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get a single user with full interest details."""
    try:
        user = user_service.get_user(db, user_id)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    interests = interest_service.get_user_interests(db, user.id)
    count = newsletter_service.get_newsletter_count(db, user.id)

    return UserDetailResponse(
        id=user.id,
        first_name=user.first_name,
        avatar_path=user.avatar_path,
        created_at=user.created_at,
        interests=[InterestFull.model_validate(i) for i in interests],
        newsletter_count=count,
    )


@router.get("/{user_id}/newsletters", response_model=UserNewslettersResponse)
def get_user_newsletters(
    user_id: int,
    year: int | None = None,
    month: int | None = None,
    db: Session = Depends(get_db),
):
    """Get newsletters for a user in a given month (defaults to current month)."""
    try:
        user_service.get_user(db, user_id)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    newsletters = newsletter_service.get_newsletters_by_month(db, user_id, year, month)

    return UserNewslettersResponse(
        newsletters=[NewsletterBrief.model_validate(n) for n in newsletters],
        year=year,
        month=month,
        count=len(newsletters),
    )
