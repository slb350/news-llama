"""
Blacklist service for News Llama.

Manages source blacklist: add, check, filter, resurrect.
Auto-populated from source failures during health checks.
"""

from sqlalchemy.orm import Session
from datetime import datetime
import logging
from typing import List, Dict

from src.web.models import SourceBlacklist

logger = logging.getLogger(__name__)


def add_to_blacklist(
    db: Session, source_type: str, source_key: str, reason: str, source_url: str = None
) -> SourceBlacklist:
    """
    Add source to blacklist or increment failure count if exists.

    Args:
        db: Database session
        source_type: 'reddit', 'rss', 'hackernews'
        source_key: Source identifier
        reason: Failure reason ('404', 'timeout', '403', 'redirect')
        source_url: Optional URL for RSS feeds

    Returns:
        SourceBlacklist entry
    """
    now = datetime.now().isoformat()

    # Check if already blacklisted
    existing = (
        db.query(SourceBlacklist)
        .filter(
            SourceBlacklist.source_type == source_type,
            SourceBlacklist.source_key == source_key,
        )
        .first()
    )

    if existing:
        # Increment failure count
        existing.failure_count += 1
        existing.last_failure_at = now
        existing.blacklisted_reason = reason  # Update to latest reason
        db.commit()
        logger.info(
            f"Incremented blacklist failure count for {source_type}:{source_key} "
            f"to {existing.failure_count}"
        )
        return existing

    # Create new blacklist entry
    blacklist = SourceBlacklist(
        source_type=source_type,
        source_key=source_key,
        source_url=source_url,
        blacklisted_at=now,
        blacklisted_reason=reason,
        failure_count=1,
        last_failure_at=now,
    )
    db.add(blacklist)
    db.commit()

    logger.warning(f"Blacklisted {source_type}:{source_key} (reason: {reason})")
    return blacklist


def is_blacklisted(db: Session, source_type: str, source_key: str) -> bool:
    """
    Check if source is blacklisted.

    Args:
        db: Database session
        source_type: 'reddit', 'rss', 'hackernews'
        source_key: Source identifier

    Returns:
        True if blacklisted, False otherwise
    """
    entry = (
        db.query(SourceBlacklist)
        .filter(
            SourceBlacklist.source_type == source_type,
            SourceBlacklist.source_key == source_key,
        )
        .first()
    )

    return entry is not None


def filter_blacklisted_sources(db: Session, sources: List[Dict]) -> List[Dict]:
    """
    Filter out blacklisted sources from candidate list.

    Args:
        db: Database session
        sources: List of dicts with 'source_type' and 'source_key' keys

    Returns:
        Filtered list excluding blacklisted sources
    """
    filtered = []
    blacklisted_count = 0

    for source in sources:
        if not is_blacklisted(db, source["source_type"], source["source_key"]):
            filtered.append(source)
        else:
            blacklisted_count += 1

    if blacklisted_count > 0:
        logger.info(f"Filtered out {blacklisted_count} blacklisted sources")

    return filtered


def mark_resurrection_attempt(db: Session, source_type: str, source_key: str):
    """
    Mark that we attempted to resurrect a blacklisted source.

    Used by weekly health check job to track resurrection attempts.
    """
    entry = (
        db.query(SourceBlacklist)
        .filter(
            SourceBlacklist.source_type == source_type,
            SourceBlacklist.source_key == source_key,
        )
        .first()
    )

    if entry:
        entry.last_attempted_resurrection = datetime.now().isoformat()
        db.commit()
        logger.debug(f"Marked resurrection attempt for {source_type}:{source_key}")


def remove_from_blacklist(db: Session, source_type: str, source_key: str):
    """
    Remove source from blacklist (resurrection successful).

    Called when health check passes for previously blacklisted source.
    """
    entry = (
        db.query(SourceBlacklist)
        .filter(
            SourceBlacklist.source_type == source_type,
            SourceBlacklist.source_key == source_key,
        )
        .first()
    )

    if entry:
        db.delete(entry)
        db.commit()
        logger.info(f"Resurrected {source_type}:{source_key} (removed from blacklist)")


def get_blacklist_stats(db: Session) -> Dict:
    """
    Get blacklist statistics.

    Returns:
        Dict with total, by_type, by_reason breakdowns
    """
    all_entries = db.query(SourceBlacklist).all()

    stats = {"total": len(all_entries), "by_type": {}, "by_reason": {}}

    for entry in all_entries:
        # Count by type
        stats["by_type"][entry.source_type] = (
            stats["by_type"].get(entry.source_type, 0) + 1
        )

        # Count by reason
        stats["by_reason"][entry.blacklisted_reason] = (
            stats["by_reason"].get(entry.blacklisted_reason, 0) + 1
        )

    return stats
