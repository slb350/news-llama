"""
Main entry point for News Llama
"""

import asyncio
import argparse
import logging
from typing import Dict, List

from src.aggregators.rss_aggregator import RSSAggregator
from src.aggregators.twitter_aggregator import TwitterAggregator
from src.aggregators.reddit_aggregator import RedditAggregator

# from src.aggregators.hackernews_aggregator import HackerNewsAggregator  # Disabled: empty content
from src.aggregators.dynamic_aggregator import DynamicAggregator
from src.processors.content_processor import ContentProcessor
from src.processors.duplicate_detector import DuplicateDetector
from src.processors.source_discovery import SourceDiscoveryEngine
from src.summarizers.llm_summarizer import LLMSummarizer
from src.generators.html_generator import HTMLGenerator
from src.generators.json_generator import JSONGenerator
from src.generators.rss_generator import RSSGenerator
from src.utils.config import Config
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


class NewsLlama:
    """Main news curation engine"""

    def __init__(
        self,
        config_path: str = None,
        user_interests: List[str] = None,
        pre_discovered_sources: List = None,
    ):
        # Skip default sources if user interests or pre-discovered sources are specified
        skip_defaults = bool(user_interests or pre_discovered_sources)
        self.config = Config(config_path, skip_default_sources=skip_defaults)
        self.user_interests = user_interests or []
        # Propagate to config so generators can read it
        self.config.user_interests = self.user_interests

        # Store pre-discovered sources if provided
        if pre_discovered_sources:
            self.config.discovered_sources = pre_discovered_sources
            self.source_discovery = None  # Skip discovery engine
        # Initialize source discovery if user interests are provided (and not pre-discovered)
        elif self.user_interests and self.config.source_discovery.enabled:
            self.source_discovery = SourceDiscoveryEngine(self.config)
        else:
            self.source_discovery = None

        # Initialize aggregators
        self.aggregators = self._setup_aggregators()

        # Initialize processors
        self.content_processor = ContentProcessor(self.config)
        self.duplicate_detector = DuplicateDetector(self.config)

        # Initialize summarizer
        self.summarizer = LLMSummarizer(self.config)

        # Initialize generators
        self.generators = self._setup_generators()

    async def initialize(self) -> None:
        """Initialize dynamic components"""
        if self.config.discovered_sources:
            # Already have pre-discovered sources, just create aggregator
            discovered_sources = self.config.discovered_sources
            self.aggregators["dynamic"] = DynamicAggregator(
                self.config, discovered_sources
            )
            logger.info(
                f"Using pre-discovered sources: {len(discovered_sources)} sources"
            )
        elif self.source_discovery and self.user_interests:
            logger.info(f"Discovering sources for interests: {self.user_interests}")
            discovered_sources = await self.source_discovery.discover_sources(
                self.user_interests
            )
            self.config.discovered_sources = discovered_sources

            # Add dynamic aggregator for discovered sources
            self.aggregators["dynamic"] = DynamicAggregator(
                self.config, discovered_sources
            )

            logger.info(
                f"Added dynamic aggregator with {len(discovered_sources)} discovered sources"
            )

    def _setup_aggregators(self) -> Dict[str, object]:
        """Initialize content aggregators"""
        aggregators = {
            "rss": RSSAggregator(self.config),
            # HackerNews disabled: produces empty content links, newspaper3k extraction fails
            # 'hackernews': HackerNewsAggregator(self.config),
        }

        # Conditionally enable Reddit if credentials are present
        try:
            if self.config.social_media.validate_reddit_credentials():
                aggregators["reddit"] = RedditAggregator(self.config)
            else:
                logger.info("Reddit disabled: missing credentials")
        except Exception:
            logger.info("Reddit disabled: credential validation failed")

        # Conditionally enable Twitter only if all creds present
        try:
            if self.config.social_media.validate_twitter_credentials():
                aggregators["twitter"] = TwitterAggregator(self.config)
            else:
                logger.info("Twitter disabled: missing credentials")
        except Exception:
            logger.info("Twitter disabled: credential validation failed")

        return aggregators

    def _setup_generators(self) -> Dict[str, object]:
        """Initialize output generators"""
        return {
            "html": HTMLGenerator(self.config),
            "json": JSONGenerator(self.config),
            "rss": RSSGenerator(self.config),
        }

    def _filter_top_articles(self, articles: List, max_articles: int = 20) -> List:
        """
        Filter to top N articles based on recency and quality signals

        Scoring factors:
        - Recency (newer = better)
        - Word count (more content = better, but HN links with no content = worse)
        - Source reputation (certain sources ranked higher)
        """
        from datetime import datetime, timezone

        scored_articles = []
        now = datetime.now(timezone.utc)

        for article in articles:
            score = 0

            # Recency score (0-10 points): newer articles get more points
            if article.published_at:
                # Normalize datetime to timezone-aware UTC
                pub_at = article.published_at
                if pub_at.tzinfo is None or pub_at.tzinfo.utcoffset(pub_at) is None:
                    pub_at = pub_at.replace(tzinfo=timezone.utc)

                age_hours = (now - pub_at).total_seconds() / 3600
                recency_score = max(
                    0, 10 - (age_hours / 24)
                )  # Linear decay over 10 days
                score += recency_score

            # Content quality score (0-10 points)
            if hasattr(article, "word_count") and article.word_count:
                # Prefer articles with substantial content
                if article.word_count > 500:
                    score += 10
                elif article.word_count > 200:
                    score += 5
                elif article.word_count > 50:
                    score += 2
                # Penalize very short/empty content
                else:
                    score -= 5

            # Source reputation boost
            source_lower = article.source.lower()
            if any(
                trusted in source_lower
                for trusted in ["reddit", "techcrunch", "ars technica", "github"]
            ):
                score += 5

            scored_articles.append((score, article))

        # Sort by score (highest first) and take top N
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        top_articles = [article for _, article in scored_articles[:max_articles]]

        return top_articles

    def _prefilter_articles_for_summarization(self, articles: List) -> List:
        """
        Pre-filter articles to top N per category BEFORE summarization to save LLM time.
        Groups by category, sorts by quality (recency + metadata), and limits to max per category.
        """
        from datetime import datetime, timezone
        from collections import defaultdict

        max_per_category = self.config.output.max_articles_per_category
        logger.info(
            f"Pre-filtering to top {max_per_category} articles per category before summarization"
        )

        # Group articles by category
        by_category = defaultdict(list)
        for article in articles:
            by_category[article.category].append(article)

        # Sort and limit each category
        filtered_articles = []
        for category, cat_articles in by_category.items():
            # Score articles by recency and quality
            scored = []
            now = datetime.now(timezone.utc)

            for article in cat_articles:
                score = 0

                # Recency score (0-10): newer = better
                if article.published_at:
                    pub_at = article.published_at
                    if pub_at.tzinfo is None or pub_at.tzinfo.utcoffset(pub_at) is None:
                        pub_at = pub_at.replace(tzinfo=timezone.utc)
                    age_hours = (now - pub_at).total_seconds() / 3600
                    recency_score = max(
                        0, 10 - (age_hours / 2.4)
                    )  # Linear decay over 24 hours
                    score += recency_score

                # Content quality score (0-10)
                if hasattr(article, "word_count") and article.word_count:
                    if article.word_count > 500:
                        score += 10
                    elif article.word_count > 200:
                        score += 5
                    elif article.word_count > 50:
                        score += 2

                # Reddit metadata score
                if hasattr(article, "metadata") and article.metadata:
                    reddit_score = article.metadata.get("score", 0)
                    # Normalize Reddit score (0-10)
                    score += min(10, reddit_score / 10)

                scored.append((score, article))

            # Sort by score (highest first) and take top N
            scored.sort(key=lambda x: x[0], reverse=True)
            top_articles = [article for _, article in scored[:max_per_category]]
            filtered_articles.extend(top_articles)

            logger.info(
                f"Category '{category}': filtered from {len(cat_articles)} to {len(top_articles)} articles"
            )

        logger.info(
            f"Pre-filtered from {len(articles)} to {len(filtered_articles)} articles total"
        )
        return filtered_articles

    def _filter_valid_summaries(self, articles: List) -> List:
        """
        Filter out articles with failed content extraction or invalid summaries

        Removes articles where:
        - Importance score is too low (< 0.6)
        - Key points list is empty
        - Summary contains failure messages
        """
        valid_articles = []

        for article in articles:
            # Check importance score
            if hasattr(article, "importance_score") and article.importance_score < 0.6:
                logger.debug(
                    f"Filtering out article with low importance score: {article.title[:50]}..."
                )
                continue

            # Check for empty key points
            if hasattr(article, "key_points") and not article.key_points:
                logger.debug(
                    f"Filtering out article with empty key points: {article.title[:50]}..."
                )
                continue

            # Check for failure messages in summary
            if hasattr(article, "ai_summary") and article.ai_summary:
                failure_indicators = [
                    "could not be accessed",
                    "unable to retrieve",
                    "cannot be accessed",
                    "cannot generate",
                    "is unavailable",
                    "failed to extract",
                ]
                if any(
                    indicator in article.ai_summary.lower()
                    for indicator in failure_indicators
                ):
                    logger.debug(
                        f"Filtering out article with failed extraction: {article.title[:50]}..."
                    )
                    continue

            valid_articles.append(article)

        return valid_articles

    async def run(self) -> None:
        """Main execution loop"""
        logger.info("Starting News Llama news curation")

        try:
            # Initialize dynamic components
            await self.initialize()

            # Collect articles from all sources
            all_articles = []
            for name, aggregator in self.aggregators.items():
                try:
                    articles = await aggregator.collect()
                    all_articles.extend(articles)
                    logger.info(f"Collected {len(articles)} articles from {name}")
                except Exception as e:
                    logger.error(f"Error collecting from {name}: {e}")

            logger.info(f"Collected {len(all_articles)} total articles")

            # Process and deduplicate content
            processed_articles = self.content_processor.process(all_articles)
            unique_articles = self.duplicate_detector.deduplicate(processed_articles)

            logger.info(f"Processed {len(unique_articles)} unique articles")

            # Pre-filter to top N per category BEFORE summarization (saves LLM time)
            articles_to_summarize = self._prefilter_articles_for_summarization(
                unique_articles
            )

            # Generate summaries only for pre-filtered articles
            logger.info(
                f"Summarizing {len(articles_to_summarize)} pre-filtered articles"
            )
            summarized_articles = await self.summarizer.summarize_batch(
                articles_to_summarize
            )

            # Filter out articles with failed content extraction
            valid_articles = self._filter_valid_summaries(summarized_articles)
            logger.info(
                f"Filtered to {len(valid_articles)} valid articles (removed {len(summarized_articles) - len(valid_articles)} failed extractions)"
            )

            # Generate outputs
            for format_name, generator in self.generators.items():
                if format_name in self.config.output.formats:
                    logger.info(f"Generating {format_name} output")
                    generator.generate(valid_articles)

            logger.info("News curation completed successfully")

            # Return summary statistics
            return {
                "total_articles": len(all_articles),
                "unique_articles": len(unique_articles),
                "summarized_articles": len(summarized_articles),
                "valid_articles": len(valid_articles),
                "sources_used": list(self.aggregators.keys()),
                "discovered_sources": len(self.config.discovered_sources)
                if hasattr(self.config, "discovered_sources")
                else 0,
            }

        except Exception as e:
            logger.error(f"Error during news curation: {e}")
            raise


async def main(interests: List[str] = None, schedule_mode: bool = False):
    """Main entry point"""
    setup_logging()

    # Use provided interests or defaults
    if not interests:
        interests = ["AI", "technology", "programming"]

    news_llama = NewsLlama(user_interests=interests)

    if schedule_mode:
        # Run in scheduler mode
        from src.utils.scheduler import NewsScheduler

        async def curation_task():
            """Wrapper for scheduled runs"""
            stats = await news_llama.run()
            if stats:
                logger.info(f"Scheduled run stats: {stats}")

        scheduler = NewsScheduler(news_llama.config, curation_task)
        logger.info("Starting in scheduler mode")
        scheduler.run_once_then_schedule()
    else:
        # Run once
        stats = await news_llama.run()

        if stats:
            print(f"\nNews Llama Summary:")
            print(f"   Total articles collected: {stats['total_articles']}")
            print(f"   Unique articles after deduplication: {stats['unique_articles']}")
            print(f"   Articles summarized: {stats['summarized_articles']}")
            print(f"   Valid articles (after filtering): {stats['valid_articles']}")
            print(f"   Sources used: {', '.join(stats['sources_used'])}")
            print(f"   Discovered sources: {stats['discovered_sources']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="News Llama - AI-powered news curation"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run in scheduled mode (uses SCHEDULER_* settings from .env)",
    )
    parser.add_argument(
        "--interests",
        nargs="+",
        help="Your interests (e.g., --interests AI programming rust)",
    )

    args = parser.parse_args()

    asyncio.run(main(interests=args.interests, schedule_mode=args.schedule))
