"""
Constants and configuration values for News Llama
"""
import re
from typing import List

# Processing Constants
class ProcessingConstants:
    # Batch sizes and limits
    DEFAULT_BATCH_SIZE = 5
    MAX_ARTICLES_PER_FEED = 50
    MAX_CONTENT_LENGTH = 2000
    WORDS_PER_MINUTE = 200

    # Similarity and filtering
    DEFAULT_SIMILARITY_THRESHOLD = 0.8
    MIN_ARTICLE_TITLE_LENGTH = 10
    MIN_ARTICLE_CONTENT_LENGTH = 200
    MAX_ARTICLE_AGE_HOURS = 24

    # Content processing
    CONTENT_SNIPPET_LENGTH = 500  # For similarity comparison
    MAX_KEYWORDS = 10
    MAX_NOUN_PHRASE_WORDS = 3
    MIN_KEYWORD_LENGTH = 4

# Rate Limiting Constants
class RateLimitConstants:
    DEFAULT_CALLS_PER_SECOND = 1.0
    RSS_REQUESTS_PER_SECOND = 2.0
    TWITTER_REQUESTS_PER_SECOND = 1.0
    REDDIT_REQUESTS_PER_SECOND = 1.0
    WEB_SEARCH_REQUESTS_PER_MINUTE = 10

# HTTP Request Constants
class HTTPConstants:
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 1.0
    MAX_REDIRECTS = 5

    # User agent for requests
    USER_AGENT = "NewsLlama/1.0 (+https://github.com/your-repo/news-llama)"

# Security Constants
class SecurityConstants:
    # Spam and malicious content indicators
    SPAM_KEYWORDS = [
        'advertisement', 'sponsored', 'promoted', 'clickbait',
        'fake news', 'misinformation', 'scam', 'phishing',
        'malware', 'virus', 'trojan', 'ransomware'
    ]

    # Suspicious URL patterns
    SUSPICIOUS_DOMAINS = [
        'bit.ly', 'tinyurl.com', 't.co', 'short.link'
    ]

    # Allowed content types
    ALLOWED_MIME_TYPES = [
        'text/html', 'text/plain', 'application/xml',
        'application/rss+xml', 'application/atom+xml'
    ]

# Content Processing Constants
class ContentConstants:
    # Common words to filter out from keywords
    COMMON_WORDS = {
        'news', 'article', 'story', 'read', 'time', 'day', 'year',
        'people', 'new', 'said', 'says', 'according', 'report',
        'also', 'would', 'could', 'should', 'might', 'may',
        'first', 'last', 'next', 'previous', 'current', 'recent',
        'local', 'national', 'international', 'global', 'world'
    }

    # Regex patterns for content cleaning
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    EXCESSIVE_WHITESPACE_PATTERN = re.compile(r'\s+')
    EXCESSIVE_PUNCTUATION_PATTERNS = {
        '.': re.compile(r'\.{2,}'),
        '!': re.compile(r'\!{2,}'),
        '?': re.compile(r'\?{2,}'),
    }

    # Pattern for preserving important Unicode characters while cleaning
    # Be more permissive with Unicode - only remove clearly problematic characters
    UNICODE_CLEANING_PATTERN = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', re.UNICODE)

# LLM Constants
class LLMConstants:
    # Summarization prompts and limits
    MAX_SUMMARY_LENGTH = 500
    MAX_KEY_POINTS = 5
    DEFAULT_IMPORTANCE_SCORE = 0.5

    # Prompt templates
    SUMMARY_PROMPT_TEMPLATE = """
Please analyze and summarize the following news article:

Title: {title}
Source: {source}
Category: {category}
Published: {published_at}

Content:
{content}

Please provide:
1. A concise summary (2-3 sentences, max {max_summary} characters)
2. {max_key_points} key bullet points
3. An importance score (0.1-1.0) based on relevance and impact

Format your response as JSON:
{{
    "summary": "Your summary here",
    "key_points": ["Point 1", "Point 2", "Point 3"],
    "importance_score": 0.7
}}
"""

# Validation Constants
class ValidationConstants:
    # URL validation patterns
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    # Email validation for API key context
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    # API key format validation (basic pattern)
    API_KEY_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{20,}$')

# Category Constants
class CategoryConstants:
    # Default categories and their priorities
    DEFAULT_CATEGORIES = {
        'technology': {
            'keywords': ['AI', 'machine learning', 'python', 'programming', 'startup', 'tech', 'software', 'development'],
            'priority': 'high'
        },
        'programming': {
            'keywords': ['code', 'development', 'software', 'github', 'open source', 'programming', 'coding'],
            'priority': 'high'
        },
        'general': {
            'keywords': ['news', 'world', 'politics', 'economy', 'business', 'finance'],
            'priority': 'medium'
        },
        'science': {
            'keywords': ['research', 'study', 'discovery', 'science', 'medical', 'health'],
            'priority': 'high'
        },
        'business': {
            'keywords': ['market', 'economy', 'finance', 'investment', 'startup', 'company', 'business'],
            'priority': 'medium'
        }
    }

    # Priority levels
    PRIORITY_LEVELS = ['high', 'medium', 'low']
    PRIORITY_WEIGHTS = {'high': 1.0, 'medium': 0.7, 'low': 0.4}

# Logging Constants
class LoggingConstants:
    # Log levels and formatting
    DEFAULT_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

    # Log file settings
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT = 5

# Export commonly used constants
__all__ = [
    'ProcessingConstants',
    'RateLimitConstants',
    'HTTPConstants',
    'SecurityConstants',
    'ContentConstants',
    'LLMConstants',
    'ValidationConstants',
    'CategoryConstants',
    'LoggingConstants'
]