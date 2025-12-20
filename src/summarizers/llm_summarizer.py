"""
LLM-based summarizer using open-agent-sdk with cache-optimized prompts
"""

import asyncio
import json
from typing import List
from datetime import datetime

from open_agent import TextBlock  # type: ignore
from open_agent.types import AgentOptions  # type: ignore
from open_agent import client as oa_client  # type: ignore

from src.utils.models import ProcessedArticle, SummarizedArticle
from src.utils.logger import logger


class LLMSummarizer:
    """Generates AI-powered summaries using local LLM"""

    def __init__(self, config):
        self.config = config
        self.llm_config = config.llm

    async def summarize_batch(
        self, articles: List[ProcessedArticle]
    ) -> List[SummarizedArticle]:
        """Summarize a batch of articles"""
        if not articles:
            return []

        logger.info(f"Starting LLM summarization for {len(articles)} articles")

        # Process articles in batches to avoid overwhelming the LLM
        batch_size = 2
        summarized_articles = []

        for i in range(0, len(articles), batch_size):
            batch = articles[i : i + batch_size]

            # Process batch concurrently
            tasks = [self.summarize_article(article) for article in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, SummarizedArticle):
                    summarized_articles.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error in batch summarization: {result}")

        logger.info(f"Generated summaries for {len(summarized_articles)} articles")
        return summarized_articles

    async def summarize_article(self, article: ProcessedArticle) -> SummarizedArticle:
        """Generate summary for a single article using cache-optimized prompts"""
        try:
            # Call LLM via open-agent-sdk with cache-optimized prompts
            summary, key_points, importance_score = await self._summarize_via_llm(
                article
            )

            return SummarizedArticle(
                title=article.title,
                content=article.content,
                url=article.url,
                source=article.source,
                source_type=article.source_type,
                category=article.category,
                author=article.author,
                published_at=article.published_at,
                metadata=article.metadata,
                image_url=article.image_url,
                summary=article.summary,
                sentiment_score=article.sentiment_score,
                word_count=article.word_count,
                reading_time_minutes=article.reading_time_minutes,
                keywords=article.keywords,
                is_duplicate=article.is_duplicate,
                duplicate_similarity=article.duplicate_similarity,
                ai_summary=summary,
                key_points=key_points,
                importance_score=importance_score,
            )

        except Exception as e:
            logger.error(f"Error summarizing article '{article.title}': {e}")
            # Return article with basic summary if LLM fails
            return SummarizedArticle(
                **article.dict(),
                ai_summary=f"Summary unavailable: {str(e)}",
                key_points=[],
                importance_score=0.0,
            )

    async def _summarize_via_llm(self, article: ProcessedArticle) -> tuple:
        """
        Call open-agent-sdk with short system prompt to avoid ROCm caching issues.

        NOTE: Reverted from cache-optimized prompts due to ROCm/AMD GPU memory issues.
        Long system prompts trigger prompt caching which causes memory allocation errors.
        """
        # Short system prompt to avoid triggering prompt caching issues
        system_prompt = (
            "You are a precise news summarization assistant. "
            "Always return valid JSON exactly matching the requested schema and nothing else."
        )

        # Create user prompt with all instructions embedded
        user_prompt = f"""Summarize this news article and return ONLY valid JSON.

Title: {article.title}
Source: {article.source}
Category: {article.category}
Published: {article.published_at}

Content:
{article.content[:20000]}

REQUIRED OUTPUT FORMAT (respond with ONLY this JSON, nothing else):
{{
  "summary": "Your 4-6 sentence detailed summary here",
  "key_points": [
    "First detailed key point with context",
    "Second detailed key point with context",
    "Third detailed key point with context",
    "Fourth detailed key point with context",
    "Fifth detailed key point with context"
  ],
  "importance_score": 0.7
}}

REQUIREMENTS:
- summary: 4-6 sentences capturing the main story with important context and details (150-300 words minimum)
- key_points: EXACTLY 5-7 detailed bullet points (REQUIRED - must not be empty). Each point should be 1-2 sentences providing specific details, not just brief phrases.
- importance_score: number between 0.1-1.0 where:
  * 0.1-0.3 = Minor news, low relevance
  * 0.4-0.6 = Moderate importance, worth reading
  * 0.7-0.9 = Significant news, high importance
  * 0.9-1.0 = Major breaking news, critical

CRITICAL:
- Return ONLY the JSON object, no other text
- NO markdown code fences (no ```json``` tags)
- NO explanations before or after the JSON
- ALL three fields (summary, key_points, importance_score) are REQUIRED
- key_points must be an array with 3-5 strings, NEVER empty
- Ensure proper JSON syntax: escaped quotes, no trailing commas
- Complete the entire JSON object before hitting token limit
"""

        options = AgentOptions(
            system_prompt=system_prompt,
            model=self.llm_config.model,
            base_url=self.llm_config.api_url,
            temperature=self.llm_config.temperature,
            max_tokens=self.llm_config.max_tokens,
            api_key="not-needed",
            timeout=self.llm_config.timeout,
        )

        text_parts: List[str] = []

        # Wrap with asyncio timeout for additional safety
        try:
            async with asyncio.timeout(self.llm_config.timeout):
                async for msg in oa_client.query(user_prompt, options):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            text_parts.append(block.text)
        except asyncio.TimeoutError:
            logger.warning(
                f"LLM summarization timed out after {self.llm_config.timeout}s"
            )
            return "Summary timed out", [], 0.0

        raw_text = "".join(text_parts).strip()
        try:
            data = json.loads(raw_text)
            summary = data.get("summary") or raw_text
            key_points = data.get("key_points") or []
            importance = data.get("importance_score") or 0.5

            # Validate that we got the required fields
            if not summary or not key_points or importance == 0.5:
                logger.warning(
                    f"LLM response missing fields for '{article.title[:50]}': "
                    f"summary={bool(summary)}, key_points={len(key_points)}, importance={importance}"
                )
        except json.JSONDecodeError as e:
            # Log the parsing error with context
            logger.warning(
                f"JSON parse error for '{article.title[:50]}': {e}. "
                f"Raw response: {raw_text[:200]}..."
            )
            # Fallback: use raw text as summary with empty key_points (will be filtered)
            summary, key_points, importance = raw_text, [], 0.5

        return summary, key_points, float(importance)
