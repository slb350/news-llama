"""
Twitter/X aggregator (placeholder implementation)
"""
from typing import List
from datetime import datetime
from src.aggregators.base import BaseAggregator
from src.utils.models import Article, SourceType
from src.utils.logger import logger


class TwitterAggregator(BaseAggregator):
    """Aggregates content from Twitter/X"""
    
    async def collect(self) -> List[Article]:
        """Collect tweets from configured Twitter accounts"""
        articles = []
        
        for twitter_config in self.config.sources.get('twitter', []):
            try:
                tweets = await self._collect_from_user(twitter_config)
                articles.extend(tweets)
                logger.info(f"Collected {len(tweets)} tweets from @{twitter_config['username']}")
            except Exception as e:
                logger.error(f"Error collecting from Twitter user {twitter_config['username']}: {e}")
        
        return articles
    
    async def _collect_from_user(self, config: dict) -> List[Article]:
        """Collect tweets from a specific Twitter user"""
        # TODO: Implement Twitter API integration using tweepy
        # This is a placeholder implementation
        username = config['username']
        category = config['category']
        
        # Placeholder tweets - replace with actual Twitter API calls
        placeholder_tweets = [
            {
                'text': f"Sample tweet from @{username}",
                'url': f"https://twitter.com/{username}/status/123456789",
                'created_at': "2023-01-01T12:00:00Z"
            }
        ]
        
        articles = []
        for tweet in placeholder_tweets:
            article = Article(
                title=f"Tweet by @{username}",
                content=tweet['text'],
                url=tweet['url'],
                source=f"Twitter @{username}",
                source_type=SourceType.TWITTER,
                category=category,
                author=username,
                published_at=datetime.fromisoformat(tweet['created_at'].replace('Z', '+00:00')),
                metadata={'tweet_id': '123456789'}
            )
            if self._is_valid_article(article):
                articles.append(article)
        
        return articles
    
    def _is_valid_article(self, article: Article) -> bool:
        """Validate tweet meets quality criteria"""
        # Check minimum length
        if len(article.content) < 20:
            return False
        
        # Skip retweets for now (could be configurable)
        if article.content.startswith('RT '):
            return False
        
        return True