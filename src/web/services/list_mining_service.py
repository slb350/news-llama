"""
List mining service for News Llama.

Mines curated lists for high-quality source discovery:
- GitHub awesome-lists
- Reddit wiki pages
"""

import aiohttp
import re
import logging
from typing import List, Dict
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


async def mine_github_list(url: str, interest: str) -> List[Dict]:
    """
    Mine a GitHub awesome-list for sources.

    Args:
        url: GitHub awesome-list URL
        interest: Interest name

    Returns:
        List of discovered sources
    """
    sources = []
    list_name = url.split("/")[-1]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}: {response.status}")
                    return []

                content = await response.text()

        # Extract RSS/Atom feeds
        rss_pattern = r"\[([^\]]+)\]\((https?://[^\)]+\.(?:xml|rss|atom|feed))\)"
        for match in re.finditer(rss_pattern, content):
            title, feed_url = match.groups()
            sources.append(
                {
                    "source_type": "rss",
                    "source_key": _generate_rss_key(feed_url),
                    "source_url": feed_url,
                    "interests": [interest],
                    "discovered_via": list_name,
                    "metadata": {"title": title, "list_url": url},
                }
            )

        # Extract subreddit links
        reddit_pattern = r"(?:reddit\.com/)?r/([a-zA-Z0-9_]+)"
        for match in re.finditer(reddit_pattern, content):
            subreddit = match.group(1)
            sources.append(
                {
                    "source_type": "reddit",
                    "source_key": subreddit,
                    "interests": [interest],
                    "discovered_via": list_name,
                    "metadata": {"list_url": url},
                }
            )

        logger.info(f"Mined {len(sources)} sources from {list_name}")
        return sources

    except Exception as e:
        logger.error(f"Error mining {url}: {e}")
        return []


async def mine_reddit_wiki(url: str, interest: str) -> List[Dict]:
    """
    Mine a Reddit wiki page for related subreddits.

    Args:
        url: Reddit wiki URL
        interest: Interest name

    Returns:
        List of discovered subreddits
    """
    sources = []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}: {response.status}")
                    return []

                content = await response.text()

        # Extract subreddit mentions
        reddit_pattern = r"/r/([a-zA-Z0-9_]+)"
        for match in re.finditer(reddit_pattern, content):
            subreddit = match.group(1)
            sources.append(
                {
                    "source_type": "reddit",
                    "source_key": subreddit,
                    "interests": [interest],
                    "discovered_via": "reddit-wiki",
                    "metadata": {"wiki_url": url},
                }
            )

        logger.info(f"Mined {len(sources)} subreddits from wiki")
        return sources

    except Exception as e:
        logger.error(f"Error mining wiki {url}: {e}")
        return []


async def mine_all_lists_for_interest(interest: str, known_lists: Dict) -> List[Dict]:
    """
    Mine all known lists for a given interest.

    Args:
        interest: Interest name
        known_lists: Dict with 'github' and 'reddit_wikis' keys

    Returns:
        Deduplicated list of sources
    """
    all_sources = []

    # Mine GitHub lists
    for github_url in known_lists.get("github", []):
        sources = await mine_github_list(github_url, interest)
        all_sources.extend(sources)

    # Mine Reddit wikis
    for wiki_url in known_lists.get("reddit_wikis", []):
        sources = await mine_reddit_wiki(wiki_url, interest)
        all_sources.extend(sources)

    # Deduplicate
    return deduplicate_sources(all_sources)


def deduplicate_sources(sources: List[Dict]) -> List[Dict]:
    """
    Deduplicate sources by (source_type, source_key).

    Keeps first occurrence, merges metadata.
    """
    seen = {}

    for source in sources:
        key = (source["source_type"], source["source_key"])
        if key not in seen:
            seen[key] = source
        else:
            # Merge discovered_via
            existing = seen[key]
            if isinstance(existing.get("discovered_via"), str):
                existing["discovered_via"] = [existing["discovered_via"]]
            if isinstance(source.get("discovered_via"), str):
                existing["discovered_via"].append(source["discovered_via"])

    return list(seen.values())


def _generate_rss_key(url: str) -> str:
    """Generate a unique key for RSS feed from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    # Use domain + first path segment
    path_parts = parsed.path.strip("/").split("/")
    key = f"{domain}_{path_parts[0]}" if path_parts else domain
    return key.replace(".", "_").replace("-", "_")
