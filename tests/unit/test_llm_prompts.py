"""
Tests for cache-optimized LLM prompt construction.

This test suite verifies that prompts are structured for maximum prompt caching effectiveness:
- System prompts contain only static content (100% cacheable)
- User prompts contain only dynamic content
- Prompts are deterministic and consistent
"""

import pytest
from src.utils.llm_prompts import LLMPrompts
from src.utils.models import ProcessedArticle, SourceType


class TestLLMPromptsStructure:
    """Test that prompts follow caching optimization structure"""

    def test_article_summary_system_prompt_is_static(self):
        """System prompt should be identical across calls (cacheable)"""
        prompt1 = LLMPrompts.get_article_summary_system_prompt()
        prompt2 = LLMPrompts.get_article_summary_system_prompt()

        assert prompt1 == prompt2
        assert isinstance(prompt1, str)
        assert len(prompt1) > 100  # Should be substantial

    def test_article_summary_user_prompt_is_dynamic(self):
        """User prompt should vary with article content"""
        article1 = ProcessedArticle(
            title="Test Article 1",
            source="Test Source",
            source_type=SourceType.RSS,
            category="Technology",
            content="Test content 1",
            url="https://example.com/1",
            published_at="2025-01-01",
            word_count=100,
            reading_time_minutes=1,
            keywords=["test"],
        )
        article2 = ProcessedArticle(
            title="Test Article 2",
            source="Test Source",
            source_type=SourceType.RSS,
            category="Technology",
            content="Test content 2",
            url="https://example.com/2",
            published_at="2025-01-02",
            word_count=100,
            reading_time_minutes=1,
            keywords=["test"],
        )

        prompt1 = LLMPrompts.get_article_summary_user_prompt(article1)
        prompt2 = LLMPrompts.get_article_summary_user_prompt(article2)

        assert prompt1 != prompt2
        assert "Test Article 1" in prompt1
        assert "Test Article 2" in prompt2

    def test_subreddit_discovery_system_prompt_is_static(self):
        """System prompt should be identical across calls"""
        prompt1 = LLMPrompts.get_subreddit_discovery_system_prompt()
        prompt2 = LLMPrompts.get_subreddit_discovery_system_prompt()

        assert prompt1 == prompt2
        assert isinstance(prompt1, str)
        assert len(prompt1) > 200  # Should contain guidelines

    def test_subreddit_discovery_user_prompt_is_dynamic(self):
        """User prompt should vary with interest"""
        prompt1 = LLMPrompts.get_subreddit_discovery_user_prompt("rust")
        prompt2 = LLMPrompts.get_subreddit_discovery_user_prompt("ai")

        assert prompt1 != prompt2
        assert "rust" in prompt1.lower()
        assert "ai" in prompt2.lower()

    def test_multi_source_discovery_system_prompt_is_static(self):
        """System prompt should be identical across calls"""
        prompt1 = LLMPrompts.get_multi_source_discovery_system_prompt()
        prompt2 = LLMPrompts.get_multi_source_discovery_system_prompt()

        assert prompt1 == prompt2
        assert isinstance(prompt1, str)
        assert len(prompt1) > 200

    def test_multi_source_discovery_user_prompt_is_dynamic(self):
        """User prompt should vary with interest"""
        prompt1 = LLMPrompts.get_multi_source_discovery_user_prompt("technology")
        prompt2 = LLMPrompts.get_multi_source_discovery_user_prompt("science")

        assert prompt1 != prompt2
        assert "technology" in prompt1.lower()
        assert "science" in prompt2.lower()


class TestArticleSummaryPromptContent:
    """Test article summary prompt contains required elements"""

    def test_system_prompt_contains_json_schema(self):
        """System prompt should include the expected JSON schema"""
        prompt = LLMPrompts.get_article_summary_system_prompt()

        # Should contain schema fields
        assert "summary" in prompt
        assert "key_points" in prompt
        assert "importance_score" in prompt

        # Should contain instructions
        assert "JSON" in prompt or "json" in prompt
        assert "max 300 words" in prompt or "300 words" in prompt

    def test_system_prompt_no_dynamic_content(self):
        """System prompt should not contain any variables or dynamic content"""
        prompt = LLMPrompts.get_article_summary_system_prompt()

        # Should not contain f-string syntax (JSON examples with {} are fine)
        # Check for patterns like {variable}, {article.title}, etc but allow JSON {"key": "value"}
        import re

        # Look for f-string placeholders like {variable} or {obj.attr} but not JSON
        fstring_pattern = r"\{[a-zA-Z_][a-zA-Z0-9_.]*\}"
        assert not re.search(fstring_pattern, prompt), (
            "Found f-string placeholder in system prompt"
        )

    def test_user_prompt_contains_article_metadata(self):
        """User prompt should contain all article metadata"""
        article = ProcessedArticle(
            title="Test Title",
            source="Test Source",
            source_type=SourceType.RSS,
            category="Technology",
            content="Test content",
            url="https://example.com",
            published_at="2025-01-01T12:00:00",
            word_count=100,
            reading_time_minutes=1,
            keywords=["test", "article"],
        )

        prompt = LLMPrompts.get_article_summary_user_prompt(article)

        assert "Test Title" in prompt
        assert "Test Source" in prompt
        assert "Technology" in prompt
        assert "Test content" in prompt
        assert "2025-01-01" in prompt

    def test_user_prompt_no_static_instructions(self):
        """User prompt should not duplicate static instructions"""
        article = ProcessedArticle(
            title="Test",
            source="Test",
            source_type=SourceType.RSS,
            category="Tech",
            content="Content",
            url="https://example.com",
            published_at="2025-01-01",
            word_count=50,
            reading_time_minutes=1,
            keywords=[],
        )

        prompt = LLMPrompts.get_article_summary_user_prompt(article)

        # Should NOT contain instructions (those should be in system prompt)
        assert "Please analyze" not in prompt
        assert "Format your response" not in prompt
        assert "Return ONLY" not in prompt.upper()


class TestSubredditDiscoveryPromptContent:
    """Test subreddit discovery prompt contains required elements"""

    def test_system_prompt_contains_guidelines(self):
        """System prompt should include discovery guidelines"""
        prompt = LLMPrompts.get_subreddit_discovery_system_prompt()

        # Should contain guidelines
        assert "subreddit" in prompt.lower()
        assert "JSON" in prompt or "json" in prompt
        assert "confidence" in prompt.lower() or "score" in prompt.lower()

    def test_system_prompt_contains_examples(self):
        """System prompt should include example patterns"""
        prompt = LLMPrompts.get_subreddit_discovery_system_prompt()

        # Should mention different discovery patterns
        assert "exact" in prompt.lower() or "match" in prompt.lower()
        assert "learning" in prompt.lower() or "learn" in prompt.lower()

    def test_user_prompt_minimal(self):
        """User prompt should be minimal (just the interest)"""
        prompt = LLMPrompts.get_subreddit_discovery_user_prompt("rust")

        # Should be very short
        assert len(prompt) < 100
        assert "rust" in prompt.lower()

        # Should not duplicate instructions
        assert "suggest" not in prompt.lower()
        assert "return" not in prompt.lower()


class TestMultiSourceDiscoveryPromptContent:
    """Test multi-source discovery prompt contains required elements"""

    def test_system_prompt_contains_source_types(self):
        """System prompt should mention all source types"""
        prompt = LLMPrompts.get_multi_source_discovery_system_prompt()

        assert "reddit" in prompt.lower()
        assert "rss" in prompt.lower() or "feed" in prompt.lower()
        assert "twitter" in prompt.lower() or "website" in prompt.lower()

    def test_system_prompt_contains_field_requirements(self):
        """System prompt should specify required fields"""
        prompt = LLMPrompts.get_multi_source_discovery_system_prompt()

        # Should specify field requirements
        assert "type" in prompt.lower()
        assert "confidence" in prompt.lower()
        assert "url" in prompt.lower() or "subreddit" in prompt.lower()

    def test_user_prompt_minimal(self):
        """User prompt should be minimal (just the interest)"""
        prompt = LLMPrompts.get_multi_source_discovery_user_prompt("ai")

        # Should be very short
        assert len(prompt) < 100
        assert "ai" in prompt.lower()


class TestPromptConsistency:
    """Test that prompts are consistent and deterministic"""

    def test_no_whitespace_variation(self):
        """Prompts should have consistent whitespace"""
        # Call multiple times to ensure no random whitespace
        prompts = [LLMPrompts.get_article_summary_system_prompt() for _ in range(5)]

        # All should be identical (byte-for-byte)
        assert all(p == prompts[0] for p in prompts)

    def test_no_timestamp_injection(self):
        """System prompts should not inject timestamps"""
        prompt = LLMPrompts.get_article_summary_system_prompt()

        # Should not contain dates
        import re

        date_pattern = r"\d{4}-\d{2}-\d{2}"
        assert not re.search(date_pattern, prompt)

    def test_no_random_elements(self):
        """Prompts should be fully deterministic"""
        import random

        random.seed(42)
        prompt1 = LLMPrompts.get_subreddit_discovery_system_prompt()

        random.seed(999)
        prompt2 = LLMPrompts.get_subreddit_discovery_system_prompt()

        # Should be identical regardless of random state
        assert prompt1 == prompt2


class TestTokenEstimates:
    """Test token count estimates for cache sizing"""

    def test_article_summary_system_prompt_size(self):
        """System prompt should be ~200-300 tokens"""
        prompt = LLMPrompts.get_article_summary_system_prompt()

        # Rough estimate: ~4 chars per token
        estimated_tokens = len(prompt) / 4

        # Should be substantial (worth caching)
        assert estimated_tokens > 150, (
            f"System prompt too small: ~{estimated_tokens} tokens"
        )
        assert estimated_tokens < 500, (
            f"System prompt too large: ~{estimated_tokens} tokens"
        )

    def test_subreddit_discovery_system_prompt_size(self):
        """System prompt should be ~300-500 tokens"""
        prompt = LLMPrompts.get_subreddit_discovery_system_prompt()

        estimated_tokens = len(prompt) / 4

        # Should be substantial (worth caching)
        assert estimated_tokens > 200, (
            f"System prompt too small: ~{estimated_tokens} tokens"
        )
        assert estimated_tokens < 800, (
            f"System prompt too large: ~{estimated_tokens} tokens"
        )

    def test_user_prompts_are_small(self):
        """User prompts should be small (mostly dynamic content)"""
        interest_prompt = LLMPrompts.get_subreddit_discovery_user_prompt("rust")

        estimated_tokens = len(interest_prompt) / 4

        # Should be minimal
        assert estimated_tokens < 50, (
            f"User prompt too large: ~{estimated_tokens} tokens"
        )


class TestCacheOptimizationStructure:
    """Test that prompts follow cache optimization best practices"""

    def test_static_content_first_principle(self):
        """Verify static content is in system prompt, dynamic in user prompt"""
        # Article summary
        system = LLMPrompts.get_article_summary_system_prompt()
        article = ProcessedArticle(
            title="Test",
            source="Test",
            source_type=SourceType.RSS,
            category="Tech",
            content="Content",
            url="https://example.com",
            published_at="2025-01-01",
            word_count=10,
            reading_time_minutes=1,
            keywords=[],
        )
        user = LLMPrompts.get_article_summary_user_prompt(article)

        # Static instructions should be in system, not user
        assert "JSON" in system or "json" in system
        assert "format" not in user.lower() or "format" in system.lower()

        # Dynamic content should be in user, not system
        assert "Test" in user
        assert (
            "Test" not in system or "example" in system.lower()
        )  # Allow example mentions

    def test_no_duplicate_instructions(self):
        """Instructions should appear once in system prompt, not in user prompt"""
        system_summary = LLMPrompts.get_article_summary_system_prompt()
        article = ProcessedArticle(
            title="Test",
            source="Test",
            source_type=SourceType.RSS,
            category="Tech",
            content="Content",
            url="https://example.com",
            published_at="2025-01-01",
            word_count=10,
            reading_time_minutes=1,
            keywords=[],
        )
        user_summary = LLMPrompts.get_article_summary_user_prompt(article)

        # Key phrases should only appear in system
        assert (
            "respond with" in system_summary.lower()
            or "return" in system_summary.lower()
        )
        assert "respond with" not in user_summary.lower()
        assert "format" not in user_summary.lower() or len(user_summary) < 50

    def test_interest_appears_once(self):
        """User interest should appear only once in final prompts"""
        user_prompt = LLMPrompts.get_subreddit_discovery_user_prompt("rust")

        # Count occurrences of interest
        count = user_prompt.lower().count("rust")

        # Should appear exactly once (no duplication)
        assert count == 1, f"Interest appears {count} times, should be 1"
