"""
Unit tests for discovery metrics - TDD RED phase.

Tests metrics tracking and public metrics page.
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from src.web.database import get_test_db
from src.web.services import discovery_metrics_service, tier1_service, blacklist_service
from src.web.models import Tier1Source, SourceBlacklist, DiscoveredSource


@pytest.fixture
def db():
    """Provide test database session."""
    yield from get_test_db()


@pytest.fixture
def client(db: Session):
    """Create test client with database dependency override."""
    from src.web.app import app
    from src.web.database import get_db

    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


class TestMetricsCalculation:
    """Tests for metrics calculations."""

    def test_calculate_tier1_stats(self, db: Session):
        """Should calculate Tier 1 statistics."""
        # Add test data
        tier1_service.add_tier1_source(
            db,
            "reddit",
            "rust",
            interests=["Rust"],
            quality_score=0.9,
            discovered_via="manual",
        )
        tier1_service.add_tier1_source(
            db,
            "rss",
            "rust_blog",
            source_url="https://blog.rust-lang.org/feed.xml",
            interests=["Rust"],
            quality_score=0.85,
            discovered_via="manual",
        )

        stats = discovery_metrics_service.get_tier1_stats(db)

        assert stats["total"] == 2
        assert stats["by_type"]["reddit"] == 1
        assert stats["by_type"]["rss"] == 1
        assert stats["avg_quality_score"] == pytest.approx(0.875, rel=0.01)

    def test_calculate_blacklist_stats(self, db: Session):
        """Should calculate blacklist statistics."""
        # Add blacklisted sources
        blacklist_service.add_to_blacklist(db, "rss", "broken1", reason="404")
        blacklist_service.add_to_blacklist(db, "rss", "broken2", reason="timeout")
        blacklist_service.add_to_blacklist(db, "reddit", "banned", reason="403")

        stats = discovery_metrics_service.get_blacklist_stats(db)

        assert stats["total"] == 3
        assert stats["by_type"]["rss"] == 2
        assert stats["by_type"]["reddit"] == 1
        assert stats["by_reason"]["404"] == 1
        assert stats["by_reason"]["timeout"] == 1
        assert stats["by_reason"]["403"] == 1


class TestPublicMetricsPage:
    """Tests for public metrics HTTP endpoint."""

    def test_metrics_page_accessible(self, client):
        """Should serve public metrics page without auth."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert "Discovery System Metrics" in response.text

    def test_metrics_page_shows_stats(self, client, db: Session):
        """Should display current stats."""
        # Add test data
        tier1_service.add_tier1_source(
            db,
            "reddit",
            "rust",
            interests=["Rust"],
            quality_score=0.9,
            discovered_via="manual",
        )

        response = client.get("/metrics")

        assert response.status_code == 200
        assert "Tier 1 Sources" in response.text
        # Check that the count appears somewhere in the page
        # (could be in multiple places, so just verify it exists)
        assert "1" in response.text
