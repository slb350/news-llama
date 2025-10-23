"""
Unit tests for source discovery models - TDD RED phase.

Tests tier1_sources, source_blacklist, discovered_sources,
source_health, source_contributions tables and relationships.
"""

import pytest
from datetime import datetime, date
from sqlalchemy.orm import Session

from src.web.database import get_test_db
from src.web.models import (
    Tier1Source,
    SourceBlacklist,
    DiscoveredSource,
    SourceHealth,
    SourceContribution,
    Newsletter,
    User,
)


@pytest.fixture
def db():
    """Provide test database session."""
    yield from get_test_db()


class TestTier1SourceModel:
    """Tests for Tier1Source model."""

    def test_create_tier1_source(self, db: Session):
        """Should create tier1 source with required fields."""
        source = Tier1Source(
            source_type="reddit",
            source_key="localllama",
            interests='["AI & Machine Learning", "LocalLLM"]',
            quality_score=0.85,
            discovered_at=datetime.now().isoformat(),
            discovered_via="direct_search",
        )
        db.add(source)
        db.commit()

        assert source.id is not None
        assert source.source_type == "reddit"
        assert source.is_healthy is True  # Default

    def test_tier1_unique_constraint(self, db: Session):
        """Should enforce unique (source_type, source_key)."""
        source1 = Tier1Source(
            source_type="reddit",
            source_key="rust",
            interests='["Rust"]',
            quality_score=0.9,
            discovered_at=datetime.now().isoformat(),
            discovered_via="list_mining",
        )
        db.add(source1)
        db.commit()

        # Try to add duplicate
        source2 = Tier1Source(
            source_type="reddit",
            source_key="rust",
            interests='["Programming"]',
            quality_score=0.8,
            discovered_at=datetime.now().isoformat(),
            discovered_via="direct_search",
        )
        db.add(source2)

        with pytest.raises(Exception):  # IntegrityError
            db.commit()

    def test_tier1_json_interests(self, db: Session):
        """Should store interests as JSON array string."""
        source = Tier1Source(
            source_type="rss",
            source_key="this_week_in_rust",
            source_url="https://this-week-in-rust.org/rss.xml",
            interests='["Rust", "Open Source"]',
            quality_score=0.92,
            discovered_at=datetime.now().isoformat(),
            discovered_via="list_mining",
        )
        db.add(source)
        db.commit()

        # Verify JSON stored correctly
        import json

        interests = json.loads(source.interests)
        assert "Rust" in interests
        assert "Open Source" in interests

    def test_tier1_optional_fields(self, db: Session):
        """Should allow optional fields to be null."""
        source = Tier1Source(
            source_type="reddit",
            source_key="python",
            interests='["Python"]',
            quality_score=0.88,
            discovered_at=datetime.now().isoformat(),
            discovered_via="list_mining",
            # Optional fields not provided
        )
        db.add(source)
        db.commit()

        assert source.source_url is None
        assert source.description is None
        assert source.last_health_check is None
        assert source.avg_posts_per_day is None
        assert source.domain_age_years is None


class TestSourceBlacklistModel:
    """Tests for SourceBlacklist model."""

    def test_create_blacklist_entry(self, db: Session):
        """Should create blacklist entry with failure reason."""
        blacklist = SourceBlacklist(
            source_type="rss",
            source_key="openai_blog",
            source_url="https://openai.com/blog/rss/",
            blacklisted_at=datetime.now().isoformat(),
            blacklisted_reason="404",
            last_failure_at=datetime.now().isoformat(),
        )
        db.add(blacklist)
        db.commit()

        assert blacklist.id is not None
        assert blacklist.failure_count == 1  # Default
        assert blacklist.blacklisted_reason == "404"

    def test_blacklist_unique_constraint(self, db: Session):
        """Should enforce unique (source_type, source_key)."""
        blacklist1 = SourceBlacklist(
            source_type="reddit",
            source_key="ArtificialIntelligence",
            blacklisted_at=datetime.now().isoformat(),
            blacklisted_reason="404",
            last_failure_at=datetime.now().isoformat(),
        )
        db.add(blacklist1)
        db.commit()

        blacklist2 = SourceBlacklist(
            source_type="reddit",
            source_key="ArtificialIntelligence",
            blacklisted_at=datetime.now().isoformat(),
            blacklisted_reason="timeout",
            last_failure_at=datetime.now().isoformat(),
        )
        db.add(blacklist2)

        with pytest.raises(Exception):
            db.commit()

    def test_blacklist_increment_failure_count(self, db: Session):
        """Should track failure count increments."""
        blacklist = SourceBlacklist(
            source_type="rss",
            source_key="broken_feed",
            blacklisted_at=datetime.now().isoformat(),
            blacklisted_reason="timeout",
            last_failure_at=datetime.now().isoformat(),
            failure_count=1,
        )
        db.add(blacklist)
        db.commit()

        # Simulate another failure
        blacklist.failure_count += 1
        blacklist.last_failure_at = datetime.now().isoformat()
        db.commit()

        assert blacklist.failure_count == 2

    def test_blacklist_optional_fields(self, db: Session):
        """Should allow optional fields to be null."""
        blacklist = SourceBlacklist(
            source_type="reddit",
            source_key="banned_sub",
            blacklisted_at=datetime.now().isoformat(),
            blacklisted_reason="403",
            last_failure_at=datetime.now().isoformat(),
            # source_url and last_attempted_resurrection not provided
        )
        db.add(blacklist)
        db.commit()

        assert blacklist.source_url is None
        assert blacklist.last_attempted_resurrection is None


class TestDiscoveredSourceModel:
    """Tests for DiscoveredSource model."""

    def test_create_discovered_source(self, db: Session):
        """Should create discovered source with metadata."""
        discovered = DiscoveredSource(
            source_type="reddit",
            source_key="golang",
            discovered_at=datetime.now().isoformat(),
            discovered_via="awesome-go",
            interests='["Go"]',
            source_metadata='{"github_stars": 5000, "list_url": "https://github.com/avelino/awesome-go"}',
        )
        db.add(discovered)
        db.commit()

        assert discovered.id is not None
        assert discovered.discovery_count == 1  # Default
        assert discovered.promoted_to_tier1 is False

    def test_increment_discovery_count(self, db: Session):
        """Should increment discovery_count if found multiple times."""
        discovered = DiscoveredSource(
            source_type="reddit",
            source_key="rust",
            discovered_at=datetime.now().isoformat(),
            discovered_via="awesome-rust",
            interests='["Rust"]',
        )
        db.add(discovered)
        db.commit()

        # Simulate finding it again
        discovered.discovery_count += 1
        db.commit()

        assert discovered.discovery_count == 2

    def test_discovered_unique_constraint(self, db: Session):
        """Should enforce unique (source_type, source_key)."""
        discovered1 = DiscoveredSource(
            source_type="reddit",
            source_key="machinelearning",
            discovered_at=datetime.now().isoformat(),
            discovered_via="list_mining",
            interests='["AI"]',
        )
        db.add(discovered1)
        db.commit()

        discovered2 = DiscoveredSource(
            source_type="reddit",
            source_key="machinelearning",
            discovered_at=datetime.now().isoformat(),
            discovered_via="direct_search",
            interests='["AI"]',
        )
        db.add(discovered2)

        with pytest.raises(Exception):
            db.commit()

    def test_discovered_promotion_flag(self, db: Session):
        """Should track promotion to Tier 1."""
        discovered = DiscoveredSource(
            source_type="rss",
            source_key="hacker_news",
            discovered_at=datetime.now().isoformat(),
            discovered_via="list_mining",
            interests='["Tech News"]',
            promoted_to_tier1=False,
        )
        db.add(discovered)
        db.commit()

        # Promote to Tier 1
        discovered.promoted_to_tier1 = True
        db.commit()

        assert discovered.promoted_to_tier1 is True

    def test_discovered_optional_fields(self, db: Session):
        """Should allow optional fields to be null."""
        discovered = DiscoveredSource(
            source_type="reddit",
            source_key="programming",
            discovered_at=datetime.now().isoformat(),
            discovered_via="direct_search",
            interests='["Programming"]',
            # Optional fields not provided
        )
        db.add(discovered)
        db.commit()

        assert discovered.source_url is None
        assert discovered.quality_score is None
        assert discovered.health_check_passed is None
        assert discovered.source_metadata is None


class TestSourceHealthModel:
    """Tests for SourceHealth model."""

    def test_create_health_record(self, db: Session):
        """Should create health record with check results."""
        health = SourceHealth(
            source_type="reddit",
            source_key="localllama",
            last_check_at=datetime.now().isoformat(),
            last_success_at=datetime.now().isoformat(),
            is_healthy=True,
            response_time_ms=250,
            articles_found=24,
        )
        db.add(health)
        db.commit()

        assert health.id is not None
        assert health.consecutive_failures == 0
        assert health.consecutive_successes == 0

    def test_track_consecutive_failures(self, db: Session):
        """Should track consecutive failure count."""
        health = SourceHealth(
            source_type="rss",
            source_key="broken_feed",
            last_check_at=datetime.now().isoformat(),
            last_failure_at=datetime.now().isoformat(),
            consecutive_failures=3,
            is_healthy=False,
            failure_reason="timeout",
        )
        db.add(health)
        db.commit()

        assert health.consecutive_failures == 3
        assert health.is_healthy is False

    def test_health_unique_constraint(self, db: Session):
        """Should enforce unique (source_type, source_key)."""
        health1 = SourceHealth(
            source_type="reddit",
            source_key="python",
            last_check_at=datetime.now().isoformat(),
            is_healthy=True,
        )
        db.add(health1)
        db.commit()

        health2 = SourceHealth(
            source_type="reddit",
            source_key="python",
            last_check_at=datetime.now().isoformat(),
            is_healthy=False,
        )
        db.add(health2)

        with pytest.raises(Exception):
            db.commit()

    def test_health_reset_on_success(self, db: Session):
        """Should reset failures on successful check."""
        health = SourceHealth(
            source_type="reddit",
            source_key="golang",
            last_check_at=datetime.now().isoformat(),
            consecutive_failures=2,
            is_healthy=False,
        )
        db.add(health)
        db.commit()

        # Simulate successful check
        health.consecutive_failures = 0
        health.consecutive_successes = 1
        health.is_healthy = True
        health.last_success_at = datetime.now().isoformat()
        db.commit()

        assert health.consecutive_failures == 0
        assert health.is_healthy is True

    def test_health_optional_fields(self, db: Session):
        """Should allow optional fields to be null."""
        health = SourceHealth(
            source_type="hackernews",
            source_key="hn",
            last_check_at=datetime.now().isoformat(),
            # Optional fields not provided
        )
        db.add(health)
        db.commit()

        assert health.last_success_at is None
        assert health.last_failure_at is None
        assert health.failure_reason is None
        assert health.response_time_ms is None
        assert health.articles_found is None


class TestSourceContributionModel:
    """Tests for SourceContribution model."""

    def test_create_contribution_record(self, db: Session):
        """Should track source contributions to newsletter."""
        from src.web.services.user_service import create_user
        from src.web.services.newsletter_service import create_pending_newsletter

        user = create_user(db, first_name="TestUser")
        newsletter = create_pending_newsletter(db, user.id, date.today())

        contribution = SourceContribution(
            newsletter_id=newsletter.id,
            source_type="reddit",
            source_key="rust",
            articles_collected=23,
            articles_included=10,
            collected_at=datetime.now().isoformat(),
        )
        db.add(contribution)
        db.commit()

        assert contribution.id is not None
        assert contribution.newsletter_id == newsletter.id

    def test_contribution_cascade_delete(self, db: Session):
        """Should cascade delete when newsletter deleted."""
        from src.web.services.user_service import create_user
        from src.web.services.newsletter_service import (
            create_pending_newsletter,
            delete_newsletter,
        )

        user = create_user(db, first_name="CascadeTest")
        newsletter = create_pending_newsletter(db, user.id, date.today())

        contribution = SourceContribution(
            newsletter_id=newsletter.id,
            source_type="reddit",
            source_key="golang",
            articles_collected=5,
            articles_included=3,
            collected_at=datetime.now().isoformat(),
        )
        db.add(contribution)
        db.commit()

        contribution_id = contribution.id

        # Delete newsletter
        delete_newsletter(db, newsletter.id)

        # Contribution should be deleted
        deleted = (
            db.query(SourceContribution)
            .filter(SourceContribution.id == contribution_id)
            .first()
        )
        assert deleted is None

    def test_contribution_multiple_sources(self, db: Session):
        """Should track multiple sources per newsletter."""
        from src.web.services.user_service import create_user
        from src.web.services.newsletter_service import create_pending_newsletter

        user = create_user(db, first_name="MultiSource")
        newsletter = create_pending_newsletter(db, user.id, date.today())

        contrib1 = SourceContribution(
            newsletter_id=newsletter.id,
            source_type="reddit",
            source_key="rust",
            articles_collected=10,
            articles_included=5,
            collected_at=datetime.now().isoformat(),
        )
        contrib2 = SourceContribution(
            newsletter_id=newsletter.id,
            source_type="rss",
            source_key="this_week_in_rust",
            articles_collected=8,
            articles_included=4,
            collected_at=datetime.now().isoformat(),
        )
        db.add_all([contrib1, contrib2])
        db.commit()

        # Query all contributions for this newsletter
        contributions = (
            db.query(SourceContribution)
            .filter(SourceContribution.newsletter_id == newsletter.id)
            .all()
        )
        assert len(contributions) == 2

    def test_contribution_default_values(self, db: Session):
        """Should use default values for articles counts."""
        from src.web.services.user_service import create_user
        from src.web.services.newsletter_service import create_pending_newsletter

        user = create_user(db, first_name="DefaultTest")
        newsletter = create_pending_newsletter(db, user.id, date.today())

        contribution = SourceContribution(
            newsletter_id=newsletter.id,
            source_type="hackernews",
            source_key="hn",
            collected_at=datetime.now().isoformat(),
            # articles_collected and articles_included not provided
        )
        db.add(contribution)
        db.commit()

        assert contribution.articles_collected == 0
        assert contribution.articles_included == 0
