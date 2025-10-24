"""
Unit tests for direct search service - TDD RED phase.

Tests LLM-powered source discovery via web search.
Uses mocked LLM responses to avoid external dependencies.
"""

import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy.orm import Session

from src.web.database import get_test_db
from src.web.services import direct_search_service


@pytest.fixture
def db():
    yield from get_test_db()


@pytest.fixture
def mock_llm_search_response():
    """Mock LLM response for source search."""
    return {
        "sources": [
            {
                "type": "reddit",
                "name": "r/boxoffice",
                "subreddit": "boxoffice",
                "confidence": 0.9,
                "reasoning": "Primary subreddit for box office discussion",
            },
            {
                "type": "rss",
                "name": "Box Office Mojo News",
                "url": "https://www.boxofficemojo.com/rss",
                "confidence": 0.8,
                "reasoning": "Official industry news feed",
            },
        ]
    }


class TestDirectSearch:
    """Tests for direct interest search."""

    @pytest.mark.asyncio
    async def test_search_for_custom_interest(self, mock_llm_search_response):
        """Should discover sources for custom interest via LLM."""
        with patch(
            "src.web.services.direct_search_service._call_llm_search",
            return_value=mock_llm_search_response,
        ):
            sources = await direct_search_service.search_for_interest("boxoffice")

        assert len(sources) == 2
        assert any(
            s["source_type"] == "reddit" and s["source_key"] == "boxoffice"
            for s in sources
        )
        assert any(s["source_type"] == "rss" for s in sources)
        assert all("confidence" in s["metadata"] for s in sources)
        assert all(s["discovered_via"] == "llm-search" for s in sources)

    @pytest.mark.asyncio
    async def test_filters_low_confidence_sources(self, mock_llm_search_response):
        """Should filter out sources with confidence < 0.6."""
        # Add low-confidence source
        mock_llm_search_response["sources"].append(
            {
                "type": "rss",
                "name": "Unreliable Feed",
                "url": "https://example.com/feed.xml",
                "confidence": 0.4,
                "reasoning": "Uncertain relevance",
            }
        )

        with patch(
            "src.web.services.direct_search_service._call_llm_search",
            return_value=mock_llm_search_response,
        ):
            sources = await direct_search_service.search_for_interest("boxoffice")

        # Should only have 2 high-confidence sources
        assert len(sources) == 2
        assert all(s["metadata"]["confidence"] >= 0.6 for s in sources)

    @pytest.mark.asyncio
    async def test_handles_llm_error_gracefully(self):
        """Should return empty list when LLM call fails."""
        with patch(
            "src.web.services.direct_search_service._call_llm_search",
            side_effect=Exception("LLM connection failed"),
        ):
            sources = await direct_search_service.search_for_interest("test")

        assert sources == []

    @pytest.mark.asyncio
    async def test_handles_empty_llm_response(self):
        """Should return empty list when LLM returns no sources."""
        with patch(
            "src.web.services.direct_search_service._call_llm_search",
            return_value={"sources": []},
        ):
            sources = await direct_search_service.search_for_interest("obscure_topic")

        assert sources == []


class TestBulkSearch:
    """Tests for searching multiple interests."""

    @pytest.mark.asyncio
    async def test_search_multiple_interests(self, db: Session):
        """Should search for multiple interests concurrently."""
        interests = ["Rust", "Go", "Python"]

        # Return different sources for each interest to avoid deduplication
        def side_effect_search(interest):
            return [{"source_type": "reddit", "source_key": interest.lower()}]

        with patch(
            "src.web.services.direct_search_service.search_for_interest"
        ) as mock_search:
            mock_search.side_effect = side_effect_search

            all_sources = await direct_search_service.search_for_interests(interests)

        assert mock_search.call_count == 3
        assert len(all_sources) == 3
        # Verify we got sources for each interest
        source_keys = {s["source_key"] for s in all_sources}
        assert source_keys == {"rust", "go", "python"}
