"""
Pydantic schemas for News Llama web API.

Request/response models for FastAPI endpoints with validation.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import date


# User Schemas
class UserCreate(BaseModel):
    """Request schema for creating a new user."""

    first_name: str = Field(..., min_length=1, max_length=100)
    interests: list[str] = Field(default_factory=list)

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: str) -> str:
        """Ensure first name is not just whitespace."""
        if not v.strip():
            raise ValueError("First name cannot be empty or whitespace")
        return v.strip()


class UserResponse(BaseModel):
    """Response schema for user data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    avatar_path: Optional[str]
    created_at: str


# Interest Schemas
class InterestAdd(BaseModel):
    """Request schema for adding an interest."""

    interest_name: str = Field(..., min_length=1, max_length=200)
    is_predefined: bool = Field(default=False)

    @field_validator("interest_name")
    @classmethod
    def validate_interest_name(cls, v: str) -> str:
        """Ensure interest name is not just whitespace."""
        if not v.strip():
            raise ValueError("Interest name cannot be empty or whitespace")
        return v.strip()


class InterestResponse(BaseModel):
    """Response schema for interest data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    interest_name: str
    is_predefined: bool
    added_at: str


class InterestSearch(BaseModel):
    """Response schema for interest search results."""

    interests: list[str]


# Newsletter Schemas
class NewsletterResponse(BaseModel):
    """Response schema for newsletter data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date: str
    guid: str
    file_path: Optional[str]
    status: str
    generated_at: Optional[str]
    retry_count: int


class NewsletterCreate(BaseModel):
    """Request schema for creating a newsletter."""

    date: str = Field(
        default_factory=lambda: date.today().isoformat(),
        description="Date in YYYY-MM-DD format (defaults to today)",
    )

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Ensure date is valid format."""
        try:
            # Validate it's a valid date
            date.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")


# Profile Schemas
class ProfileCreateRequest(BaseModel):
    """Request schema for complete profile creation."""

    first_name: str = Field(..., min_length=1, max_length=100)
    interests: list[str] = Field(default_factory=list)

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: str) -> str:
        """Ensure first name is not just whitespace."""
        if not v.strip():
            raise ValueError("First name cannot be empty or whitespace")
        return v.strip()


class ProfileResponse(BaseModel):
    """Response schema for complete profile data."""

    user: UserResponse
    interests: list[InterestResponse]
    newsletter_count: int


# Settings Schemas
class ProfileUpdateRequest(BaseModel):
    """Request schema for updating profile."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    interests: Optional[list[str]] = Field(None)

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: Optional[str]) -> Optional[str]:
        """Ensure first name is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("First name cannot be empty or whitespace")
        return v.strip() if v else None


# Error Response Schema
class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_type: Optional[str] = None
