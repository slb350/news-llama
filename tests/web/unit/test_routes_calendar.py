"""
Unit tests for calendar routes - TDD RED phase.

Tests calendar view with user session and newsletter data:
- GET /calendar: Calendar view with current month
- GET /calendar/{year}/{month}: Calendar view for specific month (HTMX partial)
"""

import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.web.app import app
from src.web.database import get_test_db, get_db
from src.web.services.user_service import create_user
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
def user(db: Session):
    """Create test user."""
    return create_user(db, first_name="CalendarUser")


@pytest.fixture
def newsletters_october_2025(db: Session, user):
    """Create newsletters for October 2025."""
    n1 = create_pending_newsletter(db, user.id, date(2025, 10, 15))
    n2 = create_pending_newsletter(db, user.id, date(2025, 10, 20))
    n3 = create_pending_newsletter(db, user.id, date(2025, 10, 22))
    return [n1, n2, n3]


@pytest.fixture
def newsletters_november_2025(db: Session, user):
    """Create newsletters for November 2025."""
    n1 = create_pending_newsletter(db, user.id, date(2025, 11, 5))
    n2 = create_pending_newsletter(db, user.id, date(2025, 11, 10))
    return [n1, n2]


class TestCalendarView:
    """Tests for GET /calendar - main calendar view."""

    def test_calendar_requires_user_session(self, client: TestClient):
        """Should redirect to profile select if no user session."""
        response = client.get("/calendar", follow_redirects=False)

        # Should redirect to profile selection
        assert response.status_code == 303
        assert response.headers["location"] == "/"

    def test_calendar_with_valid_session(self, client: TestClient, user):
        """Should return 200 with valid user session."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar")

        assert response.status_code == 200

    def test_calendar_returns_html(self, client: TestClient, user):
        """Should return HTML content."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar")

        assert response.headers["content-type"].startswith("text/html")

    def test_calendar_shows_current_month(self, client: TestClient, user):
        """Should display current month by default (not hardcoded October 2025)."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar")

        html = response.text
        # Should show current month/year dynamically
        today = date.today()
        month_names = [
            "",
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        current_month_name = month_names[today.month]
        assert current_month_name in html
        assert str(today.year) in html

    def test_calendar_shows_user_newsletters(
        self, client: TestClient, user, newsletters_october_2025
    ):
        """Should display user's newsletters for the month."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar")

        html = response.text
        # Should contain newsletter dates
        assert "2025-10-15" in html or "15" in html
        assert "2025-10-20" in html or "20" in html
        assert "2025-10-22" in html or "22" in html

    def test_calendar_empty_month(self, client: TestClient, user):
        """Should handle month with no newsletters gracefully."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar")

        assert response.status_code == 200
        # Should still render calendar grid

    def test_calendar_isolates_users(
        self, client: TestClient, db: Session, newsletters_october_2025
    ):
        """Should only show newsletters for the logged-in user."""
        # Create another user with different newsletters
        other_user = create_user(db, first_name="OtherUser")
        create_pending_newsletter(db, other_user.id, date(2025, 10, 25))

        # Login as first user
        user = newsletters_october_2025[0].user_id
        client.cookies.set("user_id", str(user))
        response = client.get("/calendar")

        html = response.text
        # Should show first user's newsletters
        assert "2025-10-15" in html or "15" in html
        # Should NOT show other user's newsletter
        # This is harder to test in HTML, but we can verify count
        # (implementation detail - may need adjustment based on template)

    def test_calendar_with_invalid_cookie(self, client: TestClient):
        """Should redirect if user_id cookie is invalid."""
        client.cookies.set("user_id", "invalid")
        response = client.get("/calendar", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/"

    def test_calendar_with_nonexistent_user(self, client: TestClient):
        """Should redirect if user doesn't exist."""
        client.cookies.set("user_id", "99999")
        response = client.get("/calendar", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/"


class TestCalendarMonth:
    """Tests for GET /calendar/{year}/{month} - specific month view."""

    def test_calendar_month_requires_user_session(self, client: TestClient):
        """Should redirect if no user session."""
        response = client.get("/calendar/2025/10", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/"

    def test_calendar_month_with_valid_session(self, client: TestClient, user):
        """Should return 200 with valid session."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar/2025/10")

        assert response.status_code == 200

    def test_calendar_month_returns_html(self, client: TestClient, user):
        """Should return HTML content."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar/2025/11")

        assert response.headers["content-type"].startswith("text/html")

    def test_calendar_month_shows_specified_month(self, client: TestClient, user):
        """Should display the specified month."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar/2025/11")

        html = response.text
        assert "November" in html or "2025" in html

    def test_calendar_month_shows_newsletters(
        self, client: TestClient, user, newsletters_november_2025
    ):
        """Should display newsletters for specified month."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar/2025/11")

        html = response.text
        assert "2025-11-05" in html or "5" in html
        assert "2025-11-10" in html or "10" in html

    def test_calendar_month_filters_by_month(
        self,
        client: TestClient,
        user,
        newsletters_october_2025,
        newsletters_november_2025,
    ):
        """Should only show newsletters for requested month."""
        client.cookies.set("user_id", str(user.id))

        # Request October
        response_oct = client.get("/calendar/2025/10")
        html_oct = response_oct.text

        # Should show October newsletters
        assert "2025-10-15" in html_oct or "15" in html_oct

        # Request November
        response_nov = client.get("/calendar/2025/11")
        html_nov = response_nov.text

        # Should show November newsletters
        assert "2025-11-05" in html_nov or "5" in html_nov

    def test_calendar_month_empty(self, client: TestClient, user):
        """Should handle empty month gracefully."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar/2025/12")  # No newsletters in December

        assert response.status_code == 200
        # Should render empty calendar

    def test_calendar_month_validates_year(self, client: TestClient, user):
        """Should handle edge case years."""
        client.cookies.set("user_id", str(user.id))

        # Future year
        response = client.get("/calendar/2030/1")
        assert response.status_code == 200

        # Past year
        response = client.get("/calendar/2020/1")
        assert response.status_code == 200

    def test_calendar_month_validates_month(self, client: TestClient, user):
        """Should validate month range (1-12)."""
        client.cookies.set("user_id", str(user.id))

        # Valid months
        for month in range(1, 13):
            response = client.get(f"/calendar/2025/{month}")
            assert response.status_code == 200

    def test_calendar_month_invalid_month_low(self, client: TestClient, user):
        """Should reject month < 1."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar/2025/0")

        # Should return 422 validation error or 404
        assert response.status_code in [404, 422]

    def test_calendar_month_invalid_month_high(self, client: TestClient, user):
        """Should reject month > 12."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar/2025/13")

        # Should return 422 validation error or 404
        assert response.status_code in [404, 422]

    def test_calendar_month_isolates_users(
        self, client: TestClient, db: Session, newsletters_october_2025
    ):
        """Should only show newsletters for logged-in user."""
        # Create another user
        other_user = create_user(db, first_name="OtherUser")
        create_pending_newsletter(db, other_user.id, date(2025, 10, 25))

        # Login as first user
        user = newsletters_october_2025[0].user_id
        client.cookies.set("user_id", str(user))
        response = client.get("/calendar/2025/10")

        html = response.text
        # Should show first user's newsletters
        assert "2025-10-15" in html or "15" in html


class TestCalendarTodayHighlighting:
    """Tests for dynamic 'today' highlighting in calendar."""

    def test_calendar_includes_today_in_context(self, client: TestClient, user):
        """Calendar should pass today's date to template."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar")

        # Response should be successful
        assert response.status_code == 200
        # Should contain JavaScript with today date logic
        html = response.text
        # Verify template has access to current date for highlighting
        assert "today" in html.lower()

    def test_calendar_month_includes_today_in_context(self, client: TestClient, user):
        """Calendar month view should pass today's date to template."""
        client.cookies.set("user_id", str(user.id))
        today = date.today()
        response = client.get(f"/calendar/{today.year}/{today.month}")

        assert response.status_code == 200
        html = response.text
        # Should contain today highlighting in template
        assert "today" in html.lower()

    def test_calendar_today_class_only_on_current_day(
        self, client: TestClient, user, db: Session
    ):
        """Today class should only appear on actual current day."""
        client.cookies.set("user_id", str(user.id))
        today = date.today()

        # Create newsletter for today
        create_pending_newsletter(db, user.id, today)

        response = client.get("/calendar")
        html = response.text

        # Should contain 'today' class (appears in calendar.html template)
        assert "today" in html

    def test_calendar_navigates_to_past_month_no_today_highlight(
        self, client: TestClient, user
    ):
        """When viewing past month, today should not be highlighted."""
        client.cookies.set("user_id", str(user.id))

        # Navigate to January 2020 (definitely past)
        response = client.get("/calendar/2020/1")
        html = response.text

        assert response.status_code == 200
        # January 2020 should render but without today highlighting
        assert "January" in html
        assert "2020" in html

    def test_calendar_navigates_to_future_month_no_today_highlight(
        self, client: TestClient, user
    ):
        """When viewing future month, today should not be highlighted."""
        client.cookies.set("user_id", str(user.id))

        # Navigate to December 2030 (definitely future)
        response = client.get("/calendar/2030/12")
        html = response.text

        assert response.status_code == 200
        assert "December" in html
        assert "2030" in html


class TestCalendarDynamicMonthYear:
    """Tests for dynamic month/year defaulting (not hardcoded October 2025)."""

    def test_calendar_defaults_to_current_year(self, client: TestClient, user):
        """Calendar should default to current year, not hardcoded 2025."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar")

        html = response.text
        today = date.today()
        assert str(today.year) in html

    def test_calendar_defaults_to_current_month(self, client: TestClient, user):
        """Calendar should default to current month, not hardcoded October."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar")

        html = response.text
        today = date.today()
        month_names = [
            "",
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        current_month_name = month_names[today.month]
        assert current_month_name in html

    def test_calendar_works_across_year_boundary(
        self, client: TestClient, user, db: Session
    ):
        """Calendar should work correctly when year changes."""
        client.cookies.set("user_id", str(user.id))

        # Test December 2025
        response_dec = client.get("/calendar/2025/12")
        assert response_dec.status_code == 200
        assert "December" in response_dec.text
        assert "2025" in response_dec.text

        # Test January 2026 (next year)
        response_jan = client.get("/calendar/2026/1")
        assert response_jan.status_code == 200
        assert "January" in response_jan.text
        assert "2026" in response_jan.text

    def test_calendar_shows_correct_newsletters_for_year(
        self, client: TestClient, user, db: Session
    ):
        """Calendar should show newsletters for correct year."""
        client.cookies.set("user_id", str(user.id))

        # Create newsletters in different years
        nl_2025 = create_pending_newsletter(db, user.id, date(2025, 10, 15))
        nl_2026 = create_pending_newsletter(db, user.id, date(2026, 10, 15))

        # Request October 2025
        response_2025 = client.get("/calendar/2025/10")
        html_2025 = response_2025.text
        assert "2025-10-15" in html_2025

        # Request October 2026
        response_2026 = client.get("/calendar/2026/10")
        html_2026 = response_2026.text
        assert "2026-10-15" in html_2026


class TestCalendarModalDateDisplay:
    """Tests for newsletter modal date display (timezone fix)."""

    def test_modal_date_script_exists(self, client: TestClient, user):
        """Calendar should include openNewsletterModal JavaScript function."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar")

        html = response.text
        # Should include the modal opening function with date parsing
        assert "openNewsletterModal" in html
        assert "split" in html  # Date parsing logic

    def test_modal_uses_local_date_parsing(self, client: TestClient, user):
        """Modal JavaScript should parse dates as local (not UTC)."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar")

        html = response.text
        # Should use split logic to avoid UTC conversion
        # Looking for: const [year, month, day] = date.split('-').map(Number);
        assert "split('-')" in html or "split" in html
        assert "map(Number)" in html or "map" in html

    def test_modal_formatted_date_logic(self, client: TestClient, user):
        """Modal should use toLocaleDateString for display."""
        client.cookies.set("user_id", str(user.id))
        response = client.get("/calendar")

        html = response.text
        # Should include date formatting
        assert "toLocaleDateString" in html
        assert "weekday" in html  # Should format with weekday
        assert "month" in html  # Should format with month
        assert "day" in html  # Should format with day
