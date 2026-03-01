"""Tests for RSS Fetcher module."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.rss_fetcher import RSSFetcher, Article


class TestRSSFetcher:
    """Tests for RSSFetcher class."""

    def test_init(self, sample_feed_config):
        """Test RSSFetcher initialization."""
        fetcher = RSSFetcher(sample_feed_config)
        assert len(fetcher.feeds) == 2

    @patch('src.rss_fetcher.feedparser.parse')
    def test_fetch_single_feed(self, mock_parse, sample_feed_config):
        """Test fetching from a single feed."""
        # Mock feedparser response
        mock_entry = Mock()
        mock_entry.title = "Test Article"
        mock_entry.link = "https://example.com/test"
        mock_entry.summary = "<p>Test summary</p>"
        mock_entry.published_parsed = (2024, 1, 15, 10, 0, 0, 0, 0, 0)

        mock_feed = Mock()
        mock_feed.entries = [mock_entry]
        mock_parse.return_value = mock_feed

        fetcher = RSSFetcher([sample_feed_config[0]])
        articles = fetcher.fetch_all()

        assert len(articles) == 1
        assert articles[0].title == "Test Article"
        assert articles[0].source == "Test Feed 1"

    def test_clean_summary(self):
        """Test HTML cleaning from summary."""
        fetcher = RSSFetcher([])

        html_summary = "<p>This is <strong>bold</strong> text</p>"
        cleaned = fetcher._clean_summary(html_summary)

        assert "<" not in cleaned
        assert ">" not in cleaned
        assert "bold" in cleaned

    def test_clean_summary_truncation(self):
        """Test summary truncation."""
        fetcher = RSSFetcher([])

        long_summary = "A" * 1000
        cleaned = fetcher._clean_summary(long_summary)

        assert len(cleaned) <= 500


class TestArticle:
    """Tests for Article dataclass."""

    def test_article_creation(self):
        """Test creating an Article instance."""
        article = Article(
            title="Test",
            link="https://example.com",
            summary="Summary",
            published=datetime.now(),
            source="Test Source",
            category="test"
        )

        assert article.title == "Test"
        assert article.category == "test"

    def test_article_without_published(self):
        """Test Article with None published date."""
        article = Article(
            title="Test",
            link="https://example.com",
            summary="Summary",
            published=None,
            source="Test Source",
            category="test"
        )

        assert article.published is None
