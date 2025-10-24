"""
Health check service for source validation.

Checks Reddit, RSS, HackerNews sources for availability and activity.
"""

import asyncio
import time
import logging
from typing import Dict, List
from sqlalchemy.orm import Session

from src.web.models import SourceHealth
from datetime import datetime

logger = logging.getLogger(__name__)


async def check_reddit_health(subreddit: str) -> Dict:
    """
    Health check Reddit subreddit.

    Returns:
        Dict with success, articles_found, response_time_ms, error
    """
    start = time.time()

    try:
        # Use Reddit aggregator to fetch posts
        from src.aggregators.reddit_aggregator import RedditAggregator

        aggregator = RedditAggregator(subreddit_names=[subreddit])
        articles = await aggregator.collect()

        elapsed_ms = int((time.time() - start) * 1000)

        return {
            "success": True,
            "articles_found": len(articles),
            "response_time_ms": elapsed_ms,
            "error": None,
        }

    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        error_str = str(e).lower()

        if "404" in error_str or "not found" in error_str:
            error_type = "404"
        elif "403" in error_str or "forbidden" in error_str:
            error_type = "403"
        elif "redirect" in error_str:
            error_type = "redirect"
        elif "timeout" in error_str:
            error_type = "timeout"
        else:
            error_type = "unknown"

        logger.debug(f"Reddit health check failed for r/{subreddit}: {error_type}")
        return {
            "success": False,
            "articles_found": 0,
            "response_time_ms": elapsed_ms,
            "error": error_type,
        }


async def check_rss_health(
    source_key: str, source_url: str, timeout_seconds: int = 5
) -> Dict:
    """
    Health check RSS feed.

    Returns:
        Dict with success, articles_found, response_time_ms, error
    """
    start = time.time()

    try:
        # Use RSS aggregator to fetch feed
        from src.aggregators.rss_aggregator import RSSAggregator

        aggregator = RSSAggregator(rss_feeds=[{"name": source_key, "url": source_url}])
        articles = await aggregator.collect()

        elapsed_ms = int((time.time() - start) * 1000)

        return {
            "success": True,
            "articles_found": len(articles),
            "response_time_ms": elapsed_ms,
            "error": None,
        }

    except asyncio.TimeoutError:
        elapsed_ms = int((time.time() - start) * 1000)
        logger.debug(f"RSS health check timeout for {source_key}")
        return {
            "success": False,
            "articles_found": 0,
            "response_time_ms": elapsed_ms,
            "error": "timeout",
        }

    except TimeoutError:
        elapsed_ms = int((time.time() - start) * 1000)
        logger.debug(f"RSS health check timeout for {source_key}")
        return {
            "success": False,
            "articles_found": 0,
            "response_time_ms": elapsed_ms,
            "error": "timeout",
        }

    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        error_str = str(e).lower()

        if "404" in error_str or "not found" in error_str:
            error_type = "404"
        elif "403" in error_str or "forbidden" in error_str:
            error_type = "403"
        elif "timeout" in error_str:
            error_type = "timeout"
        else:
            error_type = "unknown"

        logger.debug(f"RSS health check failed for {source_key}: {error_type}")
        return {
            "success": False,
            "articles_found": 0,
            "response_time_ms": elapsed_ms,
            "error": error_type,
        }


async def bulk_health_check(sources: List[Dict]) -> List[Dict]:
    """
    Health check multiple sources concurrently.

    Args:
        sources: List of dicts with source_type, source_key, source_url

    Returns:
        List of health check results
    """
    tasks = []
    source_list = []

    for source in sources:
        if source["source_type"] == "reddit":
            task = check_reddit_health(source["source_key"])
            tasks.append(task)
            source_list.append(source)
        elif source["source_type"] == "rss":
            task = check_rss_health(source["source_key"], source["source_url"])
            tasks.append(task)
            source_list.append(source)
        elif source["source_type"] == "hackernews":
            # HackerNews always healthy
            source_list.append(source)
            # No task, will handle separately

    # Run all tasks concurrently using asyncio.gather
    if tasks:
        health_results = await asyncio.gather(*tasks, return_exceptions=True)
    else:
        health_results = []

    # Build results
    results = []
    task_index = 0
    for source in source_list:
        if source["source_type"] == "hackernews":
            results.append(
                {
                    "source": source,
                    "success": True,
                    "articles_found": -1,  # Unknown
                    "response_time_ms": 0,
                    "error": None,
                }
            )
        else:
            health = health_results[task_index]
            task_index += 1
            # Handle exceptions from gather
            if isinstance(health, Exception):
                results.append(
                    {
                        "source": source,
                        "success": False,
                        "articles_found": 0,
                        "response_time_ms": 0,
                        "error": "exception",
                    }
                )
            else:
                results.append({"source": source, **health})

    return results


async def bulk_health_check_and_update(db: Session, sources: List[Dict]):
    """
    Health check sources and update source_health table.

    Args:
        db: Database session
        sources: List of source dicts
    """
    results = await bulk_health_check(sources)

    for result in results:
        source = result["source"]
        update_health_record(db, source, result)

    logger.info(f"Health checked {len(results)} sources, updated database")


def update_health_record(db: Session, source: Dict, health_result: Dict):
    """Update source_health table with health check result."""
    now = datetime.now().isoformat()

    # Get or create health record
    health = (
        db.query(SourceHealth)
        .filter(
            SourceHealth.source_type == source["source_type"],
            SourceHealth.source_key == source["source_key"],
        )
        .first()
    )

    if not health:
        health = SourceHealth(
            source_type=source["source_type"],
            source_key=source["source_key"],
            last_check_at=now,
        )
        db.add(health)

    # Update with results
    health.last_check_at = now
    health.response_time_ms = health_result["response_time_ms"]
    health.articles_found = health_result["articles_found"]

    if health_result["success"]:
        health.last_success_at = now
        health.consecutive_successes = (health.consecutive_successes or 0) + 1
        health.consecutive_failures = 0
        health.is_healthy = True
        health.failure_reason = None
    else:
        health.last_failure_at = now
        health.consecutive_failures = (health.consecutive_failures or 0) + 1
        health.consecutive_successes = 0
        health.failure_reason = health_result["error"]

        # Mark unhealthy if 3+ consecutive failures
        if health.consecutive_failures >= 3:
            health.is_healthy = False

    db.commit()
