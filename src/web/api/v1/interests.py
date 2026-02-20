"""API v1 interest endpoints for the News Llama native client."""

from fastapi import APIRouter

from src.web.services import interest_service
from src.web.api.schemas import (
    InterestGroup,
    InterestSearchResponse,
    PredefinedInterestsFlatResponse,
    PredefinedInterestsGroupedResponse,
)

router = APIRouter()


@router.get("/predefined")
def get_predefined_interests(flat: bool = False):
    """Get predefined interests, grouped by category or as a flat list."""
    if flat:
        interests = interest_service.get_predefined_interests()
        return PredefinedInterestsFlatResponse(interests=interests)

    grouped = interest_service.get_predefined_interests_grouped()
    groups = [
        InterestGroup(
            key=key,
            name=data["name"],
            emoji=data["emoji"],
            interests=data["interests"],
        )
        for key, data in grouped.items()
    ]
    return PredefinedInterestsGroupedResponse(groups=groups)


@router.get("/search", response_model=InterestSearchResponse)
def search_interests(q: str = ""):
    """Search predefined interests by query string."""
    results = interest_service.search_interests(q)
    return InterestSearchResponse(results=results, count=len(results))
