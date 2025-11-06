"""
Tests for LLMSummarizer prompt structure.

NOTE: Cache-optimized prompts disabled due to ROCm/AMD GPU memory issues.
Verifies that LLMSummarizer uses short system prompts to avoid triggering
prompt caching issues on the LLM server.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from contextlib import nullcontext

from src.summarizers.llm_summarizer import LLMSummarizer
from src.utils.models import ProcessedArticle, SourceType
from src.utils.llm_prompts import LLMPrompts
from open_agent import TextBlock  # type: ignore


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    config = Mock()
    config.llm = Mock()
    config.llm.model = "/home/steve/dev/llama.cpp/models/gpt-oss-120b-mxfp4.gguf"
    config.llm.api_url = "http://192.168.1.62:8052/v1"
    config.llm.temperature = 0.7
    config.llm.max_tokens = 4000
    config.llm.timeout = 120
    return config


@pytest.fixture
def test_article():
    """Sample article for testing"""
    return ProcessedArticle(
        title="Test Article About AI",
        source="Test Source",
        source_type=SourceType.RSS,
        category="Technology",
        content="This is test content about artificial intelligence and machine learning.",
        url="https://example.com/test",
        published_at=datetime(2025, 1, 1, 12, 0, 0),
        word_count=100,
        reading_time_minutes=1,
        keywords=["ai", "machine learning"],
    )


class TestLLMSummarizerCacheOptimization:
    """Test that LLMSummarizer uses short system prompts to avoid caching issues"""

    def test_uses_llm_prompts_utility(self, mock_config, test_article):
        """LLMPrompts utility exists but is not used due to ROCm issues"""
        summarizer = LLMSummarizer(mock_config)

        # LLMPrompts utility still exists but is not used in production code
        assert hasattr(LLMPrompts, "get_article_summary_system_prompt")
        assert hasattr(LLMPrompts, "get_article_summary_user_prompt")

    @patch("src.summarizers.llm_summarizer.oa_client.query")
    @pytest.mark.asyncio
    async def test_system_prompt_is_static(self, mock_query, mock_config, test_article):
        """System prompt should be static across different articles"""
        summarizer = LLMSummarizer(mock_config)

        # Mock LLM response
        mock_response = Mock()
        mock_text_block = Mock()
        mock_text_block.text = (
            '{"summary": "Test", "key_points": ["point"], "importance_score": 0.5}'
        )
        mock_response.content = [mock_text_block]
        mock_query.return_value = AsyncMock()
        mock_query.return_value.__aiter__.return_value = [mock_response]

        # Summarize first article
        article1 = test_article
        await summarizer.summarize_article(article1)

        # Get the AgentOptions from the first call
        first_call_options = mock_query.call_args[0][1]
        first_system_prompt = first_call_options.system_prompt

        # Summarize second article (different content)
        article2 = ProcessedArticle(
            title="Different Article",
            source="Different Source",
            source_type=SourceType.RSS,
            category="Science",
            content="Completely different content here.",
            url="https://example.com/different",
            published_at=datetime(2025, 1, 2, 12, 0, 0),
            word_count=50,
            reading_time_minutes=1,
            keywords=["science"],
        )
        await summarizer.summarize_article(article2)

        # Get the AgentOptions from the second call
        second_call_options = mock_query.call_args[0][1]
        second_system_prompt = second_call_options.system_prompt

        # System prompts should be identical (cached)
        assert first_system_prompt == second_system_prompt
        assert first_system_prompt is not None
        assert len(first_system_prompt) > 100  # Substantial prompt

    @patch("src.summarizers.llm_summarizer.oa_client.query")
    @pytest.mark.asyncio
    async def test_user_prompt_is_dynamic(self, mock_query, mock_config, test_article):
        """User prompt should contain article-specific data"""
        summarizer = LLMSummarizer(mock_config)

        # Mock LLM response
        mock_response = Mock()
        mock_text_block = Mock()
        mock_text_block.text = (
            '{"summary": "Test", "key_points": ["point"], "importance_score": 0.5}'
        )
        mock_response.content = [mock_text_block]
        mock_query.return_value = AsyncMock()
        mock_query.return_value.__aiter__.return_value = [mock_response]

        # Summarize article
        await summarizer.summarize_article(test_article)

        # Get the user prompt from the call
        user_prompt = mock_query.call_args[0][0]

        # User prompt should contain article data
        assert "Test Article About AI" in user_prompt
        assert "Test Source" in user_prompt
        assert "Technology" in user_prompt
        assert "artificial intelligence" in user_prompt

    @patch("src.summarizers.llm_summarizer.oa_client.query")
    @pytest.mark.asyncio
    async def test_user_prompt_no_instructions(
        self, mock_query, mock_config, test_article
    ):
        """User prompt should contain instructions (reverted from cache-optimized)"""
        summarizer = LLMSummarizer(mock_config)

        # Mock LLM response
        mock_response = Mock()
        mock_text_block = Mock()
        mock_text_block.text = (
            '{"summary": "Test", "key_points": ["point"], "importance_score": 0.5}'
        )
        mock_response.content = [mock_text_block]
        mock_query.return_value = AsyncMock()
        mock_query.return_value.__aiter__.return_value = [mock_response]

        # Summarize article
        await summarizer.summarize_article(test_article)

        # Get the user prompt from the call
        user_prompt = mock_query.call_args[0][0]

        # User prompt SHOULD contain instructions (reverted approach)
        assert "Please" in user_prompt or "provide" in user_prompt
        assert "CRITICAL REQUIREMENTS:" in user_prompt or "Return ONLY" in user_prompt

    @patch("src.summarizers.llm_summarizer.oa_client.query")
    @pytest.mark.asyncio
    async def test_system_prompt_contains_json_schema(
        self, mock_query, mock_config, test_article
    ):
        """System prompt should be short to avoid ROCm caching issues"""
        summarizer = LLMSummarizer(mock_config)

        # Mock LLM response
        mock_response = Mock()
        mock_text_block = Mock()
        mock_text_block.text = (
            '{"summary": "Test", "key_points": ["point"], "importance_score": 0.5}'
        )
        mock_response.content = [mock_text_block]
        mock_query.return_value = AsyncMock()
        mock_query.return_value.__aiter__.return_value = [mock_response]

        # Summarize article
        await summarizer.summarize_article(test_article)

        # Get the AgentOptions from the call
        call_options = mock_query.call_args[0][1]
        system_prompt = call_options.system_prompt

        # System prompt should be SHORT (< 100 tokens) to avoid caching issues
        assert len(system_prompt) < 500  # ~100 tokens
        assert "JSON" in system_prompt
        assert (
            "summarization" in system_prompt
            or "news" in system_prompt
            or "json" in system_prompt
        )

    @patch("src.summarizers.llm_summarizer.oa_client.query")
    @pytest.mark.asyncio
    async def test_matches_llm_prompts_utility(
        self, mock_query, mock_config, test_article
    ):
        """Prompts should NOT match LLMPrompts utility (reverted due to ROCm issues)"""
        summarizer = LLMSummarizer(mock_config)

        # Mock LLM response
        mock_response = Mock()
        mock_text_block = Mock()
        mock_text_block.text = (
            '{"summary": "Test", "key_points": ["point"], "importance_score": 0.5}'
        )
        mock_response.content = [mock_text_block]
        mock_query.return_value = AsyncMock()
        mock_query.return_value.__aiter__.return_value = [mock_response]

        # Summarize article
        await summarizer.summarize_article(test_article)

        # Get prompts from the call
        user_prompt = mock_query.call_args[0][0]
        call_options = mock_query.call_args[0][1]
        system_prompt = call_options.system_prompt

        # Get expected prompts from LLMPrompts utility
        expected_system = LLMPrompts.get_article_summary_system_prompt()
        expected_user = LLMPrompts.get_article_summary_user_prompt(test_article)

        # Should NOT match (we reverted to old approach to fix ROCm issues)
        assert system_prompt != expected_system
        assert user_prompt != expected_user

        # But both prompts should still be functional
        assert len(system_prompt) > 0
        assert len(user_prompt) > 0
        assert test_article.title in user_prompt

    @patch("src.summarizers.llm_summarizer.oa_client.query")
    @pytest.mark.asyncio
    async def test_batch_processing_uses_same_system_prompt(
        self, mock_query, mock_config
    ):
        """Batch processing should use same system prompt for all articles"""
        summarizer = LLMSummarizer(mock_config)

        # Mock LLM response
        mock_response = Mock()
        mock_text_block = Mock()
        mock_text_block.text = (
            '{"summary": "Test", "key_points": ["point"], "importance_score": 0.5}'
        )
        mock_response.content = [mock_text_block]
        mock_query.return_value = AsyncMock()
        mock_query.return_value.__aiter__.return_value = [mock_response]

        # Create batch of articles
        articles = [
            ProcessedArticle(
                title=f"Article {i}",
                source="Test Source",
                source_type=SourceType.RSS,
                category="Technology",
                content=f"Content {i}",
                url=f"https://example.com/{i}",
                published_at=datetime(2025, 1, 1, 12, 0, 0),
                word_count=100,
                reading_time_minutes=1,
                keywords=[f"keyword{i}"],
            )
            for i in range(5)
        ]

        # Summarize batch
        await summarizer.summarize_batch(articles)

        # Extract all system prompts from calls
        system_prompts = [
            call[0][1].system_prompt for call in mock_query.call_args_list
        ]

        # All system prompts should be identical (fully cached)
        assert len(system_prompts) == 5
        assert all(sp == system_prompts[0] for sp in system_prompts)

        # All user prompts should be different (dynamic)
        user_prompts = [call[0][0] for call in mock_query.call_args_list]
        assert len(set(user_prompts)) == 5  # All unique


class TestLLMSummarizerBackwardCompatibility:
    """Ensure refactored summarizer maintains existing behavior"""

    @patch("src.summarizers.llm_summarizer.asyncio.timeout")
    @patch("src.summarizers.llm_summarizer.oa_client.query")
    @pytest.mark.asyncio
    async def test_returns_summarized_article(
        self, mock_query, mock_timeout, mock_config, test_article
    ):
        """Should return SummarizedArticle with all fields"""
        # Mock asyncio.timeout to be a pass-through using nullcontext
        mock_timeout.return_value = nullcontext()

        summarizer = LLMSummarizer(mock_config)

        # Mock LLM response with proper TextBlock
        mock_response = Mock()
        text_json = '{"summary": "AI summary", "key_points": ["point1", "point2"], "importance_score": 0.8}'
        mock_text_block = TextBlock(text=text_json)
        mock_response.content = [mock_text_block]
        mock_query.return_value = AsyncMock()
        mock_query.return_value.__aiter__.return_value = [mock_response]

        # Summarize
        result = await summarizer.summarize_article(test_article)

        # Verify result structure
        assert result.title == test_article.title
        assert result.ai_summary == "AI summary"
        assert result.key_points == ["point1", "point2"]
        assert result.importance_score == 0.8

    @patch("src.summarizers.llm_summarizer.asyncio.timeout")
    @patch("src.summarizers.llm_summarizer.oa_client.query")
    @pytest.mark.asyncio
    async def test_handles_json_parse_error(
        self, mock_query, mock_timeout, mock_config, test_article
    ):
        """Should handle invalid JSON gracefully"""
        # Mock asyncio.timeout to be a pass-through using nullcontext
        mock_timeout.return_value = nullcontext()

        summarizer = LLMSummarizer(mock_config)

        # Mock LLM response with invalid JSON using proper TextBlock
        mock_response = Mock()
        mock_text_block = TextBlock(text="This is not JSON")
        mock_response.content = [mock_text_block]
        mock_query.return_value = AsyncMock()
        mock_query.return_value.__aiter__.return_value = [mock_response]

        # Should not raise exception
        result = await summarizer.summarize_article(test_article)

        assert result.ai_summary == "This is not JSON"
        assert result.key_points == []
        assert result.importance_score == 0.5
