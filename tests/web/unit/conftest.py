"""
Pytest configuration for web unit tests.

Provides shared fixtures and setup/teardown for all tests.
"""

import pytest


@pytest.fixture(autouse=True)
def reset_rate_limiter(request):
    """
    Automatically reset rate limiter before each test.

    Prevents rate limiting from affecting unit tests that make
    multiple requests in rapid succession.

    Skip this for tests that are specifically testing rate limiting.
    """
    # Don't reset for tests that are testing rate limiting itself
    if "test_newsletter_generation_has_rate_limit" in request.node.name:
        yield
        return

    from src.web.rate_limiter import newsletter_rate_limiter

    # Clear rate limiter state before test
    newsletter_rate_limiter._requests.clear()

    yield

    # Clean up after test
    newsletter_rate_limiter._requests.clear()
