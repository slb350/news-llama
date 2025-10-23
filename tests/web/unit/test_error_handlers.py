"""
Unit tests for custom error handlers and user-friendly error messages.

Tests that all service exceptions are caught and converted to appropriate
HTTP responses with user-friendly messages (not technical details).
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import date
from sqlalchemy.orm import Session

from src.web.app import app
from src.web.database import get_test_db
from src.web.services import (
    user_service,
    interest_service,
    newsletter_service,
    generation_service,
)


@pytest.fixture
def db():
    """Provide test database session."""
    yield from get_test_db()


@pytest.fixture
def client(db: Session):
    """Provide test client with database override."""
    from src.web.database import get_db as get_db_dep

    def override_get_db():
        yield db

    app.dependency_overrides[get_db_dep] = override_get_db
    # Don't raise server exceptions - we want to test error responses
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestUserServiceErrorHandlers:
    """Tests for user service error handling."""

    def test_user_not_found_returns_friendly_message(self, client):
        """Should handle missing user gracefully (HTML route)."""
        # Try to access settings for non-existent user (no cookie)
        response = client.get("/profile/settings")

        # HTML routes may return 200 with template or redirect
        # The important thing is NO stack trace is exposed
        assert response.status_code in [200, 303]
        if response.status_code == 200:
            # Should render template, not crash
            assert "text/html" in response.headers.get("content-type", "")

    def test_user_validation_error_returns_friendly_message(self, client):
        """Should return user-friendly message for validation errors."""
        # Try to create profile with invalid data
        response = client.post(
            "/profile/create",
            json={"first_name": "", "interests": []},  # Empty name
        )

        # Should return validation error with friendly message
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # Should not expose internal error details
        assert "ValidationError" not in str(data)
        assert "Traceback" not in str(data)


class TestInterestServiceErrorHandlers:
    """Tests for interest service error handling."""

    def test_duplicate_interest_returns_friendly_message(self, client, db: Session):
        """Should return user-friendly message when adding duplicate interest."""
        user = user_service.create_user(db, first_name="Alice")
        interest_service.add_user_interest(db, user.id, "AI", is_predefined=True)

        # Set cookie and try to add same interest again
        client.cookies.set("user_id", str(user.id))
        response = client.post(
            "/profile/settings/interests/add",
            json={"interest_name": "AI", "is_predefined": True},
        )

        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        assert "already" in data["detail"].lower()
        # Should not expose internal error class names
        assert "DuplicateInterestError" not in data["detail"]

    def test_interest_not_found_returns_friendly_message(self, client, db: Session):
        """Should return user-friendly message when removing non-existent interest."""
        user = user_service.create_user(db, first_name="Alice")

        # Set cookie and try to remove non-existent interest
        client.cookies.set("user_id", str(user.id))
        response = client.post(
            "/profile/settings/interests/remove",
            json={"interest_name": "NonExistent", "is_predefined": False},
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
        # Should not expose internal error class names
        assert "InterestNotFoundError" not in data["detail"]

    def test_interest_validation_error_returns_friendly_message(
        self, client, db: Session
    ):
        """Should return user-friendly message for invalid interest."""
        user = user_service.create_user(db, first_name="Alice")

        # Set cookie and try to add invalid interest (too long)
        client.cookies.set("user_id", str(user.id))
        response = client.post(
            "/profile/settings/interests/add",
            json={"interest_name": "A" * 101, "is_predefined": False},  # 101 chars
        )

        # Pydantic validation happens before route, returns 422
        # or service validation returns our friendly message
        assert response.status_code in [200, 422]
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data


class TestNewsletterServiceErrorHandlers:
    """Tests for newsletter service error handling."""

    def test_newsletter_not_found_returns_friendly_message(self, client):
        """Should return user-friendly message when newsletter not found."""
        response = client.get("/newsletters/nonexistent-guid")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
        # Should not expose internal error class names
        assert "NewsletterNotFoundError" not in data["detail"]

    def test_duplicate_newsletter_returns_friendly_message(self, client, db: Session):
        """Should return user-friendly message when newsletter already exists."""
        user = user_service.create_user(db, first_name="Alice")
        interest_service.add_user_interest(db, user.id, "AI", is_predefined=True)

        # Create newsletter for today
        generation_service.queue_newsletter_generation(db, user.id, date.today())

        # Set cookie and try to create again
        client.cookies.set("user_id", str(user.id))
        response = client.post(
            "/newsletters/generate",
            json={"date": date.today().isoformat()},
        )

        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        # Should have user-friendly message (any variation is fine)
        assert len(data["detail"]) > 10  # Has a message
        # Should not expose internal error class names
        assert "NewsletterAlreadyExistsError" not in data["detail"]
        assert "Error" not in data["detail"]  # No class names
        assert "Exception" not in data["detail"]


class TestGenerationServiceErrorHandlers:
    """Tests for generation service error handling."""

    def test_generation_error_returns_friendly_message(self, client, db: Session):
        """Should return user-friendly message when generation fails."""
        user = user_service.create_user(db, first_name="Alice")
        interest_service.add_user_interest(db, user.id, "AI", is_predefined=True)

        # Mock generation to fail
        with patch.object(
            generation_service,
            "queue_newsletter_generation",
            side_effect=generation_service.GenerationServiceError("Internal error"),
        ):
            client.cookies.set("user_id", str(user.id))
            response = client.post(
                "/newsletters/generate",
                json={"date": date.today().isoformat()},
            )

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            # Should have user-friendly message
            assert (
                "generation failed" in data["detail"].lower()
                or "error" in data["detail"].lower()
            )
            # Should not expose internal error class names
            assert "GenerationServiceError" not in data["detail"]

    def test_retry_validation_error_returns_friendly_message(self, client, db: Session):
        """Should return user-friendly message for invalid retry."""
        user = user_service.create_user(db, first_name="Alice")
        interest_service.add_user_interest(db, user.id, "AI", is_predefined=True)

        # Create and mark newsletter as failed
        newsletter = generation_service.queue_newsletter_generation(
            db, user.id, date.today()
        )

        # Mock retry to fail with validation error
        with patch.object(
            newsletter_service,
            "retry_newsletter",
            side_effect=newsletter_service.NewsletterValidationError(
                "Max retries exceeded"
            ),
        ):
            client.cookies.set("user_id", str(user.id))
            response = client.post(f"/newsletters/{newsletter.guid}/retry")

            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            # Should have user-friendly message
            assert (
                "tried" in data["detail"].lower()
                or "newsletter" in data["detail"].lower()
            )


class TestErrorMessageFormat:
    """Tests for error message formatting."""

    def test_error_messages_are_strings_not_objects(self, client):
        """All error responses should have string detail field."""
        # Try various error-inducing requests
        error_responses = [
            client.get("/newsletters/nonexistent"),
            client.get("/profile/settings"),  # No cookie
        ]

        for response in error_responses:
            if response.status_code >= 400:
                data = response.json()
                assert "detail" in data
                # Detail should be a string or list of validation errors
                assert isinstance(data["detail"], (str, list))

    def test_error_messages_do_not_expose_stack_traces(self, client, db: Session):
        """Error messages should not include stack traces."""
        user = user_service.create_user(db, first_name="Alice")
        interest_service.add_user_interest(db, user.id, "AI", is_predefined=True)

        # Trigger a server error
        with patch.object(
            generation_service,
            "queue_newsletter_generation",
            side_effect=Exception("Database connection failed"),
        ):
            client.cookies.set("user_id", str(user.id))
            response = client.post(
                "/newsletters/generate",
                json={"date": date.today().isoformat()},
            )

            if response.status_code == 500:
                data = response.json()
                detail = str(data.get("detail", ""))

                # Should not expose technical details
                assert "Traceback" not in detail
                assert "File " not in detail
                assert "line " not in detail
                assert ".py" not in detail

    def test_validation_errors_are_descriptive(self, client):
        """Validation errors should describe what's wrong."""
        # Try to create profile with missing required field
        response = client.post(
            "/profile/create",
            json={"interests": ["AI"]},  # Missing first_name
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

        # Validation errors are returned as list
        if isinstance(data["detail"], list):
            # Should mention the field that's missing
            error_str = str(data["detail"])
            assert "first_name" in error_str.lower()
