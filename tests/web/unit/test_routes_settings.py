"""
Unit tests for settings routes - TDD RED phase.

Tests profile settings management:
- GET /profile/settings: Display settings page with user info and interests
- POST /profile/settings: Update profile (name, interests)
"""

import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch

from src.web.app import app
from src.web.database import get_test_db, get_db
from src.web.services.user_service import create_user
from src.web.services.interest_service import add_user_interest
from src.web.services.newsletter_service import create_pending_newsletter


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
    user = create_user(db, first_name="SettingsUser")
    add_user_interest(db, user.id, "AI", is_predefined=True)
    add_user_interest(db, user.id, "rust", is_predefined=True)
    add_user_interest(db, user.id, "python", is_predefined=True)
    return user


class TestProfileSettingsGet:
    """Tests for GET /profile/settings - settings page."""

    def test_settings_requires_user_session(self, client: TestClient):
        """Should redirect to profile select if no user session."""
        response = client.get("/profile/settings", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/"

    def test_settings_with_valid_session(self, client: TestClient, user_with_interests):
        """Should return 200 with valid user session."""
        client.cookies.set("user_id", str(user_with_interests.id))
        response = client.get("/profile/settings")

        assert response.status_code == 200

    def test_settings_returns_html(self, client: TestClient, user_with_interests):
        """Should return HTML content."""
        client.cookies.set("user_id", str(user_with_interests.id))
        response = client.get("/profile/settings")

        assert response.headers["content-type"].startswith("text/html")

    def test_settings_shows_user_info(self, client: TestClient, user_with_interests):
        """Should display user's profile information."""
        client.cookies.set("user_id", str(user_with_interests.id))
        response = client.get("/profile/settings")

        html = response.text
        assert "SettingsUser" in html

    def test_settings_shows_user_interests(
        self, client: TestClient, user_with_interests
    ):
        """Should display user's selected interests."""
        client.cookies.set("user_id", str(user_with_interests.id))
        response = client.get("/profile/settings")

        html = response.text
        assert "AI" in html
        assert "rust" in html
        assert "python" in html

    def test_settings_shows_available_interests(
        self, client: TestClient, user_with_interests
    ):
        """Should display available predefined interests."""
        client.cookies.set("user_id", str(user_with_interests.id))
        response = client.get("/profile/settings")

        html = response.text
        # Check for some predefined interests not already selected
        assert "databases" in html or "machine learning" in html

    def test_settings_with_invalid_cookie(self, client: TestClient):
        """Should redirect if user_id cookie is invalid."""
        client.cookies.set("user_id", "invalid")
        response = client.get("/profile/settings", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/"

    def test_settings_with_nonexistent_user(self, client: TestClient):
        """Should redirect if user doesn't exist."""
        client.cookies.set("user_id", "99999")
        response = client.get("/profile/settings", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/"


class TestProfileSettingsPost:
    """Tests for POST /profile/settings - update profile."""

    def test_update_first_name(
        self, client: TestClient, user_with_interests, db: Session
    ):
        """Should update user's first name."""
        client.cookies.set("user_id", str(user_with_interests.id))

        response = client.post(
            "/profile/settings",
            json={"first_name": "UpdatedName"},
            follow_redirects=False,
        )

        # Should return success (200 or redirect)
        assert response.status_code in [200, 303]

        # Verify update
        from src.web.services.user_service import get_user

        user = get_user(db, user_with_interests.id)
        assert user.first_name == "UpdatedName"

    def test_update_trims_whitespace(
        self, client: TestClient, user_with_interests, db: Session
    ):
        """Should trim whitespace from first name."""
        client.cookies.set("user_id", str(user_with_interests.id))

        response = client.post(
            "/profile/settings",
            json={"first_name": "  Trimmed  "},
        )

        # Should return success (200 or redirect)
        assert response.status_code in [200, 303]

        from src.web.services.user_service import get_user

        user = get_user(db, user_with_interests.id)
        assert user.first_name == "Trimmed"

    def test_update_validates_empty_name(self, client: TestClient, user_with_interests):
        """Should reject empty first name."""
        client.cookies.set("user_id", str(user_with_interests.id))

        response = client.post(
            "/profile/settings",
            json={"first_name": ""},
        )

        # Should return validation error
        assert response.status_code == 422

    def test_update_validates_max_length(self, client: TestClient, user_with_interests):
        """Should enforce max length on first name (100 chars)."""
        client.cookies.set("user_id", str(user_with_interests.id))

        long_name = "A" * 101
        response = client.post(
            "/profile/settings",
            json={"first_name": long_name},
        )

        assert response.status_code == 422

    def test_add_interest(self, client: TestClient, user_with_interests, db: Session):
        """Should add new interest to user's profile."""
        client.cookies.set("user_id", str(user_with_interests.id))

        response = client.post(
            "/profile/settings/interests/add",
            json={"interest_name": "databases", "is_predefined": True},
        )

        assert response.status_code == 200

        # Verify interest was added
        from src.web.services.interest_service import get_user_interests

        interests = get_user_interests(db, user_with_interests.id)
        interest_names = [i.interest_name for i in interests]
        assert "databases" in interest_names

    def test_add_custom_interest(
        self, client: TestClient, user_with_interests, db: Session
    ):
        """Should add custom (non-predefined) interest."""
        client.cookies.set("user_id", str(user_with_interests.id))

        response = client.post(
            "/profile/settings/interests/add",
            json={"interest_name": "mycustominterest", "is_predefined": False},
        )

        assert response.status_code == 200

        from src.web.services.interest_service import get_user_interests

        interests = get_user_interests(db, user_with_interests.id)
        interest_map = {i.interest_name: i.is_predefined for i in interests}
        assert "mycustominterest" in interest_map
        assert interest_map["mycustominterest"] is False

    def test_add_duplicate_interest_fails(
        self, client: TestClient, user_with_interests
    ):
        """Should prevent adding duplicate interest."""
        client.cookies.set("user_id", str(user_with_interests.id))

        # Try to add "AI" which already exists
        response = client.post(
            "/profile/settings/interests/add",
            json={"interest_name": "AI", "is_predefined": True},
        )

        # Should return error (409 Conflict or 400 Bad Request)
        assert response.status_code in [400, 409, 422]

    def test_remove_interest(
        self, client: TestClient, user_with_interests, db: Session
    ):
        """Should remove interest from user's profile."""
        client.cookies.set("user_id", str(user_with_interests.id))

        response = client.post(
            "/profile/settings/interests/remove",
            json={"interest_name": "rust"},
        )

        assert response.status_code == 200

        # Verify interest was removed
        from src.web.services.interest_service import get_user_interests

        interests = get_user_interests(db, user_with_interests.id)
        interest_names = [i.interest_name for i in interests]
        assert "rust" not in interest_names
        # Other interests should still be there
        assert "AI" in interest_names
        assert "python" in interest_names

    def test_remove_nonexistent_interest(self, client: TestClient, user_with_interests):
        """Should return error when removing non-existent interest."""
        client.cookies.set("user_id", str(user_with_interests.id))

        response = client.post(
            "/profile/settings/interests/remove",
            json={"interest_name": "doesnotexist"},
        )

        # Should return error (404 Not Found or 400 Bad Request)
        assert response.status_code in [400, 404, 422]

    def test_settings_requires_user_session(self, client: TestClient):
        """Should require user session for updates."""
        response = client.post(
            "/profile/settings",
            json={"first_name": "NewName"},
            follow_redirects=False,
        )

        # Should redirect or return 401
        assert response.status_code in [303, 401]

    def test_add_interest_requires_session(self, client: TestClient):
        """Should require user session to add interests."""
        response = client.post(
            "/profile/settings/interests/add",
            json={"interest_name": "AI", "is_predefined": True},
        )

        # Should redirect or return 401
        assert response.status_code in [303, 401]

    def test_remove_interest_requires_session(self, client: TestClient):
        """Should require user session to remove interests."""
        response = client.post(
            "/profile/settings/interests/remove",
            json={"interest_name": "AI"},
        )

        # Should redirect or return 401
        assert response.status_code in [303, 401]


class TestInterestUpdateNewsletterRegeneration:
    """Tests for newsletter regeneration when interests are modified."""

    @patch("src.web.services.generation_service.queue_newsletter_generation")
    def test_add_interest_queues_newsletter_regeneration(
        self, mock_queue, client: TestClient, user_with_interests, db: Session
    ):
        """Should queue newsletter regeneration when interest is added."""
        client.cookies.set("user_id", str(user_with_interests.id))

        # Add an interest
        response = client.post(
            "/profile/settings/interests/add",
            json={"interest_name": "databases", "is_predefined": True},
        )

        assert response.status_code == 200

        # Verify newsletter regeneration was queued
        mock_queue.assert_called_once()
        call_args = mock_queue.call_args[0]
        assert call_args[0] == db  # db session
        assert call_args[1] == user_with_interests.id  # user_id
        assert call_args[2] == date.today()  # today's date

    @patch("src.web.services.generation_service.queue_newsletter_generation")
    def test_remove_interest_queues_newsletter_regeneration(
        self, mock_queue, client: TestClient, user_with_interests, db: Session
    ):
        """Should queue newsletter regeneration when interest is removed."""
        client.cookies.set("user_id", str(user_with_interests.id))

        # Remove an interest
        response = client.post(
            "/profile/settings/interests/remove",
            json={"interest_name": "rust"},
        )

        assert response.status_code == 200

        # Verify newsletter regeneration was queued
        mock_queue.assert_called_once()
        call_args = mock_queue.call_args[0]
        assert call_args[0] == db  # db session
        assert call_args[1] == user_with_interests.id  # user_id
        assert call_args[2] == date.today()  # today's date

    @patch("src.web.services.generation_service.queue_newsletter_generation")
    def test_interest_update_deletes_existing_pending_newsletter(
        self, mock_queue, client: TestClient, user_with_interests, db: Session
    ):
        """Should delete existing pending newsletter before queueing new one."""
        client.cookies.set("user_id", str(user_with_interests.id))

        # Create existing pending newsletter for today
        existing = create_pending_newsletter(db, user_with_interests.id, date.today())

        # Add an interest
        response = client.post(
            "/profile/settings/interests/add",
            json={"interest_name": "databases", "is_predefined": True},
        )

        assert response.status_code == 200

        # Verify old newsletter was deleted
        from src.web.services.newsletter_service import get_newsletter_by_guid

        with pytest.raises(Exception):  # NewsletterNotFoundError
            get_newsletter_by_guid(db, existing.guid)

        # Verify new newsletter was queued
        mock_queue.assert_called_once()

    def test_interest_update_returns_regeneration_message(
        self, client: TestClient, user_with_interests
    ):
        """Should return message about newsletter regeneration."""
        client.cookies.set("user_id", str(user_with_interests.id))

        response = client.post(
            "/profile/settings/interests/add",
            json={"interest_name": "databases", "is_predefined": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        # Should indicate newsletter is being regenerated
        assert "newsletter_regenerated" in data or "regenerating" in str(data).lower()
