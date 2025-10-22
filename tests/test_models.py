"""
Test suite for News Llama
"""
import pytest
from datetime import datetime
from src.utils.models import Article, SourceType


@pytest.fixture
def sample_article():
    """Sample article for testing"""
    return Article(
        title="Test Article",
        content="This is a test article content for testing purposes.",
        url="https://example.com/article",
        source="Test Source",
        source_type=SourceType.RSS,
        category="technology",
        author="Test Author",
        published_at=datetime.now(),
        metadata={"test": True}
    )


def test_article_model(sample_article):
    """Test Article model validation"""
    assert sample_article.title == "Test Article"
    assert sample_article.source_type == SourceType.RSS
    assert sample_article.category == "technology"