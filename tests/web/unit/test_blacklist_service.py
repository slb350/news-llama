"""
Unit tests for blacklist service - TDD RED phase.

Tests blacklist management: add, check, resurrect, filter.
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from src.web.database import get_test_db
from src.web.services.blacklist_service import (
    add_to_blacklist,
    is_blacklisted,
    filter_blacklisted_sources,
    mark_resurrection_attempt,
    remove_from_blacklist,
    get_blacklist_stats,
)
from src.web.models import SourceBlacklist


@pytest.fixture
def db():
    yield from get_test_db()


class TestAddToBlacklist:
    """Tests for adding sources to blacklist."""

    def test_add_rss_feed_404(self, db: Session):
        """Should blacklist RSS feed with 404 error."""
        add_to_blacklist(
            db,
            source_type="rss",
            source_key="openai_blog",
            source_url="https://openai.com/blog/rss/",
            reason="404",
        )

        # Verify blacklisted
        is_blacklisted_result = is_blacklisted(db, "rss", "openai_blog")
        assert is_blacklisted_result is True

    def test_add_reddit_404(self, db: Session):
        """Should blacklist subreddit that doesn't exist."""
        add_to_blacklist(db, "reddit", "ArtificialIntelligence", reason="404")

        assert is_blacklisted(db, "reddit", "ArtificialIntelligence")

    def test_increment_failure_count(self, db: Session):
        """Should increment failure_count if already blacklisted."""
        # Add first time
        add_to_blacklist(db, "rss", "broken_feed", reason="timeout")

        entry = (
            db.query(SourceBlacklist)
            .filter(SourceBlacklist.source_key == "broken_feed")
            .first()
        )
        assert entry.failure_count == 1

        # Add again (should increment)
        add_to_blacklist(db, "rss", "broken_feed", reason="timeout")

        db.refresh(entry)
        assert entry.failure_count == 2

    def test_update_reason_on_re_add(self, db: Session):
        """Should update reason when re-adding with different failure."""
        # Add with timeout
        add_to_blacklist(db, "rss", "unstable_feed", reason="timeout")

        # Add again with 404
        add_to_blacklist(db, "rss", "unstable_feed", reason="404")

        entry = (
            db.query(SourceBlacklist)
            .filter(SourceBlacklist.source_key == "unstable_feed")
            .first()
        )
        assert entry.blacklisted_reason == "404"
        assert entry.failure_count == 2


class TestIsBlacklisted:
    """Tests for checking blacklist status."""

    def test_not_blacklisted(self, db: Session):
        """Should return False for non-blacklisted source."""
        is_blacklisted_result = is_blacklisted(db, "reddit", "rust")
        assert is_blacklisted_result is False

    def test_is_blacklisted(self, db: Session):
        """Should return True for blacklisted source."""
        add_to_blacklist(db, "reddit", "banned_sub", reason="404")

        assert is_blacklisted(db, "reddit", "banned_sub") is True


class TestFilterBlacklist:
    """Tests for filtering sources against blacklist."""

    def test_filter_removes_blacklisted(self, db: Session):
        """Should remove blacklisted sources from list."""
        # Blacklist some sources
        add_to_blacklist(db, "reddit", "ArtificialIntelligence", reason="404")
        add_to_blacklist(db, "rss", "broken_feed", reason="timeout")

        # List of candidate sources
        candidates = [
            {"source_type": "reddit", "source_key": "rust"},
            {
                "source_type": "reddit",
                "source_key": "ArtificialIntelligence",
            },  # Blacklisted
            {"source_type": "rss", "source_key": "this_week_in_rust"},
            {"source_type": "rss", "source_key": "broken_feed"},  # Blacklisted
        ]

        filtered = filter_blacklisted_sources(db, candidates)

        assert len(filtered) == 2
        assert any(s["source_key"] == "rust" for s in filtered)
        assert any(s["source_key"] == "this_week_in_rust" for s in filtered)
        assert not any(s["source_key"] == "ArtificialIntelligence" for s in filtered)

    def test_filter_empty_list(self, db: Session):
        """Should handle empty source list."""
        add_to_blacklist(db, "reddit", "banned", reason="404")

        filtered = filter_blacklisted_sources(db, [])

        assert filtered == []

    def test_filter_all_blacklisted(self, db: Session):
        """Should return empty list if all sources blacklisted."""
        add_to_blacklist(db, "reddit", "sub1", reason="404")
        add_to_blacklist(db, "rss", "feed1", reason="timeout")

        candidates = [
            {"source_type": "reddit", "source_key": "sub1"},
            {"source_type": "rss", "source_key": "feed1"},
        ]

        filtered = filter_blacklisted_sources(db, candidates)

        assert len(filtered) == 0


class TestAttemptResurrection:
    """Tests for attempting to resurrect blacklisted sources."""

    def test_mark_resurrection_attempt(self, db: Session):
        """Should update last_attempted_resurrection timestamp."""
        add_to_blacklist(db, "rss", "maybe_fixed", reason="404")

        mark_resurrection_attempt(db, "rss", "maybe_fixed")

        entry = (
            db.query(SourceBlacklist)
            .filter(SourceBlacklist.source_key == "maybe_fixed")
            .first()
        )
        assert entry.last_attempted_resurrection is not None

    def test_mark_resurrection_non_existent(self, db: Session):
        """Should handle marking resurrection on non-existent entry."""
        # Should not raise error
        mark_resurrection_attempt(db, "rss", "non_existent")

        # Verify no entry was created
        entry = (
            db.query(SourceBlacklist)
            .filter(SourceBlacklist.source_key == "non_existent")
            .first()
        )
        assert entry is None

    def test_remove_from_blacklist(self, db: Session):
        """Should remove from blacklist if resurrection successful."""
        add_to_blacklist(db, "rss", "fixed_feed", reason="404")
        assert is_blacklisted(db, "rss", "fixed_feed")

        # Simulate successful resurrection
        remove_from_blacklist(db, "rss", "fixed_feed")

        assert is_blacklisted(db, "rss", "fixed_feed") is False

    def test_remove_non_existent(self, db: Session):
        """Should handle removing non-existent entry gracefully."""
        # Should not raise error
        remove_from_blacklist(db, "rss", "never_existed")

        # Verify still doesn't exist
        assert is_blacklisted(db, "rss", "never_existed") is False


class TestGetBlacklistStats:
    """Tests for blacklist statistics."""

    def test_get_stats(self, db: Session):
        """Should return blacklist statistics by type."""
        # Add various blacklisted sources
        add_to_blacklist(db, "reddit", "sub1", reason="404")
        add_to_blacklist(db, "reddit", "sub2", reason="redirect")
        add_to_blacklist(db, "rss", "feed1", reason="timeout")
        add_to_blacklist(db, "rss", "feed2", reason="404")
        add_to_blacklist(db, "rss", "feed3", reason="403")

        stats = get_blacklist_stats(db)

        assert stats["total"] == 5
        assert stats["by_type"]["reddit"] == 2
        assert stats["by_type"]["rss"] == 3
        assert stats["by_reason"]["404"] == 2
        assert stats["by_reason"]["timeout"] == 1
        assert stats["by_reason"]["403"] == 1
        assert stats["by_reason"]["redirect"] == 1

    def test_get_stats_empty(self, db: Session):
        """Should return empty stats for empty blacklist."""
        stats = get_blacklist_stats(db)

        assert stats["total"] == 0
        assert stats["by_type"] == {}
        assert stats["by_reason"] == {}
