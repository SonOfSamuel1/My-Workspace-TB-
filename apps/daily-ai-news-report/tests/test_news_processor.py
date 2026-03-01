"""Tests for News Processor module."""

import pytest
from datetime import datetime, timedelta

from src.news_processor import NewsProcessor
from src.rss_fetcher import Article


class TestNewsProcessor:
    """Tests for NewsProcessor class."""

    def test_init_default_values(self):
        """Test default initialization values."""
        processor = NewsProcessor()

        assert processor.max_articles == 10
        assert processor.min_relevance_score == 0.3
        assert processor.dedup_window_days == 7

    def test_init_custom_values(self):
        """Test custom initialization values."""
        processor = NewsProcessor(
            max_articles=5,
            min_relevance_score=0.5,
            dedup_window_days=3
        )

        assert processor.max_articles == 5
        assert processor.min_relevance_score == 0.5

    def test_process_filters_by_relevance(self, sample_articles):
        """Test that low relevance articles are filtered out."""
        # Create article with no AI keywords
        low_relevance = Article(
            title="Sports News Today",
            link="https://example.com/sports",
            summary="Local team wins championship",
            published=datetime.now(),
            source="Sports Daily",
            category="sports"
        )

        processor = NewsProcessor(min_relevance_score=0.3)
        result = processor.process([low_relevance])

        assert len(result) == 0

    def test_process_includes_ai_articles(self, sample_articles):
        """Test that AI-related articles pass the filter."""
        processor = NewsProcessor(min_relevance_score=0.1)
        result = processor.process(sample_articles)

        assert len(result) > 0

    def test_deduplication(self):
        """Test that duplicate articles are removed."""
        article1 = Article(
            title="OpenAI Announces New Model",
            link="https://example.com/1",
            summary="Details about the model",
            published=datetime.now(),
            source="Tech News",
            category="research"
        )
        article2 = Article(
            title="OpenAI Announces New Model",  # Same title
            link="https://example.com/2",
            summary="More details",
            published=datetime.now(),
            source="Tech News",  # Same source
            category="research"
        )

        processor = NewsProcessor()
        result = processor.process([article1, article2])

        assert len(result) == 1

    def test_filter_by_date(self):
        """Test that old articles are filtered out."""
        old_article = Article(
            title="AI breakthrough with machine learning",
            link="https://example.com/old",
            summary="Old news about AI",
            published=datetime.now() - timedelta(days=30),
            source="Tech News",
            category="research"
        )

        processor = NewsProcessor(dedup_window_days=7)
        result = processor.process([old_article])

        assert len(result) == 0

    def test_max_articles_limit(self, sample_articles):
        """Test that max_articles limit is respected."""
        # Create many articles
        articles = []
        for i in range(20):
            articles.append(Article(
                title=f"AI and machine learning news {i}",
                link=f"https://example.com/{i}",
                summary="AI artificial intelligence neural network",
                published=datetime.now(),
                source=f"Source {i}",
                category="research"
            ))

        processor = NewsProcessor(max_articles=5, min_relevance_score=0.1)
        result = processor.process(articles)

        assert len(result) <= 5

    def test_relevance_scoring_high_keywords(self):
        """Test that high-priority keywords get higher scores."""
        processor = NewsProcessor()

        high_score_article = Article(
            title="OpenAI GPT-5 Large Language Model Released",
            link="https://example.com/1",
            summary="New artificial intelligence breakthrough",
            published=datetime.now(),
            source="AI News",
            category="research"
        )

        score = processor._calculate_relevance_score(high_score_article)
        assert score >= 0.5

    def test_get_seen_hashes(self):
        """Test getting seen hashes after processing."""
        processor = NewsProcessor()

        article = Article(
            title="AI News with machine learning",
            link="https://example.com/1",
            summary="AI content",
            published=datetime.now(),
            source="News",
            category="tech"
        )

        processor.process([article])
        hashes = processor.get_seen_hashes()

        assert len(hashes) > 0
