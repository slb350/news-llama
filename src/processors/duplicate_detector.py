"""
Duplicate detection using similarity analysis
"""
import re
from collections import defaultdict
from datetime import UTC
from functools import lru_cache

from src.utils.constants import ProcessingConstants
from src.utils.logger import logger
from src.utils.models import ProcessedArticle


class DuplicateDetector:
    """Detects and removes duplicate articles"""
    
    def __init__(self, config):
        self.config = config
        self.threshold = config.processing.duplicate_threshold or ProcessingConstants.DEFAULT_SIMILARITY_THRESHOLD

    @staticmethod
    def _normalize_datetime(dt):
        """Normalize datetime to timezone-aware UTC for comparison"""
        if dt is None:
            return dt
        # If timezone-naive, assume UTC
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            return dt.replace(tzinfo=UTC)
        return dt
    
    def deduplicate(self, articles: list[ProcessedArticle]) -> list[ProcessedArticle]:
        """Remove duplicate articles from the list"""
        if not articles:
            return []
        
        logger.info(f"Starting deduplication with threshold {self.threshold}")
        
        # Group by category for more efficient comparison
        articles_by_category = defaultdict(list)
        for article in articles:
            articles_by_category[article.category].append(article)
        
        unique_articles = []
        duplicates_found = 0
        
        for category, category_articles in articles_by_category.items():
            unique_in_category, dup_count = self._deduplicate_category(category_articles)
            unique_articles.extend(unique_in_category)
            duplicates_found += dup_count
        
        logger.info(f"Removed {duplicates_found} duplicates, kept {len(unique_articles)} unique articles")
        
        return unique_articles
    
    def _deduplicate_category(self, articles: list[ProcessedArticle]) -> tuple[list[ProcessedArticle], int]:
        """Deduplicate articles within a specific category"""
        if len(articles) <= 1:
            return articles, 0

        # Sort by published time (newest first) - normalize datetimes for comparison
        articles.sort(key=lambda x: self._normalize_datetime(x.published_at), reverse=True)
        
        unique_articles = []
        duplicates_found = 0
        
        for current_article in articles:
            is_duplicate = False
            
            # Check against already accepted unique articles
            for unique_article in unique_articles:
                similarity = self._calculate_similarity(current_article, unique_article)
                
                if similarity >= self.threshold:
                    is_duplicate = True
                    current_article.is_duplicate = True
                    current_article.duplicate_similarity = similarity
                    duplicates_found += 1
                    break
            
            if not is_duplicate:
                unique_articles.append(current_article)
        
        return unique_articles, duplicates_found
    
    def _calculate_similarity(self, article1: ProcessedArticle, article2: ProcessedArticle) -> float:
        """Dice overlap of content words, or of title words when either article has no content.

        The same URL is always a duplicate. A shared domain adds nothing, since one site publishes many
        different stories.
        """
        if str(article1.url) == str(article2.url):
            return 1.0

        snippet_length = ProcessingConstants.CONTENT_SNIPPET_LENGTH
        content1 = _content_words(article1.content[:snippet_length])
        content2 = _content_words(article2.content[:snippet_length])
        if content1 and content2:
            return _dice(content1, content2)
        return _dice(_content_words(article1.title), _content_words(article2.title))


# Function words that carry no topic, so two unrelated articles do not match on them.
_STOPWORDS = frozenset(
    ["a", "an", "the", "and", "or", "of", "in", "on", "to", "for", "with", "is", "are", "was", "were", "be", "been", "this", "that", "these", "those", "it", "its", "as", "at", "by", "from", "has", "have", "had", "can", "could", "will", "would", "about", "new"]
)


# Cached because every article is compared against every kept article in its category.
@lru_cache(maxsize=4096)
def _content_words(text: str) -> frozenset:
    return frozenset(w for w in re.findall(r"[a-z0-9%$]+", text.lower()) if w not in _STOPWORDS)


def _dice(words1: frozenset, words2: frozenset) -> float:
    if not words1 or not words2:
        return 0.0
    return 2 * len(words1 & words2) / (len(words1) + len(words2))
