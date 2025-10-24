"""
Tests for NewsLlama accepting pre-discovered sources.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from main import NewsLlama
from src.utils.config import DiscoveredSource


class TestNewsLlamaPreDiscoveredSources:
    """Test NewsLlama can accept pre-discovered sources."""

    def test_accepts_pre_discovered_sources(self):
        """Should accept pre_discovered_sources parameter."""
        sources = [
            DiscoveredSource(
                name="r/rust",
                subreddit="rust",
                source_type="reddit",
                category="Rust",
                confidence_score=0.95,
                reason="Tier 1 source",
            )
        ]

        news_llama = NewsLlama(user_interests=["Rust"], pre_discovered_sources=sources)

        # Should store pre-discovered sources
        assert news_llama.config.discovered_sources == sources
        # Should NOT create SourceDiscoveryEngine
        assert news_llama.source_discovery is None

    @patch("src.processors.source_discovery.SourceDiscoveryEngine")
    def test_skips_discovery_when_pre_discovered(self, mock_engine_class):
        """Should skip LLM discovery when pre-discovered provided."""
        sources = [
            DiscoveredSource(
                name="r/python",
                subreddit="python",
                source_type="reddit",
                category="Python",
                confidence_score=0.9,
                reason="Tier 1",
            )
        ]

        news_llama = NewsLlama(
            user_interests=["Python"], pre_discovered_sources=sources
        )

        # Should NOT create discovery engine
        mock_engine_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_pre_discovered_in_aggregation(self):
        """Should pass pre-discovered sources to DynamicAggregator."""
        sources = [
            DiscoveredSource(
                name="rust_blog",
                url="https://blog.rust-lang.org/feed.xml",
                source_type="rss",
                category="Rust",
                confidence_score=0.88,
                reason="Tier 1",
            )
        ]

        with patch("main.DynamicAggregator") as mock_dynamic_class:
            news_llama = NewsLlama(
                user_interests=["Rust"], pre_discovered_sources=sources
            )

            # Initialize (should use pre-discovered, not discover)
            await news_llama.initialize()

            # Should create DynamicAggregator with pre-discovered sources
            mock_dynamic_class.assert_called_once()
            call_args = mock_dynamic_class.call_args[0]
            assert call_args[1] == sources  # Second arg is discovered_sources

    def test_backward_compatible_without_pre_discovered(self):
        """Should work normally without pre_discovered_sources."""
        # Old way should still work
        news_llama = NewsLlama(user_interests=["AI", "Python"])

        # Should create discovery engine as before
        assert news_llama.source_discovery is not None
        assert news_llama.config.discovered_sources == []

    def test_handles_mixed_source_types(self):
        """Should handle RSS, Reddit, and other source types."""
        sources = [
            DiscoveredSource(
                name="r/rust",
                subreddit="rust",
                source_type="reddit",
                category="Rust",
                confidence_score=0.95,
                reason="Tier 1",
            ),
            DiscoveredSource(
                name="Rust Blog",
                url="https://blog.rust-lang.org/feed.xml",
                source_type="rss",
                category="Rust",
                confidence_score=0.88,
                reason="Tier 1",
            ),
        ]

        news_llama = NewsLlama(user_interests=["Rust"], pre_discovered_sources=sources)

        assert len(news_llama.config.discovered_sources) == 2
        assert news_llama.config.discovered_sources[0].source_type == "reddit"
        assert news_llama.config.discovered_sources[1].source_type == "rss"
