"""
Pytest configuration for web unit tests.

Provides shared fixtures and setup/teardown for all tests.
"""

import pytest


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """
    Automatically reset rate limiter before each test.

    Prevents rate limiting from affecting unit tests that make
    multiple requests in rapid succession.
    """
    from src.web.rate_limiter import newsletter_rate_limiter

    # Clear rate limiter state before test
    newsletter_rate_limiter._requests.clear()

    yield

    # Clean up after test
    newsletter_rate_limiter._requests.clear()
