"""
Digest construction shared by the HTML, JSON and RSS generators
"""
from datetime import datetime
from typing import Dict, List

from src.utils.models import NewsDigest, SummarizedArticle


def build_digest(articles: List[SummarizedArticle], config) -> NewsDigest:
    """Group articles by category, most important first, into today's digest.

    No per-category limit is applied here; main.py pre-filters before summarization.
    """
    articles_by_category: Dict[str, List[SummarizedArticle]] = {}
    for article in articles:
        articles_by_category.setdefault(article.category, []).append(article)
    for category_articles in articles_by_category.values():
        category_articles.sort(key=lambda a: a.importance_score, reverse=True)

    return NewsDigest(
        date=datetime.now(),
        articles_by_category=articles_by_category,
        total_articles=len(articles),
        processing_time_seconds=0.0,
        sources_used=list({article.source for article in articles}),
        discovered_sources_count=len(getattr(config, "discovered_sources", [])),
        user_interests=getattr(config, "user_interests", []),
    )
