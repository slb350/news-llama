"""Unit tests for RedditAggregator with asyncpraw and the image cache faked."""

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.aggregators.reddit_aggregator import RedditAggregator


def _submission(**fields):
    defaults = {
        "title": "A sufficiently long link post title",
        "selftext": "",
        "is_self": False,
        "url": "https://example.com/story",
        "permalink": "/r/rust/comments/1/story/",
        "subreddit": "rust",
        "author": "alice",
        "created_utc": time.time() - 3600,
        "score": 42,
        "num_comments": 7,
        "upvote_ratio": 0.95,
        "link_flair_text": "news",
    }
    defaults.update(fields)
    return SimpleNamespace(**defaults)


class FakeSubreddit:
    def __init__(self, top=(), searches=None):
        self._top = list(top)
        self._searches = searches or {}
        self.search_calls = []

    async def top(self, time_filter, limit):
        for submission in self._top:
            yield submission

    async def search(self, query, limit, time_filter):
        self.search_calls.append(time_filter)
        for submission in self._searches.get(time_filter, []):
            yield submission


class FakeReddit:
    def __init__(self, subreddit):
        self._subreddit = subreddit
        self.close = AsyncMock()
        self.requested = []

    async def subreddit(self, name):
        self.requested.append(name)
        return self._subreddit


def _config(sources=None, **creds):
    social = {"reddit_client_id": None, "reddit_client_secret": None, "reddit_username": None, "reddit_password": None, "reddit_user_agent": None}
    social.update(creds)
    return SimpleNamespace(
        social_media=SimpleNamespace(**social),
        processing=SimpleNamespace(max_article_age=24, min_article_length=50),
        sources={"reddit": sources or []},
    )


def _aggregator(subreddit, sources=None):
    aggregator = RedditAggregator(_config(sources))
    aggregator.reddit = FakeReddit(subreddit)
    aggregator._client_initialized = True
    return aggregator


@pytest.fixture(autouse=True)
def no_image_downloads():
    with patch(
        "src.aggregators.reddit_aggregator.download_and_cache_image",
        new=AsyncMock(return_value="cache/abc.jpg"),
    ) as download:
        yield download


class TestClientInitialization:
    @pytest.mark.asyncio
    async def test_script_credentials(self):
        aggregator = RedditAggregator(
            _config(reddit_client_id="id", reddit_client_secret="secret", reddit_username="u", reddit_password="p")
        )
        with patch("src.aggregators.reddit_aggregator.asyncpraw.Reddit") as reddit:
            await aggregator._ensure_reddit_client()
            await aggregator._ensure_reddit_client()  # only initializes once

        reddit.assert_called_once_with(
            client_id="id", client_secret="secret", user_agent="news-llama/1.0", username="u", password="p"
        )
        assert aggregator._client_initialized

    @pytest.mark.asyncio
    async def test_read_only_credentials(self):
        aggregator = RedditAggregator(
            _config(reddit_client_id="id", reddit_client_secret="secret", reddit_user_agent="agent/2")
        )
        with patch("src.aggregators.reddit_aggregator.asyncpraw.Reddit") as reddit:
            await aggregator._ensure_reddit_client()

        reddit.assert_called_once_with(client_id="id", client_secret="secret", user_agent="agent/2")

    @pytest.mark.asyncio
    async def test_missing_credentials_disable_collection_and_search(self):
        aggregator = RedditAggregator(_config())

        assert await aggregator.collect() == []
        assert await aggregator.search_reddit("rust", "rust") == []
        assert aggregator._initialization_failed
        await aggregator.close()  # no client: nothing to close

    @pytest.mark.asyncio
    async def test_client_construction_error_disables_reddit(self):
        aggregator = RedditAggregator(_config(reddit_client_id="id", reddit_client_secret="secret"))
        with patch("src.aggregators.reddit_aggregator.asyncpraw.Reddit", side_effect=RuntimeError("bad")):
            await aggregator._ensure_reddit_client()

        assert aggregator.reddit is None and aggregator._initialization_failed


class TestCollect:
    @pytest.mark.asyncio
    async def test_collects_valid_recent_posts(self):
        posts = [
            _submission(),
            _submission(title="Old post with a long enough title", created_utc=time.time() - 30 * 3600),
            _submission(title="Downvoted post with a long title", score=0),
            _submission(title="Short title"),
        ]
        aggregator = _aggregator(FakeSubreddit(top=posts), sources=[{"subreddit": "rust", "category": "Rust"}])

        [article] = await aggregator.collect()

        assert str(article.url) == "https://reddit.com/r/rust/comments/1/story/"
        assert article.source == "Reddit r/rust"
        assert article.category == "Rust"
        assert article.content == "https://example.com/story"
        assert article.metadata == {
            "score": 42,
            "num_comments": 7,
            "upvote_ratio": 0.95,
            "is_self_post": False,
            "flair": "news",
        }
        await aggregator.close()
        aggregator.reddit.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_self_posts_need_enough_text(self):
        posts = [
            _submission(is_self=True, selftext="word " * 20, author=None),
            _submission(title="Empty self post title here", is_self=True, selftext="   "),
            _submission(title="Tiny", is_self=True, selftext="short"),
        ]
        aggregator = _aggregator(FakeSubreddit(top=posts))

        [article] = await aggregator._collect_from_subreddit({"subreddit": "rust", "category": "Rust"})

        assert article.author == "deleted"
        assert article.metadata["is_self_post"] is True

    @pytest.mark.asyncio
    async def test_failing_subreddit_does_not_stop_others(self):
        aggregator = _aggregator(
            FakeSubreddit(top=[_submission()]),
            sources=[{"subreddit": "broken", "category": "x"}, {"subreddit": "rust", "category": "Rust"}],
        )
        original = aggregator._collect_from_subreddit

        async def collect(config):
            if config["subreddit"] == "broken":
                raise RuntimeError("403")
            return await original(config)

        aggregator._collect_from_subreddit = collect

        assert len(await aggregator.collect()) == 1

    @pytest.mark.asyncio
    async def test_unparseable_submission_is_skipped(self):
        aggregator = _aggregator(FakeSubreddit(top=[SimpleNamespace(), _submission()]))

        assert len(await aggregator._collect_from_subreddit({"subreddit": "rust", "category": "Rust"})) == 1


class TestSearch:
    @pytest.mark.asyncio
    async def test_widens_time_filter_until_results(self):
        subreddit = FakeSubreddit(searches={"year": [_submission()]})
        aggregator = _aggregator(subreddit)

        [article] = await aggregator.search_reddit("rust", "Rust")

        assert subreddit.search_calls == ["month", "year"]
        assert aggregator.reddit.requested == ["all"]
        assert article.category == "Rust"

    @pytest.mark.asyncio
    async def test_no_results_in_any_window(self):
        subreddit = FakeSubreddit(searches={"all": [SimpleNamespace()]})
        aggregator = _aggregator(subreddit)

        assert await aggregator.search_reddit("nothing", "x") == []
        assert subreddit.search_calls == ["month", "year", "all"]

    @pytest.mark.asyncio
    async def test_search_error_returns_nothing(self):
        aggregator = _aggregator(FakeSubreddit())
        aggregator.reddit.subreddit = AsyncMock(side_effect=RuntimeError("503"))

        assert await aggregator.search_reddit("rust", "Rust") == []


class TestMediaExtraction:
    @pytest.mark.asyncio
    async def test_video_link(self, no_image_downloads):
        aggregator = _aggregator(FakeSubreddit())
        submission = _submission(url="https://v.redd.it/abc123")

        assert await aggregator._extract_media_info(submission) == ("https://v.redd.it/abc123", False, 0, True)
        article = await aggregator._parse_submission(submission, "x")
        assert article.local_image_path is None
        no_image_downloads.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_gallery_uses_first_image(self):
        submission = _submission(
            url="https://www.reddit.com/gallery/abc",
            is_gallery=True,
            gallery_data={"items": [{"media_id": "m1"}, {"media_id": "m2"}]},
            media_metadata={"m1": {"s": {"u": "https://preview.redd.it/m1.jpg?a=1&amp;b=2"}}},
        )

        info = await _aggregator(FakeSubreddit())._extract_media_info(submission)

        assert info == ("https://preview.redd.it/m1.jpg?a=1&b=2", True, 2, False)

    @pytest.mark.asyncio
    async def test_direct_image_url_is_cached(self, no_image_downloads):
        aggregator = _aggregator(FakeSubreddit())
        submission = _submission(url="https://i.redd.it/picture.png")

        article = await aggregator._parse_submission(submission, "x")

        assert str(article.image_url) == "https://i.redd.it/picture.png"
        assert article.local_image_path == "cache/abc.jpg"

    @pytest.mark.asyncio
    async def test_preview_image_fallback(self):
        submission = _submission(preview={"images": [{"source": {"url": "https://preview.redd.it/p.jpg?x=1&amp;y=2"}}]})

        info = await _aggregator(FakeSubreddit())._extract_media_info(submission)

        assert info == ("https://preview.redd.it/p.jpg?x=1&y=2", False, 0, False)

    @pytest.mark.asyncio
    async def test_no_media(self):
        info = await _aggregator(FakeSubreddit())._extract_media_info(_submission(url=None))

        assert info == (None, False, 0, False)
