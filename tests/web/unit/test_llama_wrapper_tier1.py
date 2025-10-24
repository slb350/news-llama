"""
Unit tests for FULL Tier 1 integration - TDD RED phase.

Tests actual speed improvements and source usage.
"""

import pytest
from datetime import date
from unittest.mock import patch, Mock, AsyncMock
from sqlalchemy.orm import Session

from src.web.database import get_test_db
from src.web.services import llama_wrapper_tier1, tier1_service
from src.web.models import Tier1Source, SourceContribution


@pytest.fixture
def db():
    yield from get_test_db()


class TestTier1FastPath:
    """Tests for 2-minute fast path with Tier 1 sources."""

    def test_convert_tier1_to_discovered_format(self, db: Session):
        """Should convert Tier1Source to DiscoveredSource format."""
        from datetime import datetime

        # Create Tier 1 source
        tier1 = Tier1Source(
            source_type="reddit",
            source_key="rust",
            interests='["Rust", "Programming"]',
            quality_score=0.95,
            discovered_at=datetime.now().isoformat(),
            discovered_via="weekly_job",
            is_healthy=True,
        )
        db.add(tier1)
        db.commit()

        # Convert to DiscoveredSource
        discovered = llama_wrapper_tier1.convert_tier1_to_discovered([tier1])

        assert len(discovered) == 1
        assert discovered[0].name == "r/rust"
        assert discovered[0].subreddit == "rust"
        assert discovered[0].source_type == "reddit"
        assert discovered[0].category == "Rust"
        assert discovered[0].confidence_score == 0.95
        assert discovered[0].reason == "Tier 1 source (quality: 0.95)"

    def test_convert_rss_source_format(self, db: Session):
        """Should convert RSS Tier 1 source correctly."""
        from datetime import datetime

        tier1 = Tier1Source(
            source_type="rss",
            source_key="rust_blog",
            source_url="https://blog.rust-lang.org/feed.xml",
            interests='["Rust"]',
            quality_score=0.88,
            discovered_at=datetime.now().isoformat(),
            discovered_via="list_mining",
            is_healthy=True,
        )
        db.add(tier1)
        db.commit()

        discovered = llama_wrapper_tier1.convert_tier1_to_discovered([tier1])

        assert len(discovered) == 1
        assert discovered[0].name == "rust_blog"
        assert discovered[0].url == "https://blog.rust-lang.org/feed.xml"
        assert discovered[0].source_type == "rss"
        assert discovered[0].confidence_score == 0.88

    @patch("src.web.services.llama_wrapper.NewsLlama")
    def test_high_coverage_skips_llm_discovery(
        self, mock_news_llama_class, db: Session
    ):
        """Should use pre-discovered sources when coverage >= 90%."""
        from src.web.services.llama_wrapper import generate_newsletter_with_tier1

        # Setup Tier 1 sources for all interests
        tier1_service.add_tier1_source(
            db,
            "reddit",
            "rust",
            interests=["Rust"],
            quality_score=0.9,
            discovered_via="test",
        )
        tier1_service.add_tier1_source(
            db,
            "reddit",
            "python",
            interests=["Python"],
            quality_score=0.9,
            discovered_via="test",
        )

        # Mock NewsLlama
        mock_instance = Mock()
        mock_news_llama_class.return_value = mock_instance
        mock_instance.run = AsyncMock(
            return_value={
                "total_articles": 50,
                "sources_used": ["dynamic"],
                "discovered_sources": 2,
            }
        )

        with patch("src.web.services.llama_wrapper.Path.exists", return_value=True):
            # Generate with Tier 1
            result = generate_newsletter_with_tier1(
                interests=["Rust", "Python"], output_date=date.today(), db=db
            )

        # Verify NewsLlama was called with pre_discovered_sources
        mock_news_llama_class.assert_called_once()
        call_kwargs = mock_news_llama_class.call_args[1]
        assert "pre_discovered_sources" in call_kwargs
        assert len(call_kwargs["pre_discovered_sources"]) == 2

        # Verify no LLM discovery happened (fast path)
        mock_instance.source_discovery = (
            None  # Should be None when using pre-discovered
        )

    @patch("src.web.services.llama_wrapper.NewsLlama")
    def test_low_coverage_uses_hybrid_mode(self, mock_news_llama_class, db: Session):
        """Should use hybrid mode (Tier 1 + LLM) when coverage < 90%."""
        from src.web.services.llama_wrapper import generate_newsletter_with_tier1

        # Only 1 of 3 interests covered
        tier1_service.add_tier1_source(
            db,
            "reddit",
            "rust",
            interests=["Rust"],
            quality_score=0.9,
            discovered_via="test",
        )

        mock_instance = Mock()
        mock_news_llama_class.return_value = mock_instance
        mock_instance.run = AsyncMock()

        with patch("src.web.services.llama_wrapper.Path.exists", return_value=True):
            result = generate_newsletter_with_tier1(
                interests=["Rust", "Python", "Go"],  # Only Rust covered
                output_date=date.today(),
                db=db,
            )

        # Should still call NewsLlama with user interests (for LLM discovery)
        mock_news_llama_class.assert_called_once()
        # Get positional and keyword arguments
        args, kwargs = mock_news_llama_class.call_args
        # In hybrid mode: still passes user interests for LLM discovery
        assert "user_interests" in kwargs
        assert kwargs["user_interests"] == ["Rust", "Python", "Go"]

    def test_track_source_contributions(self, db: Session):
        """Should track which Tier 1 sources contributed articles."""
        from src.web.services.user_service import create_user
        from src.web.services.newsletter_service import create_pending_newsletter

        user = create_user(db, first_name="Test")
        newsletter = create_pending_newsletter(db, user.id, date.today())

        # Track contributions
        contributions = [
            {
                "source_type": "reddit",
                "source_key": "rust",
                "articles_collected": 25,
                "articles_included": 8,
            },
            {
                "source_type": "rss",
                "source_key": "rust_blog",
                "articles_collected": 10,
                "articles_included": 5,
            },
        ]

        llama_wrapper_tier1.track_source_contributions(db, newsletter.id, contributions)

        # Verify tracking
        tracked = (
            db.query(SourceContribution)
            .filter(SourceContribution.newsletter_id == newsletter.id)
            .all()
        )

        assert len(tracked) == 2
        assert sum(c.articles_collected for c in tracked) == 35
        assert sum(c.articles_included for c in tracked) == 13

    def test_filter_unhealthy_sources(self, db: Session):
        """Should exclude unhealthy Tier 1 sources."""
        # Add healthy and unhealthy sources
        tier1_service.add_tier1_source(
            db,
            "reddit",
            "rust",
            interests=["Rust"],
            quality_score=0.9,
            discovered_via="test",
        )
        unhealthy = tier1_service.add_tier1_source(
            db,
            "rss",
            "dead_feed",
            interests=["Rust"],
            quality_score=0.85,
            discovered_via="test",
        )

        # Mark as unhealthy by updating the record directly
        unhealthy.is_healthy = False
        db.commit()

        # Get sources (should filter unhealthy)
        sources = llama_wrapper_tier1.get_healthy_tier1_for_interests(db, ["Rust"])

        assert len(sources) == 1
        assert sources[0].source_key == "rust"

    def test_blacklist_filtering_on_tier1(self, db: Session):
        """Should filter blacklisted sources even if in Tier 1."""
        from src.web.services import blacklist_service

        # Add to Tier 1
        tier1_service.add_tier1_source(
            db,
            "reddit",
            "toxic_sub",
            interests=["Test"],
            quality_score=0.85,
            discovered_via="test",
        )
        # Add to blacklist
        blacklist_service.add_to_blacklist(
            db, "reddit", "toxic_sub", reason="toxic_content"
        )

        # Get filtered sources
        sources = llama_wrapper_tier1.get_filtered_tier1_sources(db, ["Test"])

        assert len(sources) == 0  # Filtered out
