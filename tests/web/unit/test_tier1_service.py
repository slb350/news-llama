"""
Unit tests for Tier 1 source service - TDD RED phase.

Tests Tier 1 source management: add, query, coverage, health updates.
"""

import pytest
import json
from datetime import datetime
from sqlalchemy.orm import Session

from src.web.database import get_test_db
from src.web.services.tier1_service import (
    add_tier1_source,
    get_sources_for_interests,
    get_coverage_stats,
    mark_source_unhealthy,
    mark_source_healthy,
)
from src.web.models import Tier1Source


@pytest.fixture
def db():
    yield from get_test_db()


class TestAddTier1Source:
    """Tests for adding sources to Tier 1."""

    def test_add_reddit_source(self, db: Session):
        """Should add Reddit source to Tier 1."""
        source = add_tier1_source(
            db,
            source_type="reddit",
            source_key="localllama",
            interests=["AI & Machine Learning", "LocalLLM"],
            quality_score=0.85,
            discovered_via="direct_search",
            description="Local LLM community",
            avg_posts_per_day=24.0,
        )

        assert source.id is not None
        assert source.source_key == "localllama"
        assert source.is_healthy is True

        # Verify JSON interests
        interests = json.loads(source.interests)
        assert "LocalLLM" in interests

    def test_add_rss_source(self, db: Session):
        """Should add RSS feed to Tier 1."""
        source = add_tier1_source(
            db,
            source_type="rss",
            source_key="this_week_in_rust",
            source_url="https://this-week-in-rust.org/rss.xml",
            interests=["Rust", "Open Source"],
            quality_score=0.92,
            discovered_via="list_mining",
            description="Weekly Rust newsletter",
        )

        assert source.source_url is not None
        assert source.quality_score == 0.92

    def test_duplicate_source_updates(self, db: Session):
        """Should update existing source if already in Tier 1."""
        # Add first time
        add_tier1_source(
            db,
            "reddit",
            "rust",
            interests=["Rust"],
            quality_score=0.8,
            discovered_via="direct_search",
        )

        # Add again with different interests (should update)
        updated = add_tier1_source(
            db,
            "reddit",
            "rust",
            interests=["Rust", "Programming"],
            quality_score=0.85,
            discovered_via="list_mining",
        )

        # Should only have one entry
        all_rust = db.query(Tier1Source).filter(Tier1Source.source_key == "rust").all()
        assert len(all_rust) == 1

        # Should have merged interests
        interests = json.loads(updated.interests)
        assert "Rust" in interests
        assert "Programming" in interests


class TestQueryTier1Sources:
    """Tests for querying Tier 1 sources."""

    def test_get_sources_for_single_interest(self, db: Session):
        """Should return sources matching single interest."""
        # Add sources
        add_tier1_source(
            db,
            "reddit",
            "rust",
            interests=["Rust"],
            quality_score=0.9,
            discovered_via="manual",
        )
        add_tier1_source(
            db,
            "reddit",
            "golang",
            interests=["Go"],
            quality_score=0.85,
            discovered_via="manual",
        )
        add_tier1_source(
            db,
            "rss",
            "this_week_in_rust",
            source_url="https://...",
            interests=["Rust", "Open Source"],
            quality_score=0.92,
            discovered_via="manual",
        )

        # Query for Rust sources
        rust_sources = get_sources_for_interests(db, ["Rust"])

        assert len(rust_sources) == 2
        assert any(s.source_key == "rust" for s in rust_sources)
        assert any(s.source_key == "this_week_in_rust" for s in rust_sources)

    def test_get_sources_for_multiple_interests(self, db: Session):
        """Should return sources matching any of the interests."""
        add_tier1_source(
            db,
            "reddit",
            "rust",
            interests=["Rust"],
            quality_score=0.9,
            discovered_via="manual",
        )
        add_tier1_source(
            db,
            "reddit",
            "golang",
            interests=["Go"],
            quality_score=0.85,
            discovered_via="manual",
        )
        add_tier1_source(
            db,
            "reddit",
            "programming",
            interests=["Programming"],
            quality_score=0.8,
            discovered_via="manual",
        )

        # Query for Rust OR Go
        sources = get_sources_for_interests(db, ["Rust", "Go"])

        assert len(sources) == 2
        assert any(s.source_key == "rust" for s in sources)
        assert any(s.source_key == "golang" for s in sources)

    def test_only_healthy_sources(self, db: Session):
        """Should only return healthy sources."""
        # Add healthy source
        add_tier1_source(
            db,
            "reddit",
            "rust",
            interests=["Rust"],
            quality_score=0.9,
            discovered_via="manual",
        )

        # Add unhealthy source
        unhealthy = add_tier1_source(
            db,
            "rss",
            "broken_feed",
            source_url="https://...",
            interests=["Rust"],
            quality_score=0.7,
            discovered_via="manual",
        )
        mark_source_unhealthy(db, unhealthy.id, "404")

        # Query should only return healthy
        sources = get_sources_for_interests(db, ["Rust"])

        assert len(sources) == 1
        assert sources[0].source_key == "rust"

    def test_get_sources_empty_interests(self, db: Session):
        """Should handle empty interests list gracefully."""
        add_tier1_source(
            db,
            "reddit",
            "rust",
            interests=["Rust"],
            quality_score=0.9,
            discovered_via="manual",
        )

        # Empty interests should return empty list
        sources = get_sources_for_interests(db, [])

        assert sources == []


class TestCoverageStats:
    """Tests for coverage statistics."""

    def test_calculate_coverage(self, db: Session):
        """Should calculate coverage percentage for user interests."""
        # Add Tier 1 sources
        add_tier1_source(
            db,
            "reddit",
            "rust",
            interests=["Rust"],
            quality_score=0.9,
            discovered_via="manual",
        )
        add_tier1_source(
            db,
            "reddit",
            "localllama",
            interests=["LocalLLM", "AI & Machine Learning"],
            quality_score=0.85,
            discovered_via="manual",
        )

        # User interests: ["Rust", "LocalLLM", "Go", "Python"]
        # Coverage: 2/4 = 50%
        stats = get_coverage_stats(db, ["Rust", "LocalLLM", "Go", "Python"])

        assert stats["total_interests"] == 4
        assert stats["covered_interests"] == 2
        assert stats["coverage_percentage"] == 50.0
        assert "Rust" in stats["covered"]
        assert "LocalLLM" in stats["covered"]
        assert "Go" in stats["missing"]
        assert "Python" in stats["missing"]

    def test_coverage_with_empty_tier1(self, db: Session):
        """Should handle empty Tier 1 (no sources yet)."""
        stats = get_coverage_stats(db, ["Rust", "Go", "Python"])

        assert stats["total_interests"] == 3
        assert stats["covered_interests"] == 0
        assert stats["coverage_percentage"] == 0.0
        assert len(stats["missing"]) == 3


class TestHealthUpdates:
    """Tests for health status updates."""

    def test_mark_unhealthy(self, db: Session):
        """Should mark source as unhealthy."""
        source = add_tier1_source(
            db,
            "rss",
            "test_feed",
            source_url="https://...",
            interests=["Test"],
            quality_score=0.8,
            discovered_via="manual",
        )

        mark_source_unhealthy(db, source.id, "404")

        db.refresh(source)
        assert source.is_healthy is False

    def test_mark_healthy(self, db: Session):
        """Should mark source as healthy (resurrection)."""
        source = add_tier1_source(
            db,
            "rss",
            "test_feed",
            source_url="https://...",
            interests=["Test"],
            quality_score=0.8,
            discovered_via="manual",
        )
        mark_source_unhealthy(db, source.id, "timeout")

        # Resurrect
        mark_source_healthy(db, source.id)

        db.refresh(source)
        assert source.is_healthy is True

    def test_mark_unhealthy_nonexistent_id(self, db: Session):
        """Should handle non-existent source ID gracefully."""
        # Should not raise error
        mark_source_unhealthy(db, 99999, "404")

        # Verify no entries created
        source = db.query(Tier1Source).filter(Tier1Source.id == 99999).first()
        assert source is None
