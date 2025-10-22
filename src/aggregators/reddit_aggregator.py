"""
Reddit aggregator using asyncpraw
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List
import asyncpraw

from src.aggregators.base import BaseAggregator
from src.utils.models import Article, SourceType
from src.utils.logger import logger


class RedditAggregator(BaseAggregator):
    """Aggregates content from Reddit using async API"""

    def __init__(self, config):
        super().__init__(config)
        self.reddit = None
        self._setup_reddit_client()

    def _setup_reddit_client(self):
        """Setup Reddit API client from config credentials"""
        try:
            creds = self.config.social_media
            user_agent = creds.reddit_user_agent or "news-llama/1.0"

            if creds.reddit_client_id and creds.reddit_client_secret and creds.reddit_username and creds.reddit_password:
                # Script auth
                self.reddit = asyncpraw.Reddit(
                    client_id=creds.reddit_client_id,
                    client_secret=creds.reddit_client_secret,
                    user_agent=user_agent,
                    username=creds.reddit_username,
                    password=creds.reddit_password,
                )
                logger.info("Reddit client configured with asyncpraw script credentials")
            elif creds.reddit_client_id and creds.reddit_client_secret:
                # Read-only app
                self.reddit = asyncpraw.Reddit(
                    client_id=creds.reddit_client_id,
                    client_secret=creds.reddit_client_secret,
                    user_agent=user_agent,
                )
                logger.info("Reddit client configured with asyncpraw in read-only mode")
            else:
                logger.warning("Reddit credentials not set; disabling Reddit aggregation")
                self.reddit = None
        except Exception as e:
            logger.warning(f"Reddit client setup failed: {e}")
            self.reddit = None
    
    async def collect(self) -> List[Article]:
        """Collect posts from configured subreddits"""
        if not self.reddit:
            logger.warning("Reddit client not configured, skipping Reddit aggregation")
            return []

        try:
            articles = []

            for subreddit_config in self.config.sources.get('reddit', []):
                try:
                    posts = await self._collect_from_subreddit(subreddit_config)
                    articles.extend(posts)
                    logger.info(f"Collected {len(posts)} posts from r/{subreddit_config['subreddit']}")
                except Exception as e:
                    logger.error(f"Error collecting from subreddit r/{subreddit_config['subreddit']}: {e}")

            return articles
        finally:
            # Note: Don't close reddit client here, it may be reused by search_reddit
            pass

    async def close(self):
        """Close the Reddit client session"""
        if self.reddit:
            await self.reddit.close()

    async def search_reddit(self, query: str, category: str, limit: int = 50) -> List[Article]:
        """Search all of Reddit for posts matching a query with progressive time filter fallback"""
        if not self.reddit:
            logger.warning("Reddit client not configured, skipping Reddit search")
            return []

        try:
            # Progressive time filters: try month -> year -> all time
            time_filters = ['month', 'year', 'all']

            for time_filter in time_filters:
                logger.info(f"Searching Reddit for: {query} (time: {time_filter})")

                articles = []
                subreddit = await self.reddit.subreddit("all")

                # Build search parameters
                search_params = {
                    'limit': limit,
                    'time_filter': time_filter
                }

                async for submission in subreddit.search(query, **search_params):
                    try:
                        article = await self._parse_submission(submission, category)
                        if article and self._is_valid_article(article):
                            articles.append(article)
                    except Exception as e:
                        logger.warning(f"Error parsing search result for '{query}': {e}")

                # If we found articles, return them
                if articles:
                    logger.info(f"Found {len(articles)} posts for query '{query}' using time_filter '{time_filter}'")
                    return articles
                else:
                    logger.info(f"Found 0 posts for query '{query}' with time_filter '{time_filter}', trying broader filter")

            # If we exhausted all time filters without finding anything
            logger.info(f"Found 0 posts for query '{query}' across all time filters")
            return []

        except Exception as e:
            logger.error(f"Error searching Reddit for '{query}': {e}")
            return []

    async def _collect_from_subreddit(self, config: dict) -> List[Article]:
        """Collect posts from a specific subreddit"""
        subreddit_name = config['subreddit']
        category = config['category']
        limit = config.get('limit', 50)

        subreddit = await self.reddit.subreddit(subreddit_name)

        articles = []
        # Get top posts from last 24 hours
        async for submission in subreddit.top(time_filter='day', limit=limit):
            try:
                article = await self._parse_submission(submission, category)
                if article and self._is_valid_article(article):
                    articles.append(article)
            except Exception as e:
                logger.warning(f"Error parsing submission from r/{subreddit_name}: {e}")

        return articles

    async def _parse_submission(self, submission, category: str) -> Article:
        """Parse Reddit submission into Article model"""
        # Skip if too old
        max_age_hours = self.config.processing.max_article_age
        post_time = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
        if post_time < datetime.now(timezone.utc) - timedelta(hours=max_age_hours):
            return None

        # Extract content (self-text or external URL)
        content = submission.selftext if submission.is_self else (submission.url or "")

        # Extract image URL if available
        image_url = None
        if hasattr(submission, 'preview') and submission.preview:
            images = submission.preview.get('images', [])
            if images:
                image_url = images[0]['source']['url']

        return Article(
            title=submission.title,
            content=content,
            url=f"https://reddit.com{submission.permalink}",
            source=f"Reddit r/{submission.subreddit}",
            source_type=SourceType.REDDIT,
            category=category,
            author=str(submission.author) if submission.author else "deleted",
            published_at=post_time,
            image_url=image_url,
            metadata={
                'score': submission.score,
                'num_comments': submission.num_comments,
                'upvote_ratio': getattr(submission, 'upvote_ratio', 0),
                'is_self_post': submission.is_self,
                'flair': submission.link_flair_text
            }
        )
    
    def _is_valid_article(self, article: Article) -> bool:
        """Validate Reddit post meets quality criteria"""
        # Skip posts with very low scores (could be spam)
        score_threshold = 1
        if article.metadata.get('score', 0) < score_threshold:
            return False

        # For link posts, just check title length (content is just URL)
        # For self posts, check combined length
        if article.metadata.get('is_self_post'):
            # Self post: check full content
            if not article.content.strip():
                return False
            min_length = self.config.processing.min_article_length
            if len(article.title) + len(article.content) < min_length:
                return False
        else:
            # Link post: just check title has reasonable length
            if len(article.title) < 20:
                return False

        return True