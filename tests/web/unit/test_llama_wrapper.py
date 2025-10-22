"""
Unit tests for NewsLlama engine wrapper - TDD RED phase.

Tests integration between web app and main NewsLlama engine:
- generate_newsletter_for_interests: Create digest for given interests/date
- get_output_file_path: Generate proper output path for newsletter
- ensure_output_directory: Create output directory if missing
"""

import pytest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile

from src.web.services.llama_wrapper import (
    generate_newsletter_for_interests,
    get_output_file_path,
    ensure_output_directory,
    NewsLlamaWrapperError,
)


class TestGenerateNewsletterForInterests:
    """Tests for generate_newsletter_for_interests."""

    @patch("src.web.services.llama_wrapper.NewsLlama")
    def test_generate_newsletter_success(self, mock_news_llama_class):
        """Should generate newsletter and return file path."""
        # Mock NewsLlama instance
        mock_instance = Mock()
        mock_news_llama_class.return_value = mock_instance

        # Mock run method to create output file
        def mock_run():
            # Simulate creating output file
            pass

        mock_instance.run = Mock(side_effect=mock_run)

        interests = ["AI", "rust", "python"]
        output_date = date(2025, 10, 22)

        with patch("src.web.services.llama_wrapper.Path.exists", return_value=True):
            file_path = generate_newsletter_for_interests(interests, output_date)

        # Verify NewsLlama was initialized with interests
        mock_news_llama_class.assert_called_once_with(user_interests=interests)

        # Verify run was called
        mock_instance.run.assert_called_once()

        # Verify file path is returned
        assert file_path is not None
        assert "news-2025-10-22" in file_path
        assert file_path.endswith(".html")

    @patch("src.web.services.llama_wrapper.NewsLlama")
    def test_generate_newsletter_with_empty_interests(self, mock_news_llama_class):
        """Should handle empty interests list."""
        mock_instance = Mock()
        mock_news_llama_class.return_value = mock_instance
        mock_instance.run = Mock()

        interests = []
        output_date = date(2025, 10, 22)

        with patch("src.web.services.llama_wrapper.Path.exists", return_value=True):
            file_path = generate_newsletter_for_interests(interests, output_date)

        # Should still create newsletter with empty interests
        mock_news_llama_class.assert_called_once_with(user_interests=[])
        assert file_path is not None

    @patch("src.web.services.llama_wrapper.NewsLlama")
    def test_generate_newsletter_engine_failure(self, mock_news_llama_class):
        """Should raise error if NewsLlama engine fails."""
        mock_instance = Mock()
        mock_news_llama_class.return_value = mock_instance

        # Mock engine failure
        mock_instance.run.side_effect = Exception("LLM connection timeout")

        interests = ["AI"]
        output_date = date(2025, 10, 22)

        with pytest.raises(NewsLlamaWrapperError, match="Failed to generate"):
            generate_newsletter_for_interests(interests, output_date)

    @patch("src.web.services.llama_wrapper.NewsLlama")
    def test_generate_newsletter_file_not_created(self, mock_news_llama_class):
        """Should raise error if output file is not created."""
        mock_instance = Mock()
        mock_news_llama_class.return_value = mock_instance
        mock_instance.run = Mock()  # Run succeeds but no file created

        interests = ["AI"]
        output_date = date(2025, 10, 22)

        # Mock file doesn't exist after generation
        with patch("src.web.services.llama_wrapper.Path.exists", return_value=False):
            with pytest.raises(NewsLlamaWrapperError, match="Output file.*not created"):
                generate_newsletter_for_interests(interests, output_date)

    @patch("src.web.services.llama_wrapper.NewsLlama")
    def test_generate_newsletter_creates_output_dir(self, mock_news_llama_class):
        """Should create output directory if missing."""
        mock_instance = Mock()
        mock_news_llama_class.return_value = mock_instance
        mock_instance.run = Mock()

        interests = ["AI"]
        output_date = date(2025, 10, 22)

        with patch(
            "src.web.services.llama_wrapper.ensure_output_directory"
        ) as mock_ensure:
            with patch("src.web.services.llama_wrapper.Path.exists", return_value=True):
                generate_newsletter_for_interests(interests, output_date)

        # Should ensure output directory exists
        mock_ensure.assert_called_once()

    @patch("src.web.services.llama_wrapper.NewsLlama")
    def test_generate_newsletter_uses_correct_date_format(self, mock_news_llama_class):
        """Should format date correctly in output filename."""
        mock_instance = Mock()
        mock_news_llama_class.return_value = mock_instance
        mock_instance.run = Mock()

        interests = ["AI"]
        output_date = date(2025, 1, 5)  # Test single-digit month/day

        with patch("src.web.services.llama_wrapper.Path.exists", return_value=True):
            file_path = generate_newsletter_for_interests(interests, output_date)

        # Should use YYYY-MM-DD format
        assert "2025-01-05" in file_path


class TestGetOutputFilePath:
    """Tests for get_output_file_path."""

    def test_get_output_file_path_format(self):
        """Should return properly formatted output path."""
        output_date = date(2025, 10, 22)

        file_path = get_output_file_path(output_date)

        # Should be in output/newsletters directory
        assert "output" in file_path
        assert "newsletters" in file_path

        # Should include date
        assert "2025-10-22" in file_path

        # Should be HTML file
        assert file_path.endswith(".html")

    def test_get_output_file_path_different_dates(self):
        """Should generate different paths for different dates."""
        date1 = date(2025, 10, 22)
        date2 = date(2025, 10, 23)

        path1 = get_output_file_path(date1)
        path2 = get_output_file_path(date2)

        assert path1 != path2
        assert "2025-10-22" in path1
        assert "2025-10-23" in path2

    def test_get_output_file_path_absolute(self):
        """Should return absolute path."""
        output_date = date(2025, 10, 22)

        file_path = get_output_file_path(output_date)

        # Should be absolute path (starts with /)
        assert Path(file_path).is_absolute()

    def test_get_output_file_path_includes_guid(self):
        """Should optionally include GUID for uniqueness."""
        output_date = date(2025, 10, 22)
        guid = "abc123-def456"

        file_path = get_output_file_path(output_date, guid=guid)

        # Should include GUID in filename
        assert guid in file_path


class TestEnsureOutputDirectory:
    """Tests for ensure_output_directory."""

    def test_ensure_directory_creates_if_missing(self):
        """Should create directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "output" / "newsletters"

            # Directory doesn't exist yet
            assert not test_path.exists()

            ensure_output_directory(str(test_path))

            # Directory should now exist
            assert test_path.exists()
            assert test_path.is_dir()

    def test_ensure_directory_does_nothing_if_exists(self):
        """Should not fail if directory already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "output" / "newsletters"
            test_path.mkdir(parents=True)

            # Directory exists
            assert test_path.exists()

            # Should not raise error
            ensure_output_directory(str(test_path))

            # Directory should still exist
            assert test_path.exists()

    def test_ensure_directory_creates_parent_dirs(self):
        """Should create parent directories as needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "a" / "b" / "c" / "newsletters"

            # None of the parent dirs exist
            assert not test_path.parent.parent.exists()

            ensure_output_directory(str(test_path))

            # All parent directories should be created
            assert test_path.exists()
            assert test_path.parent.exists()
            assert test_path.parent.parent.exists()

    def test_ensure_directory_handles_permissions(self):
        """Should handle permission errors gracefully."""
        # Test with a path we can't write to
        restricted_path = "/root/news-llama-test"

        # Should raise NewsLlamaWrapperError (not PermissionError)
        with pytest.raises(NewsLlamaWrapperError, match="Failed to create"):
            ensure_output_directory(restricted_path)


class TestIntegrationWithRealFiles:
    """Integration tests with actual file system."""

    @patch("src.web.services.llama_wrapper.NewsLlama")
    def test_full_generation_workflow(self, mock_news_llama_class):
        """Test complete workflow with real file creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mock NewsLlama
            mock_instance = Mock()
            mock_news_llama_class.return_value = mock_instance

            # Create a real output file when run() is called
            output_file = Path(tmpdir) / "news-2025-10-22.html"

            def create_output_file():
                output_file.write_text("<html>Test Newsletter</html>")

            mock_instance.run.side_effect = create_output_file

            # Mock the output path to use our temp directory
            with patch(
                "src.web.services.llama_wrapper.get_output_file_path",
                return_value=str(output_file),
            ):
                interests = ["AI", "rust"]
                output_date = date(2025, 10, 22)

                file_path = generate_newsletter_for_interests(interests, output_date)

                # Verify file was created
                assert Path(file_path).exists()
                assert Path(file_path).read_text() == "<html>Test Newsletter</html>"

    def test_output_directory_structure(self):
        """Test that output directory has correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            newsletters_dir = Path(tmpdir) / "output" / "newsletters"

            ensure_output_directory(str(newsletters_dir))

            # Verify structure
            assert newsletters_dir.exists()
            assert newsletters_dir.is_dir()
            assert newsletters_dir.parent.name == "output"
