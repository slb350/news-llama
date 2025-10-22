"""
LLM-based summarizer using open-agent-sdk
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
        
    async def summarize_batch(self, articles: List[ProcessedArticle]) -> List[SummarizedArticle]:
        """Summarize a batch of articles"""
        if not articles:
            return []
        
        logger.info(f"Starting LLM summarization for {len(articles)} articles")
        
        # Process articles in batches to avoid overwhelming the LLM
        batch_size = 5
        summarized_articles = []
        
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            
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
        """Generate summary for a single article"""
        try:
            # Create summarization prompt
            prompt = self._create_summarization_prompt(article)
            
            # Call LLM via open-agent-sdk and parse JSON response
            summary, key_points, importance_score = await self._summarize_via_llm(prompt)
            
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
                importance_score=importance_score
            )
            
        except Exception as e:
            logger.error(f"Error summarizing article '{article.title}': {e}")
            # Return article with basic summary if LLM fails
            return SummarizedArticle(
                **article.dict(),
                ai_summary=f"Summary unavailable: {str(e)}",
                key_points=[],
                importance_score=0.0
            )
    
    def _create_summarization_prompt(self, article: ProcessedArticle) -> str:
        """Create a prompt for LLM summarization"""
        prompt = f"""
Please analyze and summarize the following news article:

Title: {article.title}
Source: {article.source}
Category: {article.category}
Published: {article.published_at}

Content:
{article.content[:20000]}

Please provide:
1. A concise summary (max 300 words)
2. 3-5 key bullet points
3. An importance score (0.1-1.0) based on relevance and impact

Format your response as JSON:
{{
    "summary": "Your summary here",
    "key_points": ["Point 1", "Point 2", "Point 3"],
    "importance_score": 0.7
}}
"""
        return prompt
    
    async def _summarize_via_llm(self, prompt: str) -> tuple:
        """Call open-agent-sdk and parse JSON with summary, key_points, importance_score"""
        options = AgentOptions(
            system_prompt=(
                "You are a precise news summarization assistant. "
                "Always return valid JSON exactly matching the requested schema and nothing else."
            ),
            model=self.llm_config.model,
            base_url=self.llm_config.api_url,
            temperature=self.llm_config.temperature,
            max_tokens=self.llm_config.max_tokens,
            api_key="not-needed",
            timeout=self.llm_config.timeout
        )

        text_parts: List[str] = []

        # Wrap with asyncio timeout for additional safety
        try:
            async with asyncio.timeout(self.llm_config.timeout):
                async for msg in oa_client.query(prompt, options):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            text_parts.append(block.text)
        except asyncio.TimeoutError:
            logger.warning(f"LLM summarization timed out after {self.llm_config.timeout}s")
            return "Summary timed out", [], 0.0

        raw_text = "".join(text_parts).strip()
        try:
            data = json.loads(raw_text)
            summary = data.get("summary") or raw_text
            key_points = data.get("key_points") or []
            importance = data.get("importance_score") or 0.5
        except json.JSONDecodeError:
            # Fallback: use raw text as summary
            summary, key_points, importance = raw_text, [], 0.5

        return summary, key_points, float(importance)