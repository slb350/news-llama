"""
Unit tests for health check service - TDD RED phase.

Tests source health checking: Reddit, RSS, HackerNews.
Uses mocked aggregators to avoid external network dependencies.
"""

import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.orm import Session

from src.web.database import get_test_db
from src.web.services.health_check_service import (
    check_reddit_health,
    check_rss_health,
    bulk_health_check,
    bulk_health_check_and_update,
)


@pytest.fixture
def db():
    yield from get_test_db()


@pytest.fixture
def mock_reddit_aggregator():
    """Mock Reddit aggregator for health checks."""
    mock = AsyncMock()

    async def mock_collect():
        # Simulate different responses based on subreddit in aggregator
        if hasattr(mock, "_subreddit"):
            subreddit = mock._subreddit
            if subreddit == "rust" or subreddit == "golang":
                # Return mock articles for healthy subreddits
                return [{"title": f"Article {i}"} for i in range(10)]
            elif subreddit == "thissubredditdoesnotexist12345":
                # Simulate 404
                raise Exception("404: Subreddit not found")
            elif subreddit == "ArtificialIntelligence":
                # Simulate banned/redirect
                raise Exception("403: Forbidden")
        return []

    mock.collect.side_effect = mock_collect
    return mock


@pytest.fixture
def mock_rss_aggregator():
    """Mock RSS aggregator for health checks."""
    mock = AsyncMock()

    async def mock_collect():
        # Simulate different responses based on URL in aggregator
        if hasattr(mock, "_url"):
            url = mock._url
            if "this-week-in-rust.org" in url:
                # Return mock articles for healthy feed
                return [{"title": f"Article {i}"} for i in range(5)]
            elif "does-not-exist.xml" in url:
                # Simulate 404
                raise Exception("404: Not Found")
            elif "slow-feed" in url:
                # Simulate timeout
                raise TimeoutError("Request timed out")
        return []

    mock.collect.side_effect = mock_collect
    return mock


class TestRedditHealthCheck:
    """Tests for Reddit health checks."""

    @pytest.mark.asyncio
    async def test_healthy_subreddit(self, mock_reddit_aggregator):
        """Should pass health check for active subreddit."""
        mock_reddit_aggregator._subreddit = "rust"

        with patch("src.aggregators.reddit_aggregator.RedditAggregator") as MockClass:
            MockClass.return_value = mock_reddit_aggregator
            result = await check_reddit_health("rust")

        assert result["success"] is True
        assert result["articles_found"] == 10
        assert result["response_time_ms"] >= 0
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_404_subreddit(self, mock_reddit_aggregator):
        """Should fail health check for non-existent subreddit."""
        mock_reddit_aggregator._subreddit = "thissubredditdoesnotexist12345"

        with patch("src.aggregators.reddit_aggregator.RedditAggregator") as MockClass:
            MockClass.return_value = mock_reddit_aggregator
            result = await check_reddit_health("thissubredditdoesnotexist12345")

        assert result["success"] is False
        assert result["error"] == "404"

    @pytest.mark.asyncio
    async def test_banned_subreddit(self, mock_reddit_aggregator):
        """Should fail health check for banned/private subreddit."""
        mock_reddit_aggregator._subreddit = "ArtificialIntelligence"

        with patch("src.aggregators.reddit_aggregator.RedditAggregator") as MockClass:
            MockClass.return_value = mock_reddit_aggregator
            result = await check_reddit_health("ArtificialIntelligence")

        assert result["success"] is False
        assert result["error"] == "403"


class TestRSSHealthCheck:
    """Tests for RSS feed health checks."""

    @pytest.mark.asyncio
    async def test_healthy_rss_feed(self, mock_rss_aggregator):
        """Should pass health check for working RSS feed."""
        mock_rss_aggregator._url = "https://this-week-in-rust.org/rss.xml"

        with patch("src.aggregators.rss_aggregator.RSSAggregator") as MockClass:
            MockClass.return_value = mock_rss_aggregator
            result = await check_rss_health(
                "this_week_in_rust", "https://this-week-in-rust.org/rss.xml"
            )

        assert result["success"] is True
        assert result["articles_found"] == 5
        assert result["response_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_404_rss_feed(self, mock_rss_aggregator):
        """Should fail health check for 404 RSS feed."""
        mock_rss_aggregator._url = "https://example.com/does-not-exist.xml"

        with patch("src.aggregators.rss_aggregator.RSSAggregator") as MockClass:
            MockClass.return_value = mock_rss_aggregator
            result = await check_rss_health(
                "broken_feed", "https://example.com/does-not-exist.xml"
            )

        assert result["success"] is False
        assert result["error"] == "404"

    @pytest.mark.asyncio
    async def test_timeout_rss_feed(self, mock_rss_aggregator):
        """Should fail health check for slow RSS feed."""
        mock_rss_aggregator._url = "https://example.com/slow-feed.xml"

        with patch("src.aggregators.rss_aggregator.RSSAggregator") as MockClass:
            MockClass.return_value = mock_rss_aggregator
            result = await check_rss_health(
                "slow_feed", "https://example.com/slow-feed.xml", timeout_seconds=2
            )

        assert result["success"] is False
        assert result["error"] == "timeout"


class TestBulkHealthCheck:
    """Tests for bulk health checking."""

    @pytest.mark.asyncio
    async def test_bulk_check_multiple_sources(
        self, db: Session, mock_reddit_aggregator, mock_rss_aggregator
    ):
        """Should health check multiple sources concurrently."""
        sources = [
            {"source_type": "reddit", "source_key": "rust"},
            {"source_type": "reddit", "source_key": "golang"},
            {
                "source_type": "rss",
                "source_key": "this_week_in_rust",
                "source_url": "https://this-week-in-rust.org/rss.xml",
            },
        ]

        # Set up mocks to return success for these specific sources
        mock_reddit_aggregator._subreddit = "rust"
        mock_rss_aggregator._url = "https://this-week-in-rust.org/rss.xml"

        def reddit_factory(subreddit_names):
            mock = AsyncMock()
            mock._subreddit = subreddit_names[0] if subreddit_names else None

            async def mock_collect():
                return [{"title": f"Article {i}"} for i in range(10)]

            mock.collect = mock_collect
            return mock

        def rss_factory(rss_feeds):
            mock = AsyncMock()
            mock._url = rss_feeds[0]["url"] if rss_feeds else None

            async def mock_collect():
                return [{"title": f"Article {i}"} for i in range(5)]

            mock.collect = mock_collect
            return mock

        with (
            patch("src.aggregators.reddit_aggregator.RedditAggregator", reddit_factory),
            patch("src.aggregators.rss_aggregator.RSSAggregator", rss_factory),
        ):
            results = await bulk_health_check(sources)

        assert len(results) == 3
        assert all("success" in r for r in results)
        assert all("response_time_ms" in r for r in results)

    @pytest.mark.asyncio
    async def test_bulk_check_updates_database(self, db: Session):
        """Should update source_health table with results."""
        sources = [
            {"source_type": "reddit", "source_key": "rust"},
        ]

        def reddit_factory(subreddit_names):
            mock = AsyncMock()

            async def mock_collect():
                return [{"title": f"Article {i}"} for i in range(10)]

            mock.collect = mock_collect
            return mock

        with patch(
            "src.aggregators.reddit_aggregator.RedditAggregator", reddit_factory
        ):
            await bulk_health_check_and_update(db, sources)

        # Verify database updated
        from src.web.models import SourceHealth

        health = (
            db.query(SourceHealth).filter(SourceHealth.source_key == "rust").first()
        )

        assert health is not None
        assert health.last_check_at is not None
        assert health.articles_found == 10
        assert health.is_healthy is True
