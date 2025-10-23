"""
Tier 1 source service for News Llama.

Manages dynamic Tier 1 sources: add, query, coverage stats, health updates.
Tier 1 sources are auto-populated via weekly discovery job.
"""

from sqlalchemy.orm import Session
from datetime import datetime
import json
import logging
from typing import List, Dict

from src.web.models import Tier1Source

logger = logging.getLogger(__name__)


def add_tier1_source(
    db: Session,
    source_type: str,
    source_key: str,
    interests: List[str],
    quality_score: float,
    discovered_via: str,
    source_url: str = None,
    description: str = None,
    avg_posts_per_day: float = None,
    domain_age_years: int = None,
) -> Tier1Source:
    """
    Add source to Tier 1 or update if exists.

    Args:
        db: Database session
        source_type: 'reddit', 'rss', 'hackernews'
        source_key: Source identifier
        interests: List of interest names
        quality_score: 0.0-1.0 quality score
        discovered_via: 'list_mining', 'direct_search', 'manual'
        source_url: Optional URL for RSS feeds
        description: Human-readable description
        avg_posts_per_day: Average activity level
        domain_age_years: Domain age for quality scoring

    Returns:
        Tier1Source entry
    """
    now = datetime.now().isoformat()

    # Check if already exists
    existing = (
        db.query(Tier1Source)
        .filter(
            Tier1Source.source_type == source_type, Tier1Source.source_key == source_key
        )
        .first()
    )

    if existing:
        # Update interests (merge with existing)
        existing_interests = json.loads(existing.interests)
        merged_interests = list(set(existing_interests + interests))
        existing.interests = json.dumps(merged_interests)
        existing.quality_score = quality_score
        existing.last_health_check = now
        existing.discovered_via = discovered_via  # Update to latest
        if description:
            existing.description = description
        if avg_posts_per_day:
            existing.avg_posts_per_day = avg_posts_per_day
        db.commit()
        logger.info(f"Updated Tier 1 source {source_type}:{source_key}")
        return existing

    # Create new Tier 1 source
    source = Tier1Source(
        source_type=source_type,
        source_key=source_key,
        source_url=source_url,
        description=description,
        interests=json.dumps(interests),
        quality_score=quality_score,
        discovered_at=now,
        discovered_via=discovered_via,
        last_health_check=now,
        is_healthy=True,
        avg_posts_per_day=avg_posts_per_day,
        domain_age_years=domain_age_years,
    )
    db.add(source)
    db.commit()

    logger.info(
        f"Added Tier 1 source {source_type}:{source_key} "
        f"(score: {quality_score}, interests: {interests})"
    )
    return source


def get_sources_for_interests(
    db: Session, user_interests: List[str], only_healthy: bool = True
) -> List[Tier1Source]:
    """
    Get Tier 1 sources matching user interests.

    Args:
        db: Database session
        user_interests: List of interest names
        only_healthy: Only return healthy sources (default True)

    Returns:
        List of matching Tier1Source objects
    """
    query = db.query(Tier1Source)

    if only_healthy:
        query = query.filter(Tier1Source.is_healthy == True)

    all_sources = query.all()

    # Filter by interests (JSON array contains any of user interests)
    matching = []
    for source in all_sources:
        source_interests = json.loads(source.interests)
        if any(interest in source_interests for interest in user_interests):
            matching.append(source)

    logger.debug(
        f"Found {len(matching)} Tier 1 sources for {len(user_interests)} interests"
    )
    return matching


def get_coverage_stats(db: Session, user_interests: List[str]) -> Dict:
    """
    Calculate Tier 1 coverage for user interests.

    Args:
        db: Database session
        user_interests: List of interest names

    Returns:
        Dict with coverage stats
    """
    tier1_sources = get_sources_for_interests(db, user_interests, only_healthy=True)

    # Which interests are covered?
    covered = set()
    for source in tier1_sources:
        source_interests = json.loads(source.interests)
        for interest in user_interests:
            if interest in source_interests:
                covered.add(interest)

    missing = set(user_interests) - covered
    coverage_pct = (len(covered) / len(user_interests) * 100) if user_interests else 0

    return {
        "total_interests": len(user_interests),
        "covered_interests": len(covered),
        "missing_interests": len(missing),
        "coverage_percentage": coverage_pct,
        "covered": list(covered),
        "missing": list(missing),
        "tier1_source_count": len(tier1_sources),
    }


def mark_source_unhealthy(db: Session, source_id: int, reason: str):
    """Mark Tier 1 source as unhealthy."""
    source = db.query(Tier1Source).filter(Tier1Source.id == source_id).first()
    if source:
        source.is_healthy = False
        source.last_health_check = datetime.now().isoformat()
        db.commit()
        logger.warning(
            f"Marked Tier 1 source {source.source_key} unhealthy (reason: {reason})"
        )


def mark_source_healthy(db: Session, source_id: int):
    """Mark Tier 1 source as healthy (resurrection)."""
    source = db.query(Tier1Source).filter(Tier1Source.id == source_id).first()
    if source:
        source.is_healthy = True
        source.last_health_check = datetime.now().isoformat()
        db.commit()
        logger.info(f"Resurrected Tier 1 source {source.source_key}")


def get_all_tier1_sources(db: Session, only_healthy: bool = False) -> List[Tier1Source]:
    """Get all Tier 1 sources."""
    query = db.query(Tier1Source)
    if only_healthy:
        query = query.filter(Tier1Source.is_healthy == True)
    return query.all()


def get_tier1_stats(db: Session) -> Dict:
    """Get Tier 1 statistics."""
    all_sources = get_all_tier1_sources(db)
    healthy = [s for s in all_sources if s.is_healthy]

    by_type = {}
    for source in all_sources:
        by_type[source.source_type] = by_type.get(source.source_type, 0) + 1

    return {
        "total": len(all_sources),
        "healthy": len(healthy),
        "unhealthy": len(all_sources) - len(healthy),
        "by_type": by_type,
    }
