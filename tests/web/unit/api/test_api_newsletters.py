"""
Unit tests for API v1 newsletter endpoints.

Tests JSON API responses for native client consumption:
- GET /api/v1/newsletters/{guid}/content — newsletter HTML content (JSON)
- GET /api/v1/newsletters/{guid}/render — raw HTML for WKWebView rendering
"""

import pytest
from datetime import date
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.web.app import app
from src.web.database import get_test_db, get_db
from src.web.services.user_service import create_user
from src.web.services.newsletter_service import (
    create_pending_newsletter,
    mark_newsletter_completed,
)


@pytest.fixture
def db():
    """Provide test database session."""
    yield from get_test_db()


@pytest.fixture
def client(db: Session):
    """Provide test client with database override."""

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def user(db: Session):
    """Create test user."""
    return create_user(db, first_name="TestUser")


@pytest.fixture
def completed_newsletter(db: Session, user):
    """Create a completed newsletter with file path."""
    newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 15))
    mark_newsletter_completed(db, newsletter.id, "output/news-2025-10-15.html")
    return newsletter


@pytest.fixture
def pending_newsletter(db: Session, user):
    """Create a pending newsletter."""
    return create_pending_newsletter(db, user.id, date(2025, 10, 20))


class TestNewsletterContent:
    """Tests for GET /api/v1/newsletters/{guid}/content."""

    def test_completed_newsletter_returns_html_content(
        self, client: TestClient, completed_newsletter
    ):
        """Should return HTML content for completed newsletter."""
        html_bytes = b"<html><body><h1>News Digest</h1></body></html>"

        with patch(
            "src.web.api.v1.newsletters.file_cache.read_newsletter_file"
        ) as mock_read:
            mock_read.return_value = html_bytes

            response = client.get(
                f"/api/v1/newsletters/{completed_newsletter.guid}/content"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["guid"] == completed_newsletter.guid
        assert data["status"] == "completed"
        assert data["html_content"] == html_bytes.decode("utf-8")
        assert data["date"] == "2025-10-15"

    def test_pending_newsletter_returns_null_html(
        self, client: TestClient, pending_newsletter
    ):
        """Should return null html_content for pending newsletter."""
        response = client.get(f"/api/v1/newsletters/{pending_newsletter.guid}/content")

        assert response.status_code == 200
        data = response.json()
        assert data["guid"] == pending_newsletter.guid
        assert data["status"] == "pending"
        assert data["html_content"] is None

    def test_newsletter_not_found(self, client: TestClient):
        """Should return 404 for nonexistent GUID."""
        response = client.get("/api/v1/newsletters/nonexistent-guid/content")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_completed_newsletter_missing_file(
        self, client: TestClient, completed_newsletter
    ):
        """Should return null html_content when file is missing on disk."""
        with patch(
            "src.web.api.v1.newsletters.file_cache.read_newsletter_file"
        ) as mock_read:
            mock_read.return_value = None

            response = client.get(
                f"/api/v1/newsletters/{completed_newsletter.guid}/content"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["html_content"] is None

    def test_newsletter_content_has_all_fields(
        self, client: TestClient, pending_newsletter
    ):
        """Response should include all expected fields."""
        response = client.get(f"/api/v1/newsletters/{pending_newsletter.guid}/content")
        data = response.json()

        assert "guid" in data
        assert "date" in data
        assert "status" in data
        assert "generated_at" in data
        assert "retry_count" in data
        assert "html_content" in data


class TestNewsletterRender:
    """Tests for GET /api/v1/newsletters/{guid}/render."""

    def test_render_returns_raw_html(self, client: TestClient, completed_newsletter):
        """Should return raw HTML with text/html content type."""
        html_bytes = b"<html><body><h1>News Digest</h1></body></html>"

        with patch(
            "src.web.api.v1.newsletters.file_cache.read_newsletter_file"
        ) as mock_read:
            mock_read.return_value = html_bytes

            response = client.get(
                f"/api/v1/newsletters/{completed_newsletter.guid}/render"
            )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert response.text == html_bytes.decode("utf-8")

    def test_render_pending_returns_404(self, client: TestClient, pending_newsletter):
        """Should return 404 for pending newsletter."""
        response = client.get(
            f"/api/v1/newsletters/{pending_newsletter.guid}/render"
        )
        assert response.status_code == 404

    def test_render_not_found_returns_404(self, client: TestClient):
        """Should return 404 for nonexistent GUID."""
        response = client.get("/api/v1/newsletters/nonexistent-guid/render")
        assert response.status_code == 404

    def test_render_missing_file_returns_404(
        self, client: TestClient, completed_newsletter
    ):
        """Should return 404 when HTML file is missing on disk."""
        with patch(
            "src.web.api.v1.newsletters.file_cache.read_newsletter_file"
        ) as mock_read:
            mock_read.return_value = None

            response = client.get(
                f"/api/v1/newsletters/{completed_newsletter.guid}/render"
            )

        assert response.status_code == 404
