"""
Dynamic aggregator for LLM-discovered sources
"""


from src.aggregators.base import BaseAggregator
from src.aggregators.reddit_aggregator import RedditAggregator
from src.aggregators.rss_aggregator import RSSAggregator
from src.utils.config import DiscoveredSource
from src.utils.logger import logger
from src.utils.models import Article


class DynamicAggregator(BaseAggregator):
    """Aggregator that handles dynamically discovered sources"""

    def __init__(self, config, discovered_sources: list[DiscoveredSource]):
        super().__init__(config)
        self.discovered_sources = discovered_sources
        self.delegate_aggregators = {
            "rss": RSSAggregator(config),
            "reddit": RedditAggregator(config),
        }

    async def collect(self) -> list[Article]:
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

    def _group_sources_by_type(self) -> dict[str, list[DiscoveredSource]]:
        """Group discovered sources by their type"""
        grouped = {}
        for source in self.discovered_sources:
            if source.source_type not in grouped:
                grouped[source.source_type] = []
            grouped[source.source_type].append(source)
        return grouped

    async def _collect_from_source_type(
        self, source_type: str, sources: list[DiscoveredSource]
    ) -> list[Article]:
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
            logger.warning("Web search sources skipped: no search backend is implemented")
            return []
        else:
            logger.warning(f"Unknown source type: {source_type}")
            return []

    async def _collect_from_rss_sources(
        self, sources: list[DiscoveredSource]
    ) -> list[Article]:
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

    async def _collect_from_reddit_sources(
        self, sources: list[DiscoveredSource]
    ) -> list[Article]:
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
        self, sources: list[DiscoveredSource]
    ) -> list[Article]:
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
