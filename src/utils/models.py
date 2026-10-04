"""
Base models and data structures
"""
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class SourceType(str, Enum):
    RSS = "rss"
    TWITTER = "twitter"
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    WEB_SEARCH = "web_search"


class Article(BaseModel):
    """Base article model"""
    title: str
    content: str
    url: HttpUrl
    source: str
    source_type: SourceType
    category: str
    author: str | None = None
    published_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    image_url: HttpUrl | None = None
    local_image_path: str | None = None  # Cached image path (e.g., /static/article-images/abc.jpg)
    is_gallery: bool = False  # True if post has multiple images
    gallery_count: int = 0  # Number of images in gallery
    is_video: bool = False  # True if post links to video (redgifs, etc.)
    summary: str | None = None
    sentiment_score: float | None = None
    relevance_score: float | None = None


class ProcessedArticle(Article):
    """Article after processing and analysis"""
    word_count: int
    reading_time_minutes: int
    keywords: list[str] = Field(default_factory=list)
    is_duplicate: bool = False
    duplicate_similarity: float | None = None


class SummarizedArticle(ProcessedArticle):
    """Article with AI-generated summary"""
    ai_summary: str
    key_points: list[str] = Field(default_factory=list)
    importance_score: float = 0.0


class NewsDigest(BaseModel):
    """Daily news digest output"""
    date: datetime
    articles_by_category: dict[str, list[SummarizedArticle]]
    total_articles: int
    processing_time_seconds: float
    sources_used: list[str]
    discovered_sources_count: int = 0
    user_interests: list[str] = Field(default_factory=list)