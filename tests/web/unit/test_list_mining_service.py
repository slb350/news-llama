"""
Unit tests for list mining service - TDD RED phase.

Tests mining curated lists for source discovery.
Uses mocked HTTP requests to avoid external dependencies.
"""

import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy.orm import Session

from src.web.database import get_test_db
from src.web.services import list_mining_service


@pytest.fixture
def db():
    yield from get_test_db()


@pytest.fixture
def mock_github_awesome_list():
    """Mock GitHub awesome-list response."""
    return """
    # Awesome Rust

    ## Resources
    - [This Week in Rust](https://this-week-in-rust.org/rss.xml) - Newsletter
    - [r/rust](https://reddit.com/r/rust) - Community

    ## Blogs
    - [Rust Blog](https://blog.rust-lang.org/feed.xml) - Official blog
    """


@pytest.fixture
def mock_reddit_wiki():
    """Mock Reddit wiki response."""
    return """
    # Related Subreddits

    - /r/learnrust - For beginners
    - /r/rust_gamedev - Game development
    """


class TestGitHubListMining:
    """Tests for mining GitHub awesome-lists."""

    @pytest.mark.asyncio
    async def test_mine_awesome_rust(self, mock_github_awesome_list):
        """Should extract sources from awesome-rust list."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.text.return_value = mock_github_awesome_list
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            sources = await list_mining_service.mine_github_list(
                "https://github.com/rust-unofficial/awesome-rust", interest="Rust"
            )

        assert len(sources) >= 2
        assert any(
            s["source_type"] == "rss" and "rust-lang.org" in s["source_url"]
            for s in sources
        )
        assert any(
            s["source_type"] == "reddit" and s["source_key"] == "rust" for s in sources
        )
        assert all(s["discovered_via"] == "awesome-rust" for s in sources)

    @pytest.mark.asyncio
    async def test_mine_returns_empty_on_404(self):
        """Should return empty list on 404."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_get.return_value.__aenter__.return_value = mock_response

            sources = await list_mining_service.mine_github_list(
                "https://github.com/nonexistent/list", interest="Test"
            )

        assert sources == []

    @pytest.mark.asyncio
    async def test_mine_handles_timeout_gracefully(self):
        """Should return empty list on timeout/connection error."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = Exception("Connection timeout")

            sources = await list_mining_service.mine_github_list(
                "https://github.com/timeout/list", interest="Test"
            )

        assert sources == []

    @pytest.mark.asyncio
    async def test_mine_returns_empty_when_no_matches(self):
        """Should return empty list when content has no RSS/subreddit patterns."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.text.return_value = "# Empty List\n\nNo sources here!"
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            sources = await list_mining_service.mine_github_list(
                "https://github.com/empty/list", interest="Test"
            )

        assert sources == []


class TestRedditWikiMining:
    """Tests for mining Reddit wiki pages."""

    @pytest.mark.asyncio
    async def test_mine_rust_wiki(self, mock_reddit_wiki):
        """Should extract subreddits from wiki."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.text.return_value = mock_reddit_wiki
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            sources = await list_mining_service.mine_reddit_wiki(
                "https://www.reddit.com/r/rust/wiki/index", interest="Rust"
            )

        assert len(sources) == 2
        assert any(s["source_key"] == "learnrust" for s in sources)
        assert any(s["source_key"] == "rust_gamedev" for s in sources)
        assert all(s["source_type"] == "reddit" for s in sources)


class TestBulkListMining:
    """Tests for mining multiple lists for an interest."""

    @pytest.mark.asyncio
    async def test_mine_all_lists_for_rust(
        self, mock_github_awesome_list, mock_reddit_wiki
    ):
        """Should mine all known lists for Rust."""
        with patch("aiohttp.ClientSession.get") as mock_get:

            def side_effect_get(url):
                mock_response = AsyncMock()
                mock_response.status = 200
                if "github.com" in url:
                    mock_response.text.return_value = mock_github_awesome_list
                else:
                    mock_response.text.return_value = mock_reddit_wiki
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value = mock_response
                return mock_context

            mock_get.side_effect = side_effect_get

            sources = await list_mining_service.mine_all_lists_for_interest(
                "Rust",
                known_lists={
                    "github": ["https://github.com/rust-unofficial/awesome-rust"],
                    "reddit_wikis": ["https://www.reddit.com/r/rust/wiki/index"],
                },
            )

        # Should deduplicate across lists
        assert len(sources) > 0
        assert all("source_type" in s for s in sources)
        assert all("interests" in s for s in sources)

    @pytest.mark.asyncio
    async def test_deduplicates_across_lists(self):
        """Should deduplicate sources found in multiple lists."""
        # Mock finding r/rust in both awesome-list and wiki
        sources = [
            {
                "source_type": "reddit",
                "source_key": "rust",
                "discovered_via": "awesome-rust",
            },
            {
                "source_type": "reddit",
                "source_key": "rust",
                "discovered_via": "reddit-wiki",
            },
        ]

        deduplicated = list_mining_service.deduplicate_sources(sources)

        assert len(deduplicated) == 1
        assert "discovered_via" in deduplicated[0]
