"""
NewsLlama engine wrapper for web application integration.

Provides interface between web app and main NewsLlama newsletter generation engine.
"""

from datetime import date
from pathlib import Path

# Import main NewsLlama engine
from main import NewsLlama


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
    try:
        # Get output file path
        output_file = get_output_file_path(output_date)

        # Ensure output directory exists
        ensure_output_directory(str(Path(output_file).parent))

        # Initialize NewsLlama with user interests
        news_llama = NewsLlama(user_interests=interests)

        # Generate the newsletter
        news_llama.run()

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

    # Build absolute path: project_root/output/newsletters/filename
    output_path = project_root / "output" / "newsletters" / filename

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
