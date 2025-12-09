#!/usr/bin/env python3
"""
RSS Feed Fetcher for Atlanta News Report

Fetches and parses RSS feeds from Atlanta news sources.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import pytz


logger = logging.getLogger(__name__)


@dataclass
class Article:
    """Represents a news article."""
    title: str
    url: str
    summary: str
    published: datetime
    source: str
    category: str
    image_url: Optional[str] = None
    author: Optional[str] = None
    id: str = field(default="")

    def __post_init__(self):
        """Generate unique ID if not provided."""
        if not self.id:
            # Create unique ID from URL hash
            self.id = hashlib.md5(self.url.encode()).hexdigest()[:12]


class NewsFetcher:
    """
    Fetches news articles from RSS feeds.

    Attributes:
        feeds_config: List of feed configurations from config.yaml
        timeout: Request timeout in seconds
        timezone: Timezone for date parsing
    """

    DEFAULT_TIMEOUT = 30
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        feeds_config: List[Dict[str, Any]],
        timeout: int = DEFAULT_TIMEOUT,
        timezone: str = "America/New_York"
    ):
        """
        Initialize the news fetcher.

        Args:
            feeds_config: List of feed dictionaries with 'name', 'url', 'category'
            timeout: Request timeout in seconds
            timezone: Timezone string for date handling
        """
        self.feeds_config = feeds_config
        self.timeout = timeout
        self.timezone = pytz.timezone(timezone)
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with appropriate headers."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        })
        return session

    def fetch_all_feeds(self, max_workers: int = 5) -> List[Article]:
        """
        Fetch articles from all configured RSS feeds concurrently.

        Args:
            max_workers: Maximum number of concurrent fetches

        Returns:
            List of all articles from all feeds
        """
        all_articles = []
        errors = []

        logger.info(f"Fetching from {len(self.feeds_config)} RSS feeds...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_feed = {
                executor.submit(
                    self.fetch_feed,
                    feed['url'],
                    feed['name'],
                    feed['category']
                ): feed
                for feed in self.feeds_config
            }

            for future in as_completed(future_to_feed):
                feed = future_to_feed[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                    logger.info(
                        f"Fetched {len(articles)} articles from {feed['name']}"
                    )
                except Exception as e:
                    error_msg = f"Error fetching {feed['name']}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

        if errors:
            logger.warning(f"Completed with {len(errors)} feed errors")

        logger.info(f"Total articles fetched: {len(all_articles)}")
        return all_articles

    def fetch_feed(
        self,
        url: str,
        source_name: str,
        category: str
    ) -> List[Article]:
        """
        Fetch and parse a single RSS feed.

        Args:
            url: RSS feed URL
            source_name: Name of the news source
            category: Category for articles from this feed

        Returns:
            List of Article objects
        """
        articles = []

        try:
            # Fetch the feed content
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse with feedparser
            feed = feedparser.parse(response.content)

            if feed.bozo and feed.bozo_exception:
                logger.warning(
                    f"Feed parsing warning for {source_name}: "
                    f"{feed.bozo_exception}"
                )

            # Process each entry
            for entry in feed.entries:
                try:
                    article = self._parse_entry(entry, source_name, category)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.debug(
                        f"Error parsing entry from {source_name}: {str(e)}"
                    )

        except requests.RequestException as e:
            logger.error(f"Request error for {source_name} ({url}): {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for {source_name}: {str(e)}")
            raise

        return articles

    def _parse_entry(
        self,
        entry: Dict[str, Any],
        source_name: str,
        category: str
    ) -> Optional[Article]:
        """
        Parse a feedparser entry into an Article object.

        Args:
            entry: Feedparser entry dictionary
            source_name: Name of the news source
            category: Category for this article

        Returns:
            Article object or None if parsing fails
        """
        # Get required fields
        title = self._clean_text(entry.get('title', ''))
        url = entry.get('link', '')

        if not title or not url:
            return None

        # Get summary/description
        summary = self._extract_summary(entry)

        # Parse published date
        published = self._parse_date(entry)

        # Get optional fields
        image_url = self._extract_image(entry)
        author = entry.get('author', '') or entry.get('dc_creator', '')

        return Article(
            title=title,
            url=url,
            summary=summary,
            published=published,
            source=source_name,
            category=category,
            image_url=image_url,
            author=self._clean_text(author) if author else None
        )

    def _extract_summary(self, entry: Dict[str, Any]) -> str:
        """Extract and clean summary text from entry."""
        # Try different fields for summary
        summary = (
            entry.get('summary', '') or
            entry.get('description', '') or
            entry.get('content', [{}])[0].get('value', '')
        )

        # Clean HTML tags
        summary = self._strip_html(summary)
        summary = self._clean_text(summary)

        # Truncate if too long
        if len(summary) > 500:
            summary = summary[:497] + "..."

        return summary

    def _parse_date(self, entry: Dict[str, Any]) -> datetime:
        """Parse publication date from entry."""
        # Try different date fields
        date_str = (
            entry.get('published', '') or
            entry.get('pubDate', '') or
            entry.get('updated', '') or
            entry.get('created', '')
        )

        if date_str:
            try:
                dt = date_parser.parse(date_str)
                # Ensure timezone aware
                if dt.tzinfo is None:
                    dt = self.timezone.localize(dt)
                return dt
            except (ValueError, TypeError) as e:
                logger.debug(f"Date parsing failed for '{date_str}': {e}")

        # Fallback to current time
        return datetime.now(self.timezone)

    def _extract_image(self, entry: Dict[str, Any]) -> Optional[str]:
        """Extract image URL from entry."""
        # Try media content
        media = entry.get('media_content', [])
        if media and isinstance(media, list):
            for m in media:
                if m.get('url'):
                    return m['url']

        # Try media thumbnail
        thumbnail = entry.get('media_thumbnail', [])
        if thumbnail and isinstance(thumbnail, list):
            if thumbnail[0].get('url'):
                return thumbnail[0]['url']

        # Try enclosures
        enclosures = entry.get('enclosures', [])
        for enc in enclosures:
            if enc.get('type', '').startswith('image'):
                return enc.get('url')

        # Try to extract from content
        content = entry.get('content', [{}])[0].get('value', '')
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            img = soup.find('img')
            if img and img.get('src'):
                return img['src']

        return None

    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text(separator=' ')

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove common artifacts
        text = text.replace('\n', ' ').replace('\r', '')
        text = text.replace('&nbsp;', ' ')
        return text.strip()

    def test_feeds(self) -> Dict[str, Dict[str, Any]]:
        """
        Test connectivity to all configured feeds.

        Returns:
            Dictionary mapping feed names to test results
        """
        results = {}

        for feed in self.feeds_config:
            name = feed['name']
            url = feed['url']

            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()

                parsed = feedparser.parse(response.content)
                entry_count = len(parsed.entries)

                results[name] = {
                    'status': 'ok',
                    'entries': entry_count,
                    'url': url
                }
                logger.info(f"[OK] {name}: {entry_count} entries")

            except requests.RequestException as e:
                results[name] = {
                    'status': 'error',
                    'error': str(e),
                    'url': url
                }
                logger.error(f"[FAIL] {name}: {str(e)}")

            except Exception as e:
                results[name] = {
                    'status': 'error',
                    'error': str(e),
                    'url': url
                }
                logger.error(f"[FAIL] {name}: {str(e)}")

        return results


if __name__ == '__main__':
    # Quick test
    import yaml

    logging.basicConfig(level=logging.INFO)

    # Load config
    with open('../config.yaml') as f:
        config = yaml.safe_load(f)

    feeds = config['atlanta_news_report']['feeds']
    fetcher = NewsFetcher(feeds)

    # Test feeds
    print("\n=== Testing RSS Feeds ===\n")
    results = fetcher.test_feeds()

    # Fetch articles
    print("\n=== Fetching Articles ===\n")
    articles = fetcher.fetch_all_feeds()

    print(f"\nTotal: {len(articles)} articles")
    for article in articles[:5]:
        print(f"\n- {article.title}")
        print(f"  Source: {article.source}")
        print(f"  Published: {article.published}")
