"""
Tier 1 source integration for NewsLlama wrapper.

Provides interface between web app and Tier 1 source system for fast path generation.
"""

import json
import logging
from datetime import datetime
from typing import List, Tuple, Dict
from sqlalchemy.orm import Session

from src.web.models import Tier1Source, SourceContribution
from src.web.services import tier1_service, blacklist_service
from src.utils.config import DiscoveredSource

logger = logging.getLogger(__name__)

COVERAGE_THRESHOLD = 90.0  # % threshold for using Tier 1 only


def convert_tier1_to_discovered(
    tier1_sources: List[Tier1Source],
) -> List[DiscoveredSource]:
    """
    Convert Tier 1 database sources to DiscoveredSource format for NewsLlama.

    Args:
        tier1_sources: List of Tier1Source models from database

    Returns:
        List of DiscoveredSource objects compatible with NewsLlama
    """
    discovered = []

    for source in tier1_sources:
        # Parse interests JSON
        interests = json.loads(source.interests) if source.interests else []
        category = interests[0] if interests else "General"

        # Build DiscoveredSource based on type
        if source.source_type == "reddit":
            discovered_source = DiscoveredSource(
                name=f"r/{source.source_key}",
                subreddit=source.source_key,
                source_type="reddit",
                category=category,
                confidence_score=source.quality_score or 0.8,
                reason=f"Tier 1 source (quality: {source.quality_score:.2f})",
            )
        elif source.source_type == "rss":
            discovered_source = DiscoveredSource(
                name=source.source_key,
                url=source.source_url,
                source_type="rss",
                category=category,
                confidence_score=source.quality_score or 0.8,
                reason=f"Tier 1 source (quality: {source.quality_score:.2f})",
            )
        elif source.source_type == "twitter":
            discovered_source = DiscoveredSource(
                name=f"@{source.source_key}",
                username=source.source_key,
                source_type="twitter",
                category=category,
                confidence_score=source.quality_score or 0.8,
                reason=f"Tier 1 source (quality: {source.quality_score:.2f})",
            )
        else:
            # Generic fallback
            discovered_source = DiscoveredSource(
                name=source.source_key,
                source_type=source.source_type,
                category=category,
                confidence_score=source.quality_score or 0.8,
                reason=f"Tier 1 source (quality: {source.quality_score:.2f})",
            )

        discovered.append(discovered_source)

    return discovered


def get_sources_with_coverage(
    db: Session, user_interests: List[str]
) -> Tuple[List[Tier1Source], float]:
    """
    Get Tier 1 sources for interests with coverage percentage.

    Returns:
        (sources, coverage_percentage)
    """
    # Get Tier 1 sources
    tier1_sources = tier1_service.get_sources_for_interests(
        db, user_interests, only_healthy=True
    )

    # Calculate coverage
    stats = tier1_service.get_coverage_stats(db, user_interests)
    coverage = stats["coverage_percentage"]

    logger.info(
        f"Tier 1 coverage: {coverage:.1f}% "
        f"({stats['covered_interests']}/{stats['total_interests']} interests, "
        f"{len(tier1_sources)} sources)"
    )

    return tier1_sources, coverage


def get_healthy_tier1_for_interests(
    db: Session, user_interests: List[str]
) -> List[Tier1Source]:
    """
    Get healthy Tier 1 sources for interests.

    Only returns sources marked as healthy.
    """
    return tier1_service.get_sources_for_interests(
        db, user_interests, only_healthy=True
    )


def get_filtered_tier1_sources(
    db: Session, user_interests: List[str]
) -> List[Tier1Source]:
    """
    Get healthy, non-blacklisted Tier 1 sources for interests.

    Filters out blacklisted sources even if they're in Tier 1.
    """
    # Get all healthy Tier 1 sources
    tier1_sources = tier1_service.get_sources_for_interests(
        db, user_interests, only_healthy=True
    )

    # Filter blacklisted
    filtered = []
    for source in tier1_sources:
        if not blacklist_service.is_blacklisted(
            db, source.source_type, source.source_key
        ):
            filtered.append(source)

    blacklisted_count = len(tier1_sources) - len(filtered)
    if blacklisted_count > 0:
        logger.info(f"Filtered {blacklisted_count} blacklisted sources from Tier 1")

    return filtered


def track_source_contributions(
    db: Session, newsletter_id: int, contributions: List[Dict]
):
    """
    Track which sources contributed articles to newsletter.

    Args:
        db: Database session
        newsletter_id: Newsletter ID
        contributions: List of dicts with:
            - source_type
            - source_key
            - articles_collected
            - articles_included
    """
    now = datetime.now().isoformat()

    for contrib in contributions:
        entry = SourceContribution(
            newsletter_id=newsletter_id,
            source_type=contrib["source_type"],
            source_key=contrib["source_key"],
            articles_collected=contrib["articles_collected"],
            articles_included=contrib["articles_included"],
            collected_at=now,
        )
        db.add(entry)

    db.commit()
    logger.debug(
        f"Tracked {len(contributions)} source contributions for newsletter {newsletter_id}"
    )


def extract_contributions_from_stats(stats: Dict) -> List[Dict]:
    """
    Extract source contribution data from NewsLlama stats.

    This is a placeholder that would need to be implemented based on
    actual NewsLlama stats format.
    """
    # TODO: Extract actual contribution data from NewsLlama stats
    # For now, return empty list
    contributions = []

    # In the future, this would parse stats to find:
    # - Which sources were used
    # - How many articles from each
    # - How many made it to final output

    return contributions
