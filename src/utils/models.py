"""
Base models and data structures
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, HttpUrl, Field
from enum import Enum


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
    author: Optional[str] = None
    published_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    image_url: Optional[HttpUrl] = None
    summary: Optional[str] = None
    sentiment_score: Optional[float] = None
    relevance_score: Optional[float] = None


class ProcessedArticle(Article):
    """Article after processing and analysis"""
    word_count: int
    reading_time_minutes: int
    keywords: List[str] = Field(default_factory=list)
    is_duplicate: bool = False
    duplicate_similarity: Optional[float] = None


class SummarizedArticle(ProcessedArticle):
    """Article with AI-generated summary"""
    ai_summary: str
    key_points: List[str] = Field(default_factory=list)
    importance_score: float = 0.0


class NewsDigest(BaseModel):
    """Daily news digest output"""
    date: datetime
    articles_by_category: Dict[str, List[SummarizedArticle]]
    total_articles: int
    processing_time_seconds: float
    sources_used: List[str]
    discovered_sources_count: int = 0
    user_interests: List[str] = Field(default_factory=list)