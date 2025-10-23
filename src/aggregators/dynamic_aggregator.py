"""
Dynamic aggregator for LLM-discovered sources
"""

from typing import List, Dict
from datetime import datetime

from src.aggregators.base import BaseAggregator
from src.aggregators.rss_aggregator import RSSAggregator
from src.aggregators.twitter_aggregator import TwitterAggregator
from src.aggregators.reddit_aggregator import RedditAggregator
from src.utils.models import Article, SourceType
from src.utils.config import DiscoveredSource
from src.utils.logger import logger


class DynamicAggregator(BaseAggregator):
    """Aggregator that handles dynamically discovered sources"""

    def __init__(self, config, discovered_sources: List[DiscoveredSource]):
        super().__init__(config)
        self.discovered_sources = discovered_sources
        self.delegate_aggregators = {
            "rss": RSSAggregator(config),
            # 'twitter': TwitterAggregator(config),  # Disabled: placeholder returns fake tweets
            "reddit": RedditAggregator(config),
        }

    async def collect(self) -> List[Article]:
        """Collect articles from discovered sources"""
        articles = []

        try:
            # Group sources by type
            sources_by_type = self._group_sources_by_type()

            # Collect from each source type
            for source_type, sources in sources_by_type.items():
                try:
                    type_articles = await self._collect_from_source_type(
                        source_type, sources
                    )
                    articles.extend(type_articles)
                    logger.info(
                        f"Collected {len(type_articles)} articles from {source_type} discovered sources"
                    )
                except Exception as e:
                    logger.error(
                        f"Error collecting from {source_type} discovered sources: {e}"
                    )

            return articles
        finally:
            # Close any open aggregator sessions
            if "reddit" in self.delegate_aggregators:
                await self.delegate_aggregators["reddit"].close()

    def _group_sources_by_type(self) -> Dict[str, List[DiscoveredSource]]:
        """Group discovered sources by their type"""
        grouped = {}
        for source in self.discovered_sources:
            if source.source_type not in grouped:
                grouped[source.source_type] = []
            grouped[source.source_type].append(source)
        return grouped

    async def _collect_from_source_type(
        self, source_type: str, sources: List[DiscoveredSource]
    ) -> List[Article]:
        """Collect articles from a specific source type"""
        if source_type == "rss":
            return await self._collect_from_rss_sources(sources)
        elif source_type == "twitter":
            logger.warning("Twitter sources skipped: placeholder implementation")
            return []  # Disabled: placeholder returns fake tweets
        elif source_type == "reddit":
            return await self._collect_from_reddit_sources(sources)
        elif source_type == "reddit_search":
            return await self._collect_from_reddit_search(sources)
        elif source_type == "web_search":
            return await self._collect_from_web_search(sources)
        else:
            logger.warning(f"Unknown source type: {source_type}")
            return []

    async def _collect_from_rss_sources(
        self, sources: List[DiscoveredSource]
    ) -> List[Article]:
        """Collect from RSS sources"""
        articles = []

        for source in sources:
            if not source.url:
                continue

            # Create temporary RSS config
            temp_config = {
                "url": source.url,
                "name": source.name,
                "category": source.category,
            }

            try:
                # Use RSS aggregator to collect from this source
                rss_aggregator = RSSAggregator(self.config)
                feed_articles = await rss_aggregator._collect_from_feed(temp_config)
                articles.extend(feed_articles)
            except Exception as e:
                logger.warning(f"Error collecting from RSS source {source.name}: {e}")

        return articles

    async def _collect_from_twitter_sources(
        self, sources: List[DiscoveredSource]
    ) -> List[Article]:
        """Collect from Twitter sources"""
        articles = []

        for source in sources:
            if not source.username:
                continue

            # Create temporary Twitter config
            temp_config = {"username": source.username, "category": source.category}

            try:
                # Use Twitter aggregator to collect from this user
                twitter_aggregator = TwitterAggregator(self.config)
                tweets = await twitter_aggregator._collect_from_user(temp_config)
                articles.extend(tweets)
            except Exception as e:
                logger.warning(
                    f"Error collecting from Twitter source {source.name}: {e}"
                )

        return articles

    async def _collect_from_reddit_sources(
        self, sources: List[DiscoveredSource]
    ) -> List[Article]:
        """Collect from Reddit sources"""
        articles = []

        reddit_aggregator = self.delegate_aggregators.get("reddit")
        if not reddit_aggregator:
            logger.warning("Reddit aggregator not available")
            return articles

        # Ensure Reddit client is initialized (lazy initialization)
        await reddit_aggregator._ensure_reddit_client()

        for source in sources:
            if not source.subreddit:
                continue

            # Create temporary Reddit config
            temp_config = {
                "subreddit": source.subreddit,
                "category": source.category,
                "limit": 25,  # Reduced for discovered sources
            }

            try:
                # Use shared Reddit aggregator instance
                posts = await reddit_aggregator._collect_from_subreddit(temp_config)
                articles.extend(posts)
                logger.info(f"Collected {len(posts)} posts from r/{source.subreddit}")
            except Exception as e:
                logger.warning(
                    f"Error collecting from Reddit source {source.name}: {e}"
                )

        return articles

    async def _collect_from_reddit_search(
        self, sources: List[DiscoveredSource]
    ) -> List[Article]:
        """Collect from Reddit search queries"""
        articles = []

        reddit_aggregator = self.delegate_aggregators.get("reddit")
        if not reddit_aggregator:
            logger.warning("Reddit aggregator not available for search")
            return articles

        # Ensure Reddit client is initialized (lazy initialization)
        await reddit_aggregator._ensure_reddit_client()

        logger.info(f"Processing {len(sources)} Reddit search sources")
        for source in sources:
            try:
                # Extract the search query from the source category
                query = source.category
                logger.info(f"Searching Reddit for query: '{query}'")
                # Search Reddit for this query
                search_results = await reddit_aggregator.search_reddit(
                    query, source.category, limit=25
                )
                articles.extend(search_results)
                logger.info(
                    f"Got {len(search_results)} results from Reddit search for '{query}'"
                )
            except Exception as e:
                logger.warning(f"Error searching Reddit for '{source.category}': {e}")

        return articles

    async def _collect_from_web_search(
        self, sources: List[DiscoveredSource]
    ) -> List[Article]:
        """Collect from web search sources"""
        articles = []

        for source in sources:
            if source.source_type != "web_search":
                continue

            try:
                search_articles = await self._perform_web_search(source)
                articles.extend(search_articles)
            except Exception as e:
                logger.warning(f"Error performing web search for {source.name}: {e}")

        return articles

    async def _perform_web_search(self, source: DiscoveredSource) -> List[Article]:
        """Perform web search for a specific topic"""
        # TODO: Implement actual web search using API (Google, DuckDuckGo, etc.)
        # For now, return placeholder articles

        search_query = f"{source.category} news {source.name}"

        # Placeholder implementation - replace with actual search API
        placeholder_articles = [
            Article(
                title=f"Latest {source.category} News - {search_query}",
                content=f"This is a placeholder article from web search for {search_query}. Replace with actual search results.",
                url=f"https://example.com/search/{search_query.replace(' ', '-')}",
                source=f"Web Search: {source.name}",
                source_type=SourceType.WEB_SEARCH,
                category=source.category,
                published_at=datetime.now(),
                metadata={
                    "search_query": search_query,
                    "discovery_reason": source.reason,
                    "confidence_score": source.confidence_score,
                },
            )
        ]

        return placeholder_articles

    def _is_valid_article(self, article: Article) -> bool:
        """Validate article meets quality criteria"""
        # Use the same validation as base aggregators
        min_length = self.config.processing.min_article_length

        # Check title and content length
        if len(article.title) < 10 or len(article.content) < min_length:
            return False

        # Check for spam indicators
        spam_keywords = ["advertisement", "sponsored", "promoted"]
        title_lower = article.title.lower()
        content_lower = article.content.lower()

        if any(
            keyword in title_lower or keyword in content_lower
            for keyword in spam_keywords
        ):
            return False

        # Additional validation for discovered sources based on confidence
        if "confidence_score" in article.metadata:
            min_confidence = 0.3  # Minimum confidence threshold
            if article.metadata["confidence_score"] < min_confidence:
                return False

        return True
