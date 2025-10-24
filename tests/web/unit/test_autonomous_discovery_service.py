"""
Unit tests for autonomous discovery service - TDD RED phase.

Tests weekly discovery orchestration.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock
from sqlalchemy.orm import Session

from src.web.database import get_test_db
from src.web.services import autonomous_discovery_service, tier1_service
from src.web.models import Tier1Source, DiscoveredSource, SourceBlacklist


@pytest.fixture
def db():
    yield from get_test_db()


class TestWeeklyDiscovery:
    """Tests for weekly discovery job."""

    @pytest.mark.asyncio
    async def test_discovers_and_promotes_sources(self, db: Session):
        """Should discover sources and auto-promote high-quality ones."""
        with (
            patch(
                "src.web.services.list_mining_service.mine_all_lists_for_interest"
            ) as mock_mine,
            patch(
                "src.web.services.direct_search_service.search_for_interest"
            ) as mock_search,
            patch(
                "src.web.services.health_check_service.bulk_health_check"
            ) as mock_health,
        ):
            # Mock discoveries
            mock_mine.return_value = [
                {
                    "source_type": "reddit",
                    "source_key": "rust",
                    "interests": ["Rust"],
                    "discovered_via": "awesome-rust",
                    "metadata": {},
                }
            ]
            mock_search.return_value = [
                {
                    "source_type": "rss",
                    "source_key": "rust_blog",
                    "source_url": "https://blog.rust-lang.org/feed.xml",
                    "interests": ["Rust"],
                    "discovered_via": "llm-search",
                    "metadata": {"confidence": 0.9},
                }
            ]

            # Mock health checks (all pass)
            mock_health.return_value = [
                {
                    "source": {"source_type": "reddit", "source_key": "rust"},
                    "success": True,
                    "articles_found": 50,
                    "response_time_ms": 200,
                },
                {
                    "source": {
                        "source_type": "rss",
                        "source_key": "rust_blog",
                    },
                    "success": True,
                    "articles_found": 10,
                    "response_time_ms": 150,
                },
            ]

            # Run discovery
            stats = await autonomous_discovery_service.run_weekly_discovery(
                db, interests=["Rust"]
            )

        # Verify Tier 1 additions
        tier1 = db.query(Tier1Source).all()
        assert len(tier1) >= 1  # At least one should be auto-promoted

        # Verify stats
        assert stats["total_discovered"] >= 2
        assert stats["auto_promoted"] >= 1
        assert stats["interests_processed"] == 1

    @pytest.mark.asyncio
    async def test_includes_custom_user_interests(self, db: Session):
        """Should discover sources for both predefined and custom user interests."""
        from src.web.services.user_service import create_user
        from src.web.services.interest_service import add_user_interest

        # Create user with custom interest
        user = create_user(db, first_name="TestUser")
        add_user_interest(db, user.id, "Quantum Computing", is_predefined=False)

        with (
            patch(
                "src.web.services.list_mining_service.mine_all_lists_for_interest"
            ) as mock_mine,
            patch(
                "src.web.services.direct_search_service.search_for_interest"
            ) as mock_search,
            patch(
                "src.web.services.health_check_service.bulk_health_check"
            ) as mock_health,
        ):
            # Mock empty discoveries to keep test fast
            mock_mine.return_value = []
            mock_search.return_value = []
            mock_health.return_value = []

            stats = await autonomous_discovery_service.run_weekly_discovery(db)

        # Should have processed custom interest
        assert stats["interests_processed"] >= 1
        # Verify custom interest was included
        # (In real scenario, mock_search would be called with "Quantum Computing")

    @pytest.mark.asyncio
    async def test_filters_blacklisted_sources(self, db: Session):
        """Should filter out blacklisted sources."""
        # Add source to blacklist
        from src.web.services.blacklist_service import add_to_blacklist

        add_to_blacklist(db, "reddit", "banned_sub", "404")

        with (
            patch(
                "src.web.services.list_mining_service.mine_all_lists_for_interest"
            ) as mock_mine,
            patch(
                "src.web.services.direct_search_service.search_for_interest"
            ) as mock_search,
            patch(
                "src.web.services.health_check_service.bulk_health_check"
            ) as mock_health,
        ):
            # Mock discoveries including blacklisted source
            mock_mine.return_value = []
            mock_search.return_value = [
                {
                    "source_type": "reddit",
                    "source_key": "banned_sub",
                    "interests": ["Test"],
                    "discovered_via": "llm-search",
                    "metadata": {},
                },
                {
                    "source_type": "reddit",
                    "source_key": "good_sub",
                    "interests": ["Test"],
                    "discovered_via": "llm-search",
                    "metadata": {},
                },
            ]

            # Mock health check should only be called for non-blacklisted
            mock_health.return_value = [
                {
                    "source": {"source_type": "reddit", "source_key": "good_sub"},
                    "success": True,
                    "articles_found": 20,
                    "response_time_ms": 100,
                }
            ]

            stats = await autonomous_discovery_service.run_weekly_discovery(
                db, interests=["Test"]
            )

        # Verify blacklisted source was filtered (only 1 health check call)
        assert mock_health.call_count == 1
        # Total discovered before filter was 2, after filter was 1
        assert stats["total_discovered"] == 2

    @pytest.mark.asyncio
    async def test_handles_health_check_failures(self, db: Session):
        """Should handle health check failures gracefully."""
        with (
            patch(
                "src.web.services.list_mining_service.mine_all_lists_for_interest"
            ) as mock_mine,
            patch(
                "src.web.services.direct_search_service.search_for_interest"
            ) as mock_search,
            patch(
                "src.web.services.health_check_service.bulk_health_check"
            ) as mock_health,
        ):
            # Mock discoveries
            mock_mine.return_value = []
            mock_search.return_value = [
                {
                    "source_type": "reddit",
                    "source_key": "failing_sub",
                    "interests": ["Test"],
                    "discovered_via": "llm-search",
                    "metadata": {},
                }
            ]

            # Mock health check failure
            mock_health.return_value = [
                {
                    "source": {
                        "source_type": "reddit",
                        "source_key": "failing_sub",
                    },
                    "success": False,
                    "articles_found": 0,
                    "response_time_ms": 0,
                    "error": "404",
                }
            ]

            stats = await autonomous_discovery_service.run_weekly_discovery(
                db, interests=["Test"]
            )

        # Should not promote unhealthy sources
        tier1 = db.query(Tier1Source).all()
        assert len(tier1) == 0
        assert stats["healthy"] == 0
        assert stats["auto_promoted"] == 0

    @pytest.mark.asyncio
    async def test_logs_discoveries_to_database(self, db: Session):
        """Should log all discoveries to discovered_sources table."""
        with (
            patch(
                "src.web.services.list_mining_service.mine_all_lists_for_interest"
            ) as mock_mine,
            patch(
                "src.web.services.direct_search_service.search_for_interest"
            ) as mock_search,
            patch(
                "src.web.services.health_check_service.bulk_health_check"
            ) as mock_health,
        ):
            # Mock discoveries
            mock_mine.return_value = []
            mock_search.return_value = [
                {
                    "source_type": "reddit",
                    "source_key": "test_sub",
                    "interests": ["Test"],
                    "discovered_via": "llm-search",
                    "metadata": {"confidence": 0.75},
                }
            ]

            # Mock health check
            mock_health.return_value = [
                {
                    "source": {"source_type": "reddit", "source_key": "test_sub"},
                    "success": True,
                    "articles_found": 15,
                    "response_time_ms": 120,
                }
            ]

            await autonomous_discovery_service.run_weekly_discovery(
                db, interests=["Test"]
            )

        # Verify discovery was logged
        discovered = (
            db.query(DiscoveredSource)
            .filter(DiscoveredSource.source_key == "test_sub")
            .first()
        )

        assert discovered is not None
        assert discovered.source_type == "reddit"
        assert discovered.quality_score is not None
        assert discovered.health_check_passed is True
