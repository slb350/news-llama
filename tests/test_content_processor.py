"""
Test suite for content processing functionality
"""
import pytest
from datetime import datetime
from textblob import TextBlob

from src.processors.content_processor import ContentProcessor
from src.utils.models import Article, SourceType
from src.utils.constants import ProcessingConstants


class TestContentProcessor:
    """Test content processing functionality"""

    @pytest.fixture
    def processor(self):
        """Create a mock config and processor for testing"""
        class MockConfig:
            class Processing:
                min_article_length = 200
                max_article_age = 24
                sentiment_analysis = True
                duplicate_threshold = 0.8

            processing = Processing()

        return ContentProcessor(MockConfig())

    @pytest.fixture
    def sample_article(self):
        """Create a sample article for testing"""
        return Article(
            title="AI Breakthrough: New Model Achieves Human-Level Performance",
            content="""
            Researchers at OpenAI have announced a groundbreaking new AI model that achieves
            human-level performance across a wide range of tasks. The model, called GPT-5,
            demonstrates unprecedented capabilities in reasoning, creativity, and emotional
            understanding. This breakthrough represents a significant milestone in artificial
            intelligence research and could have far-reaching implications for various industries
            including healthcare, education, and entertainment. The development team spent over
            two years training the model on a diverse dataset and implementing novel safety
            measures to ensure responsible AI development.
            """,
            url="https://example.com/ai-breakthrough",
            source="TechNews",
            source_type=SourceType.RSS,
            category="technology",
            author="Jane Smith",
            published_at=datetime.now(),
            metadata={"author_bio": "AI researcher and journalist"}
        )

    def test_article_processing(self, processor, sample_article):
        """Test basic article processing"""
        processed = processor._process_article(sample_article)

        # Verify basic fields are preserved
        assert processed.title == sample_article.title
        assert processed.url == sample_article.url
        assert processed.source == sample_article.source
        assert processed.category == sample_article.category

        # Verify processing results
        assert processed.word_count > 0
        assert processed.reading_time_minutes >= 1
        assert isinstance(processed.keywords, list)
        assert processed.sentiment_score is not None

    def test_empty_content_handling(self, processor):
        """Test handling of articles with empty content"""
        article = Article(
            title="Test Article",
            content="",
            url="https://example.com/test",
            source="Test",
            source_type=SourceType.RSS,
            category="test",
            published_at=datetime.now()
        )

        processed = processor._process_article(article)
        assert processed.content == ""
        assert processed.word_count == 0
        assert processed.reading_time_minutes == 1

    def test_word_count_calculation(self, processor, sample_article):
        """Test word count calculation"""
        processed = processor._process_article(sample_article)
        expected_words = len(sample_article.content.split())
        assert processed.word_count == expected_words

    def test_reading_time_calculation(self, processor):
        """Test reading time calculation"""
        # Create content with known word count
        content = "word " * 400  # 400 words
        article = Article(
            title="Test Article",
            content=content,
            url="https://example.com/test",
            source="Test",
            source_type=SourceType.RSS,
            category="test",
            published_at=datetime.now()
        )

        processed = processor._process_article(article)
        expected_time = max(1, round(400 / ProcessingConstants.WORDS_PER_MINUTE))
        assert processed.reading_time_minutes == expected_time

    def test_content_cleaning(self, processor):
        """Test content cleaning functionality"""
        dirty_content = """
        <p>This is <b>HTML</b> content!!! With <a href='link'>links</a>
        and excessive punctuation...</p>

        <script>alert('xss')</script>

        Normal text with unicode: café, naïve, résumé.
        """

        cleaned = processor._clean_content(dirty_content)

        # HTML tags should be removed
        assert "<p>" not in cleaned
        assert "<b>" not in cleaned
        assert "<script>" not in cleaned

        # Excessive punctuation should be normalized
        assert "!!!" not in cleaned
        assert "..." not in cleaned

        # Unicode characters should be preserved
        assert "café" in cleaned
        assert "naïve" in cleaned
        assert "résumé" in cleaned

        # Normal text should remain
        assert "This is HTML content" in cleaned
        assert "Normal text with unicode" in cleaned

    def test_unicode_preservation(self, processor):
        """Test that Unicode characters are properly preserved"""
        unicode_content = """
        Article with various Unicode characters:
        • Chinese: 人工智能
        • Arabic: الذكاء الاصطناعي
        • Russian: искусственный интеллект
        • Emoji: 🤖🧠💡
        • Accents: café, naïve, résumé, señor
        • Currency: $100, €200, ¥3000
        • Math: E=mc², ∞, π, ±
        """

        cleaned = processor._clean_content(unicode_content)

        # Unicode characters should be preserved
        assert "人工智能" in cleaned
        assert "الذكاء الاصطناعي" in cleaned
        assert "искусственный интеллект" in cleaned
        assert "🤖" in cleaned
        assert "café" in cleaned
        assert "€200" in cleaned
        assert "E=mc²" in cleaned

    def test_keyword_extraction(self, processor):
        """Test keyword extraction functionality"""
        text = """
        Artificial intelligence and machine learning are transforming the technology industry.
        Deep learning models, neural networks, and natural language processing are key areas
        of AI research. Python programming is widely used for developing AI applications.
        Open source AI frameworks like TensorFlow and PyTorch enable developers to build
        sophisticated machine learning systems.
        """

        keywords = processor._extract_keywords(text)

        # Should extract relevant keywords
        assert isinstance(keywords, list)
        assert len(keywords) <= ProcessingConstants.MAX_KEYWORDS

        # Should contain expected keywords
        text_lower = text.lower()
        for keyword in keywords:
            assert keyword in text_lower

        # Should filter out common words
        common_words = ["news", "article", "story", "time", "day"]
        for common in common_words:
            assert common not in keywords

    def test_keyword_extraction_empty_text(self, processor):
        """Test keyword extraction with empty text"""
        keywords = processor._extract_keywords("")
        assert keywords == []

    def test_sentiment_analysis(self, processor):
        """Test sentiment analysis functionality"""
        # Test positive sentiment
        positive_text = "This is wonderful and amazing news! Everyone is excited about the breakthrough."
        sentiment = processor._analyze_sentiment(positive_text)
        assert sentiment > 0.6  # Should be positive

        # Test negative sentiment
        negative_text = "This is terrible and disappointing news. The failure has caused many problems."
        sentiment = processor._analyze_sentiment(negative_text)
        assert sentiment < 0.4  # Should be negative

        # Test neutral sentiment
        neutral_text = "The article discusses various aspects of the technology industry."
        sentiment = processor._analyze_sentiment(neutral_text)
        assert 0.4 <= sentiment <= 0.6  # Should be neutral

    def test_sentiment_analysis_error_handling(self, processor):
        """Test sentiment analysis error handling"""
        # Test with problematic text
        problematic_text = "😀🎉🚀" * 1000  # Lots of emojis

        # Should not crash and should return neutral sentiment
        sentiment = processor._analyze_sentiment(problematic_text)
        assert isinstance(sentiment, float)
        assert 0.0 <= sentiment <= 1.0

    def test_batch_processing(self, processor, sample_article):
        """Test processing multiple articles in batch"""
        # Create multiple articles
        articles = [sample_article]

        # Modify for variety
        for i in range(3):
            article = Article(
                title=f"Article {i+1}: {sample_article.title}",
                content=f"{sample_article.content} Additional content for article {i+1}.",
                url=f"https://example.com/article-{i+1}",
                source=f"Source{i+1}",
                source_type=SourceType.RSS,
                category=sample_article.category,
                published_at=datetime.now()
            )
            articles.append(article)

        processed_articles = processor.process(articles)

        # Verify all articles were processed
        assert len(processed_articles) == len(articles)

        # Verify each article was processed correctly
        for processed in processed_articles:
            assert processed.word_count > 0
            assert processed.reading_time_minutes >= 1
            assert isinstance(processed.keywords, list)
            assert processed.sentiment_score is not None

    def test_error_handling_in_processing(self, processor):
        """Test error handling during article processing"""
        # Create article with problematic content
        article = Article(
            title="Test Article",
            content="Valid content",
            url="https://example.com/test",
            source="Test",
            source_type=SourceType.RSS,
            category="test",
            published_at=datetime.now()
        )

        # Mock the _clean_content method to raise an exception
        original_clean = processor._clean_content
        processor._clean_content = lambda x: (_ for _ in ()).throw(Exception("Test error"))

        try:
            processed = processor._process_article(article)

            # Should return a minimal processed article
            assert processed.title == article.title
            assert processed.content == article.content
            assert processed.word_count == 0
            assert processed.reading_time_minutes == 1
            assert processed.keywords == []
            assert processed.sentiment_score == 0.5

        finally:
            # Restore original method
            processor._clean_content = original_clean

    def test_processing_with_sentiment_disabled(self, sample_article):
        """Test processing when sentiment analysis is disabled"""
        class MockConfig:
            class Processing:
                min_article_length = 200
                max_article_age = 24
                sentiment_analysis = False  # Disabled
                duplicate_threshold = 0.8

            processing = Processing()

        processor = ContentProcessor(MockConfig())
        processed = processor._process_article(sample_article)

        # Sentiment should be None when disabled
        assert processed.sentiment_score is None

    def test_keyword_filtering(self, processor):
        """Test that keywords are properly filtered"""
        text = """
        News article about technology. People read news every day.
        According to reports, new technology emerges constantly.
        This story could change everything. Time will tell.
        """

        keywords = processor._extract_keywords(text)

        # Should filter out common words
        common_words = ["news", "article", "story", "time", "day", "people", "new", "said"]
        for common in common_words:
            assert common not in keywords

        # Should contain meaningful phrases
        meaningful_keywords = [kw for kw in keywords if len(kw.split()) > 1]
        assert len(meaningful_keywords) > 0