"""
Unit tests for quality scoring - TDD RED phase.

Tests quality score calculation based on multiple signals.
"""

import pytest
from src.web.services.quality_scoring import (
    calculate_quality_score,
    should_auto_add,
    AUTO_ADD_THRESHOLD,
)


class TestQualityScoring:
    """Tests for quality score calculation."""

    def test_base_score_health_check_passed(self):
        """Should give 0.3 base score if health check passed."""
        source = {
            "health_check_passed": True,
            "discovery_count": 1,
            "domain_age_years": 0,
            "avg_posts_per_day": 0,
            "source_type": "reddit",
        }

        score = calculate_quality_score(source)
        assert score >= 0.3

    def test_zero_score_health_check_failed(self):
        """Should give 0.0 score if health check failed."""
        source = {
            "health_check_passed": False,
            "discovery_count": 5,  # Doesn't matter
            "domain_age_years": 10,
            "source_type": "reddit",
        }

        score = calculate_quality_score(source)
        assert score == 0.0

    def test_multiple_discovery_bonus(self):
        """Should add 0.2-0.4 for multiple discoveries."""
        source = {
            "health_check_passed": True,
            "discovery_count": 3,  # Found by 3 methods
            "source_type": "reddit",
        }

        score = calculate_quality_score(source)
        # Base 0.3 + 0.4 (max for 3 discoveries) = 0.7
        assert score >= 0.7

    def test_domain_age_bonus(self):
        """Should add 0.1-0.2 for established domains."""
        # 1-3 years: +0.1
        source1 = {
            "health_check_passed": True,
            "discovery_count": 1,
            "domain_age_years": 2,
            "source_type": "rss",
        }
        score1 = calculate_quality_score(source1)
        assert score1 >= 0.4  # 0.3 base + 0.1 age

        # 3+ years: +0.2
        source2 = {
            "health_check_passed": True,
            "discovery_count": 1,
            "domain_age_years": 5,
            "source_type": "rss",
        }
        score2 = calculate_quality_score(source2)
        assert score2 >= 0.5  # 0.3 base + 0.2 age

    def test_reddit_activity_bonus(self):
        """Should add 0.2 for active subreddits (>5 posts/day)."""
        source = {
            "health_check_passed": True,
            "discovery_count": 1,
            "source_type": "reddit",
            "avg_posts_per_day": 15.0,
        }

        score = calculate_quality_score(source)
        assert score >= 0.5  # 0.3 base + 0.2 activity

    def test_rss_update_frequency_bonus(self):
        """Should add 0.2 for frequently updated RSS feeds."""
        source = {
            "health_check_passed": True,
            "discovery_count": 1,
            "source_type": "rss",
            "posts_last_30_days": 15,
        }

        score = calculate_quality_score(source)
        assert score >= 0.5  # 0.3 base + 0.2 activity

    def test_awesome_list_bonus(self):
        """Should add 0.2 for sources in high-quality awesome-lists."""
        source = {
            "health_check_passed": True,
            "discovery_count": 1,
            "source_type": "reddit",
            "found_in_awesome_list_with_stars": 5000,
        }

        score = calculate_quality_score(source)
        assert score >= 0.5  # 0.3 base + 0.2 awesome-list

    def test_max_score_capped_at_1(self):
        """Should cap score at 1.0 max."""
        source = {
            "health_check_passed": True,
            "discovery_count": 5,
            "domain_age_years": 10,
            "source_type": "reddit",
            "avg_posts_per_day": 50,
            "found_in_awesome_list_with_stars": 10000,
        }

        score = calculate_quality_score(source)
        assert score <= 1.0

    def test_auto_add_threshold(self):
        """Should auto-add sources with score > 0.8."""
        # High quality source
        source = {
            "health_check_passed": True,
            "discovery_count": 2,
            "domain_age_years": 5,  # >3 years for +0.2
            "source_type": "rss",
            "posts_last_30_days": 20,
        }
        # 0.3 + 0.2 + 0.2 + 0.2 = 0.9

        score = calculate_quality_score(source)
        should_add = should_auto_add(score)

        assert score > 0.8
        assert should_add is True

    def test_auto_add_threshold_edge_case(self):
        """Should not auto-add sources with score exactly at 0.8."""
        # Verify threshold is strictly greater than
        assert should_auto_add(0.8) is False
        assert should_auto_add(0.801) is True
        assert should_auto_add(0.79) is False
