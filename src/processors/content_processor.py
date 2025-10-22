"""
Content processing and analysis
"""
import re
from datetime import datetime
from typing import List
from textblob import TextBlob

from src.utils.models import Article, ProcessedArticle
from src.utils.logger import logger
from src.utils.constants import (
    ProcessingConstants,
    ContentConstants
)


class ContentProcessor:
    """Processes and analyzes article content"""
    
    def __init__(self, config):
        self.config = config
    
    def process(self, articles: List[Article]) -> List[ProcessedArticle]:
        """Process a list of articles"""
        processed = []
        
        for article in articles:
            try:
                processed_article = self._process_article(article)
                processed.append(processed_article)
            except Exception as e:
                logger.warning(f"Error processing article '{article.title}': {e}")
        
        logger.info(f"Processed {len(processed)} articles")
        return processed
    
    def _process_article(self, article: Article) -> ProcessedArticle:
        """Process individual article"""
        try:
            # Validate input
            if not article.content:
                logger.warning(f"Empty content for article: {article.title}")
                cleaned_content = ""
            else:
                # Clean content
                cleaned_content = self._clean_content(article.content)

            # Calculate word count and reading time using constants
            word_count = len(cleaned_content.split()) if cleaned_content else 0
            reading_time = max(1, round(word_count / ProcessingConstants.WORDS_PER_MINUTE))

            # Extract keywords
            full_text = f"{article.title} {cleaned_content}"
            keywords = self._extract_keywords(full_text)

            # Perform sentiment analysis if enabled
            sentiment_score = None
            if self.config.processing.sentiment_analysis and cleaned_content:
                sentiment_score = self._analyze_sentiment(cleaned_content)

            return ProcessedArticle(
                title=article.title,
                content=cleaned_content,
                url=article.url,
                source=article.source,
                source_type=article.source_type,
                category=article.category,
                author=article.author,
                published_at=article.published_at,
                metadata=article.metadata,
                image_url=article.image_url,
                summary=article.summary,
                sentiment_score=sentiment_score,
                word_count=word_count,
                reading_time_minutes=reading_time,
                keywords=keywords
            )

        except Exception as e:
            logger.error(f"Error processing article '{article.title}': {e}")
            # Return a minimal processed article
            return ProcessedArticle(
                title=article.title,
                content=article.content or "",
                url=article.url,
                source=article.source,
                source_type=article.source_type,
                category=article.category,
                author=article.author,
                published_at=article.published_at,
                metadata=article.metadata,
                image_url=article.image_url,
                summary=article.summary,
                sentiment_score=0.5,  # Neutral sentiment
                word_count=0,
                reading_time_minutes=1,
                keywords=[]
            )
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content while preserving Unicode characters"""
        if not content:
            return ""

        try:
            # Remove HTML tags using pattern from constants
            content = ContentConstants.HTML_TAG_PATTERN.sub('', content)

            # Normalize whitespace
            content = ContentConstants.EXCESSIVE_WHITESPACE_PATTERN.sub(' ', content)

            # Fix excessive punctuation using patterns from constants
            for punct_char, pattern in ContentConstants.EXCESSIVE_PUNCTUATION_PATTERNS.items():
                content = pattern.sub(punct_char, content)

            # Clean dangerous characters while preserving Unicode
            # This pattern preserves letters, numbers, spaces, common punctuation, and important Unicode marks
            content = ContentConstants.UNICODE_CLEANING_PATTERN.sub('', content)

            # Final cleanup: normalize spaces around punctuation
            content = re.sub(r'\s+([.,!?;:])', r'\1', content)

            return content.strip()

        except Exception as e:
            logger.error(f"Error cleaning content: {e}")
            return content.strip()  # Return original content if cleaning fails
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text using improved filtering"""
        if not text:
            return []

        try:
            # Simple keyword extraction using TextBlob
            blob = TextBlob(text.lower())

            # Get noun phrases as potential keywords
            noun_phrases = blob.noun_phrases

            # Use common words from constants
            common_words = ContentConstants.COMMON_WORDS

            keywords = []
            for phrase in noun_phrases:
                words = phrase.split()

                # Apply filtering criteria from constants
                if (len(words) <= ProcessingConstants.MAX_NOUN_PHRASE_WORDS and
                    len(phrase) >= ProcessingConstants.MIN_KEYWORD_LENGTH and
                    phrase not in common_words):
                    keywords.append(phrase)

            # Return limited number of keywords using constant
            return keywords[:ProcessingConstants.MAX_KEYWORDS]

        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return []
    
    def _analyze_sentiment(self, content: str) -> float:
        """Analyze sentiment of content"""
        try:
            blob = TextBlob(content)
            polarity = blob.sentiment.polarity
            # Convert to 0-1 scale
            return (polarity + 1) / 2
        except Exception:
            return 0.5  # Neutral sentiment