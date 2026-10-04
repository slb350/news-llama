"""
Tests that SourceDiscoveryEngine parses LLM discovery responses using the field names
the discovery prompt asks for (type, confidence, reasoning).
"""

import json

from src.processors.source_discovery import SourceDiscoveryEngine
from src.utils.config import Config


def _response(*sources):
    return json.dumps({"sources": list(sources)})


class TestParseLLMResponse:
    def setup_method(self):
        self.engine = SourceDiscoveryEngine(Config())

    def test_reads_prompt_field_names(self):
        response = _response(
            {
                "type": "reddit",
                "name": "r/rust",
                "subreddit": "rust",
                "confidence": 0.9,
                "reasoning": "Primary community",
            }
        )

        [source] = self.engine._parse_llm_response(response, "rust")

        assert source.source_type == "reddit"
        assert source.confidence_score == 0.9
        assert source.reason == "Primary community"
        assert source.subreddit == "rust"
        assert source.category == "rust"

    def test_each_source_keeps_its_own_type(self):
        response = _response(
            {"type": "rss", "name": "Feed", "url": "https://example.com/feed.xml", "confidence": 0.8, "reasoning": "r"},
            {"type": "twitter", "name": "Acct", "username": "acct", "confidence": 0.7, "reasoning": "t"},
        )

        sources = self.engine._parse_llm_response(response, "ai")

        assert [s.source_type for s in sources] == ["rss", "twitter"]
        assert sources[0].url == "https://example.com/feed.xml"
        assert sources[1].username == "acct"

    def test_missing_optional_fields_use_defaults(self):
        [source] = self.engine._parse_llm_response(_response({"name": "Unknown"}), "ai")

        assert source.source_type == "web_search"
        assert source.confidence_score == 0.5
        assert source.reason == "LLM discovered"
