"""Unit tests for the HTML, JSON and RSS newsletter generators."""

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import feedparser
import pytest

from src.generators.digest import build_digest
from src.generators.html_generator import HTMLGenerator
from src.generators.json_generator import JSONGenerator
from src.generators.rss_generator import RSSGenerator
from src.utils.models import SourceType, SummarizedArticle

REPO_TEMPLATES = Path(__file__).resolve().parents[2] / "templates"


def _article(title, category, importance, source="Feed", key_points=("First point",)):
    return SummarizedArticle(
        title=title,
        content="Body text",
        url=f"https://example.com/{title.replace(' ', '-').lower()}",
        source=source,
        source_type=SourceType.RSS,
        category=category,
        published_at=datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc),
        word_count=100,
        reading_time_minutes=1,
        keywords=[],
        ai_summary=f"Summary of {title} & more",
        key_points=list(key_points),
        importance_score=importance,
    )


ARTICLES = [
    _article("Low AI story", "AI", 0.2),
    _article("High AI story", "AI", 0.9, source="Other"),
    _article("Rust story", "Rust", 0.5, key_points=()),
]


def _config(tmp_path, template_dir=REPO_TEMPLATES, **extra):
    output = SimpleNamespace(directory=str(tmp_path), template_dir=str(template_dir))
    return SimpleNamespace(output=output, **extra)


class TestBuildDigest:
    def test_groups_sorts_and_counts(self, tmp_path):
        config = _config(tmp_path, user_interests=["AI"], discovered_sources=[object(), object()])

        digest = build_digest(ARTICLES, config)

        assert [a.title for a in digest.articles_by_category["AI"]] == ["High AI story", "Low AI story"]
        assert list(digest.articles_by_category) == ["AI", "Rust"]
        assert digest.total_articles == 3
        assert sorted(digest.sources_used) == ["Feed", "Other"]
        assert digest.discovered_sources_count == 2
        assert digest.user_interests == ["AI"]

    def test_config_without_discovery_fields(self, tmp_path):
        digest = build_digest(ARTICLES, _config(tmp_path))

        assert digest.discovered_sources_count == 0
        assert digest.user_interests == []


@pytest.mark.parametrize("generator_class", [HTMLGenerator, JSONGenerator, RSSGenerator])
def test_no_articles_writes_nothing(tmp_path, generator_class):
    generator_class(_config(tmp_path)).generate([])

    assert list(tmp_path.iterdir()) == []


class TestJSONGenerator:
    def test_writes_digest(self, tmp_path):
        JSONGenerator(_config(tmp_path, user_interests=["AI"])).generate(ARTICLES)

        [output] = tmp_path.glob("news-*.json")
        data = json.loads(output.read_text())
        assert data["total_articles"] == 3
        assert [a["title"] for a in data["articles_by_category"]["AI"]] == ["High AI story", "Low AI story"]
        assert data["user_interests"] == ["AI"]


class TestRSSGenerator:
    def _write(self, tmp_path, **extra):
        RSSGenerator(_config(tmp_path, **extra)).generate(ARTICLES)
        [output] = tmp_path.glob("news-*.xml")
        return output.read_text()

    def test_feed_parses_with_one_item_per_article(self, tmp_path):
        feed = feedparser.parse(self._write(tmp_path, user_interests=["AI", "Rust"]))

        assert not feed.bozo
        assert [e.title for e in feed.entries] == ["High AI story", "Low AI story", "Rust story"]
        assert feed.feed.description == "AI-powered news curation for: AI, Rust"
        assert feed.entries[0].published == "Sat, 03 Oct 2026 12:00:00 GMT"

    def test_description_html_is_character_data(self, tmp_path):
        """RSS readers expect the description's HTML as text, not as child XML elements"""
        channel = ET.fromstring(self._write(tmp_path)).find("channel")
        description = channel.find("item").find("description")

        assert len(description) == 0
        assert "<p><strong>AI Summary:</strong> Summary of High AI story &amp; more</p>" in description.text
        assert "<li>First point</li>" in description.text

    def test_without_interests_describes_general_feed(self, tmp_path):
        feed = feedparser.parse(self._write(tmp_path))

        assert feed.feed.description == "AI-powered news curation for: General"

    def test_escape_xml(self, tmp_path):
        escape = RSSGenerator(_config(tmp_path))._escape_xml

        assert escape("") == ""
        assert escape("a & b < c > d \"e\" 'f'") == "a &amp; b &lt; c &gt; d &quot;e&quot; &apos;f&apos;"


class TestHTMLGenerator:
    def test_renders_repo_template(self, tmp_path):
        HTMLGenerator(_config(tmp_path, user_interests=["AI"])).generate(ARTICLES)

        [output] = tmp_path.glob("news-*.html")
        html = output.read_text()
        assert html.index("High AI story") < html.index("Low AI story")
        assert "Summary of High AI story &amp; more" in html

    def test_custom_output_filename(self, tmp_path):
        HTMLGenerator(_config(tmp_path)).generate(ARTICLES, output_filename="custom.html")

        assert (tmp_path / "custom.html").exists()

    def test_creates_default_template_when_missing(self, tmp_path):
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        output_dir = tmp_path / "out"
        output_dir.mkdir()

        HTMLGenerator(_config(output_dir, template_dir=template_dir)).generate(ARTICLES)

        assert (template_dir / "news.html").exists()
        assert "Rust story" in next(output_dir.glob("news-*.html")).read_text()
