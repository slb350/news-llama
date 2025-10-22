"""
Hacker News aggregator
"""
import asyncio
from datetime import datetime, timedelta
from typing import List
import requests
from newspaper import Article as NewspaperArticle

from src.aggregators.base import BaseAggregator
from src.utils.models import Article, SourceType
from src.utils.logger import logger


class HackerNewsAggregator(BaseAggregator):
    """Aggregates content from Hacker News"""
    
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    async def collect(self) -> List[Article]:
        """Collect stories from Hacker News"""
        if not self.config.sources.get('hackernews', {}).get('enabled', False):
            return []

        articles = []

        categories = self.config.sources.get('hackernews', {}).get('categories', ['top'])
        limit = self.config.sources.get('hackernews', {}).get('limit', 50)

        for category in categories:
            try:
                stories = await self._collect_stories(category, limit)
                articles.extend(stories)
                logger.info(f"Collected {len(stories)} stories from Hacker News {category}")
            except Exception as e:
                logger.error(f"Error collecting Hacker News {category} stories: {e}")

        # Fetch actual content for top 5 highest-scored articles
        articles_with_content = await self._fetch_content_for_top_articles(articles, top_n=5)

        return articles_with_content
    
    async def _collect_stories(self, category: str, limit: int) -> List[Article]:
        """Collect stories from a specific Hacker News category"""
        # Get story IDs for the category
        if category == 'top':
            story_ids_url = f"{self.BASE_URL}/topstories.json"
        elif category == 'best':
            story_ids_url = f"{self.BASE_URL}/beststories.json"
        elif category == 'new':
            story_ids_url = f"{self.BASE_URL}/newstories.json"
        else:
            story_ids_url = f"{self.BASE_URL}/topstories.json"
        
        response = requests.get(story_ids_url)
        story_ids = response.json()[:limit]
        
        articles = []
        # Fetch story details concurrently
        tasks = [self._fetch_story(story_id) for story_id in story_ids]
        stories = await asyncio.gather(*tasks, return_exceptions=True)
        
        for story in stories:
            if isinstance(story, Article) and self._is_valid_article(story):
                articles.append(story)
        
        return articles
    
    async def _fetch_story(self, story_id: int) -> Article:
        """Fetch individual story details"""
        story_url = f"{self.BASE_URL}/item/{story_id}.json"
        
        try:
            response = requests.get(story_url)
            story_data = response.json()
            
            if not story_data or story_data.get('type') != 'story':
                return None
            
            # Skip if too old
            if 'time' in story_data:
                post_time = datetime.fromtimestamp(story_data['time'])
                max_age_hours = self.config.processing.max_article_age
                if post_time < datetime.now() - timedelta(hours=max_age_hours):
                    return None
            else:
                post_time = datetime.now()
            
            # Determine category based on title content (simple heuristic)
            title = story_data.get('title', '')
            category = self._categorize_story(title)
            
            return Article(
                title=title,
                content=story_data.get('text', ''),
                url=story_data.get('url', f"https://news.ycombinator.com/item?id={story_id}"),
                source="Hacker News",
                source_type=SourceType.HACKERNEWS,
                category=category,
                author=story_data.get('by', ''),
                published_at=post_time,
                metadata={
                    'score': story_data.get('score', 0),
                    'descendants': story_data.get('descendants', 0),  # Number of comments
                    'story_id': story_id
                }
            )
        
        except Exception as e:
            logger.warning(f"Error fetching Hacker News story {story_id}: {e}")
            return None
    
    def _categorize_story(self, title: str) -> str:
        """Simple categorization based on title keywords"""
        title_lower = title.lower()
        
        # Technology keywords
        tech_keywords = ['ai', 'machine learning', 'python', 'programming', 'code', 'tech', 'startup']
        if any(keyword in title_lower for keyword in tech_keywords):
            return 'technology'
        
        # Programming keywords
        prog_keywords = ['github', 'open source', 'software', 'development', 'api']
        if any(keyword in title_lower for keyword in prog_keywords):
            return 'programming'
        
        # Default to general
        return 'general'
    
    def _is_valid_article(self, article: Article) -> bool:
        """Validate Hacker News story meets quality criteria"""
        # Skip stories with very low scores
        score_threshold = 1
        if article.metadata.get('score', 0) < score_threshold:
            return False

        # Check minimum title length
        if len(article.title) < 10:
            return False

        # Skip job postings (could be configurable)
        job_keywords = ['hiring', 'looking for', 'job', 'career']
        title_lower = article.title.lower()
        if any(keyword in title_lower for keyword in job_keywords):
            return False

        return True

    async def _fetch_content_for_top_articles(self, articles: List[Article], top_n: int = 5) -> List[Article]:
        """
        Fetch actual article content for top N highest-scored HN posts

        Args:
            articles: List of HN articles (with minimal content)
            top_n: Number of top articles to fetch content for

        Returns:
            List of articles with actual content fetched for top articles
        """
        if not articles:
            return articles

        # Sort by score (highest first)
        sorted_articles = sorted(articles, key=lambda x: x.metadata.get('score', 0), reverse=True)

        # Split into top and rest
        top_articles = sorted_articles[:top_n]
        rest_articles = sorted_articles[top_n:]

        logger.info(f"Fetching full content for top {len(top_articles)} HN articles...")

        # Fetch content for top articles
        tasks = [self._fetch_article_content(article) for article in top_articles]
        enriched_articles = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine enriched top articles with the rest
        result = []
        for article in enriched_articles:
            if isinstance(article, Article):
                result.append(article)

        # Add the rest (without fetching content - they'll be filtered later anyway)
        result.extend(rest_articles)

        logger.info(f"Successfully enriched {len([a for a in enriched_articles if isinstance(a, Article)])} HN articles with content")

        return result

    async def _fetch_article_content(self, article: Article) -> Article:
        """
        Fetch actual article content from the URL using newspaper3k

        Args:
            article: Article with URL but no content

        Returns:
            Article with fetched content, or original if fetch fails
        """
        # Skip if it's an HN discussion (no external URL)
        if 'news.ycombinator.com' in article.url:
            logger.debug(f"Skipping HN discussion: {article.title}")
            return article

        try:
            # Use newspaper3k to fetch and parse article
            news_article = NewspaperArticle(article.url)
            news_article.download()
            news_article.parse()

            # Update article with fetched content
            if news_article.text:
                article.content = news_article.text
                logger.info(f"Fetched content for: {article.title[:50]}... ({len(news_article.text)} chars)")
            else:
                logger.warning(f"No content extracted from: {article.url}")

        except Exception as e:
            logger.warning(f"Failed to fetch content from {article.url}: {e}")

        return article