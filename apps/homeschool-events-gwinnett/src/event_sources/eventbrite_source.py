"""Eventbrite web scraping source for homeschool events in Gwinnett County."""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser
from event_parser import Event
from event_sources.base import BaseEventSource

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Map Eventbrite category/subcategory strings to app categories
CATEGORY_MAP = {
    "field trip": "field trips",
    "field trips": "field trips",
    "museum": "field trips",
    "tour": "field trips",
    "nature": "parks & rec",
    "outdoor": "parks & rec",
    "park": "parks & rec",
    "hiking": "parks & rec",
    "sports": "sports",
    "athletics": "sports",
    "art": "arts",
    "arts": "arts",
    "craft": "arts",
    "music": "arts",
    "theater": "arts",
    "theatre": "arts",
    "science": "science fairs",
    "stem": "science fairs",
    "math": "classes",
    "class": "classes",
    "lesson": "classes",
    "tutoring": "classes",
    "workshop": "workshops",
    "seminar": "workshops",
    "conference": "workshops",
    "expo": "workshops",
    "fair": "workshops",
    "co-op": "co-ops",
    "coop": "co-ops",
    "cooperative": "co-ops",
    "meetup": "meetups",
    "social": "meetups",
    "playdate": "meetups",
    "play date": "meetups",
    "hangout": "meetups",
    "library": "library programs",
    "reading": "library programs",
    "story time": "library programs",
    "storytime": "library programs",
    "support": "support groups",
    "parent": "support groups",
}


class EventbriteSource(BaseEventSource):
    """Scrapes Eventbrite for homeschool events in Gwinnett County."""

    def __init__(
        self,
        url: str = "https://www.eventbrite.com/d/ga--gwinnett-county/homeschool/",
        max_pages: int = 3,
    ):
        self.base_url = url.rstrip("/")
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    @property
    def name(self) -> str:
        return "Eventbrite"

    def fetch_events(self, lookahead_days: int = 30) -> List[Event]:
        """Scrape Eventbrite search results pages."""
        try:
            return self._fetch_events_inner(lookahead_days)
        except Exception as e:
            logger.error(f"Eventbrite fetch failed: {e}", exc_info=True)
            return []

    def _fetch_events_inner(self, lookahead_days: int) -> List[Event]:
        cutoff = datetime.now() + timedelta(days=lookahead_days)
        all_events: List[Event] = []

        for page in range(1, self.max_pages + 1):
            url = f"{self.base_url}/?page={page}"
            logger.info(f"Fetching Eventbrite page {page}: {url}")

            try:
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
            except requests.RequestException as e:
                logger.warning(f"Eventbrite page {page} request failed: {e}")
                break

            html = resp.text

            # Try structured JSON extraction first
            events = self._extract_from_server_data(html, cutoff)
            if not events:
                # Fallback to HTML card parsing
                events = self._extract_from_html_cards(html, cutoff)

            if not events:
                logger.info(f"No events found on page {page}, stopping pagination")
                break

            all_events.extend(events)

            # Be polite
            if page < self.max_pages:
                time.sleep(1)

        logger.info(f"Eventbrite: found {len(all_events)} events total")
        return all_events

    def _extract_json_blob(self, html: str) -> Optional[dict]:
        """Extract __SERVER_DATA__ JSON using brace-depth counting."""
        marker = "window.__SERVER_DATA__ = "
        idx = html.find(marker)
        if idx < 0:
            return None

        start = idx + len(marker)
        depth = 0
        i = start
        while i < len(html):
            ch = html[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(html[start : i + 1])
                    except json.JSONDecodeError:
                        logger.debug("Failed to parse __SERVER_DATA__ JSON")
                        return None
            i += 1
        return None

    def _extract_from_server_data(self, html: str, cutoff: datetime) -> List[Event]:
        """Extract events from window.__SERVER_DATA__ JSON blob."""
        data = self._extract_json_blob(html)
        if not data:
            return []

        events: List[Event] = []

        # Primary path: search_data -> events -> results
        event_list = data.get("search_data", {}).get("events", {}).get("results", [])

        for item in event_list:
            event = self._server_data_item_to_event(item, cutoff)
            if event:
                events.append(event)

        if events:
            logger.info(f"Extracted {len(events)} events from __SERVER_DATA__")

        return events

    def _server_data_item_to_event(
        self, item: dict, cutoff: datetime
    ) -> Optional[Event]:
        """Convert a __SERVER_DATA__ event dict to an Event."""
        try:
            title = item.get("name") or item.get("title", "")
            if not title:
                return None

            # start_date is "YYYY-MM-DD", start_time is "HH:MM" (24h)
            date_str = item.get("start_date", "")
            if not date_str:
                return None

            try:
                event_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return None

            if event_date > cutoff:
                return None

            # Convert start_time "HH:MM" to "H:MM AM/PM"
            start_time = None
            raw_start = item.get("start_time", "")
            if raw_start:
                try:
                    t = datetime.strptime(raw_start, "%H:%M")
                    start_time = t.strftime("%I:%M %p").lstrip("0")
                except ValueError:
                    pass

            # Convert end_time "HH:MM" to "H:MM AM/PM"
            end_time = None
            raw_end = item.get("end_time", "")
            if raw_end:
                try:
                    t = datetime.strptime(raw_end, "%H:%M")
                    end_time = t.strftime("%I:%M %p").lstrip("0")
                except ValueError:
                    pass

            # Location + coordinates
            lat = None
            lon = None
            venue = item.get("primary_venue") or item.get("venue", {})
            if isinstance(venue, dict):
                venue_name = venue.get("name", "")
                address = venue.get("address", {})
                if isinstance(address, dict):
                    city = address.get("city", "")
                    region = address.get("region", "")
                    location = f"{venue_name}, {city}, {region}".strip(", ")
                    # Extract coordinates for distance filtering
                    try:
                        raw_lat = address.get("latitude")
                        raw_lon = address.get("longitude")
                        if raw_lat is not None and raw_lon is not None:
                            lat = float(raw_lat)
                            lon = float(raw_lon)
                    except (ValueError, TypeError):
                        pass
                else:
                    location = venue_name
            else:
                location = str(venue) if venue else None

            # URL
            url = item.get("url") or item.get("tickets_url", "")

            # Description
            description = (
                item.get("summary") or item.get("description", {}).get("text", "") or ""
            )
            if isinstance(description, dict):
                description = description.get("text", "")
            # Truncate long descriptions
            if len(description) > 200:
                description = description[:197] + "..."

            # Category
            category = self._map_category(
                item.get("category", ""),
                item.get("subcategory", ""),
                title,
            )

            return Event(
                title=title.strip(),
                date=date_str,
                start_time=start_time,
                end_time=end_time,
                location=location or None,
                description=description or None,
                url=url or None,
                category=category,
                source="Eventbrite",
                is_all_day=False,
                latitude=lat,
                longitude=lon,
            )
        except Exception as e:
            logger.debug(f"Error parsing Eventbrite server data item: {e}")
            return None

    def _extract_from_html_cards(self, html: str, cutoff: datetime) -> List[Event]:
        """Fallback: extract events from HTML event cards using BeautifulSoup."""
        soup = BeautifulSoup(html, "lxml")
        events: List[Event] = []

        # Eventbrite uses various card selectors
        cards = soup.select(
            '[data-testid="search-event-card"], '
            ".search-event-card-wrapper, "
            ".eds-event-card-content__content, "
            "article.eds-event-card"
        )

        if not cards:
            # Broader fallback: look for any link with eventbrite event pattern
            cards = soup.select('a[href*="/e/"]')

        for card in cards:
            event = self._html_card_to_event(card, cutoff)
            if event:
                events.append(event)

        if events:
            logger.info(f"Extracted {len(events)} events from HTML cards")

        return events

    def _html_card_to_event(self, card, cutoff: datetime) -> Optional[Event]:
        """Parse a single HTML event card into an Event."""
        try:
            # Title
            title_el = card.select_one(
                "h2, h3, "
                '[data-testid="event-card-title"], '
                ".eds-event-card-content__title"
            )
            if title_el:
                title = title_el.get_text(strip=True)
            elif card.name == "a":
                title = card.get_text(strip=True)
            else:
                return None

            if not title or len(title) < 5:
                return None

            # Date/time
            date_el = card.select_one(
                '[data-testid="event-card-date"], '
                ".eds-event-card-content__sub-title, "
                "time, .card-text--truncated__one"
            )
            date_text = date_el.get_text(strip=True) if date_el else ""

            date_str = None
            start_time = None
            if date_text:
                try:
                    dt = dateutil_parser.parse(date_text, fuzzy=True)
                    if dt.replace(tzinfo=None) > cutoff:
                        return None
                    date_str = dt.strftime("%Y-%m-%d")
                    if dt.hour != 0 or dt.minute != 0:
                        start_time = dt.strftime("%I:%M %p").lstrip("0")
                except (ValueError, TypeError):
                    pass

            if not date_str:
                return None

            # Location
            loc_el = card.select_one(
                '[data-testid="event-card-location"], '
                ".card-text--truncated__one + .card-text--truncated__one, "
                ".eds-event-card-content__sub-content"
            )
            location = loc_el.get_text(strip=True) if loc_el else None

            # URL
            url = None
            link = card.select_one("a[href]") if card.name != "a" else card
            if link and link.get("href"):
                href = link["href"]
                if href.startswith("/"):
                    url = f"https://www.eventbrite.com{href}"
                elif href.startswith("http"):
                    url = href

            category = self._map_category("", "", title)

            return Event(
                title=title.strip(),
                date=date_str,
                start_time=start_time,
                location=location,
                url=url,
                category=category,
                source="Eventbrite",
                is_all_day=start_time is None,
            )
        except Exception as e:
            logger.debug(f"Error parsing Eventbrite HTML card: {e}")
            return None

    def _map_category(self, eb_category: str, eb_subcategory: str, title: str) -> str:
        """Map Eventbrite category info + title keywords to app categories."""
        combined = f"{eb_category} {eb_subcategory} {title}".lower()
        for keyword, cat in CATEGORY_MAP.items():
            if keyword in combined:
                return cat
        return "General"

    def validate(self) -> bool:
        """Check that Eventbrite search page is reachable."""
        try:
            resp = self.session.head(self.base_url, timeout=10)
            return resp.status_code < 400
        except requests.RequestException:
            return False
