"""
RSS feed generator
"""
from datetime import datetime
from pathlib import Path
from typing import List
from email.utils import formatdate

from src.utils.models import SummarizedArticle, NewsDigest
from src.utils.logger import logger


class RSSGenerator:
    """Generates RSS 2.0 feed output for news summaries"""

    def __init__(self, config):
        self.config = config
        self.output_dir = Path(config.output.directory)

    def generate(self, articles: List[SummarizedArticle]) -> None:
        """Generate RSS output"""
        if not articles:
            logger.warning("No articles to generate RSS for")
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

        # Generate RSS file
        self._generate_rss_file(digest)

        logger.info(f"Generated RSS with {len(articles)} articles")

    def _group_by_category(self, articles: List[SummarizedArticle]) -> dict:
        """Group articles by category"""
        grouped = {}
        for article in articles:
            category = article.category
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(article)
        return grouped

    def _generate_rss_file(self, digest: NewsDigest) -> None:
        """Generate the RSS XML file"""
        # Build RSS 2.0 XML
        rss_items = []

        # Generate items for each article
        for category, articles in digest.articles_by_category.items():
            for article in articles:
                # Build description with summary and key points
                description = f"<p><strong>AI Summary:</strong> {self._escape_xml(article.ai_summary)}</p>"

                if article.key_points:
                    description += "<p><strong>Key Points:</strong></p><ul>"
                    for point in article.key_points:
                        description += f"<li>{self._escape_xml(point)}</li>"
                    description += "</ul>"

                # Add metadata
                description += f"<p><em>Source: {self._escape_xml(article.source)} | "
                description += f"Category: {self._escape_xml(category)} | "
                description += f"Reading time: {article.reading_time_minutes} min | "
                description += f"Importance: {article.importance_score:.1f}</em></p>"

                # Format pub date in RFC 822 format
                pub_date = formatdate(
                    timeval=article.published_at.timestamp(),
                    localtime=False,
                    usegmt=True
                )

                # Create RSS item
                item = f"""    <item>
      <title>{self._escape_xml(article.title)}</title>
      <link>{self._escape_xml(str(article.url))}</link>
      <description>{description}</description>
      <category>{self._escape_xml(category)}</category>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="true">{self._escape_xml(str(article.url))}</guid>
    </item>"""
                rss_items.append(item)

        # Build complete RSS feed
        build_date = formatdate(
            timeval=digest.date.timestamp(),
            localtime=False,
            usegmt=True
        )

        interests_str = ", ".join(digest.user_interests) if digest.user_interests else "General"

        rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Daily News Digest - {digest.date.strftime('%Y-%m-%d')}</title>
    <link>about:blank</link>
    <description>AI-powered news curation for: {self._escape_xml(interests_str)}</description>
    <language>en-us</language>
    <lastBuildDate>{build_date}</lastBuildDate>
    <generator>News Llama</generator>
    <category>News</category>
    <ttl>1440</ttl>

{chr(10).join(rss_items)}

  </channel>
</rss>"""

        # Write to file
        output_file = self.output_dir / f"news-{digest.date.strftime('%Y-%m-%d')}.xml"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(rss_content)

        logger.info(f"RSS generated: {output_file}")

    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters"""
        if not text:
            return ""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;"))
