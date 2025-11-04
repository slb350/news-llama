"""
Direct search service for News Llama with cache-optimized prompts.

Uses LLM with web search to discover sources for any interest.
"""

import asyncio
import json
import logging
import os
from typing import List, Dict
from urllib.parse import urlparse

from open_agent import TextBlock, Client  # type: ignore
from open_agent.types import AgentOptions  # type: ignore

from src.utils.llm_prompts import LLMPrompts

logger = logging.getLogger(__name__)

# Confidence threshold for accepting discovered sources
CONFIDENCE_THRESHOLD = 0.6


async def search_for_interest(interest: str) -> List[Dict]:
    """
    Search for sources related to an interest using LLM.

    Args:
        interest: Interest name

    Returns:
        List of discovered sources
    """
    try:
        # Call LLM with web search tool
        response = await _call_llm_search(interest)

        # Convert to standard source format
        sources = []
        for source in response.get("sources", []):
            # Filter by confidence
            if source.get("confidence", 0) < CONFIDENCE_THRESHOLD:
                continue

            source_type = _normalize_source_type(source["type"])
            source_key = _extract_source_key(source)

            sources.append(
                {
                    "source_type": source_type,
                    "source_key": source_key,
                    "source_url": source.get("url"),
                    "interests": [interest],
                    "discovered_via": "llm-search",
                    "metadata": {
                        "confidence": source.get("confidence"),
                        "reasoning": source.get("reasoning"),
                        "llm_name": source.get("name"),
                    },
                }
            )

        logger.info(
            f"Discovered {len(sources)} sources for '{interest}' via LLM search"
        )
        return sources

    except Exception as e:
        logger.error(f"Error searching for interest '{interest}': {e}")
        return []


async def search_for_interests(interests: List[str]) -> List[Dict]:
    """
    Search for sources for multiple interests concurrently.

    Args:
        interests: List of interest names

    Returns:
        Deduplicated list of all discovered sources
    """
    tasks = [search_for_interest(interest) for interest in interests]
    results = await asyncio.gather(*tasks)

    # Flatten and deduplicate
    all_sources = []
    for sources in results:
        all_sources.extend(sources)

    return _deduplicate_sources(all_sources)


async def _call_llm_search(interest: str) -> Dict:
    """
    Call LLM with cache-optimized prompts to find sources.

    Uses LLMPrompts utility to construct:
    - Static system prompt (100% cacheable, ~300 tokens)
    - Dynamic user prompt (interest only, ~5-20 tokens)

    This structure enables prompt caching for 95%+ of tokens after first call.

    Args:
        interest: Interest name

    Returns:
        LLM response with discovered sources
    """
    # Get LLM config from environment
    llm_api_url = os.getenv("LLM_API_URL", "http://localhost:8000/v1")
    llm_model = os.getenv("LLM_MODEL", "llama-3.1-8b-instruct")
    llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    llm_timeout = int(os.getenv("LLM_TIMEOUT", "300"))

    # Get cache-optimized prompts from LLMPrompts utility
    system_prompt = LLMPrompts.get_multi_source_discovery_system_prompt()
    user_prompt = LLMPrompts.get_multi_source_discovery_user_prompt(interest)

    options = AgentOptions(
        system_prompt=system_prompt,
        model=llm_model,
        base_url=llm_api_url,
        temperature=llm_temperature,
        max_tokens=llm_max_tokens,
        api_key="not-needed",
        tools=[],
        auto_execute_tools=False,
        timeout=llm_timeout,
        max_turns=1,
    )

    parts: List[str] = []

    try:
        async with asyncio.timeout(llm_timeout):
            client = Client(options)
            await client.query(user_prompt)

            async for block in client.receive_messages():
                if isinstance(block, TextBlock):
                    parts.append(block.text)

            await client.close()
    except asyncio.TimeoutError:
        logger.warning(f"LLM search timed out for interest: {interest}")
        return {"sources": []}

    llm_response = "".join(parts).strip()

    if not llm_response:
        logger.warning(f"Empty LLM response for interest: {interest}")
        return {"sources": []}

    logger.debug(f"LLM response for '{interest}': {llm_response[:200]}...")

    return _parse_llm_response(llm_response)


def _parse_llm_response(response: str) -> Dict:
    """Parse LLM JSON response, handling markdown code blocks."""
    try:
        # Strip markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            lines = lines[1:]  # Remove first line (```json or ```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # Remove last line (```)
            response = "\n".join(lines).strip()

        # Try to find JSON if LLM added text before/after
        if not response.startswith("{"):
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                response = response[start:end]

        return json.loads(response)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        logger.error(f"Response was: {response[:500]}")
        return {"sources": []}


def _normalize_source_type(source_type: str) -> str:
    """Normalize source type from LLM response."""
    type_map = {
        "reddit": "reddit",
        "subreddit": "reddit",
        "rss": "rss",
        "feed": "rss",
        "atom": "rss",
        "website": "rss",
    }
    return type_map.get(source_type.lower(), "rss")


def _extract_source_key(source: Dict) -> str:
    """Extract source key from LLM response."""
    if source["type"].lower() in ["reddit", "subreddit"]:
        # Use subreddit field if provided, otherwise extract from URL or name
        if "subreddit" in source:
            return source["subreddit"]
        url = source.get("url", "")
        if "/r/" in url:
            return url.split("/r/")[1].split("/")[0]
        # Fallback: clean up name
        name = source.get("name", "").replace("r/", "").replace(" ", "")
        return name.lower()
    else:
        # For RSS, use domain as key
        url = source.get("url", "")
        if url:
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "").replace(".", "_")
        # Fallback: use cleaned name
        return source.get("name", "unknown").lower().replace(" ", "_")


def _deduplicate_sources(sources: List[Dict]) -> List[Dict]:
    """Deduplicate sources by (source_type, source_key)."""
    seen = {}
    for source in sources:
        key = (source["source_type"], source["source_key"])
        if key not in seen:
            seen[key] = source
    return list(seen.values())
