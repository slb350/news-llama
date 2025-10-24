"""
Autonomous discovery service for News Llama.

Orchestrates weekly source discovery:
1. Get all interests (predefined + custom user interests)
2. Mine curated lists
3. Direct LLM search
4. Deduplicate candidates
5. Filter blacklist
6. Health check all
7. Quality score all
8. Auto-promote to Tier 1 if score > 0.8
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict
from sqlalchemy.orm import Session

from src.web.models import DiscoveredSource, UserInterest
from src.web.services import (
    list_mining_service,
    direct_search_service,
    health_check_service,
    quality_scoring,
    tier1_service,
    blacklist_service,
    interest_service,
)

logger = logging.getLogger(__name__)

# Known lists for list mining (expandable)
# Maps interest names to their known GitHub awesome-lists and Reddit wikis
KNOWN_LISTS = {
    "Rust": {
        "github": ["https://github.com/rust-unofficial/awesome-rust"],
        "reddit_wikis": ["https://www.reddit.com/r/rust/wiki/index"],
    },
    "Python": {
        "github": ["https://github.com/vinta/awesome-python"],
        "reddit_wikis": ["https://www.reddit.com/r/Python/wiki/index"],
    },
    "AI & Machine Learning": {
        "github": [
            "https://github.com/josephmisiti/awesome-machine-learning",
            "https://github.com/ChristosChristofidis/awesome-deep-learning",
        ],
        "reddit_wikis": ["https://www.reddit.com/r/MachineLearning/wiki/index"],
    },
    "JavaScript & Web Dev": {
        "github": ["https://github.com/sorrycc/awesome-javascript"],
        "reddit_wikis": ["https://www.reddit.com/r/webdev/wiki/index"],
    },
    "Linux": {
        "github": ["https://github.com/inputsh/awesome-linux"],
        "reddit_wikis": ["https://www.reddit.com/r/linux/wiki/index"],
    },
    "Self-Hosting": {
        "github": ["https://github.com/awesome-selfhosted/awesome-selfhosted"],
        "reddit_wikis": ["https://www.reddit.com/r/selfhosted/wiki/index"],
    },
    "Open Source": {
        "github": ["https://github.com/sindresorhus/awesome"],
        "reddit_wikis": [],
    },
    "Photography": {
        "github": ["https://github.com/ibaaj/awesome-OpenSourcePhotography"],
        "reddit_wikis": ["https://www.reddit.com/r/photography/wiki/index"],
    },
    "Cooking & Recipes": {
        "github": [],
        "reddit_wikis": ["https://www.reddit.com/r/Cooking/wiki/index"],
    },
    "Minecraft": {
        "github": [],
        "reddit_wikis": ["https://www.reddit.com/r/Minecraft/wiki/index"],
    },
}


async def run_weekly_discovery(db: Session, interests: List[str] = None) -> Dict:
    """
    Run weekly autonomous discovery job.

    Args:
        db: Database session
        interests: Optional list of interests (defaults to all)

    Returns:
        Stats dict with discovery results
    """
    logger.info("Starting weekly autonomous discovery job")
    start_time = datetime.now()

    # Get all interests if not provided
    if interests is None:
        interests = _get_all_interests(db)

    logger.info(f"Discovering sources for {len(interests)} interests")

    # Phase 1: List mining
    list_candidates = await _mine_all_lists(interests)
    logger.info(f"List mining found {len(list_candidates)} candidates")

    # Phase 2: Direct search
    search_candidates = await _direct_search(interests)
    logger.info(f"Direct search found {len(search_candidates)} candidates")

    # Phase 3: Deduplicate
    all_candidates = list_mining_service.deduplicate_sources(
        list_candidates + search_candidates
    )
    logger.info(f"Total unique candidates: {len(all_candidates)}")

    # Phase 4: Filter blacklist
    filtered_candidates = blacklist_service.filter_blacklisted_sources(
        db, all_candidates
    )
    logger.info(
        f"After blacklist filter: {len(filtered_candidates)} (removed {len(all_candidates) - len(filtered_candidates)})"
    )

    if not filtered_candidates:
        logger.info("No candidates remaining after blacklist filter")
        return {
            "total_discovered": len(all_candidates),
            "healthy": 0,
            "auto_promoted": 0,
            "duration_seconds": (datetime.now() - start_time).total_seconds(),
            "interests_processed": len(interests),
        }

    # Phase 5: Health check
    health_results = await health_check_service.bulk_health_check(filtered_candidates)
    healthy_candidates = []
    for i, health in enumerate(health_results):
        if health.get("success", False):
            healthy_candidates.append((filtered_candidates[i], health))
    logger.info(f"Healthy sources: {len(healthy_candidates)}")

    # Phase 6: Quality scoring
    scored_candidates = []
    for candidate, health in healthy_candidates:
        # Build quality score input
        score_input = {
            "health_check_passed": True,
            "discovery_count": 1,
            "source_type": candidate["source_type"],
            "avg_posts_per_day": 0,  # Unknown from health check
            "domain_age_years": 0,  # Unknown
        }

        # Add health check data
        if "articles_found" in health:
            score_input["articles_found"] = health["articles_found"]
        if "response_time_ms" in health:
            score_input["response_time_ms"] = health["response_time_ms"]

        # Check if from awesome-list (high quality signal)
        discovered_via = candidate.get("discovered_via", "")
        if "awesome" in discovered_via.lower() or "wiki" in discovered_via.lower():
            # Assume high-quality curated list (5000+ stars for awesome-lists)
            score_input["found_in_awesome_list_with_stars"] = 5000
            # Curated lists typically link to established sources (3+ years)
            score_input["domain_age_years"] = 5
            # If both list mining AND direct search found it, discovery_count = 2
            score_input["discovery_count"] = 2

        # For Reddit: estimate activity from articles_found
        if candidate["source_type"] == "reddit" and "articles_found" in health:
            # Rough estimate: if health check found 50+ articles, likely active (>5/day)
            if health["articles_found"] >= 20:
                score_input["avg_posts_per_day"] = 10.0

        # For RSS: estimate update frequency from articles_found
        if candidate["source_type"] == "rss" and "articles_found" in health:
            # If found 10+ articles, likely updated frequently
            if health["articles_found"] >= 10:
                score_input["posts_last_30_days"] = 15
            # Assume established RSS feeds (3+ years) if they have good content
            if health["articles_found"] >= 5:
                score_input["domain_age_years"] = 5

        # Calculate score
        score = quality_scoring.calculate_quality_score(score_input)
        candidate["quality_score"] = score
        scored_candidates.append(candidate)

    # Phase 7: Auto-promote to Tier 1
    auto_promoted = 0
    for candidate in scored_candidates:
        if quality_scoring.should_auto_add(candidate["quality_score"]):
            try:
                tier1_service.add_tier1_source(
                    db,
                    source_type=candidate["source_type"],
                    source_key=candidate["source_key"],
                    source_url=candidate.get("source_url"),
                    interests=candidate["interests"],
                    quality_score=candidate["quality_score"],
                    discovered_via=candidate["discovered_via"],
                )
                auto_promoted += 1
                logger.info(
                    f"Auto-promoted: {candidate['source_type']}:{candidate['source_key']} (score: {candidate['quality_score']:.2f})"
                )
            except Exception as e:
                logger.warning(f"Failed to promote {candidate['source_key']}: {e}")

    # Phase 8: Log all to discovered_sources table
    _log_discoveries(db, scored_candidates)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    stats = {
        "total_discovered": len(all_candidates),
        "healthy": len(healthy_candidates),
        "auto_promoted": auto_promoted,
        "duration_seconds": duration,
        "interests_processed": len(interests),
    }

    logger.info(f"Discovery complete: {stats}")
    return stats


def _get_all_interests(db: Session) -> List[str]:
    """Get all unique interests (predefined + custom user interests)."""
    # Predefined interests
    predefined = interest_service.get_predefined_interests()

    # Custom user interests
    custom = db.query(UserInterest.interest_name).distinct().all()
    custom = [c[0] for c in custom]

    # Combine and deduplicate
    all_interests = list(set(predefined + custom))
    logger.debug(
        f"Found {len(predefined)} predefined + {len(custom)} custom = {len(all_interests)} total interests"
    )
    return all_interests


async def _mine_all_lists(interests: List[str]) -> List[Dict]:
    """Mine curated lists for all interests."""
    tasks = []
    for interest in interests:
        known_lists = KNOWN_LISTS.get(interest, {"github": [], "reddit_wikis": []})
        if known_lists["github"] or known_lists["reddit_wikis"]:
            tasks.append(
                list_mining_service.mine_all_lists_for_interest(interest, known_lists)
            )

    if not tasks:
        logger.debug("No known lists to mine")
        return []

    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Flatten and filter exceptions
    all_sources = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"List mining failed: {result}")
        elif isinstance(result, list):
            all_sources.extend(result)
    return all_sources


async def _direct_search(interests: List[str]) -> List[Dict]:
    """Direct LLM search for all interests."""
    try:
        return await direct_search_service.search_for_interests(interests)
    except Exception as e:
        logger.error(f"Direct search failed: {e}")
        return []


def _log_discoveries(db: Session, candidates: List[Dict]):
    """Log all discoveries to discovered_sources table."""
    for candidate in candidates:
        try:
            # Check if already exists
            existing = (
                db.query(DiscoveredSource)
                .filter(
                    DiscoveredSource.source_type == candidate["source_type"],
                    DiscoveredSource.source_key == candidate["source_key"],
                )
                .first()
            )

            if existing:
                existing.discovery_count += 1
                existing.quality_score = candidate.get("quality_score")
                existing.health_check_passed = True
                logger.debug(
                    f"Updated discovery count for {candidate['source_key']}: {existing.discovery_count}"
                )
            else:
                # Convert interests list to JSON string
                interests_json = json.dumps(candidate.get("interests", []))
                metadata_json = json.dumps(candidate.get("metadata", {}))

                discovered = DiscoveredSource(
                    source_type=candidate["source_type"],
                    source_key=candidate["source_key"],
                    source_url=candidate.get("source_url"),
                    discovered_at=datetime.now().isoformat(),
                    discovered_via=candidate["discovered_via"],
                    quality_score=candidate.get("quality_score"),
                    health_check_passed=True,
                    interests=interests_json,
                    source_metadata=metadata_json,
                )
                db.add(discovered)
                logger.debug(f"Logged new discovery: {candidate['source_key']}")

        except Exception as e:
            logger.error(
                f"Failed to log discovery for {candidate.get('source_key')}: {e}"
            )

    db.commit()
