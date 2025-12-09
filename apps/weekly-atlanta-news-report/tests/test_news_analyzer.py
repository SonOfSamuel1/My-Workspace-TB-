"""
Tests for news_analyzer.py - Article processing functionality.
"""
import pytest
from datetime import datetime, timedelta

import pytz

from news_analyzer import NewsAnalyzer, ProcessedNews
from news_fetcher import Article


class TestNewsAnalyzer:
    """Tests for NewsAnalyzer class."""

    def test_init(self, sample_config):
        """Test NewsAnalyzer initialization."""
        config = sample_config['atlanta_news_report']
        analyzer = NewsAnalyzer(config)

        assert analyzer.max_articles == 25
        assert analyzer.min_articles == 15
        assert analyzer.lookback_days == 7
        assert analyzer.deduplicate is True
        assert analyzer.similarity_threshold == 0.7

    def test_process_articles(self, sample_config, sample_articles):
        """Test article processing pipeline."""
        config = sample_config['atlanta_news_report']
        analyzer = NewsAnalyzer(config)

        processed = analyzer.process_articles(sample_articles)

        assert isinstance(processed, ProcessedNews)
        assert processed.total_count > 0
        assert len(processed.top_stories) <= 5
        assert processed.duplicates_removed >= 0

    def test_filter_by_date(self, sample_config, timezone):
        """Test date filtering."""
        config = sample_config['atlanta_news_report']
        analyzer = NewsAnalyzer(config)

        now = datetime.now(timezone)
        articles = [
            Article(
                title="Recent Article",
                url="https://example.com/1",
                summary="Recent",
                published=now - timedelta(hours=1),
                source="Test",
                category="general"
            ),
            Article(
                title="Old Article",
                url="https://example.com/2",
                summary="Old",
                published=now - timedelta(days=10),
                source="Test",
                category="general"
            ),
        ]

        start = now - timedelta(days=7)
        end = now

        filtered = analyzer.filter_by_date(articles, start, end)

        assert len(filtered) == 1
        assert filtered[0].title == "Recent Article"

    def test_deduplicate_articles(self, sample_config, timezone):
        """Test article deduplication."""
        config = sample_config['atlanta_news_report']
        analyzer = NewsAnalyzer(config)

        now = datetime.now(timezone)
        articles = [
            Article(
                title="Atlanta Mayor announces new infrastructure plan",
                url="https://example.com/1",
                summary="Original article",
                published=now,
                source="AJC",
                category="general"
            ),
            Article(
                title="Atlanta Mayor announces new infrastructure initiative",  # Similar
                url="https://example.com/2",
                summary="Duplicate article",
                published=now - timedelta(hours=1),
                source="11Alive",
                category="general"
            ),
            Article(
                title="Completely different article about sports",
                url="https://example.com/3",
                summary="Different topic",
                published=now - timedelta(hours=2),
                source="WSB",
                category="general"
            ),
        ]

        deduplicated = analyzer.deduplicate_articles(articles)

        # Should keep 2 unique articles
        assert len(deduplicated) == 2

    def test_deduplicate_keeps_newest(self, sample_config, timezone):
        """Test that deduplication keeps the newest article."""
        config = sample_config['atlanta_news_report']
        analyzer = NewsAnalyzer(config)

        now = datetime.now(timezone)
        articles = [
            Article(
                title="Breaking news story",
                url="https://example.com/1",
                summary="Newer version",
                published=now,
                source="AJC",
                category="general"
            ),
            Article(
                title="Breaking news story",  # Exact duplicate title
                url="https://example.com/2",
                summary="Older version",
                published=now - timedelta(hours=2),
                source="11Alive",
                category="general"
            ),
        ]

        deduplicated = analyzer.deduplicate_articles(articles)

        assert len(deduplicated) == 1
        assert deduplicated[0].source == "AJC"  # Newest kept

    def test_rank_articles(self, sample_config, timezone):
        """Test article ranking."""
        config = sample_config['atlanta_news_report']
        analyzer = NewsAnalyzer(config)

        now = datetime.now(timezone)
        articles = [
            Article(
                title="Old article with short title",
                url="https://example.com/1",
                summary="",  # No summary
                published=now - timedelta(days=5),
                source="Test",
                category="general"
            ),
            Article(
                title="Recent article with a good descriptive title for readers",
                url="https://example.com/2",
                summary="A detailed summary that provides context about the article.",
                published=now - timedelta(hours=1),
                source="Test",
                category="general",
                image_url="https://example.com/image.jpg"
            ),
        ]

        ranked = analyzer.rank_articles(articles)

        # Recent article with better content should rank first
        assert ranked[0].title.startswith("Recent")

    def test_categorize_articles(self, sample_config, sample_articles):
        """Test article categorization."""
        config = sample_config['atlanta_news_report']
        analyzer = NewsAnalyzer(config)

        categorized = analyzer.categorize_articles(sample_articles)

        assert 'general' in categorized
        assert 'business' in categorized
        assert len(categorized['general']) > 0
        assert len(categorized['business']) > 0

    def test_similarity_calculation(self, sample_config):
        """Test similarity calculation between titles."""
        config = sample_config['atlanta_news_report']
        analyzer = NewsAnalyzer(config)

        # Very similar titles
        sim1 = analyzer._calculate_similarity(
            "atlanta mayor announces new plan",
            "atlanta mayor announces new initiative"
        )
        assert sim1 > 0.7

        # Different titles
        sim2 = analyzer._calculate_similarity(
            "atlanta mayor announces new plan",
            "sports team wins championship game"
        )
        assert sim2 < 0.3

        # Identical titles
        sim3 = analyzer._calculate_similarity(
            "same title",
            "same title"
        )
        assert sim3 == 1.0

    def test_get_statistics(self, sample_config, sample_articles):
        """Test statistics generation."""
        config = sample_config['atlanta_news_report']
        analyzer = NewsAnalyzer(config)

        processed = analyzer.process_articles(sample_articles)
        stats = analyzer.get_statistics(processed)

        assert 'total_articles' in stats
        assert 'top_stories' in stats
        assert 'general_news' in stats
        assert 'business_news' in stats
        assert 'duplicates_removed' in stats
        assert 'sources' in stats
        assert 'period' in stats

    def test_empty_articles(self, sample_config):
        """Test processing empty article list."""
        config = sample_config['atlanta_news_report']
        analyzer = NewsAnalyzer(config)

        processed = analyzer.process_articles([])

        assert processed.total_count == 0
        assert len(processed.top_stories) == 0
        assert len(processed.general_news) == 0
        assert len(processed.business_news) == 0

    def test_source_diversity_in_top_stories(self, sample_config, timezone):
        """Test that top stories have source diversity."""
        config = sample_config['atlanta_news_report']
        config['report']['top_stories_count'] = 3
        analyzer = NewsAnalyzer(config)

        now = datetime.now(timezone)
        # Create many articles from same source
        articles = [
            Article(
                title=f"Article {i} from AJC",
                url=f"https://example.com/{i}",
                summary="Summary",
                published=now - timedelta(hours=i),
                source="AJC",
                category="general"
            )
            for i in range(10)
        ]
        # Add one from different source
        articles.append(Article(
            title="Article from 11Alive",
            url="https://example.com/11alive",
            summary="Summary",
            published=now,
            source="11Alive",
            category="general"
        ))

        processed = analyzer.process_articles(articles)

        # Check that not all top stories are from same source
        top_sources = [a.source for a in processed.top_stories]
        # Max 2 from same source allowed in top stories
        assert top_sources.count("AJC") <= 2
