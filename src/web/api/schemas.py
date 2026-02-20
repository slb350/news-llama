"""Pydantic response schemas for the News Llama JSON API v1."""

from pydantic import BaseModel, ConfigDict
from typing import Optional


class InterestBrief(BaseModel):
    """Brief interest info for user listings."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    interest_name: str
    is_predefined: bool


class InterestFull(BaseModel):
    """Full interest info with user association details."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    interest_name: str
    is_predefined: bool
    added_at: str


class UserBrief(BaseModel):
    """User summary for list views."""

    id: int
    first_name: str
    avatar_path: Optional[str]
    created_at: str
    interests: list[InterestBrief]
    newsletter_count: int


class UserListResponse(BaseModel):
    """Response for GET /api/v1/users."""

    users: list[UserBrief]
    count: int


class UserDetailResponse(BaseModel):
    """Response for GET /api/v1/users/{id}."""

    id: int
    first_name: str
    avatar_path: Optional[str]
    created_at: str
    interests: list[InterestFull]
    newsletter_count: int


class NewsletterBrief(BaseModel):
    """Newsletter summary for calendar views."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date: str
    guid: str
    file_path: Optional[str]
    status: str
    generated_at: Optional[str]
    retry_count: int


class UserNewslettersResponse(BaseModel):
    """Response for GET /api/v1/users/{id}/newsletters."""

    newsletters: list[NewsletterBrief]
    year: int
    month: int
    count: int


class InterestGroup(BaseModel):
    """A category group of predefined interests."""

    key: str
    name: str
    emoji: str
    interests: list[str]


class PredefinedInterestsGroupedResponse(BaseModel):
    """Response for GET /api/v1/interests/predefined (grouped)."""

    groups: list[InterestGroup]


class PredefinedInterestsFlatResponse(BaseModel):
    """Response for GET /api/v1/interests/predefined?flat=true."""

    interests: list[str]


class InterestSearchResponse(BaseModel):
    """Response for GET /api/v1/interests/search."""

    results: list[str]
    count: int


class NewsletterContentResponse(BaseModel):
    """Response for GET /api/v1/newsletters/{guid}/content."""

    guid: str
    date: str
    status: str
    generated_at: Optional[str]
    retry_count: int
    html_content: Optional[str]
