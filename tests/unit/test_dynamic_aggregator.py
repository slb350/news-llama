"""Unit tests for DynamicAggregator routing of LLM-discovered sources."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.aggregators.dynamic_aggregator import DynamicAggregator
from src.utils.config import Config, DiscoveredSource
from src.utils.models import Article, SourceType


def _source(source_type, **fields):
    return DiscoveredSource(
        name=fields.pop("name", f"{source_type} source"),
        source_type=source_type,
        category=fields.pop("category", "ai"),
        confidence_score=fields.pop("confidence_score", 0.9),
        reason="test",
        **fields,
    )


def _article(title="Article title long enough", content="x" * 300, **metadata):
    return Article(
        title=title,
        content=content,
        url="https://example.com/a",
        source="Feed",
        source_type=SourceType.RSS,
        category="ai",
        published_at=datetime.now(UTC),
        metadata=metadata,
    )


@pytest.fixture
def aggregator():
    sources = [
        _source("rss", url="https://example.com/feed.xml"),
        _source("rss"),  # no url: skipped
        _source("reddit", subreddit="rust"),
        _source("reddit"),  # no subreddit: skipped
        _source("reddit_search", category="rust async"),
        _source("twitter", username="someone"),
        _source("web_search"),
        _source("carrier_pigeon"),
    ]
    agg = DynamicAggregator(Config(), sources)
    reddit = agg.delegate_aggregators["reddit"]
    reddit._ensure_reddit_client = AsyncMock()
    reddit._collect_from_subreddit = AsyncMock(return_value=[_article("Reddit post title")])
    reddit.search_reddit = AsyncMock(return_value=[_article("Search result title")])
    reddit.close = AsyncMock()
    return agg


class TestDynamicAggregatorCollect:
    @pytest.mark.asyncio
    async def test_routes_each_source_type(self, aggregator):
        with patch(
            "src.aggregators.dynamic_aggregator.RSSAggregator._collect_from_feed",
            new=AsyncMock(return_value=[_article("Feed article title")]),
        ) as collect_feed:
            articles = await aggregator.collect()

        assert sorted(a.title for a in articles) == [
            "Feed article title",
            "Reddit post title",
            "Search result title",
        ]
        collect_feed.assert_awaited_once_with(
            {"url": "https://example.com/feed.xml", "name": "rss source", "category": "ai"}
        )
        reddit = aggregator.delegate_aggregators["reddit"]
        reddit._collect_from_subreddit.assert_awaited_once_with(
            {"subreddit": "rust", "category": "ai", "limit": 25}
        )
        reddit.search_reddit.assert_awaited_once_with("rust async", "rust async", limit=25)
        reddit.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_web_search_sources_produce_no_articles(self, aggregator):
        articles = await aggregator._collect_from_source_type("web_search", [_source("web_search")])

        assert articles == []

    @pytest.mark.asyncio
    async def test_failing_source_type_does_not_stop_others(self, aggregator):
        reddit = aggregator.delegate_aggregators["reddit"]
        reddit._ensure_reddit_client = AsyncMock(side_effect=RuntimeError("auth failed"))

        with patch(
            "src.aggregators.dynamic_aggregator.RSSAggregator._collect_from_feed",
            new=AsyncMock(return_value=[_article("Feed article title")]),
        ):
            articles = await aggregator.collect()

        assert [a.title for a in articles] == ["Feed article title"]
        reddit.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_failing_individual_sources_are_skipped(self, aggregator):
        reddit = aggregator.delegate_aggregators["reddit"]
        reddit._collect_from_subreddit = AsyncMock(side_effect=RuntimeError("404"))
        reddit.search_reddit = AsyncMock(side_effect=RuntimeError("rate limited"))

        with patch(
            "src.aggregators.dynamic_aggregator.RSSAggregator._collect_from_feed",
            new=AsyncMock(side_effect=RuntimeError("timeout")),
        ):
            assert await aggregator.collect() == []

    @pytest.mark.asyncio
    async def test_reddit_paths_without_reddit_aggregator(self, aggregator):
        del aggregator.delegate_aggregators["reddit"]

        assert await aggregator._collect_from_reddit_sources([_source("reddit", subreddit="rust")]) == []
        assert await aggregator._collect_from_reddit_search([_source("reddit_search")]) == []
        assert await aggregator.collect() is not None


class TestDynamicAggregatorValidation:
    @pytest.fixture
    def validator(self):
        return DynamicAggregator(Config(), [])

    def test_accepts_substantial_article(self, validator):
        assert validator._is_valid_article(_article(confidence_score=0.9))

    @pytest.mark.parametrize(
        "article",
        [
            _article(title="Short"),
            _article(content="too short"),
            _article(title="Sponsored: buy this now"),
            _article(content="advertisement " * 30),
            _article(confidence_score=0.1),
        ],
    )
    def test_rejects(self, validator, article):
        assert not validator._is_valid_article(article)
