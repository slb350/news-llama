"""
RSS feed aggregator
"""
import asyncio
import feedparser
from datetime import datetime, timedelta
from typing import List
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

from src.aggregators.base import BaseAggregator
from src.utils.models import Article, SourceType
from src.utils.logger import logger
from src.utils.security import URLValidator, get_secure_http_client
from src.utils.constants import (
    ProcessingConstants,
    SecurityConstants,
    HTTPConstants
)


class RSSAggregator(BaseAggregator):
    """Aggregates content from RSS feeds"""

    def __init__(self, config):
        super().__init__(config)
        self.http_client = get_secure_http_client()

    async def collect(self) -> List[Article]:
        """Collect articles from configured RSS feeds"""
        articles = []

        # Collect from all feeds concurrently
        tasks = []
        for feed_config in self.config.sources.get('rss', []):
            task = self._collect_from_feed(feed_config)
            tasks.append(task)

        # Wait for all feeds to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            feed_config = self.config.sources.get('rss', [])[i]
            feed_name = feed_config.get('name', f'Feed {i}')

            if isinstance(result, Exception):
                logger.error(f"Error collecting from RSS feed {feed_name}: {result}")
            elif isinstance(result, list):
                articles.extend(result)
                logger.info(f"Collected {len(result)} articles from {feed_name}")

        return articles
    
    async def _collect_from_feed(self, feed_config: dict) -> List[Article]:
        """Collect articles from a single RSS feed"""
        feed_url = feed_config['url']
        feed_name = feed_config['name']
        category = feed_config['category']

        # Validate and sanitize feed URL
        if not URLValidator.is_valid_url(feed_url):
            logger.error(f"Invalid RSS feed URL: {feed_url}")
            return []

        sanitized_url = URLValidator.sanitize_url(feed_url)
        if not sanitized_url:
            logger.error(f"Could not sanitize RSS feed URL: {feed_url}")
            return []

        # Download RSS feed content securely
        try:
            response = await self.http_client.get(sanitized_url, rate_limit_key='rss')
            if not response:
                logger.error(f"Failed to fetch RSS feed: {feed_name}")
                return []

            feed_content = response.text
        except Exception as e:
            logger.error(f"Error downloading RSS feed {feed_name}: {e}")
            return []

        # Parse RSS feed
        try:
            feed = feedparser.parse(feed_content)

            # Check for feed parsing errors
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"RSS feed parsing warning for {feed_name}: {feed.bozo_exception}")

            if not feed.entries:
                logger.warning(f"No entries found in RSS feed: {feed_name}")
                return []

        except Exception as e:
            logger.error(f"Error parsing RSS feed {feed_name}: {e}")
            return []

        articles = []
        for entry in feed.entries[:ProcessingConstants.MAX_ARTICLES_PER_FEED]:
            try:
                article = await self._parse_entry(entry, feed_name, category, feed_url)
                if article and self._is_valid_article(article):
                    articles.append(article)
            except Exception as e:
                logger.warning(f"Error parsing entry from {feed_name}: {e}")

        return articles
    
    async def _parse_entry(self, entry, feed_name: str, category: str, source_feed_url: str) -> Article:
        """Parse RSS entry into Article model"""
        # Validate entry title
        if not hasattr(entry, 'title') or not entry.title:
            logger.debug("Skipping entry without title")
            return None

        # Validate entry link
        if not hasattr(entry, 'link') or not entry.link:
            logger.debug("Skipping entry without link")
            return None

        # Validate and sanitize article URL
        if not URLValidator.is_valid_url(entry.link):
            logger.warning(f"Invalid article URL in RSS feed: {entry.link}")
            return None

        sanitized_url = URLValidator.sanitize_url(entry.link)
        if not sanitized_url:
            logger.warning(f"Could not sanitize article URL: {entry.link}")
            return None

        # Extract publication date
        published_at = datetime.now()
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                published_at = datetime(*entry.published_parsed[:6])
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid published date in RSS entry: {e}")
                published_at = datetime.now()
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            try:
                published_at = datetime(*entry.updated_parsed[:6])
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid updated date in RSS entry: {e}")
                published_at = datetime.now()

        # Skip if too old
        max_age_hours = self.config.processing.max_article_age
        if published_at < datetime.now() - timedelta(hours=max_age_hours):
            return None

        # Extract content
        content = ""
        if hasattr(entry, 'content') and entry.content:
            content = entry.content[0].value
        elif hasattr(entry, 'summary'):
            content = entry.summary
        elif hasattr(entry, 'description'):
            content = entry.description

        # Clean HTML content
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            content = soup.get_text(strip=True)

        # Extract and validate image URL
        image_url = None
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if hasattr(enclosure, 'type') and enclosure.type.startswith('image/'):
                    if hasattr(enclosure, 'href') and enclosure.href:
                        if URLValidator.is_valid_url(enclosure.href):
                            image_url = URLValidator.sanitize_url(enclosure.href)
                            break
                        else:
                            logger.warning(f"Invalid image URL in RSS entry: {enclosure.href}")

        return Article(
            title=entry.title,
            content=content,
            url=sanitized_url,
            source=feed_name,
            source_type=SourceType.RSS,
            category=category,
            author=getattr(entry, 'author', None),
            published_at=published_at,
            image_url=image_url,
            metadata={
                'feed_url': source_feed_url,
                'tags': [tag.term for tag in getattr(entry, 'tags', [])],
                'raw_link': entry.link  # Keep original for debugging
            }
        )
    
    def _is_valid_article(self, article: Article) -> bool:
        """Validate article meets quality criteria"""
        # Use constants from the new constants file
        min_title_length = ProcessingConstants.MIN_ARTICLE_TITLE_LENGTH
        min_content_length = self.config.processing.min_article_length or ProcessingConstants.MIN_ARTICLE_CONTENT_LENGTH

        # Check title and content length
        if len(article.title) < min_title_length or len(article.content) < min_content_length:
            return False

        # Check for spam and malicious content indicators
        spam_keywords = SecurityConstants.SPAM_KEYWORDS
        title_lower = article.title.lower()
        content_lower = article.content.lower()

        if any(keyword in title_lower or keyword in content_lower for keyword in spam_keywords):
            logger.debug(f"Filtered spam article: {article.title}")
            return False

        # Additional content quality checks
        # Check for excessive capitalization (possible clickbait)
        if sum(1 for c in article.title if c.isupper()) > len(article.title) * 0.5:
            logger.debug(f"Filtered excessive caps title: {article.title}")
            return False

        # Check for very short sentences (possible gibberish)
        sentences = article.content.split('.')
        if any(len(s.strip()) < 5 for s in sentences if s.strip()):
            logger.debug(f"Filtered article with very short sentences: {article.title}")
            return False

        return True