"""
Web Scraper - Extracts additional content from article URLs.
"""

import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Default headers to avoid being blocked
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


class WebScraper:
    """Scrapes additional content from web pages."""

    def __init__(self, timeout: int = 10, headers: Optional[dict] = None):
        """
        Initialize the web scraper.

        Args:
            timeout: Request timeout in seconds
            headers: Custom headers for requests
        """
        self.timeout = timeout
        self.headers = headers or DEFAULT_HEADERS

    def get_full_content(self, url: str) -> Optional[str]:
        """
        Fetch and extract main content from a URL.

        Args:
            url: The article URL to scrape

        Returns:
            Extracted text content or None if failed
        """
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            return self._extract_content(soup)

        except requests.RequestException as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main content from parsed HTML.

        Args:
            soup: BeautifulSoup object

        Returns:
            Extracted text content
        """
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()

        # Try common article content selectors
        content_selectors = [
            'article',
            '[role="main"]',
            '.post-content',
            '.article-content',
            '.entry-content',
            'main',
        ]

        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                text = content.get_text(separator=' ', strip=True)
                if len(text) > 200:  # Minimum content length
                    return text[:2000]  # Limit length

        # Fallback to body content
        body = soup.find('body')
        if body:
            return body.get_text(separator=' ', strip=True)[:2000]

        return ""

    def get_meta_description(self, url: str) -> Optional[str]:
        """
        Fetch meta description from a URL.

        Args:
            url: The URL to fetch

        Returns:
            Meta description or None
        """
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Try different meta tags
            for attr in ['description', 'og:description', 'twitter:description']:
                meta = soup.find('meta', attrs={'name': attr}) or \
                       soup.find('meta', attrs={'property': attr})
                if meta and meta.get('content'):
                    return meta['content']

            return None

        except Exception as e:
            logger.warning(f"Failed to get meta for {url}: {e}")
            return None
