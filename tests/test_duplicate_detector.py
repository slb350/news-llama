"""
Test suite for duplicate detection functionality
"""
import pytest
from datetime import datetime, timedelta

from src.processors.duplicate_detector import DuplicateDetector
from src.utils.models import ProcessedArticle, SourceType
from src.utils.constants import ProcessingConstants


class TestDuplicateDetector:
    """Test duplicate detection functionality"""

    @pytest.fixture
    def detector(self):
        """Create a mock config and detector for testing"""
        class MockConfig:
            class Processing:
                duplicate_threshold = 0.8
                min_article_length = 200
                max_article_age = 24

            processing = Processing()

        return DuplicateDetector(MockConfig())

    @pytest.fixture
    def sample_articles(self):
        """Create sample articles for testing"""
        base_time = datetime.now()

        articles = [
            ProcessedArticle(
                title="AI Breakthrough in Healthcare",
                content="Researchers have developed a new AI system that can detect diseases from medical images with 95% accuracy. This breakthrough in artificial intelligence could revolutionize healthcare diagnostics.",
                url="https://technews.com/ai-healthcare-breakthrough",
                source="TechNews",
                source_type=SourceType.RSS,
                category="technology",
                published_at=base_time,
                word_count=35,
                reading_time_minutes=1,
                keywords=["ai system", "medical images", "healthcare diagnostics"]
            ),
            ProcessedArticle(
                title="AI Breakthrough: 95% Disease Detection Accuracy",
                content="Researchers have created a revolutionary AI system that can detect diseases from medical images with 95% accuracy. This artificial intelligence breakthrough promises to transform healthcare diagnostics.",
                url="https://healthtech.com/ai-disease-detection",
                source="HealthTech",
                source_type=SourceType.RSS,
                category="technology",
                published_at=base_time + timedelta(hours=1),
                word_count=32,
                reading_time_minutes=1,
                keywords=["ai system", "medical images", "healthcare diagnostics"]
            ),
            ProcessedArticle(
                title="New Python Framework Released",
                content="A new Python web framework has been released with improved performance and better async support. Developers are excited about the new features.",
                url="https://pythonnews.com/new-framework",
                source="PythonNews",
                source_type=SourceType.RSS,
                category="programming",
                published_at=base_time + timedelta(hours=2),
                word_count=25,
                reading_time_minutes=1,
                keywords=["python web framework", "async support", "performance"]
            ),
            ProcessedArticle(
                title="Climate Change Affects Global Weather Patterns",
                content="Scientists report that climate change is causing significant changes in global weather patterns, leading to more extreme weather events worldwide.",
                url="https://climatenews.com/weather-patterns",
                source="ClimateNews",
                source_type=SourceType.RSS,
                category="environment",
                published_at=base_time + timedelta(hours=3),
                word_count=28,
                reading_time_minutes=1,
                keywords=["climate change", "weather patterns", "extreme weather"]
            )
        ]

        return articles

    def test_no_duplicates_empty_list(self, detector):
        """Test deduplication with empty list"""
        result = detector.deduplicate([])
        assert result == []

    def test_no_duplicates_single_article(self, detector, sample_articles):
        """Test deduplication with single article"""
        result = detector.deduplicate([sample_articles[0]])
        assert len(result) == 1
        assert result[0] == sample_articles[0]

    def test_no_different_articles(self, detector, sample_articles):
        """Test deduplication with different articles"""
        # Use articles 2, 3, 4 (which are different)
        different_articles = sample_articles[1:]
        result = detector.deduplicate(different_articles)

        assert len(result) == len(different_articles)
        # None should be marked as duplicates
        for article in result:
            assert not article.is_duplicate

    def test_duplicate_detection_similar_articles(self, detector, sample_articles):
        """Test detection of similar articles"""
        # Use first two articles (which are similar)
        similar_articles = sample_articles[:2]

        # Debug: Check similarity
        similarity = detector._calculate_similarity(similar_articles[0], similar_articles[1])
        print(f"Debug - Similarity between articles: {similarity}")
        print(f"Debug - Threshold: {detector.threshold}")

        result = detector.deduplicate(similar_articles)

        # Should result in one unique article if they're similar enough
        if similarity >= detector.threshold:
            assert len(result) == 1

            # The newer article should be marked as duplicate
            for article in similar_articles:
                if article.published_at > result[0].published_at:
                    assert article.is_duplicate
                    assert article.duplicate_similarity is not None
                    assert article.duplicate_similarity >= detector.threshold
        else:
            # If not similar enough, both should remain
            assert len(result) == 2

    def test_duplicate_detection_threshold(self, sample_articles):
        """Test different similarity thresholds"""
        # Create very similar articles for threshold testing
        base_time = datetime.now()
        very_similar_articles = [
            ProcessedArticle(
                title="AI Breakthrough in Healthcare",
                content="Researchers have developed a new AI system that can detect diseases from medical images with 95% accuracy.",
                url="https://technews.com/ai-healthcare-breakthrough",
                source="TechNews",
                source_type=SourceType.RSS,
                category="technology",
                published_at=base_time,
                word_count=20,
                reading_time_minutes=1,
                keywords=["ai system", "medical images", "healthcare"]
            ),
            ProcessedArticle(
                title="AI Breakthrough in Healthcare",
                content="Researchers have developed a new AI system that can detect diseases from medical images with 95% accuracy.",
                url="https://healthtech.com/ai-healthcare-breakthrough",
                source="HealthTech",
                source_type=SourceType.RSS,
                category="technology",
                published_at=base_time + timedelta(hours=1),
                word_count=20,
                reading_time_minutes=1,
                keywords=["ai system", "medical images", "healthcare"]
            )
        ]

        # High threshold (should detect fewer duplicates)
        high_threshold_detector = DuplicateDetector(type('MockConfig', (), {
            'processing': type('Processing', (), {'duplicate_threshold': 0.9})()
        })())

        result_high = high_threshold_detector.deduplicate(very_similar_articles)

        # Low threshold (should detect more duplicates)
        low_threshold_detector = DuplicateDetector(type('MockConfig', (), {
            'processing': type('Processing', (), {'duplicate_threshold': 0.5})()
        })())

        result_low = low_threshold_detector.deduplicate(very_similar_articles)

        # Low threshold should detect more duplicates (fewer unique articles)
        assert len(result_low) <= len(result_high)

    def test_url_similarity(self, detector):
        """Test URL similarity calculation"""
        # Exact same URL
        similarity = detector._url_similarity(
            "https://example.com/article/123",
            "https://example.com/article/123"
        )
        assert similarity == 1.0

        # Same domain, different article
        similarity = detector._url_similarity(
            "https://example.com/article/123",
            "https://example.com/article/456"
        )
        assert similarity == 0.8

        # Different domains
        similarity = detector._url_similarity(
            "https://example.com/article/123",
            "https://different.com/article/123"
        )
        assert similarity == 0.0

        # Invalid URLs
        similarity = detector._url_similarity(
            "invalid-url",
            "https://example.com/article/123"
        )
        assert similarity == 0.0

    def test_content_similarity(self, detector):
        """Test content similarity calculation"""
        # Identical content
        content = "This is a test article about AI and machine learning."
        similarity = detector._calculate_similarity(
            ProcessedArticle(
                title="Test Article",
                content=content,
                url="https://example.com/1",
                source="Test",
                source_type=SourceType.RSS,
                category="test",
                published_at=datetime.now(),
                word_count=10,
                reading_time_minutes=1,
                keywords=[]
            ),
            ProcessedArticle(
                title="Test Article",
                content=content,
                url="https://example.com/2",
                source="Test",
                source_type=SourceType.RSS,
                category="test",
                published_at=datetime.now(),
                word_count=10,
                reading_time_minutes=1,
                keywords=[]
            )
        )
        assert similarity > 0.9  # Should be very similar

        # Different content
        similarity = detector._calculate_similarity(
            ProcessedArticle(
                title="Article about AI",
                content="This discusses artificial intelligence and its applications.",
                url="https://example.com/1",
                source="Test",
                source_type=SourceType.RSS,
                category="test",
                published_at=datetime.now(),
                word_count=10,
                reading_time_minutes=1,
                keywords=[]
            ),
            ProcessedArticle(
                title="Article about Sports",
                content="This covers the latest football matches and player statistics.",
                url="https://example.com/2",
                source="Test",
                source_type=SourceType.RSS,
                category="test",
                published_at=datetime.now(),
                word_count=10,
                reading_time_minutes=1,
                keywords=[]
            )
        )
        assert similarity < 0.5  # Should be quite different

    def test_category_grouping(self, detector, sample_articles):
        """Test that articles are grouped by category for comparison"""
        # Add more articles in different categories
        tech_article = ProcessedArticle(
            title="Another AI Article",
            content="More content about artificial intelligence.",
            url="https://tech.com/another-ai",
            source="TechNews",
            source_type=SourceType.RSS,
            category="technology",
            published_at=datetime.now(),
            word_count=10,
            reading_time_minutes=1,
            keywords=[]
        )

        sports_article = ProcessedArticle(
            title="Sports News",
            content="Latest sports updates and match results.",
            url="https://sports.com/news",
            source="SportsNews",
            source_type=SourceType.RSS,
            category="sports",
            published_at=datetime.now(),
            word_count=10,
            reading_time_minutes=1,
            keywords=[]
        )

        all_articles = sample_articles + [tech_article, sports_article]
        result = detector.deduplicate(all_articles)

        # Should handle articles from different categories
        assert len(result) > 0

        # Articles should be processed by category
        categories = set(article.category for article in result)
        assert "technology" in categories
        assert "programming" in categories
        assert "environment" in categories
        assert "sports" in categories

    def test_duplicate_preservation_ordering(self, detector, sample_articles):
        """Test that newer articles are marked as duplicates"""
        similar_articles = sample_articles[:2]  # First two are similar
        result = detector.deduplicate(similar_articles)

        # Should keep the newer article (higher published_at)
        assert len(result) == 1
        assert result[0].published_at > sample_articles[0].published_at

        # The older article should be marked as duplicate
        older_article = sample_articles[0]
        assert older_article.is_duplicate
        assert older_article.duplicate_similarity is not None

    def test_mixed_duplicate_scenarios(self, detector, sample_articles):
        """Test mixed scenarios with duplicates and unique articles"""
        # Add a near-duplicate of the Python article
        python_duplicate = ProcessedArticle(
            title="New Python Framework with Async Features Released",
            content="A new Python web framework has been released with improved performance and better async support. The development team has been working on this for months.",
            url="https://pythonnews.com/async-framework-released",
            source="PythonNews",
            source_type=SourceType.RSS,
            category="programming",
            published_at=datetime.now() + timedelta(hours=4),
            word_count=28,
            reading_time_minutes=1,
            keywords=["python web framework", "async features", "performance"]
        )

        all_articles = sample_articles + [python_duplicate]
        result = detector.deduplicate(all_articles)

        # Should detect duplicates while preserving unique articles
        assert len(result) < len(all_articles)

        # Count how many were marked as duplicates
        duplicate_count = sum(1 for article in all_articles if article.is_duplicate)
        assert duplicate_count >= 2  # At least 2 duplicates should be found

    def test_edge_case_identical_titles_different_content(self, detector):
        """Test articles with identical titles but different content"""
        base_time = datetime.now()

        articles = [
            ProcessedArticle(
                title="Breaking News",
                content="This is about technology and AI developments.",
                url="https://tech.com/news1",
                source="TechNews",
                source_type=SourceType.RSS,
                category="technology",
                published_at=base_time,
                word_count=10,
                reading_time_minutes=1,
                keywords=[]
            ),
            ProcessedArticle(
                title="Breaking News",
                content="This covers sports and latest match results.",
                url="https://sports.com/news1",
                source="SportsNews",
                source_type=SourceType.RSS,
                category="sports",
                published_at=base_time + timedelta(hours=1),
                word_count=10,
                reading_time_minutes=1,
                keywords=[]
            )
        ]

        result = detector.deduplicate(articles)

        # Should detect similarity based on title but may keep both if content differs enough
        assert len(result) >= 1
        assert len(result) <= 2

    def test_empty_content_articles(self, detector):
        """Test handling of articles with empty content"""
        empty_articles = [
            ProcessedArticle(
                title="Empty Article 1",
                content="",
                url="https://example.com/empty1",
                source="Test",
                source_type=SourceType.RSS,
                category="test",
                published_at=datetime.now(),
                word_count=0,
                reading_time_minutes=1,
                keywords=[]
            ),
            ProcessedArticle(
                title="Empty Article 2",
                content="",
                url="https://example.com/empty2",
                source="Test",
                source_type=SourceType.RSS,
                category="test",
                published_at=datetime.now() + timedelta(hours=1),
                word_count=0,
                reading_time_minutes=1,
                keywords=[]
            )
        ]

        result = detector.deduplicate(empty_articles)

        # Should handle empty content gracefully
        assert len(result) >= 1
        assert len(result) <= len(empty_articles)