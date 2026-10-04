"""Which aggregators NewsLlama enables from the configured credentials."""

from unittest.mock import patch

from main import NewsLlama


class TestSetupAggregators:
    def test_twitter_credentials_do_not_enable_a_twitter_aggregator(self):
        """There is no Twitter integration, so valid credentials must not add a source of fake tweets"""
        with patch(
            "src.utils.config.SocialMediaConfig.validate_twitter_credentials", return_value=True
        ), patch("src.utils.config.SocialMediaConfig.validate_reddit_credentials", return_value=False):
            news_llama = NewsLlama(user_interests=["AI"])

        assert set(news_llama.aggregators) == {"rss"}

    def test_reddit_credentials_enable_reddit(self):
        with patch("src.utils.config.SocialMediaConfig.validate_reddit_credentials", return_value=True):
            news_llama = NewsLlama(user_interests=["AI"])

        assert "reddit" in news_llama.aggregators

    def test_reddit_validation_error_leaves_reddit_disabled(self):
        with patch(
            "src.utils.config.SocialMediaConfig.validate_reddit_credentials",
            side_effect=RuntimeError("bad config"),
        ):
            news_llama = NewsLlama(user_interests=["AI"])

        assert "reddit" not in news_llama.aggregators
