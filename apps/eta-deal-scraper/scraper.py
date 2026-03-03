"""Broker website scraper for ETA deals."""

import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Common paths to try for finding a broker's listings page
LISTINGS_PATHS = [
    "/listings",
    "/businesses-for-sale",
    "/buy-a-business",
    "/business-listings",
    "/active-listings",
    "/businesses-available",
    "/for-sale",
    "/listings/businesses-for-sale",
    "/available-businesses",
    "/businesses",
    "/search",
    "/buy",
]

# URL patterns that indicate an INDIVIDUAL listing detail page.
# Each alternative must be followed by a non-empty slug/ID segment.
# We intentionally exclude index-style URLs like /businesses-for-sale/page/N.
LISTING_URL_PATTERN = re.compile(
    r"""
    (
        # /listing/12345  or  /listings/long-slug-name
        /listings?/(?!page/)[\w][\w\-_%]+

        # /businesses/slug/id/  (two-segment path — Website Closers style)
      | /businesses/(?!for-sale)[\w][\w\-_%]+/[\w][\w\-_%]+

        # /buy/listing-slug  (must have non-trivial slug, not just /buy/)
      | /buy/[\w][\w\-_%]{3,}

        # /acquisitions/company-name
      | /acquisitions?/[\w][\w\-_%]+

        # /business-detail/id  or  /business-details/id
      | /business[-_]details?/[\w][\w\-_%]+

        # /profile/company-name
      | /profile/[\w][\w\-_%]+

        # /available/business-name  (must have 4+ chars after /available/)
      | /available/[\w][\w\-_%]{3,}

        # /deals/listing-slug
      | /deals?/[\w][\w\-_%]+
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Nav link text that points to a listings section
LISTINGS_NAV_KEYWORDS = [
    "listings",
    "businesses for sale",
    "buy a business",
    "businesses available",
    "available businesses",
    "for sale",
    "active listings",
    "business listings",
    "find a business",
    "search businesses",
]

# Keywords that signal a page contains business listing content
LISTINGS_PAGE_SIGNALS = [
    "asking price",
    "cash flow",
    "gross revenue",
    "ebitda",
    "listing",
    "business for sale",
    "inquire",
    "sde",
    "seller discretionary",
    "multiple",
]


class BrokerScraper:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get_listings(self, base_url: str) -> list[dict]:
        """Return all listing dicts found on a broker's site."""
        listings_url = self._find_listings_page(base_url)
        if not listings_url:
            logger.warning(f"  Could not find listings page at {base_url}")
            return []
        logger.info(f"  Listings page: {listings_url}")
        return self._extract_listings(listings_url, base_url)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_listings_page(self, base_url: str) -> Optional[str]:
        """
        Try three strategies in order:
        1. Follow a nav link that says 'listings', 'businesses for sale', etc.
        2. Try common URL paths.
        3. Treat the homepage itself as the listings page.
        """
        base = base_url.rstrip("/")

        # Strategy 1: nav link on homepage
        nav_url = self._nav_link_on_page(base_url, base_url)
        if nav_url:
            return nav_url

        # Strategy 2: common paths
        for path in LISTINGS_PATHS:
            url = base + path
            try:
                resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                if resp.status_code == 200 and self._is_listings_page(resp.text):
                    return resp.url
            except requests.RequestException:
                continue

        # Strategy 3: homepage fallback
        try:
            resp = self.session.get(base_url, timeout=self.timeout)
            if resp.status_code == 200 and self._is_listings_page(resp.text):
                return base_url
        except requests.RequestException:
            pass

        return None

    def _nav_link_on_page(self, page_url: str, base_url: str) -> Optional[str]:
        """Scan page for a nav link pointing at the listings section."""
        try:
            resp = self.session.get(page_url, timeout=self.timeout)
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True).lower()
                if any(kw in text for kw in LISTINGS_NAV_KEYWORDS):
                    return urljoin(base_url, a["href"])
        except Exception:
            pass
        return None

    def _is_listings_page(self, html: str) -> bool:
        """Return True if the page appears to list businesses for sale."""
        text = BeautifulSoup(html, "html.parser").get_text().lower()
        hits = sum(1 for kw in LISTINGS_PAGE_SIGNALS if kw in text)
        return hits >= 2

    def _extract_listings(self, page_url: str, base_url: str) -> list[dict]:
        """Pull individual listing links out of a listings page."""
        try:
            resp = self.session.get(page_url, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"  Failed to fetch {page_url}: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        listings: list[dict] = []
        seen: set[str] = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(page_url, href)

            # Must be on the same domain
            if not self._same_domain(full_url, base_url):
                continue

            # URL must match a recognized listing URL pattern — no fallback to
            # container heuristics, which are too noisy (nav <li> items etc.)
            if not LISTING_URL_PATTERN.search(full_url):
                continue

            # Normalize URL: strip trailing slash for deduplication
            canonical = full_url.rstrip("/")
            if canonical in seen:
                continue
            seen.add(canonical)

            title = a.get_text(strip=True) or a.get("title", "")

            # Generic CTA labels are not useful — extract from parent card instead
            generic_labels = {
                "view listing", "view details", "learn more", "click here",
                "details", "read more", "available", "inquire", "see listing",
                "unlock listing view listing",
            }
            if not title or title.lower().strip() in generic_labels or len(title) < 6:
                parent = a.find_parent(["article", "li", "div", "h2", "h3"])
                if parent:
                    title = parent.get_text(separator=" ", strip=True)[:150]

            # Final fallback: derive a readable name from the URL slug
            if not title or title.lower().strip() in generic_labels or len(title) < 6:
                # Use the second-to-last segment (slug), not the numeric ID
                parts = [p for p in canonical.rstrip("/").split("/") if p]
                slug = parts[-2] if len(parts) >= 2 and parts[-1].isdigit() else parts[-1]
                title = slug.replace("-", " ").replace("_", " ").title()[:150]

            listings.append({"url": canonical + "/", "title": title[:200]})

        logger.info(f"  Extracted {len(listings)} potential listings")
        return listings

    def _same_domain(self, url: str, base_url: str) -> bool:
        try:
            u = urlparse(url).netloc.lstrip("www.")
            b = urlparse(base_url).netloc.lstrip("www.")
            return u == b or u.endswith("." + b)
        except Exception:
            return False
