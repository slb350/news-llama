"""
Rate limiting for News Llama web application.

Simple in-memory rate limiter with sliding window algorithm.
For production, consider Redis-backed rate limiting.
"""

import time
from collections import defaultdict, deque
from typing import Dict, Deque, Tuple
from functools import wraps

from fastapi import HTTPException, status


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window.

    Tracks requests per identifier (e.g., user_id) and enforces
    limits over a time window.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Store deques of timestamps per identifier
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)

    def is_allowed(self, identifier: str) -> Tuple[bool, int]:
        """
        Check if request is allowed for identifier.

        Args:
            identifier: Unique identifier (e.g., user_id)

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Get request queue for this identifier
        request_queue = self._requests[identifier]

        # Remove timestamps outside the current window
        while request_queue and request_queue[0] < window_start:
            request_queue.popleft()

        # Check if under limit
        current_count = len(request_queue)
        remaining = max(0, self.max_requests - current_count)

        if current_count < self.max_requests:
            # Add this request timestamp
            request_queue.append(now)
            return True, remaining - 1

        return False, 0

    def reset(self, identifier: str) -> None:
        """
        Reset rate limit for identifier.

        Args:
            identifier: Unique identifier to reset
        """
        if identifier in self._requests:
            del self._requests[identifier]

    def cleanup_old_entries(self) -> None:
        """
        Clean up expired entries to prevent memory growth.

        Should be called periodically in production.
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Remove identifiers with no recent requests
        identifiers_to_remove = []
        for identifier, request_queue in self._requests.items():
            # Remove old timestamps
            while request_queue and request_queue[0] < window_start:
                request_queue.popleft()

            # If queue is empty, mark for removal
            if not request_queue:
                identifiers_to_remove.append(identifier)

        # Remove empty queues
        for identifier in identifiers_to_remove:
            del self._requests[identifier]


# Global rate limiter instance for newsletter generation
# 10 requests per 60 seconds per user
newsletter_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)


def rate_limit(identifier_func, limiter: RateLimiter = newsletter_rate_limiter):
    """
    Decorator to apply rate limiting to FastAPI endpoints.

    Args:
        identifier_func: Function to extract identifier from request
        limiter: RateLimiter instance to use

    Example:
        @rate_limit(lambda user: str(user.id))
        async def generate_newsletter(user: User = Depends(get_current_user)):
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract identifier from function arguments
            # Look for the result of identifier_func in kwargs
            identifier = None

            # Try to get identifier from kwargs
            for key, value in kwargs.items():
                try:
                    identifier = identifier_func(value)
                    break
                except (AttributeError, TypeError):
                    continue

            if identifier is None:
                # No identifier found, allow request
                # (fail open for safety)
                return await func(*args, **kwargs)

            # Check rate limit
            is_allowed, remaining = limiter.is_allowed(str(identifier))

            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {limiter.window_seconds} seconds.",
                    headers={"Retry-After": str(limiter.window_seconds)},
                )

            # Add remaining count to response headers would require middleware
            # For now, just allow the request
            return await func(*args, **kwargs)

        return wrapper

    return decorator
