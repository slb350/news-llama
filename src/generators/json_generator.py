"""
JSON output generator
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List

from src.utils.models import SummarizedArticle, NewsDigest
from src.utils.logger import logger


class JSONGenerator:
    """Generates JSON output for news summaries"""

    def __init__(self, config):
        self.config = config
        self.output_dir = Path(config.output.directory)

    def generate(self, articles: List[SummarizedArticle]) -> None:
        """Generate JSON output"""
        if not articles:
            logger.warning("No articles to generate JSON for")
            return

        # Group articles by category
        articles_by_category = self._group_by_category(articles)

        # Sort articles within each category by importance
        for category in articles_by_category:
            articles_by_category[category].sort(
                key=lambda x: x.importance_score,
                reverse=True
            )
            # Note: No limit here - pre-filtering happens before summarization in main.py

        # Create news digest
        digest = NewsDigest(
            date=datetime.now(),
            articles_by_category=articles_by_category,
            total_articles=len(articles),
            processing_time_seconds=0.0,  # TODO: Add timing
            sources_used=list(set(article.source for article in articles)),
            discovered_sources_count=len(getattr(self.config, 'discovered_sources', [])),
            user_interests=getattr(self.config, 'user_interests', [])
        )

        # Generate JSON file
        self._generate_json_file(digest)

        logger.info(f"Generated JSON with {len(articles)} articles")

    def _group_by_category(self, articles: List[SummarizedArticle]) -> dict:
        """Group articles by category"""
        grouped = {}
        for article in articles:
            category = article.category
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(article)
        return grouped

    def _generate_json_file(self, digest: NewsDigest) -> None:
        """Generate the JSON output file"""
        # Convert digest to dict using Pydantic's model_dump
        digest_dict = digest.model_dump(mode='json')

        # Write to file with pretty formatting
        output_file = self.output_dir / f"news-{digest.date.strftime('%Y-%m-%d')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(digest_dict, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"JSON generated: {output_file}")
