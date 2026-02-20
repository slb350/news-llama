"""
Image caching utility for downloading and storing article images locally.
"""

import asyncio
import hashlib
import re
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import aiohttp
from PIL import Image
import io

from src.utils.logger import logger

# Supported image domains
IMAGE_DOMAINS = {
    "i.redd.it",
    "i.imgur.com",
    "imgur.com",
    "preview.redd.it",
}

# Video domains (return link instead of embedding)
VIDEO_DOMAINS = {
    "redgifs.com",
    "v.redd.it",
    "gfycat.com",
}

# Image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# Cache configuration
CACHE_DIR = Path("src/web/static/article-images")
MAX_IMAGE_WIDTH = 800
MAX_IMAGE_HEIGHT = 600
JPEG_QUALITY = 85


def is_image_url(url: str) -> bool:
    """Check if URL points to an image based on domain or extension."""
    if not url:
        return False

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()

    # Check domain
    if any(img_domain in domain for img_domain in IMAGE_DOMAINS):
        return True

    # Check extension
    if any(path.endswith(ext) for ext in IMAGE_EXTENSIONS):
        return True

    return False


def is_video_url(url: str) -> bool:
    """Check if URL points to a video."""
    if not url:
        return False

    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    return any(vid_domain in domain for vid_domain in VIDEO_DOMAINS)


def get_cache_filename(url: str) -> str:
    """Generate a unique cache filename for a URL."""
    # Hash the URL for a unique, filesystem-safe name
    url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
    return f"{url_hash}.jpg"


def get_cached_path(url: str) -> Optional[Path]:
    """Get the cached file path if it exists."""
    filename = get_cache_filename(url)
    cache_path = CACHE_DIR / filename
    if cache_path.exists():
        return cache_path
    return None


async def download_and_cache_image(url: str) -> Optional[str]:
    """
    Download an image and cache it locally.

    Returns the web-accessible path (e.g., /static/article-images/abc123.jpg)
    or None if download fails.
    """
    if not url:
        return None

    # Ensure cache directory exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    filename = get_cache_filename(url)
    cache_path = CACHE_DIR / filename

    # Return cached path if already exists
    if cache_path.exists():
        return f"/static/article-images/{filename}"

    try:
        # Clean up Reddit preview URLs (they have HTML entities)
        clean_url = url.replace("&amp;", "&")

        async with aiohttp.ClientSession() as session:
            async with session.get(
                clean_url,
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                }
            ) as response:
                if response.status != 200:
                    logger.warning(f"Failed to download image: {url} (status {response.status})")
                    return None

                content_type = response.headers.get("Content-Type", "")
                if not content_type.startswith("image/"):
                    logger.warning(f"Not an image: {url} (content-type: {content_type})")
                    return None

                data = await response.read()

        # Process image with PIL
        image = Image.open(io.BytesIO(data))

        # Convert to RGB if necessary (handles PNG transparency, RGBA, etc.)
        if image.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")

        # Resize if too large (maintain aspect ratio)
        if image.width > MAX_IMAGE_WIDTH or image.height > MAX_IMAGE_HEIGHT:
            image.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.Resampling.LANCZOS)

        # Save as optimized JPEG
        image.save(cache_path, "JPEG", quality=JPEG_QUALITY, optimize=True)

        logger.debug(f"Cached image: {url} -> {cache_path}")
        return f"/static/article-images/{filename}"

    except asyncio.TimeoutError:
        logger.warning(f"Timeout downloading image: {url}")
        return None
    except Exception as e:
        logger.warning(f"Error caching image {url}: {e}")
        return None


async def cache_images_batch(urls: list[str], max_concurrent: int = 5) -> dict[str, Optional[str]]:
    """
    Cache multiple images concurrently.

    Returns a dict mapping original URLs to cached paths.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def download_with_limit(url: str) -> Tuple[str, Optional[str]]:
        async with semaphore:
            cached_path = await download_and_cache_image(url)
            return (url, cached_path)

    tasks = [download_with_limit(url) for url in urls if url]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    url_to_path = {}
    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"Batch download error: {result}")
            continue
        url, path = result
        url_to_path[url] = path

    return url_to_path
