"""
Duplicate detection using similarity analysis
"""
from typing import List, Tuple
from difflib import SequenceMatcher
from collections import defaultdict
from datetime import timezone

from src.utils.models import ProcessedArticle
from src.utils.logger import logger
from src.utils.constants import ProcessingConstants


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
            return dt.replace(tzinfo=timezone.utc)
        return dt
    
    def deduplicate(self, articles: List[ProcessedArticle]) -> List[ProcessedArticle]:
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
    
    def _deduplicate_category(self, articles: List[ProcessedArticle]) -> Tuple[List[ProcessedArticle], int]:
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
        """Calculate similarity between two articles"""
        # Title similarity (weighted more heavily)
        title_similarity = SequenceMatcher(None, article1.title.lower(), article2.title.lower()).ratio()
        
        # URL similarity (exact domain match)
        url_similarity = self._url_similarity(str(article1.url), str(article2.url))
        
        # Content similarity
        snippet_length = ProcessingConstants.CONTENT_SNIPPET_LENGTH
        content_similarity = SequenceMatcher(
            None,
            article1.content[:snippet_length],
            article2.content[:snippet_length]
        ).ratio()
        
        # Weighted combination
        # Title is most important, then URL, then content
        total_similarity = (
            title_similarity * 0.5 +
            url_similarity * 0.3 +
            content_similarity * 0.2
        )
        
        return total_similarity
    
    def _url_similarity(self, url1: str, url2: str) -> float:
        """Calculate URL similarity"""
        # Extract domain
        domain1 = url1.split('/')[2] if len(url1.split('/')) > 2 else ''
        domain2 = url2.split('/')[2] if len(url2.split('/')) > 2 else ''
        
        if domain1 == domain2:
            # Same domain, check if it's the same article
            path1 = '/'.join(url1.split('/')[3:]) if len(url1.split('/')) > 3 else ''
            path2 = '/'.join(url2.split('/')[3:]) if len(url2.split('/')) > 3 else ''
            
            if path1 == path2:
                return 1.0  # Exact same URL
            else:
                return 0.8  # Same domain, different articles
        
        return 0.0  # Different domains