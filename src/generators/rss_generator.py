"""
RSS feed generator
"""
from email.utils import formatdate
from pathlib import Path

from src.generators.digest import build_digest
from src.utils.logger import logger
from src.utils.models import NewsDigest, SummarizedArticle


class RSSGenerator:
    """Generates RSS 2.0 feed output for news summaries"""

    def __init__(self, config):
        self.config = config
        self.output_dir = Path(config.output.directory)

    def generate(self, articles: list[SummarizedArticle]) -> None:
        """Generate RSS output"""
        if not articles:
            logger.warning("No articles to generate RSS for")
            return

        digest = build_digest(articles, self.config)

        # Generate RSS file
        self._generate_rss_file(digest)

        logger.info(f"Generated RSS with {len(articles)} articles")

    def _generate_rss_file(self, digest: NewsDigest) -> None:
        """Generate the RSS XML file"""
        # Build RSS 2.0 XML
        rss_items = []

        # Generate items for each article
        for category, articles in digest.articles_by_category.items():
            for article in articles:
                # Description is HTML carried as CDATA; escaped text cannot contain "]]>"
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
      <description><![CDATA[{description}]]></description>
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
