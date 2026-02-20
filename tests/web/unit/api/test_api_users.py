"""
Unit tests for API v1 user endpoints.

Tests JSON API responses for native client consumption:
- GET /api/v1/users — list users with interests and newsletter counts
- GET /api/v1/users/{id} — single user with full interest details
- GET /api/v1/users/{id}/newsletters — newsletters for a given month
"""

import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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
    """Create a test user with interests."""
    user = create_user(db, first_name="Alice")
    add_user_interest(db, user.id, "AI & Machine Learning", is_predefined=True)
    add_user_interest(db, user.id, "Rust", is_predefined=True)
    return user


@pytest.fixture
def multiple_users(db: Session):
    """Create multiple test users."""
    user1 = create_user(db, first_name="Alice")
    user2 = create_user(db, first_name="Bob")
    add_user_interest(db, user1.id, "AI & Machine Learning", is_predefined=True)
    add_user_interest(db, user2.id, "Python", is_predefined=True)
    return [user1, user2]


class TestListUsers:
    """Tests for GET /api/v1/users."""

    def test_list_users_returns_json(self, client: TestClient, multiple_users):
        """Should return JSON with users array and count."""
        response = client.get("/api/v1/users")

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "count" in data
        assert data["count"] == 2
        assert len(data["users"]) == 2

    def test_list_users_includes_interests(self, client: TestClient, multiple_users):
        """Each user should include their interests."""
        response = client.get("/api/v1/users")
        data = response.json()

        alice = next(u for u in data["users"] if u["first_name"] == "Alice")
        assert len(alice["interests"]) == 1
        assert alice["interests"][0]["interest_name"] == "AI & Machine Learning"

    def test_list_users_includes_newsletter_count(
        self, client: TestClient, db: Session, multiple_users
    ):
        """Each user should include newsletter_count."""
        # Create a newsletter for Alice
        create_pending_newsletter(db, multiple_users[0].id, date(2025, 10, 15))

        response = client.get("/api/v1/users")
        data = response.json()

        alice = next(u for u in data["users"] if u["first_name"] == "Alice")
        assert alice["newsletter_count"] == 1

        bob = next(u for u in data["users"] if u["first_name"] == "Bob")
        assert bob["newsletter_count"] == 0

    def test_list_users_empty(self, client: TestClient):
        """Should return empty list when no users exist."""
        response = client.get("/api/v1/users")

        assert response.status_code == 200
        data = response.json()
        assert data["users"] == []
        assert data["count"] == 0

    def test_list_users_has_user_fields(self, client: TestClient, multiple_users):
        """Each user should have all expected fields."""
        response = client.get("/api/v1/users")
        data = response.json()
        user = data["users"][0]

        assert "id" in user
        assert "first_name" in user
        assert "avatar_path" in user
        assert "created_at" in user
        assert "interests" in user
        assert "newsletter_count" in user


class TestGetUser:
    """Tests for GET /api/v1/users/{user_id}."""

    def test_get_user_returns_json(self, client: TestClient, user_with_interests):
        """Should return single user with full details."""
        response = client.get(f"/api/v1/users/{user_with_interests.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_with_interests.id
        assert data["first_name"] == "Alice"

    def test_get_user_includes_full_interests(
        self, client: TestClient, user_with_interests
    ):
        """Should include full interest details with user_id and added_at."""
        response = client.get(f"/api/v1/users/{user_with_interests.id}")
        data = response.json()

        assert len(data["interests"]) == 2
        interest = data["interests"][0]
        assert "id" in interest
        assert "user_id" in interest
        assert "interest_name" in interest
        assert "is_predefined" in interest
        assert "added_at" in interest

    def test_get_user_includes_newsletter_count(
        self, client: TestClient, db: Session, user_with_interests
    ):
        """Should include newsletter count."""
        create_pending_newsletter(db, user_with_interests.id, date(2025, 10, 15))

        response = client.get(f"/api/v1/users/{user_with_interests.id}")
        data = response.json()
        assert data["newsletter_count"] == 1

    def test_get_user_not_found(self, client: TestClient):
        """Should return 404 for nonexistent user."""
        response = client.get("/api/v1/users/9999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestUserNewsletters:
    """Tests for GET /api/v1/users/{user_id}/newsletters."""

    def test_get_newsletters_for_month(
        self, client: TestClient, db: Session, user_with_interests
    ):
        """Should return newsletters for the specified month."""
        uid = user_with_interests.id
        create_pending_newsletter(db, uid, date(2025, 10, 15))
        create_pending_newsletter(db, uid, date(2025, 10, 20))
        create_pending_newsletter(db, uid, date(2025, 11, 5))

        response = client.get(f"/api/v1/users/{uid}/newsletters?year=2025&month=10")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["year"] == 2025
        assert data["month"] == 10
        assert len(data["newsletters"]) == 2

    def test_get_newsletters_defaults_to_current_month(
        self, client: TestClient, db: Session, user_with_interests
    ):
        """Should default to current year/month when not specified."""
        uid = user_with_interests.id
        today = date.today()
        create_pending_newsletter(db, uid, today)

        response = client.get(f"/api/v1/users/{uid}/newsletters")

        assert response.status_code == 200
        data = response.json()
        assert data["year"] == today.year
        assert data["month"] == today.month
        assert data["count"] == 1

    def test_get_newsletters_empty_month(self, client: TestClient, user_with_interests):
        """Should return empty list for month with no newsletters."""
        response = client.get(
            f"/api/v1/users/{user_with_interests.id}/newsletters?year=2020&month=1"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["newsletters"] == []
        assert data["count"] == 0

    def test_get_newsletters_has_all_fields(
        self, client: TestClient, db: Session, user_with_interests
    ):
        """Each newsletter should have all expected fields."""
        uid = user_with_interests.id
        create_pending_newsletter(db, uid, date(2025, 10, 15))

        response = client.get(f"/api/v1/users/{uid}/newsletters?year=2025&month=10")
        data = response.json()
        newsletter = data["newsletters"][0]

        assert "id" in newsletter
        assert "user_id" in newsletter
        assert "date" in newsletter
        assert "guid" in newsletter
        assert "file_path" in newsletter
        assert "status" in newsletter
        assert "generated_at" in newsletter
        assert "retry_count" in newsletter

    def test_get_newsletters_user_not_found(self, client: TestClient):
        """Should return 404 for nonexistent user."""
        response = client.get("/api/v1/users/9999/newsletters")

        assert response.status_code == 404
