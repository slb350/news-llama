"""
Discovery metrics service for News Llama.

Tracks and reports on autonomous discovery system performance.
"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict

from src.web.models import Tier1Source, SourceBlacklist, DiscoveredSource

logger = logging.getLogger(__name__)


def get_tier1_stats(db: Session) -> Dict:
    """Get Tier 1 source statistics.

    Returns:
        Dictionary with total, healthy, by_type, and avg_quality_score
    """
    total = db.query(Tier1Source).count()
    healthy = db.query(Tier1Source).filter(Tier1Source.is_healthy == True).count()

    # By type
    by_type = {}
    type_counts = (
        db.query(Tier1Source.source_type, func.count(Tier1Source.id))
        .group_by(Tier1Source.source_type)
        .all()
    )

    for source_type, count in type_counts:
        by_type[source_type] = count

    # Average quality score
    avg_quality = db.query(func.avg(Tier1Source.quality_score)).scalar() or 0.0

    return {
        "total": total,
        "healthy": healthy,
        "by_type": by_type,
        "avg_quality_score": float(avg_quality),
    }


def get_blacklist_stats(db: Session) -> Dict:
    """Get blacklist statistics.

    Returns:
        Dictionary with total, by_type, and by_reason breakdown
    """
    total = db.query(SourceBlacklist).count()

    # By type
    by_type = {}
    type_counts = (
        db.query(SourceBlacklist.source_type, func.count(SourceBlacklist.id))
        .group_by(SourceBlacklist.source_type)
        .all()
    )

    for source_type, count in type_counts:
        by_type[source_type] = count

    # By reason
    by_reason = {}
    reason_counts = (
        db.query(SourceBlacklist.blacklisted_reason, func.count(SourceBlacklist.id))
        .group_by(SourceBlacklist.blacklisted_reason)
        .all()
    )

    for reason, count in reason_counts:
        by_reason[reason] = count

    return {"total": total, "by_type": by_type, "by_reason": by_reason}


def get_discovery_stats(db: Session) -> Dict:
    """Get discovery source statistics.

    Returns:
        Dictionary with total, promoted, promotion_rate, and by_method breakdown
    """
    total = db.query(DiscoveredSource).count()
    promoted = (
        db.query(DiscoveredSource)
        .filter(DiscoveredSource.promoted_to_tier1 == True)
        .count()
    )

    # By discovery method
    by_method = {}
    method_counts = (
        db.query(DiscoveredSource.discovered_via, func.count(DiscoveredSource.id))
        .group_by(DiscoveredSource.discovered_via)
        .all()
    )

    for method, count in method_counts:
        by_method[method] = count

    return {
        "total": total,
        "promoted": promoted,
        "promotion_rate": (promoted / total * 100) if total > 0 else 0,
        "by_method": by_method,
    }


def get_all_metrics(db: Session) -> Dict:
    """Get all discovery system metrics.

    Combines Tier 1, blacklist, and discovery stats into a single response.

    Returns:
        Dictionary with tier1, blacklist, and discovered sections
    """
    return {
        "tier1": get_tier1_stats(db),
        "blacklist": get_blacklist_stats(db),
        "discovered": get_discovery_stats(db),
    }
