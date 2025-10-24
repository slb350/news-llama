"""
NewsLlama engine wrapper for web application integration.

Provides interface between web app and main NewsLlama newsletter generation engine.
"""

import logging
from datetime import date
from pathlib import Path
from sqlalchemy.orm import Session

# Import main NewsLlama engine
from main import NewsLlama
from src.web.services import llama_wrapper_tier1

logger = logging.getLogger(__name__)


# Custom Exceptions
class NewsLlamaWrapperError(Exception):
    """Base exception for wrapper errors."""

    pass


def generate_newsletter_for_interests(interests: list[str], output_date: date) -> str:
    """
    Generate newsletter for given interests and date.

    Args:
        interests: List of user interest topics
        output_date: Date for newsletter

    Returns:
        Path to generated HTML file

    Raises:
        NewsLlamaWrapperError: If generation fails
    """
    import asyncio

    try:
        # Get output file path
        output_file = get_output_file_path(output_date)

        # Ensure output directory exists
        ensure_output_directory(str(Path(output_file).parent))

        # Initialize NewsLlama with user interests
        news_llama = NewsLlama(user_interests=interests)

        # Generate the newsletter (run async method in sync context)
        asyncio.run(news_llama.run())

        # Verify output file was created
        if not Path(output_file).exists():
            raise NewsLlamaWrapperError(
                f"Output file {output_file} not created after generation"
            )

        return output_file

    except Exception as e:
        if isinstance(e, NewsLlamaWrapperError):
            raise
        raise NewsLlamaWrapperError(f"Failed to generate newsletter: {str(e)}")


def get_output_file_path(output_date: date, guid: str = None) -> str:
    """
    Get output file path for newsletter.

    Args:
        output_date: Date for newsletter
        guid: Optional GUID for uniqueness

    Returns:
        Absolute path to output file
    """
    # Format date as YYYY-MM-DD
    date_str = output_date.strftime("%Y-%m-%d")

    # Build filename
    if guid:
        filename = f"news-{date_str}-{guid}.html"
    else:
        filename = f"news-{date_str}.html"

    # Get project root (parent of src/)
    project_root = Path(__file__).parent.parent.parent.parent

    # Build absolute path: project_root/output/filename
    # Note: NewsLlama outputs to output/, not output/newsletters/
    output_path = project_root / "output" / filename

    return str(output_path.absolute())


def ensure_output_directory(directory_path: str):
    """
    Ensure output directory exists, create if missing.

    Args:
        directory_path: Path to directory

    Raises:
        NewsLlamaWrapperError: If directory cannot be created
    """
    try:
        dir_path = Path(directory_path)
        dir_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise NewsLlamaWrapperError(
            f"Failed to create output directory {directory_path}: {str(e)}"
        )


def generate_newsletter_with_tier1(
    interests: list[str],
    output_date: date,
    newsletter_id: int = None,
    db: Session = None,
) -> str:
    """
    Generate newsletter using Tier 1 sources when available.

    Uses pre-discovered Tier 1 sources for fast path generation (2 minutes)
    when coverage >= 90%, otherwise falls back to LLM discovery.

    Args:
        interests: List of user interest topics
        output_date: Date for newsletter
        newsletter_id: Optional newsletter ID for tracking contributions
        db: Optional database session for Tier 1 access

    Returns:
        Path to generated HTML file

    Raises:
        NewsLlamaWrapperError: If generation fails
    """
    import asyncio

    try:
        output_file = get_output_file_path(output_date)
        ensure_output_directory(str(Path(output_file).parent))

        # Check Tier 1 coverage
        pre_discovered = None
        if db:
            tier1_sources, coverage = llama_wrapper_tier1.get_sources_with_coverage(
                db, interests
            )

            if coverage >= llama_wrapper_tier1.COVERAGE_THRESHOLD:
                # Fast path: Use Tier 1 only
                logger.info(f"Fast path: Using Tier 1 only (coverage: {coverage:.1f}%)")
                filtered = llama_wrapper_tier1.get_filtered_tier1_sources(db, interests)
                pre_discovered = llama_wrapper_tier1.convert_tier1_to_discovered(
                    filtered
                )
                logger.info(
                    f"Converted {len(pre_discovered)} Tier 1 sources to discovered format"
                )
            else:
                # Hybrid: Could pass partial Tier 1 + let LLM discover gaps
                logger.info(
                    f"Hybrid path: Coverage {coverage:.1f}% < 90%, using LLM discovery"
                )

        # Create NewsLlama with or without pre-discovered sources
        news_llama = NewsLlama(
            user_interests=interests, pre_discovered_sources=pre_discovered
        )

        # Run generation
        stats = asyncio.run(news_llama.run())

        # Track contributions if we have newsletter_id
        if db and newsletter_id and stats:
            # Extract contribution data from stats
            contributions = llama_wrapper_tier1.extract_contributions_from_stats(stats)
            if contributions:
                llama_wrapper_tier1.track_source_contributions(
                    db, newsletter_id, contributions
                )

        # Verify output
        if not Path(output_file).exists():
            raise NewsLlamaWrapperError(f"Output file {output_file} not created")

        return output_file

    except Exception as e:
        if isinstance(e, NewsLlamaWrapperError):
            raise
        raise NewsLlamaWrapperError(f"Failed to generate newsletter: {str(e)}")
