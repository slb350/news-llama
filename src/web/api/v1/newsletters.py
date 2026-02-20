"""API v1 newsletter endpoints for the News Llama native client."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.web.database import get_db
from src.web.services import newsletter_service
from src.web.services.newsletter_service import NewsletterNotFoundError
from src.web import file_cache
from src.web.api.schemas import NewsletterContentResponse

router = APIRouter()


@router.get("/{guid}/content", response_model=NewsletterContentResponse)
def get_newsletter_content(guid: str, db: Session = Depends(get_db)):
    """Get newsletter content by GUID, including HTML if completed."""
    try:
        newsletter = newsletter_service.get_newsletter_by_guid(db, guid)
    except NewsletterNotFoundError:
        raise HTTPException(status_code=404, detail=f"Newsletter {guid} not found")

    html_content = None
    if newsletter.status == "completed" and newsletter.file_path:
        file_bytes = file_cache.read_newsletter_file(newsletter.file_path)
        if file_bytes is not None:
            html_content = file_bytes.decode("utf-8")

    return NewsletterContentResponse(
        guid=newsletter.guid,
        date=newsletter.date,
        status=newsletter.status,
        generated_at=newsletter.generated_at,
        retry_count=newsletter.retry_count,
        html_content=html_content,
    )
