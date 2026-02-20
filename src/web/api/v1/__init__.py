"""API v1 router for the News Llama JSON API."""

from fastapi import APIRouter

from src.web.api.v1.users import router as users_router
from src.web.api.v1.interests import router as interests_router
from src.web.api.v1.newsletters import router as newsletters_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(interests_router, prefix="/interests", tags=["interests"])
api_router.include_router(
    newsletters_router, prefix="/newsletters", tags=["newsletters"]
)
