"""
Unit tests for newsletter generation routes - TDD RED phase.

Tests newsletter generation and retrieval:
- POST /newsletters/generate: Manual newsletter generation with validation
- GET /newsletters/{guid}: Database-backed newsletter retrieval
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta
from pathlib import Path
import tempfile
from unittest.mock import patch

from src.web.app import app
from src.web.database import get_test_db, get_db
from src.web.services.user_service import create_user
from src.web.services.interest_service import add_user_interest
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
def user_with_interests(db: Session):
    """Create test user with interests."""
    user = create_user(db, first_name="NewsletterUser")
    add_user_interest(db, user.id, "AI", is_predefined=True)
    add_user_interest(db, user.id, "rust", is_predefined=True)
    add_user_interest(db, user.id, "python", is_predefined=True)
    return user


@pytest.fixture
def authenticated_client(client: TestClient, user_with_interests):
    """Provide client with user session cookie."""
    # Set user_id cookie
    client.cookies.set("user_id", str(user_with_interests.id))
    return client, user_with_interests


class TestGenerateNewsletterPost:
    """Tests for POST /newsletters/generate - manual newsletter generation."""

    def test_generate_requires_authentication(self, client: TestClient):
        """Should redirect to profile select if no user session."""
        response = client.post(
            "/newsletters/generate",
            json={"date": "2025-10-22"},
            follow_redirects=False,
        )

        # Should redirect to profile selection
        assert response.status_code == 303
        assert response.headers["location"] == "/"

    @patch("src.web.services.generation_service.process_newsletter_generation")
    def test_generate_creates_pending_newsletter(
        self, mock_process, authenticated_client, db: Session
    ):
        """Should create pending newsletter and return guid."""
        client, user = authenticated_client

        response = client.post("/newsletters/generate", json={"date": "2025-10-22"})

        assert response.status_code == 200
        data = response.json()

        # Should return newsletter data
        assert "guid" in data
        assert "status" in data
        assert data["status"] == "pending"
        assert "date" in data
        assert data["date"] == "2025-10-22"

        # Verify newsletter was created in database
        from src.web.services.newsletter_service import get_newsletter_by_guid

        newsletter = get_newsletter_by_guid(db, data["guid"])
        assert newsletter.user_id == user.id
        assert newsletter.date == "2025-10-22"
        assert newsletter.status == "pending"

    @patch("src.web.services.generation_service.process_newsletter_generation")
    def test_generate_prevents_duplicates(
        self, mock_process, authenticated_client, db: Session
    ):
        """Should prevent duplicate newsletters for same user/date."""
        client, user = authenticated_client

        # Create first newsletter
        response1 = client.post("/newsletters/generate", json={"date": "2025-10-22"})
        assert response1.status_code == 200

        # Try to create duplicate
        response2 = client.post("/newsletters/generate", json={"date": "2025-10-22"})

        # Should return error
        assert response2.status_code == 409  # Conflict
        data = response2.json()
        assert "detail" in data
        assert "already exists" in data["detail"].lower()

    @patch("src.web.services.generation_service.process_newsletter_generation")
    def test_generate_accepts_today_as_default(
        self, mock_process, authenticated_client
    ):
        """Should use today's date if not specified."""
        client, user = authenticated_client

        response = client.post("/newsletters/generate", json={})

        assert response.status_code == 200
        data = response.json()

        # Should use today's date
        today = date.today().isoformat()
        assert data["date"] == today

    @patch("src.web.services.generation_service.process_newsletter_generation")
    def test_generate_accepts_future_dates(self, mock_process, authenticated_client):
        """Should allow generating newsletters for future dates."""
        client, user = authenticated_client

        future_date = (date.today() + timedelta(days=7)).isoformat()
        response = client.post("/newsletters/generate", json={"date": future_date})

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == future_date

    @patch("src.web.services.generation_service.process_newsletter_generation")
    def test_generate_validates_date_format(self, mock_process, authenticated_client):
        """Should reject invalid date formats."""
        client, user = authenticated_client

        # Invalid date format
        response = client.post("/newsletters/generate", json={"date": "10-22-2025"})

        assert response.status_code == 422  # Validation error

    @patch("src.web.services.generation_service.process_newsletter_generation")
    def test_generate_queues_background_job(
        self, mock_process, authenticated_client, db: Session
    ):
        """Should queue background generation job."""
        client, user = authenticated_client

        response = client.post("/newsletters/generate", json={"date": "2025-10-22"})

        assert response.status_code == 200
        data = response.json()

        # Mock should be called to process generation
        # (In real implementation, this would be async background job)
        # For now, we just verify the newsletter was queued
        from src.web.services.newsletter_service import get_newsletter_by_guid

        newsletter = get_newsletter_by_guid(db, data["guid"])
        assert newsletter is not None

    @patch("src.web.services.generation_service.process_newsletter_generation")
    def test_generate_multiple_dates_same_user(
        self, mock_process, authenticated_client
    ):
        """Should allow same user to generate newsletters for different dates."""
        client, user = authenticated_client

        response1 = client.post("/newsletters/generate", json={"date": "2025-10-22"})
        response2 = client.post("/newsletters/generate", json={"date": "2025-10-23"})

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Should have different guids
        assert data1["guid"] != data2["guid"]
        assert data1["date"] == "2025-10-22"
        assert data2["date"] == "2025-10-23"


class TestGetNewsletterByGuid:
    """Tests for GET /newsletters/{guid} - database-backed retrieval."""

    def test_get_newsletter_not_found(self, client: TestClient):
        """Should return 404 for non-existent guid."""
        response = client.get("/newsletters/invalid-guid-12345")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_get_newsletter_pending_status(self, authenticated_client, db: Session):
        """Should return status info for pending newsletter."""
        client, user = authenticated_client

        # Create pending newsletter
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))

        response = client.get(f"/newsletters/{newsletter.guid}")

        assert response.status_code == 200
        data = response.json()

        # Should return status information
        assert data["status"] == "pending"
        assert data["guid"] == newsletter.guid
        assert data["date"] == "2025-10-22"
        assert data["file_path"] is None

    def test_get_newsletter_completed_returns_file(
        self, authenticated_client, db: Session
    ):
        """Should serve HTML file for completed newsletter."""
        client, user = authenticated_client

        # Create completed newsletter with file
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))

        # Create temporary HTML file
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test-newsletter.html"
            test_file.write_text("<html><body>Test Newsletter</body></html>")

            # Mark as completed with file path
            mark_newsletter_completed(db, newsletter.id, str(test_file))

            response = client.get(f"/newsletters/{newsletter.guid}")

            # Should return HTML file
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/html")
            assert "Test Newsletter" in response.text

    def test_get_newsletter_completed_file_missing(
        self, authenticated_client, db: Session
    ):
        """Should return error if completed newsletter file is missing."""
        client, user = authenticated_client

        # Create completed newsletter with non-existent file
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))
        mark_newsletter_completed(db, newsletter.id, "/non/existent/path.html")

        response = client.get(f"/newsletters/{newsletter.guid}")

        # Should return error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "file not found" in data["detail"].lower()

    def test_get_newsletter_generating_status(self, authenticated_client, db: Session):
        """Should return generating status for in-progress newsletter."""
        client, user = authenticated_client

        # Create pending newsletter
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))

        # Mark as generating
        from src.web.services.newsletter_service import (
            mark_newsletter_generating,
        )

        mark_newsletter_generating(db, newsletter.id)

        response = client.get(f"/newsletters/{newsletter.guid}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "generating"

    def test_get_newsletter_failed_status(self, authenticated_client, db: Session):
        """Should return failed status with retry count."""
        client, user = authenticated_client

        # Create pending newsletter
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))

        # Mark as failed
        from src.web.services.newsletter_service import mark_newsletter_failed

        mark_newsletter_failed(db, newsletter.id)

        response = client.get(f"/newsletters/{newsletter.guid}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["retry_count"] == 1

    def test_get_newsletter_without_authentication(
        self, client: TestClient, db: Session
    ):
        """Should allow viewing newsletters without authentication."""
        # Create user and newsletter
        user = create_user(db, first_name="PublicUser")
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))

        # Request without cookie (no authentication)
        response = client.get(f"/newsletters/{newsletter.guid}")

        # Should still return newsletter data (newsletters are public via guid)
        assert response.status_code == 200
        data = response.json()
        assert data["guid"] == newsletter.guid


class TestNewsletterRetry:
    """Tests for POST /newsletters/{guid}/retry - retry failed newsletters."""

    def test_retry_requires_failed_status(self, authenticated_client, db: Session):
        """Should only allow retry of failed newsletters."""
        client, user = authenticated_client

        # Create pending newsletter
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))

        response = client.post(f"/newsletters/{newsletter.guid}/retry")

        # Should reject non-failed newsletters
        assert response.status_code == 400
        data = response.json()
        assert "failed" in data["detail"].lower()

    def test_retry_failed_newsletter(self, authenticated_client, db: Session):
        """Should reset failed newsletter to pending and queue for regeneration."""
        client, user = authenticated_client

        # Create failed newsletter
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))
        from src.web.services.newsletter_service import mark_newsletter_failed

        mark_newsletter_failed(db, newsletter.id)

        response = client.post(f"/newsletters/{newsletter.guid}/retry")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Verify newsletter was reset to pending
        from src.web.services.newsletter_service import get_newsletter_by_guid

        updated_newsletter = get_newsletter_by_guid(db, newsletter.guid)
        assert updated_newsletter.status == "pending"

    def test_retry_nonexistent_newsletter(self, authenticated_client):
        """Should return 404 for non-existent newsletter."""
        client, user = authenticated_client

        response = client.post("/newsletters/invalid-guid-12345/retry")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_retry_enforces_max_retries(self, authenticated_client, db: Session):
        """Should prevent retry if max retry count (3) exceeded."""
        client, user = authenticated_client

        # Create newsletter with 3 retries
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))
        from src.web.services.newsletter_service import mark_newsletter_failed

        # Fail it 3 times (max retries)
        mark_newsletter_failed(db, newsletter.id)
        mark_newsletter_failed(db, newsletter.id)
        mark_newsletter_failed(db, newsletter.id)

        response = client.post(f"/newsletters/{newsletter.guid}/retry")

        # Should reject due to max retries
        assert response.status_code == 400
        data = response.json()
        assert "max" in data["detail"].lower() or "limit" in data["detail"].lower()

    def test_retry_increments_retry_count(self, authenticated_client, db: Session):
        """Should preserve retry count when retrying."""
        client, user = authenticated_client

        # Create failed newsletter with 1 retry
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))
        from src.web.services.newsletter_service import mark_newsletter_failed

        mark_newsletter_failed(db, newsletter.id)

        response = client.post(f"/newsletters/{newsletter.guid}/retry")

        assert response.status_code == 200

        # Verify retry count is preserved
        from src.web.services.newsletter_service import get_newsletter_by_guid

        updated_newsletter = get_newsletter_by_guid(db, newsletter.guid)
        assert updated_newsletter.retry_count == 1
        assert updated_newsletter.status == "pending"

    def test_retry_without_authentication(self, client: TestClient, db: Session):
        """Should require authentication to retry newsletters."""
        # Create user and failed newsletter
        user = create_user(db, first_name="RetryUser")
        newsletter = create_pending_newsletter(db, user.id, date(2025, 10, 22))
        from src.web.services.newsletter_service import mark_newsletter_failed

        mark_newsletter_failed(db, newsletter.id)

        # Try to retry without authentication
        response = client.post(f"/newsletters/{newsletter.guid}/retry")

        # Should require authentication
        assert response.status_code in [303, 401]


class TestNewsletterIntegration:
    """Integration tests for full newsletter workflow."""

    @patch("src.web.services.llama_wrapper.NewsLlama")
    def test_full_generation_workflow(
        self, mock_llama_class, authenticated_client, db: Session
    ):
        """Test complete workflow: generate → process → retrieve."""
        client, user = authenticated_client

        # Mock NewsLlama
        mock_instance = mock_llama_class.return_value
        mock_instance.run = lambda: None

        # Create temporary output file
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "news-2025-10-22.html"
            output_file.write_text("<html>Generated Newsletter</html>")

            with patch(
                "src.web.services.llama_wrapper.get_output_file_path",
                return_value=str(output_file),
            ):
                with patch(
                    "src.web.services.llama_wrapper.Path.exists",
                    return_value=True,
                ):
                    # Step 1: Generate newsletter
                    response = client.post(
                        "/newsletters/generate", json={"date": "2025-10-22"}
                    )

                    assert response.status_code == 200
                    guid = response.json()["guid"]

                    # Step 2: Process generation (manually trigger)
                    from src.web.services.generation_service import (
                        process_newsletter_generation,
                    )
                    from src.web.services.newsletter_service import (
                        get_newsletter_by_guid,
                    )

                    newsletter = get_newsletter_by_guid(db, guid)

                    # Mock the actual file creation
                    with patch(
                        "src.web.services.llama_wrapper.Path.exists",
                        return_value=True,
                    ):
                        process_newsletter_generation(db, newsletter.id)

                    # Step 3: Retrieve newsletter
                    response = client.get(f"/newsletters/{guid}")

                    # Should return completed newsletter
                    assert response.status_code == 200
                    # Could be JSON status or HTML file depending on implementation
