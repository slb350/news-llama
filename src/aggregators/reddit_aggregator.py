"""
Reddit aggregator using asyncpraw
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
import asyncpraw

from src.aggregators.base import BaseAggregator
from src.utils.models import Article, SourceType
from src.utils.logger import logger
from src.utils.image_cache import is_image_url, is_video_url, download_and_cache_image


class RedditAggregator(BaseAggregator):
    """Aggregates content from Reddit using async API with lazy initialization"""

    def __init__(self, config):
        super().__init__(config)
        self.reddit = None
        self._client_initialized = False
        self._initialization_failed = False

    async def _ensure_reddit_client(self):
        """
        Lazy initialization of Reddit client.

        Only creates asyncpraw.Reddit() when actually needed (inside async context).
        This prevents "no event loop" errors when instantiated in sync code or background threads.
        """
        # Already initialized or failed
        if self._client_initialized or self._initialization_failed:
            return

        try:
            creds = self.config.social_media
            user_agent = creds.reddit_user_agent or "news-llama/1.0"

            if (
                creds.reddit_client_id
                and creds.reddit_client_secret
                and creds.reddit_username
                and creds.reddit_password
            ):
                # Script auth
                self.reddit = asyncpraw.Reddit(
                    client_id=creds.reddit_client_id,
                    client_secret=creds.reddit_client_secret,
                    user_agent=user_agent,
                    username=creds.reddit_username,
                    password=creds.reddit_password,
                )
                logger.info(
                    "Reddit client configured with asyncpraw script credentials"
                )
                self._client_initialized = True
            elif creds.reddit_client_id and creds.reddit_client_secret:
                # Read-only app
                self.reddit = asyncpraw.Reddit(
                    client_id=creds.reddit_client_id,
                    client_secret=creds.reddit_client_secret,
                    user_agent=user_agent,
                )
                logger.info("Reddit client configured with asyncpraw in read-only mode")
                self._client_initialized = True
            else:
                logger.warning(
                    "Reddit credentials not set; disabling Reddit aggregation"
                )
                self.reddit = None
                self._initialization_failed = True
        except Exception as e:
            logger.warning(f"Reddit client initialization failed: {e}")
            self.reddit = None
            self._initialization_failed = True

    async def collect(self) -> List[Article]:
        """Collect posts from configured subreddits"""
        # Lazy initialize client (only happens once, inside async context)
        await self._ensure_reddit_client()

        if not self.reddit:
            logger.warning("Reddit client not configured, skipping Reddit aggregation")
            return []

        try:
            articles = []

            for subreddit_config in self.config.sources.get("reddit", []):
                try:
                    posts = await self._collect_from_subreddit(subreddit_config)
                    articles.extend(posts)
                    logger.info(
                        f"Collected {len(posts)} posts from r/{subreddit_config['subreddit']}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error collecting from subreddit r/{subreddit_config['subreddit']}: {e}"
                    )

            return articles
        finally:
            # Note: Don't close reddit client here, it may be reused by search_reddit
            pass

    async def close(self):
        """Close the Reddit client session"""
        if self.reddit:
            await self.reddit.close()

    async def search_reddit(
        self, query: str, category: str, limit: int = 50
    ) -> List[Article]:
        """Search all of Reddit for posts matching a query with progressive time filter fallback"""
        # Lazy initialize client (only happens once, inside async context)
        await self._ensure_reddit_client()

        if not self.reddit:
            logger.warning("Reddit client not configured, skipping Reddit search")
            return []

        try:
            # Progressive time filters: try month -> year -> all time
            time_filters = ["month", "year", "all"]

            for time_filter in time_filters:
                logger.info(f"Searching Reddit for: {query} (time: {time_filter})")

                articles = []
                subreddit = await self.reddit.subreddit("all")

                # Build search parameters
                search_params = {"limit": limit, "time_filter": time_filter}

                async for submission in subreddit.search(query, **search_params):
                    try:
                        article = await self._parse_submission(submission, category)
                        if article and self._is_valid_article(article):
                            articles.append(article)
                    except Exception as e:
                        logger.warning(
                            f"Error parsing search result for '{query}': {e}"
                        )

                # If we found articles, return them
                if articles:
                    logger.info(
                        f"Found {len(articles)} posts for query '{query}' using time_filter '{time_filter}'"
                    )
                    return articles
                else:
                    logger.info(
                        f"Found 0 posts for query '{query}' with time_filter '{time_filter}', trying broader filter"
                    )

            # If we exhausted all time filters without finding anything
            logger.info(f"Found 0 posts for query '{query}' across all time filters")
            return []

        except Exception as e:
            logger.error(f"Error searching Reddit for '{query}': {e}")
            return []

    async def _collect_from_subreddit(self, config: dict) -> List[Article]:
        """Collect posts from a specific subreddit"""
        subreddit_name = config["subreddit"]
        category = config["category"]
        limit = config.get("limit", 50)

        subreddit = await self.reddit.subreddit(subreddit_name)

        articles = []
        # Get top posts from last 24 hours
        async for submission in subreddit.top(time_filter="day", limit=limit):
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

        # Extract image/media info
        image_url, is_gallery, gallery_count, is_video = await self._extract_media_info(submission)

        # Cache the image locally if we have one
        local_image_path = None
        if image_url and not is_video:
            local_image_path = await download_and_cache_image(image_url)

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
            local_image_path=local_image_path,
            is_gallery=is_gallery,
            gallery_count=gallery_count,
            is_video=is_video,
            metadata={
                "score": submission.score,
                "num_comments": submission.num_comments,
                "upvote_ratio": getattr(submission, "upvote_ratio", 0),
                "is_self_post": submission.is_self,
                "flair": submission.link_flair_text,
            },
        )

    async def _extract_media_info(
        self, submission
    ) -> Tuple[Optional[str], bool, int, bool]:
        """
        Extract media information from a Reddit submission.

        Returns: (image_url, is_gallery, gallery_count, is_video)
        """
        image_url = None
        is_gallery = False
        gallery_count = 0
        is_video = False

        # Check if it's a video link (redgifs, v.redd.it, etc.)
        if hasattr(submission, "url") and submission.url:
            if is_video_url(submission.url):
                is_video = True
                return (submission.url, False, 0, True)

        # Check for Reddit galleries (multiple images)
        if getattr(submission, "is_gallery", False):
            is_gallery = True
            # Get gallery data
            gallery_data = getattr(submission, "gallery_data", None)
            media_metadata = getattr(submission, "media_metadata", None)

            if gallery_data and media_metadata:
                items = gallery_data.get("items", [])
                gallery_count = len(items)

                # Get first image from gallery
                if items:
                    first_id = items[0].get("media_id")
                    if first_id and first_id in media_metadata:
                        media = media_metadata[first_id]
                        # Try to get the best quality source
                        if "s" in media:
                            source = media["s"]
                            image_url = source.get("u") or source.get("gif")
                            if image_url:
                                # Clean up URL (Reddit uses HTML entities)
                                image_url = image_url.replace("&amp;", "&")

        # Check for direct image URL (i.redd.it, imgur, etc.)
        if not image_url and hasattr(submission, "url") and submission.url:
            if is_image_url(submission.url):
                image_url = submission.url

        # Fall back to preview images
        if not image_url:
            if hasattr(submission, "preview") and submission.preview:
                images = submission.preview.get("images", [])
                if images:
                    source = images[0].get("source", {})
                    image_url = source.get("url")
                    if image_url:
                        image_url = image_url.replace("&amp;", "&")

        return (image_url, is_gallery, gallery_count, is_video)

    def _is_valid_article(self, article: Article) -> bool:
        """Validate Reddit post meets quality criteria"""
        # Skip posts with very low scores (could be spam)
        score_threshold = 1
        if article.metadata.get("score", 0) < score_threshold:
            return False

        # For link posts, just check title length (content is just URL)
        # For self posts, check combined length
        if article.metadata.get("is_self_post"):
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
