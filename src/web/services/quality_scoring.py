"""
Quality scoring for discovered sources.

Scores sources 0.0-1.0 based on multiple signals.
Auto-adds to Tier 1 if score > 0.8.
"""

import logging

logger = logging.getLogger(__name__)

AUTO_ADD_THRESHOLD = 0.8


def calculate_quality_score(source: dict) -> float:
    """
    Calculate quality score for discovered source.

    Args:
        source: Dict with keys:
            - health_check_passed: bool
            - discovery_count: int
            - domain_age_years: int (optional)
            - source_type: str
            - avg_posts_per_day: float (Reddit)
            - posts_last_30_days: int (RSS)
            - found_in_awesome_list_with_stars: int (optional)

    Returns:
        Score 0.0-1.0
    """
    score = 0.0

    # Health check passed (required)
    if not source.get("health_check_passed", False):
        return 0.0

    score += 0.3  # Base score

    # Multiple discovery methods found it
    discovery_count = source.get("discovery_count", 1)
    if discovery_count > 1:
        # +0.2 for 2 discoveries, +0.4 for 3+
        score += 0.2 * min(discovery_count - 1, 2)

    # Established source (domain age)
    domain_age = source.get("domain_age_years", 0)
    if domain_age > 1:
        score += 0.1
    if domain_age > 3:
        score += 0.1  # Total +0.2 for 3+ years

    # Activity level
    if source["source_type"] == "reddit":
        avg_posts = source.get("avg_posts_per_day", 0)
        if avg_posts > 5:
            score += 0.2
    elif source["source_type"] == "rss":
        posts_30d = source.get("posts_last_30_days", 0)
        if posts_30d > 10:
            score += 0.2

    # Found in high-quality awesome-list
    awesome_stars = source.get("found_in_awesome_list_with_stars", 0)
    if awesome_stars > 1000:
        score += 0.2

    return min(score, 1.0)


def should_auto_add(score: float) -> bool:
    """Should source be auto-added to Tier 1?"""
    return score > AUTO_ADD_THRESHOLD
