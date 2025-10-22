"""
Integration tests for the News Llama application
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.aggregators.rss_aggregator import RSSAggregator
from src.processors.content_processor import ContentProcessor
from src.processors.duplicate_detector import DuplicateDetector
from src.utils.models import Article, SourceType


class TestRSSAggregatorIntegration:
    """Test RSS aggregator integration"""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        class MockProcessing:
            min_article_length = 200
            max_article_age = 24

        class MockConfig:
            sources = {
                'rss': [
                    {
                        'url': 'https://feeds.bbci.co.uk/news/rss.xml',
                        'name': 'BBC News',
                        'category': 'general'
                    },
                    {
                        'url': 'https://techcrunch.com/feed/',
                        'name': 'TechCrunch',
                        'category': 'technology'
                    }
                ]
            }
            processing = MockProcessing()

        return MockConfig()

    @pytest.mark.asyncio
    async def test_rss_aggregator_integration(self, mock_config):
        """Test RSS aggregator with mock HTTP responses"""
        aggregator = RSSAggregator(mock_config)

        # Mock HTTP responses
        mock_responses = {
            'https://feeds.bbci.co.uk/news/rss.xml': """<?xml version="1.0" encoding="UTF-8"?>
            <rss version="2.0">
                <channel>
                    <title>BBC News</title>
                    <item>
                        <title>AI Breakthrough Announced</title>
                        <description>Scientists have made a major breakthrough in artificial intelligence research that could revolutionize how we understand machine learning. The research team discovered a new algorithm that significantly improves the efficiency of neural networks. This breakthrough has been published in the prestigious journal Nature and has generated significant excitement in the scientific community.</description>
                        <link>https://www.bbc.co.uk/news/ai-breakthrough</link>
                        <pubDate>Wed, 20 Oct 2025 10:00:00 GMT</pubDate>
                        <author>BBC Technology</author>
                    </item>
                </channel>
            </rss>""",
            'https://techcrunch.com/feed/': """<?xml version="1.0" encoding="UTF-8"?>
            <rss version="2.0">
                <channel>
                    <title>TechCrunch</title>
                    <item>
                        <title>Startup Raises $50M</title>
                        <description>A new AI startup has raised $50 million in Series B funding led by major venture capital firms. The company specializes in developing artificial intelligence solutions for enterprise customers and plans to use the funding to expand its engineering team and accelerate product development. Industry experts believe this investment signals growing confidence in AI technology companies.</description>
                        <link>https://techcrunch.com/2025/10/20/startup-funding</link>
                        <pubDate>Wed, 20 Oct 2025 09:00:00 GMT</pubDate>
                        <author>TechCrunch Staff</author>
                    </item>
                </channel>
            </rss>"""
        }

        # Mock the HTTP client
        with patch.object(aggregator.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def mock_response(url, rate_limit_key):
                mock_resp = Mock()
                mock_resp.text = mock_responses.get(url, "")
                mock_resp.headers = {'content-type': 'application/xml'}
                mock_resp.raise_for_status = Mock()
                return mock_resp

            mock_get.side_effect = mock_response

            # Test aggregation
            articles = await aggregator.collect()

            # Should collect articles from both feeds
            assert len(articles) == 2

            # Verify articles have correct structure
            for article in articles:
                assert isinstance(article, Article)
                assert article.title
                assert article.url
                assert article.source in ['BBC News', 'TechCrunch']
                assert article.category in ['general', 'technology']
                assert article.source_type == SourceType.RSS

    @pytest.mark.asyncio
    async def test_rss_aggregator_error_handling(self, mock_config):
        """Test RSS aggregator error handling"""
        aggregator = RSSAggregator(mock_config)

        # Mock HTTP client to raise exceptions
        with patch.object(aggregator.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Network error")

            # Should handle errors gracefully
            articles = await aggregator.collect()
            assert articles == []  # Should return empty list on error

    @pytest.mark.asyncio
    async def test_rss_aggregator_invalid_feed(self, mock_config):
        """Test RSS aggregator with invalid feed data"""
        aggregator = RSSAggregator(mock_config)

        # Mock HTTP client with invalid RSS
        with patch.object(aggregator.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_resp = Mock()
            mock_resp.text = "Invalid RSS content"
            mock_resp.headers = {'content-type': 'text/plain'}
            mock_resp.raise_for_status = Mock()
            mock_get.return_value = mock_resp

            # Should handle invalid RSS gracefully
            articles = await aggregator.collect()
            assert articles == []  # Should return empty list for invalid feed


class TestContentProcessingIntegration:
    """Test content processing integration"""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        class MockProcessing:
            min_article_length = 200
            max_article_age = 24
            sentiment_analysis = True

        class MockConfig:
            processing = MockProcessing()

        return MockConfig()

    @pytest.fixture
    def sample_articles(self):
        """Create sample articles"""
        return [
            Article(
                title="AI Revolution in Healthcare",
                content="""
                Artificial intelligence is transforming healthcare in unprecedented ways.
                Machine learning algorithms can now detect diseases from medical images
                with accuracy that rivals human experts. This breakthrough technology
                promises to revolutionize diagnostics and treatment planning.
                """,
                url="https://example.com/ai-healthcare",
                source="TechNews",
                source_type=SourceType.RSS,
                category="technology",
                author="Dr. Jane Smith",
                published_at=datetime.now()
            ),
            Article(
                title="Python 3.12 Released with Performance Improvements",
                content="""
                The Python Software Foundation has released Python 3.12 with significant
                performance improvements and new features. This version includes better
                error messages, improved type hinting, and enhanced pattern matching.
                """,
                url="https://example.com/python-312",
                source="PythonNews",
                source_type=SourceType.RSS,
                category="programming",
                author="Python Team",
                published_at=datetime.now()
            )
        ]

    def test_content_processing_pipeline(self, mock_config, sample_articles):
        """Test the complete content processing pipeline"""
        processor = ContentProcessor(mock_config)
        duplicate_detector = DuplicateDetector(mock_config)

        # Process articles
        processed_articles = processor.process(sample_articles)
        assert len(processed_articles) == len(sample_articles)

        # Verify processing results
        for article in processed_articles:
            assert article.word_count > 0
            assert article.reading_time_minutes >= 1
            assert isinstance(article.keywords, list)
            assert article.sentiment_score is not None
            assert article.sentiment_score >= 0.0
            assert article.sentiment_score <= 1.0

        # Test deduplication
        unique_articles = duplicate_detector.deduplicate(processed_articles)
        assert len(unique_articles) == len(processed_articles)  # No duplicates in sample

    def test_processing_with_unicode_content(self, mock_config):
        """Test processing content with Unicode characters"""
        processor = ContentProcessor(mock_config)

        unicode_article = Article(
            title="Global AI Development: 人工智能开发",
            content="""
            Artificial intelligence development is happening globally.
            In China, researchers are working on 人工智能 (artificial intelligence).
            In Arabic-speaking regions, الذكاء الاصطناعي is advancing rapidly.
            Russian scientists contribute to искусственный интеллект research.
            This global collaboration includes diverse characters: café, naïve, résumé.
            """,
            url="https://example.com/global-ai",
            source="GlobalTech",
            source_type=SourceType.RSS,
            category="technology",
            published_at=datetime.now()
        )

        processed = processor.process([unicode_article])
        assert len(processed) == 1

        article = processed[0]
        # Unicode characters should be preserved in content
        assert "人工智能" in article.content
        assert "الذكاء الاصطناعي" in article.content
        assert "искусственный интеллект" in article.content
        assert "café" in article.content

        # Keywords should include relevant terms
        assert any("artificial intelligence" in keyword.lower() for keyword in article.keywords)

    def test_sentiment_analysis_integration(self, mock_config):
        """Test sentiment analysis integration"""
        processor = ContentProcessor(mock_config)

        # Test different sentiment types
        articles = [
            Article(
                title="Positive News",
                content="This is wonderful and amazing news! Everyone is excited and happy.",
                url="https://example.com/positive",
                source="TestNews",
                source_type=SourceType.RSS,
                category="test",
                published_at=datetime.now()
            ),
            Article(
                title="Negative News",
                content="This is terrible and disappointing news. The situation is awful.",
                url="https://example.com/negative",
                source="TestNews",
                source_type=SourceType.RSS,
                category="test",
                published_at=datetime.now()
            ),
            Article(
                title="Neutral News",
                content="The article discusses various topics in an objective manner.",
                url="https://example.com/neutral",
                source="TestNews",
                source_type=SourceType.RSS,
                category="test",
                published_at=datetime.now()
            )
        ]

        processed = processor.process(articles)
        assert len(processed) == 3

        # Check sentiment scores
        sentiments = {article.title: article.sentiment_score for article in processed}

        assert sentiments["Positive News"] > 0.6  # Should be positive
        assert sentiments["Negative News"] < 0.4  # Should be negative
        assert 0.4 <= sentiments["Neutral News"] <= 0.6  # Should be neutral


class TestErrorHandlingIntegration:
    """Test error handling in integration scenarios"""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        class MockProcessing:
            min_article_length = 200
            max_article_age = 24
            sentiment_analysis = True

        class MockConfig:
            processing = MockProcessing()

        return MockConfig()

    def test_processing_with_malformed_data(self, mock_config):
        """Test processing with malformed article data"""
        processor = ContentProcessor(mock_config)

        # Create articles with various issues
        problematic_articles = [
            Article(
                title="",  # Empty title
                content="Some content here",
                url="https://example.com/test1",
                source="Test",
                source_type=SourceType.RSS,
                category="test",
                published_at=datetime.now()
            ),
            Article(
                title="Valid Title",
                content="",  # Empty content
                url="https://example.com/test2",
                source="Test",
                source_type=SourceType.RSS,
                category="test",
                published_at=datetime.now()
            ),
            Article(
                title="Valid Title",
                content="Short",  # Too short content
                url="https://example.com/test3",
                source="Test",
                source_type=SourceType.RSS,
                category="test",
                published_at=datetime.now()
            )
        ]

        # Should handle all problematic articles gracefully
        processed = processor.process(problematic_articles)
        assert len(processed) == len(problematic_articles)

        # Each article should be processed without crashes
        for article in processed:
            assert isinstance(article.word_count, int)
            assert isinstance(article.reading_time_minutes, int)
            assert isinstance(article.keywords, list)

    def test_duplicate_detection_with_edge_cases(self, mock_config):
        """Test duplicate detection with edge cases"""
        detector = DuplicateDetector(mock_config)

        # Create articles with edge cases
        edge_case_articles = [
            # Identical titles
            ProcessedArticle(
                title="Same Title",
                content="Different content here about technology",
                url="https://example.com/same1",
                source="Test",
                source_type=SourceType.RSS,
                category="test",
                published_at=datetime.now(),
                word_count=10,
                reading_time_minutes=1,
                keywords=[]
            ),
            ProcessedArticle(
                title="Same Title",
                content="Completely different content about sports",
                url="https://example.com/same2",
                source="Test",
                source_type=SourceType.RSS,
                category="test",
                published_at=datetime.now(),
                word_count=10,
                reading_time_minutes=1,
                keywords=[]
            ),
            # Empty content
            ProcessedArticle(
                title="Empty Content",
                content="",
                url="https://example.com/empty",
                source="Test",
                source_type=SourceType.RSS,
                category="test",
                published_at=datetime.now(),
                word_count=0,
                reading_time_minutes=1,
                keywords=[]
            )
        ]

        # Should handle edge cases without crashing
        result = detector.deduplicate(edge_case_articles)
        assert isinstance(result, list)
        assert len(result) >= 1  # At least one article should remain

    @pytest.mark.asyncio
    async def test_network_error_recovery(self):
        """Test recovery from network errors"""
        class MockProcessing:
            min_article_length = 200
            max_article_age = 24

        class MockConfig:
            sources = {
                'rss': [
                    {
                        'url': 'https://example.com/working-feed.xml',
                        'name': 'Working Feed',
                        'category': 'test'
                    },
                    {
                        'url': 'https://example.com/broken-feed.xml',
                        'name': 'Broken Feed',
                        'category': 'test'
                    }
                ]
            }
            processing = MockProcessing()

        aggregator = RSSAggregator(MockConfig())

        # Mock mixed success/failure responses
        with patch.object(aggregator.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def mock_response(url, rate_limit_key):
                if 'broken-feed' in url:
                    raise Exception("Network error")
                else:
                    mock_resp = Mock()
                    mock_resp.text = """<?xml version="1.0" encoding="UTF-8"?>
                    <rss version="2.0">
                        <channel>
                            <item>
                                <title>Working Article</title>
                                <description>This works fine</description>
                                <link>https://example.com/working</link>
                            </item>
                        </channel>
                    </rss>"""
                    mock_resp.headers = {'content-type': 'application/xml'}
                    mock_resp.raise_for_status = Mock()
                    return mock_resp

            mock_get.side_effect = mock_response

            # Should collect from working feed despite broken feed
            articles = await aggregator.collect()
            assert len(articles) == 1  # Only from working feed
            assert articles[0].title == "Working Article"


class TestPerformanceIntegration:
    """Test performance in integration scenarios"""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        class MockProcessing:
            min_article_length = 200
            max_article_age = 24
            sentiment_analysis = True

        class MockConfig:
            processing = MockProcessing()

        return MockConfig()

    def test_large_batch_processing(self, mock_config):
        """Test processing large batches of articles"""
        processor = ContentProcessor(mock_config)

        # Create many articles
        articles = []
        for i in range(100):
            article = Article(
                title=f"Article {i}: Technology News Update",
                content=f"This is article number {i} discussing the latest developments in technology. "
                       f"The content includes various technical details and insights about innovation. "
                       f"Each article is unique and contains substantial content for processing.",
                url=f"https://example.com/article-{i}",
                source="TechNews",
                source_type=SourceType.RSS,
                category="technology",
                published_at=datetime.now(),
                author=f"Author {i}"
            )
            articles.append(article)

        # Process all articles
        import time
        start_time = time.time()
        processed = processor.process(articles)
        end_time = time.time()

        # Should process all articles successfully
        assert len(processed) == 100

        # Should complete in reasonable time (less than 10 seconds for 100 articles)
        processing_time = end_time - start_time
        assert processing_time < 10.0, f"Processing took too long: {processing_time:.2f}s"

        # Verify processing results
        for article in processed:
            assert article.word_count > 0
            assert article.reading_time_minutes >= 1
            assert isinstance(article.keywords, list)
            assert article.sentiment_score is not None

    def test_memory_usage_with_large_content(self, mock_config):
        """Test memory usage with large article content"""
        processor = ContentProcessor(mock_config)

        # Create article with very large content
        large_content = "This is a large article. " * 10000  # ~150KB of content
        large_article = Article(
            title="Large Article Test",
            content=large_content,
            url="https://example.com/large-article",
            source="TestNews",
            source_type=SourceType.RSS,
            category="test",
            published_at=datetime.now()
        )

        # Process large article
        processed = processor.process([large_article])
        assert len(processed) == 1

        article = processed[0]
        assert article.word_count == len(large_content.split())
        assert article.reading_time_minutes > 10  # Should be significant reading time
        assert len(article.content) <= len(large_content)  # Content should not grow