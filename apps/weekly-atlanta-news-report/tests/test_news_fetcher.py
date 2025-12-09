"""
Tests for news_fetcher.py - RSS feed fetching functionality.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

import pytz
import responses

from news_fetcher import NewsFetcher, Article


class TestArticle:
    """Tests for Article dataclass."""

    def test_article_creation(self, timezone):
        """Test basic article creation."""
        now = datetime.now(timezone)
        article = Article(
            title="Test Title",
            url="https://example.com/test",
            summary="Test summary",
            published=now,
            source="Test Source",
            category="general"
        )

        assert article.title == "Test Title"
        assert article.url == "https://example.com/test"
        assert article.source == "Test Source"
        assert article.category == "general"
        assert article.id  # Auto-generated

    def test_article_id_generation(self, timezone):
        """Test that article IDs are generated from URLs."""
        now = datetime.now(timezone)
        article1 = Article(
            title="Title 1",
            url="https://example.com/article1",
            summary="Summary",
            published=now,
            source="Source",
            category="general"
        )
        article2 = Article(
            title="Title 2",
            url="https://example.com/article2",
            summary="Summary",
            published=now,
            source="Source",
            category="general"
        )

        assert article1.id != article2.id
        assert len(article1.id) == 12  # MD5 hash truncated

    def test_article_with_optional_fields(self, timezone):
        """Test article with optional fields."""
        now = datetime.now(timezone)
        article = Article(
            title="Test Title",
            url="https://example.com/test",
            summary="Test summary",
            published=now,
            source="Test Source",
            category="general",
            image_url="https://example.com/image.jpg",
            author="Test Author"
        )

        assert article.image_url == "https://example.com/image.jpg"
        assert article.author == "Test Author"


class TestNewsFetcher:
    """Tests for NewsFetcher class."""

    def test_init(self, sample_config):
        """Test NewsFetcher initialization."""
        feeds = sample_config['atlanta_news_report']['feeds']
        fetcher = NewsFetcher(feeds)

        assert len(fetcher.feeds_config) == 2
        assert fetcher.timeout == 30
        assert fetcher.session is not None

    def test_init_with_custom_timeout(self, sample_config):
        """Test NewsFetcher with custom timeout."""
        feeds = sample_config['atlanta_news_report']['feeds']
        fetcher = NewsFetcher(feeds, timeout=60)

        assert fetcher.timeout == 60

    @responses.activate
    def test_fetch_feed_success(self, sample_config, rss_feed_response):
        """Test successful RSS feed fetch."""
        feed_url = "https://example.com/feed.xml"
        responses.add(
            responses.GET,
            feed_url,
            body=rss_feed_response,
            status=200,
            content_type="application/xml"
        )

        feeds = sample_config['atlanta_news_report']['feeds']
        fetcher = NewsFetcher(feeds)
        articles = fetcher.fetch_feed(feed_url, "Test Source", "general")

        assert len(articles) == 2
        assert articles[0].title == "Test Article Title"
        assert articles[0].source == "Test Source"
        assert articles[0].category == "general"

    @responses.activate
    def test_fetch_feed_http_error(self, sample_config):
        """Test RSS feed fetch with HTTP error."""
        feed_url = "https://example.com/feed.xml"
        responses.add(
            responses.GET,
            feed_url,
            status=404
        )

        feeds = sample_config['atlanta_news_report']['feeds']
        fetcher = NewsFetcher(feeds)

        with pytest.raises(Exception):
            fetcher.fetch_feed(feed_url, "Test Source", "general")

    @responses.activate
    def test_fetch_all_feeds(self, sample_config, rss_feed_response):
        """Test fetching all configured feeds."""
        feeds = sample_config['atlanta_news_report']['feeds']

        # Mock both feed URLs
        for feed in feeds:
            responses.add(
                responses.GET,
                feed['url'],
                body=rss_feed_response,
                status=200,
                content_type="application/xml"
            )

        fetcher = NewsFetcher(feeds)
        articles = fetcher.fetch_all_feeds()

        # 2 feeds x 2 articles each = 4 articles
        assert len(articles) == 4

    @responses.activate
    def test_fetch_all_feeds_partial_failure(self, sample_config, rss_feed_response):
        """Test fetching when some feeds fail."""
        feeds = sample_config['atlanta_news_report']['feeds']

        # First feed succeeds
        responses.add(
            responses.GET,
            feeds[0]['url'],
            body=rss_feed_response,
            status=200,
            content_type="application/xml"
        )

        # Second feed fails
        responses.add(
            responses.GET,
            feeds[1]['url'],
            status=500
        )

        fetcher = NewsFetcher(feeds)
        articles = fetcher.fetch_all_feeds()

        # Only articles from first feed
        assert len(articles) == 2

    @responses.activate
    def test_test_feeds(self, sample_config, rss_feed_response):
        """Test the test_feeds method."""
        feeds = sample_config['atlanta_news_report']['feeds']

        # First feed succeeds
        responses.add(
            responses.GET,
            feeds[0]['url'],
            body=rss_feed_response,
            status=200,
            content_type="application/xml"
        )

        # Second feed fails
        responses.add(
            responses.GET,
            feeds[1]['url'],
            status=404
        )

        fetcher = NewsFetcher(feeds)
        results = fetcher.test_feeds()

        assert results[feeds[0]['name']]['status'] == 'ok'
        assert results[feeds[0]['name']]['entries'] == 2
        assert results[feeds[1]['name']]['status'] == 'error'

    def test_clean_text(self, sample_config):
        """Test text cleaning."""
        feeds = sample_config['atlanta_news_report']['feeds']
        fetcher = NewsFetcher(feeds)

        # Test whitespace normalization
        assert fetcher._clean_text("  multiple   spaces  ") == "multiple spaces"

        # Test newline removal
        assert fetcher._clean_text("line1\nline2") == "line1 line2"

        # Test empty string
        assert fetcher._clean_text("") == ""

        # Test None
        assert fetcher._clean_text(None) == ""

    def test_strip_html(self, sample_config):
        """Test HTML stripping."""
        feeds = sample_config['atlanta_news_report']['feeds']
        fetcher = NewsFetcher(feeds)

        html = "<p>Hello <strong>world</strong></p>"
        text = fetcher._strip_html(html)

        assert "Hello" in text
        assert "world" in text
        assert "<" not in text
        assert ">" not in text
