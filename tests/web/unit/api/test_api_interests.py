"""
Unit tests for API v1 interest endpoints.

Tests JSON API responses for native client consumption:
- GET /api/v1/interests/predefined — grouped interests
- GET /api/v1/interests/predefined?flat=true — flat list
- GET /api/v1/interests/search?q=python — filtered results
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.web.app import app
from src.web.database import get_test_db, get_db


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


class TestPredefinedInterests:
    """Tests for GET /api/v1/interests/predefined."""

    def test_grouped_interests_returns_json(self, client: TestClient):
        """Should return grouped interests with key, name, emoji, interests."""
        response = client.get("/api/v1/interests/predefined")

        assert response.status_code == 200
        data = response.json()
        assert "groups" in data
        assert len(data["groups"]) > 0

    def test_grouped_interests_structure(self, client: TestClient):
        """Each group should have key, name, emoji, and interests list."""
        response = client.get("/api/v1/interests/predefined")
        data = response.json()

        group = data["groups"][0]
        assert "key" in group
        assert "name" in group
        assert "emoji" in group
        assert "interests" in group
        assert isinstance(group["interests"], list)
        assert len(group["interests"]) > 0

    def test_grouped_interests_contains_known_groups(self, client: TestClient):
        """Should contain expected category groups."""
        response = client.get("/api/v1/interests/predefined")
        data = response.json()

        group_keys = [g["key"] for g in data["groups"]]
        assert "tech" in group_keys
        assert "creative" in group_keys
        assert "gaming" in group_keys

    def test_flat_interests_returns_list(self, client: TestClient):
        """Should return flat sorted list when flat=true."""
        response = client.get("/api/v1/interests/predefined?flat=true")

        assert response.status_code == 200
        data = response.json()
        assert "interests" in data
        assert isinstance(data["interests"], list)
        assert len(data["interests"]) > 0
        # Should be alphabetically sorted
        assert data["interests"] == sorted(data["interests"])

    def test_flat_interests_contains_known_interests(self, client: TestClient):
        """Should contain specific known interests."""
        response = client.get("/api/v1/interests/predefined?flat=true")
        data = response.json()

        assert "AI & Machine Learning" in data["interests"]
        assert "Rust" in data["interests"]
        assert "Python" in data["interests"]


class TestSearchInterests:
    """Tests for GET /api/v1/interests/search."""

    def test_search_returns_matches(self, client: TestClient):
        """Should return matching interests for query."""
        response = client.get("/api/v1/interests/search?q=python")

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "count" in data
        assert data["count"] > 0
        assert any("Python" in r for r in data["results"])

    def test_search_case_insensitive(self, client: TestClient):
        """Should match case-insensitively."""
        response = client.get("/api/v1/interests/search?q=PYTHON")
        data = response.json()
        assert data["count"] > 0

    def test_search_no_results(self, client: TestClient):
        """Should return empty results for unmatched query."""
        response = client.get("/api/v1/interests/search?q=xyznonexistent")

        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["count"] == 0

    def test_search_empty_query_returns_all(self, client: TestClient):
        """Should return all interests when query is empty."""
        response = client.get("/api/v1/interests/search?q=")
        data = response.json()

        # Should return all predefined interests
        flat_response = client.get("/api/v1/interests/predefined?flat=true")
        flat_data = flat_response.json()

        assert data["count"] == len(flat_data["interests"])
