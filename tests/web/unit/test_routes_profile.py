"""
Unit tests for profile routes - TDD RED phase.

Tests profile selection, creation, and user session management:
- GET /: Profile selection page with existing users
- GET /profile/new: Profile creation page with predefined interests
- POST /profile/create: Create profile and set session cookie
"""

import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from src.web.app import app
from src.web.database import get_test_db, get_db
from src.web.services.user_service import create_user


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
def existing_users(db: Session):
    """Create test users."""
    user1 = create_user(db, first_name="Alice")
    user2 = create_user(db, first_name="Bob")
    user3 = create_user(db, first_name="Charlie")
    return [user1, user2, user3]


class TestProfileSelect:
    """Tests for GET / - profile selection page."""

    def test_profile_select_returns_200(self, client: TestClient):
        """Should return 200 OK."""
        response = client.get("/")

        assert response.status_code == 200

    def test_profile_select_returns_html(self, client: TestClient):
        """Should return HTML content."""
        response = client.get("/")

        assert response.headers["content-type"].startswith("text/html")

    def test_profile_select_shows_users(self, client: TestClient, existing_users):
        """Should display all existing users in HTML."""
        response = client.get("/")

        html = response.text
        assert "Alice" in html
        assert "Bob" in html
        assert "Charlie" in html

    def test_profile_select_empty_users(self, client: TestClient):
        """Should handle empty user list gracefully."""
        response = client.get("/")

        assert response.status_code == 200
        # Should show "Create new profile" option even with no users

    def test_profile_select_has_create_link(self, client: TestClient):
        """Should include link to create new profile."""
        response = client.get("/")

        html = response.text
        assert "/profile/new" in html


class TestProfileCreate:
    """Tests for GET /profile/new - profile creation page."""

    def test_profile_create_returns_200(self, client: TestClient):
        """Should return 200 OK."""
        response = client.get("/profile/new")

        assert response.status_code == 200

    def test_profile_create_returns_html(self, client: TestClient):
        """Should return HTML content."""
        response = client.get("/profile/new")

        assert response.headers["content-type"].startswith("text/html")

    def test_profile_create_shows_predefined_interests(self, client: TestClient):
        """Should display predefined interests for selection."""
        response = client.get("/profile/new")

        html = response.text
        # Check for some known predefined interests
        assert "AI" in html
        assert "python" in html
        assert "rust" in html
        assert "machine learning" in html

    def test_profile_create_has_form(self, client: TestClient):
        """Should include profile creation form."""
        response = client.get("/profile/new")

        html = response.text
        assert "form" in html.lower()
        assert "first_name" in html.lower() or "name" in html.lower()


class TestProfileCreatePost:
    """Tests for POST /profile/create - create new profile."""

    def test_create_profile_with_interests(self, client: TestClient, db: Session):
        """Should create user, add interests, and redirect."""
        response = client.post(
            "/profile/create",
            json={"first_name": "Diana", "interests": ["AI", "rust", "python"]},
            follow_redirects=False,
        )

        # Should return JSON response with redirect URL
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["redirect_url"].startswith("/calendar")
        assert "user_id" in data

        # Should set user_id cookie
        assert "user_id" in response.cookies

        # Verify user was created
        user_id = data["user_id"]
        from src.web.services.user_service import get_user

        user = get_user(db, user_id)
        assert user.first_name == "Diana"

        # Verify interests were added
        from src.web.services.interest_service import get_user_interests

        interests = get_user_interests(db, user_id)
        assert len(interests) == 3
        interest_names = [i.interest_name for i in interests]
        assert "AI" in interest_names
        assert "rust" in interest_names
        assert "python" in interest_names

    def test_create_profile_without_interests(self, client: TestClient, db: Session):
        """Should create user with no interests."""
        response = client.post(
            "/profile/create",
            json={"first_name": "Eve", "interests": []},
            follow_redirects=False,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "user_id" in response.cookies

        # Verify user was created
        user_id = data["user_id"]
        from src.web.services.user_service import get_user

        user = get_user(db, user_id)
        assert user.first_name == "Eve"

        # Verify no interests
        from src.web.services.interest_service import get_user_interests

        interests = get_user_interests(db, user_id)
        assert len(interests) == 0

    def test_create_profile_validates_first_name(self, client: TestClient):
        """Should reject empty or whitespace-only first name."""
        response = client.post(
            "/profile/create", json={"first_name": "", "interests": []}
        )

        assert response.status_code == 422  # Validation error

    def test_create_profile_trims_whitespace(self, client: TestClient, db: Session):
        """Should trim whitespace from first name."""
        response = client.post(
            "/profile/create",
            json={"first_name": "  Frank  ", "interests": []},
            follow_redirects=False,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        user_id = data["user_id"]
        from src.web.services.user_service import get_user

        user = get_user(db, user_id)
        assert user.first_name == "Frank"  # Trimmed

    def test_create_profile_marks_predefined_interests(
        self, client: TestClient, db: Session
    ):
        """Should mark interests as predefined if from standard list."""
        response = client.post(
            "/profile/create",
            json={"first_name": "Grace", "interests": ["AI", "databases"]},
            follow_redirects=False,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        user_id = data["user_id"]
        from src.web.services.interest_service import get_user_interests

        interests = get_user_interests(db, user_id)
        for interest in interests:
            # Both AI and databases are predefined
            assert interest.is_predefined is True

    def test_create_profile_handles_custom_interests(
        self, client: TestClient, db: Session
    ):
        """Should handle custom (non-predefined) interests."""
        response = client.post(
            "/profile/create",
            json={
                "first_name": "Henry",
                "interests": ["AI", "mycustomtopic"],  # AI predefined, other custom
            },
            follow_redirects=False,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        user_id = data["user_id"]
        from src.web.services.interest_service import get_user_interests

        interests = get_user_interests(db, user_id)
        interest_map = {i.interest_name: i.is_predefined for i in interests}

        assert interest_map["AI"] is True  # Predefined
        assert interest_map["mycustomtopic"] is False  # Custom

    def test_create_profile_requires_first_name(self, client: TestClient):
        """Should require first_name field."""
        response = client.post("/profile/create", json={"interests": ["AI"]})

        assert response.status_code == 422  # Validation error

    def test_create_profile_max_length_first_name(self, client: TestClient):
        """Should enforce max length on first name (100 chars)."""
        long_name = "A" * 101
        response = client.post(
            "/profile/create", json={"first_name": long_name, "interests": []}
        )

        assert response.status_code == 422  # Validation error

    def test_create_profile_accepts_max_length(self, client: TestClient, db: Session):
        """Should accept first name at max length (100 chars)."""
        name_100_chars = "A" * 100
        response = client.post(
            "/profile/create",
            json={"first_name": name_100_chars, "interests": []},
            follow_redirects=False,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        user_id = data["user_id"]
        from src.web.services.user_service import get_user

        user = get_user(db, user_id)
        assert len(user.first_name) == 100

    def test_create_profile_duplicate_interests_deduped(
        self, client: TestClient, db: Session
    ):
        """Should deduplicate interests in request."""
        response = client.post(
            "/profile/create",
            json={
                "first_name": "Ivy",
                "interests": ["AI", "python", "AI"],  # Duplicate AI
            },
            follow_redirects=False,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        user_id = data["user_id"]
        from src.web.services.interest_service import get_user_interests

        interests = get_user_interests(db, user_id)
        # Should only have 2 interests (AI deduplicated)
        assert len(interests) == 2
        interest_names = [i.interest_name for i in interests]
        assert interest_names.count("AI") == 1

    def test_create_profile_cookie_is_valid_int(self, client: TestClient):
        """Should set user_id cookie as valid integer."""
        response = client.post(
            "/profile/create",
            json={"first_name": "Jack", "interests": []},
            follow_redirects=False,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        user_id_str = response.cookies["user_id"]

        # Should be convertible to int
        user_id = int(user_id_str)
        assert user_id > 0

    @patch("src.web.services.generation_service.queue_newsletter_generation")
    def test_create_profile_triggers_newsletter_generation(
        self, mock_queue, client: TestClient, db: Session
    ):
        """Should trigger newsletter generation after profile creation."""
        # Mock newsletter creation to return a realistic newsletter object
        mock_newsletter = MagicMock()
        mock_newsletter.id = 1
        mock_newsletter.user_id = 1
        mock_newsletter.date = date.today().isoformat()
        mock_newsletter.guid = "test-guid-12345"
        mock_newsletter.status = "pending"
        mock_newsletter.file_path = None
        mock_newsletter.generated_at = None
        mock_newsletter.retry_count = 0
        mock_queue.return_value = mock_newsletter

        response = client.post(
            "/profile/create",
            json={"first_name": "NewsUser", "interests": ["AI", "rust"]},
            follow_redirects=False,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        user_id = data["user_id"]

        # Verify generation was queued with correct arguments
        mock_queue.assert_called_once()
        call_args = mock_queue.call_args[0]  # Positional args
        assert call_args[0] == db  # db session
        assert call_args[1] == user_id  # user_id argument
        assert call_args[2] == date.today()  # newsletter_date argument


class TestProfileDelete:
    """Tests for DELETE /profile/{user_id} - delete profile."""

    def test_delete_profile_success(self, client: TestClient, db: Session):
        """Should delete user and return success."""
        # Create a user first
        from src.web.services.user_service import create_user

        user = create_user(db, first_name="ToDelete")
        user_id = user.id

        # Delete the user
        response = client.delete(f"/profile/{user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "deleted successfully" in data["message"].lower()

        # Verify user was actually deleted
        from src.web.services.user_service import get_user, UserNotFoundError

        with pytest.raises(UserNotFoundError):
            get_user(db, user_id)

    def test_delete_profile_not_found(self, client: TestClient):
        """Should return 404 for non-existent user."""
        response = client.delete("/profile/99999")

        assert response.status_code == 404
        data = response.json()
        assert (
            "couldn't find" in data["detail"].lower()
            or "not found" in data["detail"].lower()
        )

    def test_delete_profile_cascades_to_interests(
        self, client: TestClient, db: Session
    ):
        """Should cascade delete to user_interests table."""
        from src.web.services.user_service import create_user
        from src.web.services.interest_service import (
            add_user_interest,
            get_user_interests,
        )

        # Create user with interests
        user = create_user(db, first_name="CascadeTest")
        user_id = user.id
        add_user_interest(db, user_id, "AI", is_predefined=True)
        add_user_interest(db, user_id, "rust", is_predefined=True)

        # Verify interests exist
        interests_before = get_user_interests(db, user_id)
        assert len(interests_before) == 2

        # Delete user
        response = client.delete(f"/profile/{user_id}")
        assert response.status_code == 200

        # Verify interests were cascaded (should return empty list, not raise)
        from src.web.services.user_service import get_user, UserNotFoundError

        # User should not exist
        with pytest.raises(UserNotFoundError):
            get_user(db, user_id)

        # Try to fetch interests for non-existent user - should handle gracefully
        # (service may raise UserNotFoundError or return empty list)
        try:
            interests_after = get_user_interests(db, user_id)
            assert len(interests_after) == 0
        except UserNotFoundError:
            # This is also acceptable behavior
            pass

    def test_delete_profile_cascades_to_newsletters(
        self, client: TestClient, db: Session
    ):
        """Should cascade delete to newsletters table."""
        from src.web.services.user_service import create_user
        from src.web.services.newsletter_service import get_newsletters_by_month
        from src.web.models import Newsletter
        from datetime import datetime

        # Create user with newsletters
        user = create_user(db, first_name="NewsletterCascade")
        user_id = user.id

        # Create newsletters directly (bypassing service)
        newsletter1 = Newsletter(
            user_id=user_id,
            date=date.today().isoformat(),
            guid="test-guid-1",
            file_path="/fake/path/1.html",
            status="completed",
            generated_at=datetime.now().isoformat(),
        )
        newsletter2 = Newsletter(
            user_id=user_id,
            date=date.today().isoformat(),
            guid="test-guid-2",
            file_path="/fake/path/2.html",
            status="pending",
        )
        db.add(newsletter1)
        db.add(newsletter2)
        db.commit()

        # Verify newsletters exist
        today = date.today()
        newsletters_before = get_newsletters_by_month(
            db, user_id, today.year, today.month
        )
        assert len(newsletters_before) == 2

        # Delete user
        response = client.delete(f"/profile/{user_id}")
        assert response.status_code == 200

        # Verify newsletters were cascaded
        from src.web.services.user_service import get_user, UserNotFoundError

        # User should not exist
        with pytest.raises(UserNotFoundError):
            get_user(db, user_id)

        # Try to fetch newsletters for non-existent user
        try:
            newsletters_after = get_newsletters_by_month(
                db, user_id, today.year, today.month
            )
            assert len(newsletters_after) == 0
        except UserNotFoundError:
            # This is also acceptable behavior
            pass

    def test_delete_profile_invalid_user_id(self, client: TestClient):
        """Should return 422 for invalid user_id format."""
        response = client.delete("/profile/not-a-number")

        # FastAPI path parameter validation should fail
        assert response.status_code == 422
