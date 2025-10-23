"""
File caching for News Llama web application.

LRU cache for newsletter HTML files to reduce disk I/O.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional


# LRU cache with max 100 newsletters cached
# Average newsletter ~100KB, so max ~10MB memory
@lru_cache(maxsize=100)
def read_newsletter_file(file_path: str) -> Optional[bytes]:
    """
    Read newsletter file with LRU caching.

    Args:
        file_path: Path to newsletter HTML file

    Returns:
        File contents as bytes, or None if file doesn't exist
    """
    path = Path(file_path)
    if not path.exists():
        return None

    try:
        with open(path, "rb") as f:
            return f.read()
    except (IOError, OSError):
        return None


def clear_cache():
    """Clear the file cache."""
    read_newsletter_file.cache_clear()


def get_cache_info():
    """
    Get cache statistics.

    Returns:
        CacheInfo named tuple with hits, misses, maxsize, currsize
    """
    return read_newsletter_file.cache_info()
