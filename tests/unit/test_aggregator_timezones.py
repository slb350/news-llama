"""
Aggregators must emit timezone-aware UTC publication times and apply the age limit in UTC,
whatever the host's local timezone is.
"""

import time
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import feedparser
import pytest

from src.aggregators.hackernews_aggregator import HackerNewsAggregator
from src.aggregators.rss_aggregator import RSSAggregator


@pytest.fixture
def pacific_time(monkeypatch):
    """Run the test with the process in a timezone west of UTC."""
    monkeypatch.setenv("TZ", "America/Los_Angeles")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


def _config():
    return SimpleNamespace(processing=SimpleNamespace(max_article_age=24, min_article_length=0))


def _rss_entry(published: datetime):
    feed = feedparser.parse(
        f"""<?xml version="1.0"?><rss version="2.0"><channel><title>Feed</title><item>
        <title>Story</title><link>https://example.com/story</link>
        <description>Body</description><pubDate>{format_datetime(published, usegmt=True)}</pubDate>
        </item></channel></rss>"""
    )
    return feed.entries[0]


class TestRSSPublicationTime:
    @pytest.mark.asyncio
    async def test_entry_older_than_max_age_is_skipped_west_of_utc(self, pacific_time):
        entry = _rss_entry(datetime.now(timezone.utc) - timedelta(hours=28))

        article = await RSSAggregator(_config())._parse_entry(
            entry, "Feed", "test", "https://example.com/feed.xml"
        )

        assert article is None

    @pytest.mark.asyncio
    async def test_published_at_is_aware_utc(self, pacific_time):
        published = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(microsecond=0)

        article = await RSSAggregator(_config())._parse_entry(
            _rss_entry(published), "Feed", "test", "https://example.com/feed.xml"
        )

        assert article.published_at == published
        assert article.published_at.tzinfo == timezone.utc


class TestHackerNewsPublicationTime:
    @pytest.mark.asyncio
    async def test_published_at_is_aware_utc(self, pacific_time):
        posted = int(time.time()) - 3600
        response = Mock()
        response.json.return_value = {"type": "story", "title": "Show HN", "time": posted}

        with patch("src.aggregators.hackernews_aggregator.requests.get", return_value=response):
            article = await HackerNewsAggregator(_config())._fetch_story(1)

        assert article.published_at == datetime.fromtimestamp(posted, tz=timezone.utc)
        assert article.published_at.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_story_older_than_max_age_is_skipped(self, pacific_time):
        response = Mock()
        response.json.return_value = {
            "type": "story",
            "title": "Old",
            "time": int(time.time()) - 28 * 3600,
        }

        with patch("src.aggregators.hackernews_aggregator.requests.get", return_value=response):
            assert await HackerNewsAggregator(_config())._fetch_story(1) is None
