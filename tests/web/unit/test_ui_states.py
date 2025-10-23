"""
Unit tests for UI states (empty states, loading states).

Tests that appropriate empty state messages and loading states are displayed
in the web interface.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.web.app import app
from src.web.database import get_test_db
from src.web.services import user_service, interest_service


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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestCalendarEmptyState:
    """Tests for calendar empty state when user has no newsletters."""

    def test_calendar_shows_empty_state_no_newsletters(self, client, db: Session):
        """Should show empty state message when user has no newsletters."""
        # Create user with no newsletters
        user = user_service.create_user(db, first_name="EmptyUser")
        interest_service.add_user_interest(db, user.id, "AI", is_predefined=True)

        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar")

        assert response.status_code == 200
        # Should contain empty state message
        assert (
            "no newsletters" in response.text.lower()
            or "get started" in response.text.lower()
        )
        # Should suggest generating first newsletter
        assert "generate" in response.text.lower() or "create" in response.text.lower()

    def test_calendar_shows_empty_state_with_cta(self, client, db: Session):
        """Empty state should include call-to-action to generate newsletter."""
        user = user_service.create_user(db, first_name="EmptyUser")
        interest_service.add_user_interest(db, user.id, "AI", is_predefined=True)

        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar")

        assert response.status_code == 200
        # Should have data attribute for empty state
        assert (
            'data-empty="true"' in response.text
            or 'data-state="empty"' in response.text
            or "empty-state" in response.text.lower()
        )


class TestSettingsEmptyState:
    """Tests for settings empty state when user has no interests."""

    def test_settings_shows_empty_state_no_interests(self, client, db: Session):
        """Should show empty state message when user has no interests."""
        # Create user with no interests
        user = user_service.create_user(db, first_name="NoInterestsUser")

        client.cookies.set("user_id", str(user.id))
        response = client.get("/profile/settings")

        assert response.status_code == 200
        # Should contain empty state message about interests
        assert (
            "no interests" in response.text.lower()
            or "add interest" in response.text.lower()
            or "get started" in response.text.lower()
        )

    def test_settings_empty_state_has_add_prompt(self, client, db: Session):
        """Empty state should prompt user to add interests."""
        user = user_service.create_user(db, first_name="NoInterestsUser")

        client.cookies.set("user_id", str(user.id))
        response = client.get("/profile/settings")

        assert response.status_code == 200
        # Should encourage adding interests
        assert "add" in response.text.lower()
        # Should have empty state styling
        assert "empty" in response.text.lower()


class TestLoadingStates:
    """Tests for loading state attributes on forms and buttons."""

    def test_profile_create_form_has_loading_state(self, client):
        """Profile creation form should have loading state attributes."""
        response = client.get("/profile/new")

        assert response.status_code == 200
        # Form should have submit button with id for JavaScript loading state
        assert 'id="submit-btn"' in response.text
        # JavaScript should handle loading state (check for submit handler)
        assert "submitBtn.disabled = true" in response.text
        assert "submitBtn.textContent = 'Creating...'" in response.text

    def test_settings_form_has_loading_state(self, client, db: Session):
        """Settings form should have loading state attributes."""
        user = user_service.create_user(db, first_name="TestUser")
        interest_service.add_user_interest(db, user.id, "AI", is_predefined=True)

        client.cookies.set("user_id", str(user.id))
        response = client.get("/profile/settings")

        assert response.status_code == 200
        # Form should have submit button with id for JavaScript loading state
        assert 'id="submit-btn"' in response.text
        # JavaScript should handle loading state (check for submit handler)
        assert "submitBtn.disabled = true" in response.text
        assert "submitBtn.textContent = 'Saving...'" in response.text

    def test_interest_buttons_have_loading_state(self, client, db: Session):
        """Interest add/remove buttons should have loading state attributes."""
        user = user_service.create_user(db, first_name="TestUser")
        interest_service.add_user_interest(db, user.id, "AI", is_predefined=True)

        client.cookies.set("user_id", str(user.id))
        response = client.get("/profile/settings")

        assert response.status_code == 200
        # Interest buttons should have loading support
        assert (
            "data-loading" in response.text
            or "aria-busy" in response.text
            or "disabled" in response.text
        )


class TestFormValidationAttributes:
    """Tests for client-side validation attributes on forms."""

    def test_profile_create_has_validation_attrs(self, client):
        """Profile creation form should have validation attributes."""
        response = client.get("/profile/new")

        assert response.status_code == 200
        # First name input should have validation
        assert "required" in response.text
        assert "maxlength" in response.text or "pattern" in response.text
        # Should have aria labels for accessibility
        assert "aria-" in response.text

    def test_settings_form_has_validation_attrs(self, client, db: Session):
        """Settings form should have validation attributes."""
        user = user_service.create_user(db, first_name="TestUser")
        interest_service.add_user_interest(db, user.id, "AI", is_predefined=True)

        client.cookies.set("user_id", str(user.id))
        response = client.get("/profile/settings")

        assert response.status_code == 200
        # First name input should have validation
        assert "required" in response.text or "minlength" in response.text
        # Custom interest input should have maxlength
        assert "maxlength" in response.text

    def test_custom_interest_has_length_validation(self, client, db: Session):
        """Custom interest input should have length validation."""
        user = user_service.create_user(db, first_name="TestUser")

        client.cookies.set("user_id", str(user.id))
        response = client.get("/profile/settings")

        assert response.status_code == 200
        # Should have maxlength=100 for custom interests
        assert 'maxlength="100"' in response.text or 'max="100"' in response.text
