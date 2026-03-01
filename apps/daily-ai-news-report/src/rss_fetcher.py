"""
RSS Feed Fetcher - Fetches and parses AI news from RSS feeds.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import feedparser

logger = logging.getLogger(__name__)


@dataclass
class Article:
    """Represents a news article."""
    title: str
    link: str
    summary: str
    published: Optional[datetime]
    source: str
    category: str


class RSSFetcher:
    """Fetches articles from RSS feeds."""

    def __init__(self, feeds: List[dict]):
        """
        Initialize the RSS fetcher.

        Args:
            feeds: List of feed configs with 'name', 'url', and 'category' keys
        """
        self.feeds = feeds

    def fetch_all(self) -> List[Article]:
        """
        Fetch articles from all configured feeds.

        Returns:
            List of Article objects
        """
        all_articles = []
        for feed_config in self.feeds:
            try:
                articles = self._fetch_feed(feed_config)
                all_articles.extend(articles)
                logger.info(f"Fetched {len(articles)} articles from {feed_config['name']}")
            except Exception as e:
                logger.error(f"Error fetching feed {feed_config['name']}: {e}")
        return all_articles

    def _fetch_feed(self, feed_config: dict) -> List[Article]:
        """
        Fetch articles from a single RSS feed.

        Args:
            feed_config: Feed configuration dict

        Returns:
            List of Article objects
        """
        feed = feedparser.parse(feed_config['url'])
        articles = []

        for entry in feed.entries:
            try:
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])

                article = Article(
                    title=entry.get('title', 'No Title'),
                    link=entry.get('link', ''),
                    summary=self._clean_summary(entry.get('summary', '')),
                    published=published,
                    source=feed_config['name'],
                    category=feed_config.get('category', 'general')
                )
                articles.append(article)
            except Exception as e:
                logger.warning(f"Error parsing entry: {e}")

        return articles

    def _clean_summary(self, summary: str) -> str:
        """Clean HTML from summary text."""
        from bs4 import BeautifulSoup
        if summary:
            soup = BeautifulSoup(summary, 'html.parser')
            return soup.get_text(strip=True)[:500]  # Limit length
        return ""
