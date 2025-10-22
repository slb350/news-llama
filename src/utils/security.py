"""
Security utilities for News Llama
"""
import re
import time
import asyncio
from typing import Optional, Dict, List
from urllib.parse import urlparse
from collections import defaultdict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils.constants import (
    ValidationConstants,
    SecurityConstants,
    HTTPConstants,
    RateLimitConstants
)
from src.utils.logger import logger


class URLValidator:
    """Validates and sanitizes URLs"""

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """
        Validate if a URL is properly formatted and safe

        Args:
            url: URL to validate

        Returns:
            True if URL is valid and safe, False otherwise
        """
        if not url or not isinstance(url, str):
            return False

        # Basic format validation
        if not ValidationConstants.URL_PATTERN.match(url):
            return False

        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                return False

            # Check netloc (domain)
            if not parsed.netloc:
                return False

            # Check for suspicious domains (exact match or subdomain)
            domain = parsed.netloc.lower()
            for suspicious in SecurityConstants.SUSPICIOUS_DOMAINS:
                # Exact match or subdomain (e.g., "t.co" matches "t.co" or "foo.t.co")
                if domain == suspicious or domain.endswith('.' + suspicious):
                    logger.warning(f"Suspicious domain detected: {domain}")
                    return False

            # Check for localhost in production (optional)
            if domain in ['localhost', '127.0.0.1'] and parsed.port:
                logger.warning(f"Localhost URL with port detected: {url}")
                # Allow for development but log warning

            return True

        except Exception as e:
            logger.error(f"URL validation error for '{url}': {e}")
            return False

    @staticmethod
    def sanitize_url(url: str) -> Optional[str]:
        """
        Sanitize a URL by removing dangerous components

        Args:
            url: URL to sanitize

        Returns:
            Sanitized URL or None if invalid
        """
        if not URLValidator.is_valid_url(url):
            return None

        try:
            parsed = urlparse(url)

            # Remove URL fragments and dangerous query parameters
            # Keep common, harmless params like format/json which are widely used by news feeds
            dangerous_params = ['redirect', 'return', 'callback']

            if parsed.query:
                query_params = []
                for param in parsed.query.split('&'):
                    if '=' in param:
                        key = param.split('=')[0].lower()
                        if key not in dangerous_params:
                            query_params.append(param)

                sanitized_query = '&'.join(query_params) if query_params else ''
            else:
                sanitized_query = ''

            # Reconstruct URL without fragment
            sanitized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if sanitized_query:
                sanitized_url += f"?{sanitized_query}"

            return sanitized_url

        except Exception as e:
            logger.error(f"URL sanitization error for '{url}': {e}")
            return None


class RateLimiter:
    """Rate limiter for external API calls"""

    def __init__(self, calls_per_second: float = RateLimitConstants.DEFAULT_CALLS_PER_SECOND):
        self.calls_per_second = calls_per_second
        self.last_calls = defaultdict(list)
        self.lock = asyncio.Lock()

    async def acquire(self, identifier: str = "default") -> None:
        """
        Acquire rate limit for a given identifier

        Args:
            identifier: Unique identifier for the resource (domain, API name, etc.)
        """
        async with self.lock:
            now = time.time()
            cutoff = now - 1.0

            # Clean old calls
            self.last_calls[identifier] = [
                call_time for call_time in self.last_calls[identifier]
                if call_time > cutoff
            ]

            # Check if we need to wait
            if len(self.last_calls[identifier]) >= self.calls_per_second:
                sleep_time = 1.0 - (now - self.last_calls[identifier][0])
                if sleep_time > 0:
                    logger.debug(f"Rate limiting {identifier}: waiting {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)

            # Record this call
            self.last_calls[identifier].append(time.time())

    def get_status(self, identifier: str = "default") -> Dict[str, int]:
        """
        Get current rate limit status

        Args:
            identifier: Resource identifier

        Returns:
            Dictionary with current usage statistics
        """
        now = time.time()
        cutoff = now - 1.0

        recent_calls = [
            call_time for call_time in self.last_calls[identifier]
            if call_time > cutoff
        ]

        return {
            "calls_last_second": len(recent_calls),
            "limit_per_second": self.calls_per_second,
            "remaining": max(0, self.calls_per_second - len(recent_calls))
        }


class SecureHTTPClient:
    """Secure HTTP client with rate limiting and proper SSL handling"""

    def __init__(self):
        self.session = requests.Session()
        self.rate_limiters = {
            'default': RateLimiter(RateLimitConstants.DEFAULT_CALLS_PER_SECOND),
            'rss': RateLimiter(RateLimitConstants.RSS_REQUESTS_PER_SECOND),
            'twitter': RateLimiter(RateLimitConstants.TWITTER_REQUESTS_PER_SECOND),
            'reddit': RateLimiter(RateLimitConstants.REDDIT_REQUESTS_PER_SECOND),
            'web_search': RateLimiter(RateLimitConstants.WEB_SEARCH_REQUESTS_PER_MINUTE / 60.0)
        }

        # Configure retry strategy
        retry_strategy = Retry(
            total=HTTPConstants.MAX_RETRIES,
            backoff_factor=HTTPConstants.RETRY_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set headers
        self.session.headers.update({
            'User-Agent': HTTPConstants.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',  # Do Not Track
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    async def get(self, url: str, rate_limit_key: str = 'default', **kwargs) -> Optional[requests.Response]:
        """
        Make a secure HTTP GET request with rate limiting

        Args:
            url: URL to request
            rate_limit_key: Key for rate limiting
            **kwargs: Additional arguments for requests

        Returns:
            Response object or None if request fails
        """
        # Validate and sanitize URL
        if not URLValidator.is_valid_url(url):
            logger.error(f"Invalid URL rejected: {url}")
            return None

        sanitized_url = URLValidator.sanitize_url(url)
        if not sanitized_url:
            logger.error(f"Could not sanitize URL: {url}")
            return None

        # Apply rate limiting
        await self.rate_limiters[rate_limit_key].acquire(sanitized_url)

        # Set default parameters
        kwargs.setdefault('timeout', HTTPConstants.DEFAULT_TIMEOUT)
        kwargs.setdefault('verify', True)  # Always verify SSL
        kwargs.setdefault('allow_redirects', True)

        try:
            logger.debug(f"Making secure GET request to: {sanitized_url}")
            response = self.session.get(sanitized_url, **kwargs)

            # Check response
            response.raise_for_status()

            # Validate content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(allowed in content_type for allowed in SecurityConstants.ALLOWED_MIME_TYPES):
                logger.warning(f"Suspicious content type '{content_type}' from {url}")

            return response

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {url}")
            return None
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL error for {url}: {e}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error for {url}: {e}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error requesting {url}: {e}")
            return None

    async def close(self):
        """Close the HTTP session"""
        self.session.close()


class APIKeyValidator:
    """Validates API keys and credentials"""

    @staticmethod
    def validate_api_key(api_key: str, service_name: str) -> bool:
        """
        Validate an API key format

        Args:
            api_key: API key to validate
            service_name: Name of the service (for logging)

        Returns:
            True if API key format is valid
        """
        if not api_key or not isinstance(api_key, str):
            logger.error(f"Invalid API key format for {service_name}: empty or not string")
            return False

        # Basic length check
        if len(api_key) < 20:
            logger.error(f"API key for {service_name} too short (minimum 20 characters)")
            return False

        # Check for placeholder values
        placeholder_indicators = [
            'your_api_key', 'example_key', 'test_key', 'demo_key', 'fake_key', 'mock_key',
            'xxx', 'yyy', 'zzz'
        ]

        api_key_lower = api_key.lower()
        if any(indicator in api_key_lower for indicator in placeholder_indicators):
            logger.error(f"API key for {service_name} appears to be a placeholder")
            return False

        # Basic pattern validation
        if not ValidationConstants.API_KEY_PATTERN.match(api_key):
            logger.warning(f"API key for {service_name} doesn't match expected pattern")
            # Don't fail here as different services have different formats

        logger.debug(f"API key for {service_name} passed validation")
        return True

    @staticmethod
    def validate_twitter_credentials(social_media_config) -> bool:
        """
        Validate Twitter API credentials

        Args:
            social_media_config: SocialMediaConfig instance
        """
        required_keys = [
            'twitter_api_key', 'twitter_api_secret',
            'twitter_access_token', 'twitter_access_token_secret'
        ]

        for key in required_keys:
            api_key = getattr(social_media_config, key, None)
            if not APIKeyValidator.validate_api_key(api_key, f"Twitter {key}"):
                return False

        return True

    @staticmethod
    def validate_reddit_credentials(social_media_config) -> bool:
        """
        Validate Reddit API credentials

        Args:
            social_media_config: SocialMediaConfig instance
        """
        required_keys = ['reddit_client_id', 'reddit_client_secret']

        for key in required_keys:
            api_key = getattr(social_media_config, key, None)
            if not api_key or len(api_key) < 10:
                logger.error(f"Reddit {key} is missing or too short")
                return False

        return True


# Global secure HTTP client instance
_secure_client = None

def get_secure_http_client() -> SecureHTTPClient:
    """Get or create the global secure HTTP client"""
    global _secure_client
    if _secure_client is None:
        _secure_client = SecureHTTPClient()
    return _secure_client

async def close_secure_http_client():
    """Close the global secure HTTP client"""
    global _secure_client
    if _secure_client is not None:
        await _secure_client.close()
        _secure_client = None