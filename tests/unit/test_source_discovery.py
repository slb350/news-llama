"""Unit tests for SourceDiscoveryEngine's tiered discovery, with the LLM client faked."""

import asyncio
import json
from unittest.mock import patch

import pytest
from open_agent import TextBlock

from src.processors.source_discovery import SourceDiscoveryEngine
from src.utils.config import Config, DiscoveredSource


class FakeClient:
    """Stands in for open_agent.Client; replies with the queued text chunks."""

    replies: list = []
    prompts: list = []
    delay: float = 0.0

    def __init__(self, options):
        self.options = options

    async def query(self, prompt):
        FakeClient.prompts.append(prompt)

    async def receive_messages(self):
        if FakeClient.delay:
            await asyncio.sleep(FakeClient.delay)
        chunks = FakeClient.replies.pop(0) if FakeClient.replies else []
        for chunk in chunks:
            yield TextBlock(text=chunk)
        yield object()  # non-text blocks are ignored

    async def close(self):
        pass


@pytest.fixture
def engine():
    FakeClient.replies = []
    FakeClient.prompts = []
    FakeClient.delay = 0.0
    with patch("src.processors.source_discovery.Client", FakeClient):
        yield SourceDiscoveryEngine(Config())


def _subreddits(*names):
    return json.dumps(
        {"subreddits": [{"subreddit": n, "reason": f"{n} community", "confidence_score": 0.9} for n in names]}
    )


def _sources(*sources):
    return json.dumps({"sources": list(sources)})


class TestQueryLLM:
    @pytest.mark.asyncio
    async def test_joins_text_blocks(self, engine):
        FakeClient.replies = [["  {\"a\":", " 1}  "]]

        text = await engine._query_llm("system", "user", temperature=0.3, max_tokens=10, interest="ai")

        assert text == '{"a": 1}'
        assert FakeClient.prompts == ["user"]

    @pytest.mark.asyncio
    async def test_timeout_returns_empty_text(self, engine):
        engine.llm_config.timeout = 0.01
        FakeClient.delay = 1

        assert await engine._query_llm("system", "user", temperature=0.3, max_tokens=10, interest="ai") == ""


class TestExtractJSONObject:
    @pytest.mark.parametrize(
        "response",
        [
            '{"k": 1}',
            '```json\n{"k": 1}\n```',
            'Here you go: {"k": 1} hope that helps',
        ],
    )
    def test_extracts_object(self, response):
        assert SourceDiscoveryEngine._extract_json_object(response) == {"k": 1}

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            SourceDiscoveryEngine._extract_json_object("no json here")


class TestSubredditDiscovery:
    @pytest.mark.asyncio
    async def test_parses_subreddits(self, engine):
        FakeClient.replies = [["```json\n", _subreddits("rust", "learnrust", ""), "\n```"]]

        sources = await engine._llm_discover_subreddits("rust")

        assert [(s.subreddit, s.source_type, s.confidence_score) for s in sources] == [
            ("rust", "reddit", 0.9),
            ("learnrust", "reddit", 0.9),
        ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("reply", [[], ["not json"]])
    async def test_empty_or_invalid_reply_gives_no_sources(self, engine, reply):
        FakeClient.replies = [reply]

        assert await engine._llm_discover_subreddits("rust") == []

    @pytest.mark.asyncio
    async def test_client_error_gives_no_sources(self, engine):
        with patch.object(engine, "_query_llm", side_effect=RuntimeError("connection refused")):
            assert await engine._llm_discover_subreddits("rust") == []


class TestBroadDiscovery:
    @pytest.mark.asyncio
    async def test_parses_sources(self, engine):
        FakeClient.replies = [[_sources({"type": "rss", "name": "Feed", "url": "https://x.com/feed", "confidence": 0.8, "reasoning": "r"})]]

        [source] = await engine._llm_discovery("ai")

        assert (source.source_type, source.url, source.confidence_score) == ("rss", "https://x.com/feed", 0.8)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("reply", [[], ["{broken"]])
    async def test_empty_or_invalid_reply_gives_no_sources(self, engine, reply):
        FakeClient.replies = [reply]

        assert await engine._llm_discovery("ai") == []

    @pytest.mark.asyncio
    async def test_client_error_gives_no_sources(self, engine):
        with patch.object(engine, "_query_llm", side_effect=RuntimeError("boom")):
            assert await engine._llm_discovery("ai") == []

    @pytest.mark.asyncio
    async def test_prompt_only_requests_supported_source_types(self, engine):
        await engine._llm_discovery("ai")

        assert "twitter" not in FakeClient.prompts[0].lower()


class TestPredefinedPatterns:
    def test_known_interest_yields_reddit_and_rss_only(self, engine):
        sources = engine._check_predefined_patterns("technology")

        assert {s.source_type for s in sources} <= {"reddit", "rss"}
        assert any(s.subreddit == "technology" and s.confidence_score == 0.9 for s in sources)

    def test_rss_patterns_use_feed_urls_verbatim(self, engine):
        [feed] = [s for s in engine._check_predefined_patterns("rust") if s.source_type == "rss"]

        assert (feed.name, feed.url) == ("this-week-in-rust.org", "https://this-week-in-rust.org/rss.xml")

    def test_partial_match_uses_lower_confidence(self, engine):
        sources = engine._check_predefined_patterns("rust gamedev")

        assert sources
        assert {s.confidence_score for s in sources} == {0.7}

    def test_unknown_interest_has_no_patterns(self, engine):
        assert engine._check_predefined_patterns("knitting") == []


class TestDiscoverSources:
    @pytest.mark.asyncio
    async def test_disabled_discovery_returns_nothing(self, engine):
        engine.config.source_discovery.enabled = False

        assert await engine.discover_sources(["ai"]) == []

    @pytest.mark.asyncio
    async def test_combines_tiers_dedupes_sorts_and_caps(self, engine):
        engine.config.source_discovery.max_sources_per_category = 2
        FakeClient.replies = [
            [_subreddits("knitting", "crochet")],
            [_sources({"type": "reddit", "name": "r/knitting", "subreddit": "knitting", "confidence": 0.95, "reasoning": "r"})],
        ]

        sources = await engine.discover_sources(["knitting"])

        assert [(s.name, s.confidence_score) for s in sources] == [("r/knitting", 0.95), ("r/crochet", 0.9)]

    @pytest.mark.asyncio
    async def test_exact_subreddit_fallback_when_nothing_found(self, engine):
        [source] = await engine._discover_sources_for_interest("knitting")

        assert (source.subreddit, source.source_type, source.confidence_score) == ("knitting", "reddit", 0.8)

    @pytest.mark.asyncio
    async def test_reddit_search_fallback_for_short_interest(self, engine):
        [source] = await engine._discover_sources_for_interest("go")

        assert (source.source_type, source.category) == ("reddit_search", "go")


class TestDeduplicateSources:
    def test_keeps_highest_confidence_in_first_position(self, engine):
        def src(name, confidence, source_type="reddit"):
            return DiscoveredSource(name=name, source_type=source_type, category="ai", confidence_score=confidence, reason="r")

        unique = engine._deduplicate_sources([src("r/AI", 0.5), src("Feed", 0.6, "rss"), src("r/ai", 0.9), src("r/ai", 0.7)])

        assert [(s.name, s.confidence_score) for s in unique] == [("r/ai", 0.9), ("Feed", 0.6)]
