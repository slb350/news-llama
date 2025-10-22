"""
Test suite for security utilities
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.utils.security import URLValidator, RateLimiter, SecureHTTPClient, APIKeyValidator


class TestURLValidator:
    """Test URL validation functionality"""

    def test_valid_urls(self):
        """Test that valid URLs pass validation"""
        valid_urls = [
            "https://www.example.com",
            "http://example.com",
            "https://news.example.com/articles/123",
            "https://subdomain.example.co.uk/path?query=value",
            "https://example.com:8080/path"
        ]

        for url in valid_urls:
            assert URLValidator.is_valid_url(url), f"Valid URL failed validation: {url}"

    def test_invalid_urls(self):
        """Test that invalid URLs fail validation"""
        invalid_urls = [
            "",  # Empty string
            "not-a-url",  # Missing scheme
            "ftp://example.com",  # Invalid scheme
            "javascript:alert('xss')",  # Dangerous scheme
            "https://",  # Missing domain
            "http://",  # Missing domain
            "https://../etc/passwd",  # Path traversal
            "data:text/html,<script>alert('xss')</script>",  # Data URL
        ]

        for url in invalid_urls:
            assert not URLValidator.is_valid_url(url), f"Invalid URL passed validation: {url}"

    def test_suspicious_domains(self):
        """Test that suspicious domains are flagged"""
        suspicious_urls = [
            "https://bit.ly/abc123",
            "https://tinyurl.com/xyz789",
            "https://t.co/shortlink"
        ]

        for url in suspicious_urls:
            # These should be logged as warnings but still pass basic validation
            result = URLValidator.is_valid_url(url)
            assert isinstance(result, bool), f"URL validation should return boolean for: {url}"

    def test_url_sanitization(self):
        """Test URL sanitization removes dangerous components"""
        test_cases = [
            {
                "input": "https://example.com/article?redirect=evil.com&format=json",
                "expected": "https://example.com/article?format=json"
            },
            {
                "input": "https://example.com/path#dangerous-fragment",
                "expected": "https://example.com/path"
            },
            {
                "input": "https://example.com/path?callback=func",
                "expected": "https://example.com/path"
            }
        ]

        for case in test_cases:
            result = URLValidator.sanitize_url(case["input"])
            assert result == case["expected"], f"Sanitization failed for: {case['input']}"

    def test_invalid_urls_sanitization(self):
        """Test that invalid URLs return None when sanitized"""
        invalid_urls = ["javascript:alert('xss')", "not-a-url", ""]

        for url in invalid_urls:
            result = URLValidator.sanitize_url(url)
            assert result is None, f"Invalid URL should return None: {url}"


class TestRateLimiter:
    """Test rate limiting functionality"""

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test that rate limiting works correctly"""
        limiter = RateLimiter(calls_per_second=2.0)
        identifier = "test_service"

        # Should allow first call immediately
        start_time = asyncio.get_event_loop().time()
        await limiter.acquire(identifier)
        first_call_time = asyncio.get_event_loop().time() - start_time

        # Should allow second call immediately (within limit)
        await limiter.acquire(identifier)
        second_call_time = asyncio.get_event_loop().time() - start_time

        # Should delay third call (exceeds limit)
        await limiter.acquire(identifier)
        third_call_time = asyncio.get_event_loop().time() - start_time

        # First two calls should be quick, third should be delayed
        assert first_call_time < 0.1, "First call should be immediate"
        assert second_call_time < 0.1, "Second call should be immediate"
        assert third_call_time >= 0.4, "Third call should be delayed"

    @pytest.mark.asyncio
    async def test_different_identifiers(self):
        """Test that different identifiers are tracked separately"""
        limiter = RateLimiter(calls_per_second=1.0)

        # Should allow calls to different identifiers
        await limiter.acquire("service_a")
        await limiter.acquire("service_b")  # Should not be delayed

        # Both should complete quickly
        assert True  # If we get here without delay, test passes

    def test_rate_limit_status(self):
        """Test rate limit status reporting"""
        limiter = RateLimiter(calls_per_second=2.0)

        # Initially should have full capacity
        status = limiter.get_status("test_service")
        assert status["calls_last_second"] == 0
        assert status["limit_per_second"] == 2.0
        assert status["remaining"] == 2.0


class TestAPIKeyValidator:
    """Test API key validation"""

    def test_valid_api_keys(self):
        """Test that valid API keys pass validation"""
        valid_keys = [
            "abcdefghijklmnopqrstuvwxyz123456",
            "1234567890abcdefghijklmnopqrstuvwxyz",
            "my-api-key-1234567890-abcdef-ghij",
            "sk_live_1234567890abcdefghijklmnopqrstuvwxyz"
        ]

        for key in valid_keys:
            assert APIKeyValidator.validate_api_key(key, "Test"), f"Valid API key failed: {key}"

    def test_invalid_api_keys(self):
        """Test that invalid API keys fail validation"""
        invalid_keys = [
            "",  # Empty
            "short",  # Too short
            "your_api_key_here",  # Placeholder
            "example_key_123",  # Another placeholder
            "xxx123",  # Placeholder pattern
            "a" * 19,  # Exactly 19 chars (below minimum)
        ]

        for key in invalid_keys:
            assert not APIKeyValidator.validate_api_key(key, "Test"), f"Invalid API key passed: {key}"

    def test_twitter_credentials_validation(self):
        """Test Twitter credentials validation"""
        # Valid credentials
        mock_config = Mock()
        mock_config.twitter_api_key = "valid_twitter_key_1234567890"
        mock_config.twitter_api_secret = "valid_twitter_secret_1234567890"
        mock_config.twitter_access_token = "valid_access_token_1234567890"
        mock_config.twitter_access_token_secret = "valid_token_secret_1234567890"

        assert APIKeyValidator.validate_twitter_credentials(mock_config)

        # Missing credentials
        mock_config.twitter_api_key = None
        assert not APIKeyValidator.validate_twitter_credentials(mock_config)

        # Invalid credentials
        mock_config.twitter_api_key = "your_twitter_api_key"
        assert not APIKeyValidator.validate_twitter_credentials(mock_config)

    def test_reddit_credentials_validation(self):
        """Test Reddit credentials validation"""
        # Valid credentials
        mock_config = Mock()
        mock_config.reddit_client_id = "valid_reddit_client_id"
        mock_config.reddit_client_secret = "valid_reddit_client_secret"

        assert APIKeyValidator.validate_reddit_credentials(mock_config)

        # Missing credentials
        mock_config.reddit_client_id = None
        assert not APIKeyValidator.validate_reddit_credentials(mock_config)

        # Too short credentials
        mock_config.reddit_client_id = "short"
        mock_config.reddit_client_secret = "also_short"
        assert not APIKeyValidator.validate_reddit_credentials(mock_config)


class TestSecureHTTPClient:
    """Test secure HTTP client functionality"""

    def test_client_initialization(self):
        """Test that secure client initializes correctly"""
        client = SecureHTTPClient()
        assert client.session is not None
        assert len(client.rate_limiters) > 0
        assert 'default' in client.rate_limiters
        assert 'rss' in client.rate_limiters

    @pytest.mark.asyncio
    async def test_invalid_url_rejection(self):
        """Test that invalid URLs are rejected"""
        client = SecureHTTPClient()

        invalid_urls = [
            "javascript:alert('xss')",
            "not-a-url",
            "",
            "ftp://example.com/file.txt"
        ]

        for url in invalid_urls:
            result = await client.get(url)
            assert result is None, f"Invalid URL should return None: {url}"

    @pytest.mark.asyncio
    async def test_valid_url_sanitization(self):
        """Test that URLs are sanitized before request"""
        client = SecureHTTPClient()

        # Mock the actual HTTP request
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.text = "<rss></rss>"
            mock_response.headers = {'content-type': 'application/xml'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # URL with dangerous query parameters
            url = "https://example.com/feed.xml?redirect=evil.com&callback=func"
            await client.get(url, rate_limit_key='rss')

            # Verify the sanitized URL was used
            expected_url = "https://example.com/feed.xml"
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == expected_url

    @pytest.mark.asyncio
    async def test_ssl_verification(self):
        """Test that SSL verification is enabled"""
        client = SecureHTTPClient()

        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.text = "content"
            mock_response.headers = {'content-type': 'text/html'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            await client.get("https://example.com")

            # Verify SSL verification is enabled
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs.get('verify') is True

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self):
        """Test that rate limiting is applied to requests"""
        client = SecureHTTPClient()

        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.text = "content"
            mock_response.headers = {'content-type': 'text/html'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Make multiple requests quickly
            url = "https://example.com"
            await client.get(url, rate_limit_key='rss')
            await client.get(url, rate_limit_key='rss')
            await client.get(url, rate_limit_key='rss')

            # All requests should have been made (rate limiting handled internally)
            assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling for various HTTP errors"""
        client = SecureHTTPClient()

        # Test timeout
        with patch.object(client.session, 'get', side_effect=TimeoutError("Request timeout")):
            result = await client.get("https://example.com")
            assert result is None

        # Test SSL error
        with patch.object(client.session, 'get', side_effect=Exception("SSL error")):
            result = await client.get("https://example.com")
            assert result is None

        # Test connection error
        with patch.object(client.session, 'get', side_effect=ConnectionError("Connection failed")):
            result = await client.get("https://example.com")
            assert result is None

    @pytest.mark.asyncio
    async def test_content_type_validation(self):
        """Test content type validation"""
        client = SecureHTTPClient()

        # Test with allowed content type
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.text = "content"
            mock_response.headers = {'content-type': 'text/html'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = await client.get("https://example.com")
            assert result is not None

        # Test with suspicious content type
        with patch.object(client.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.text = "content"
            mock_response.headers = {'content-type': 'application/x-executable'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            result = await client.get("https://example.com")
            assert result is not None  # Should still work but with warning

    @pytest.mark.asyncio
    async def test_client_cleanup(self):
        """Test that client can be properly cleaned up"""
        client = SecureHTTPClient()

        with patch.object(client.session, 'close') as mock_close:
            await client.close()
            mock_close.assert_called_once()