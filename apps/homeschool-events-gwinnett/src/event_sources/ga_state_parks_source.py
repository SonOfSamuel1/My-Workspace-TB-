"""Georgia State Parks homeschool events source."""

import logging
import re
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


class GAStateParksSource(BaseEventSource):
    """Scrapes Georgia State Parks homeschool events page."""

    def __init__(
        self,
        url: str = "https://explore.gastateparks.org/Homeschool/Events",
    ):
        self.url = url
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
        return "Georgia State Parks"

    def fetch_events(self, lookahead_days: int = 30) -> List[Event]:
        """Scrape GA State Parks homeschool events page."""
        try:
            return self._fetch_events_inner(lookahead_days)
        except Exception as e:
            logger.error(f"GA State Parks fetch failed: {e}", exc_info=True)
            return []

    def _fetch_events_inner(self, lookahead_days: int) -> List[Event]:
        cutoff = datetime.now() + timedelta(days=lookahead_days)

        logger.info(f"Fetching GA State Parks: {self.url}")
        try:
            resp = self.session.get(self.url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"GA State Parks request failed: {e}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        events: List[Event] = []

        # GA State Parks uses .eventTitle for actual events
        # and .eventDateHeader for date-only section headers (skip those)
        containers = soup.select(".eventTitle")

        if not containers:
            # Fallback: try broader selectors, but skip date headers
            containers = [
                el
                for el in soup.select('[class*="event"], [class*="Event"]')
                if "eventDateHeader" not in (el.get("class") or [])
            ]

        if not containers:
            containers = self._find_event_containers(soup)

        for container in containers:
            event = self._parse_event_container(container, cutoff)
            if event:
                events.append(event)

        logger.info(f"GA State Parks: found {len(events)} events")
        return events

    def _find_event_containers(self, soup: BeautifulSoup) -> list:
        """Heuristic search for event containers when standard selectors fail."""
        containers = []

        # Look for elements with date-like text + title-like siblings
        for heading in soup.select("h2, h3, h4, h5, strong, b"):
            parent = heading.parent
            if parent:
                text = parent.get_text(" ", strip=True)
                # Check if the block has date-like content
                if re.search(
                    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2}",
                    text,
                    re.IGNORECASE,
                ):
                    containers.append(parent)

        return containers

    def _parse_event_container(self, container, cutoff: datetime) -> Optional[Event]:
        """Parse a single event container into an Event."""
        try:
            text = container.get_text(" ", strip=True)
            if len(text) < 10:
                return None

            # Title: first heading element or strong tag
            title_el = container.select_one("h2, h3, h4, h5, strong, b, a")
            if title_el:
                title = title_el.get_text(strip=True)
            else:
                # Use first line of text as title
                lines = [
                    line.strip()
                    for line in container.get_text("\n").split("\n")
                    if line.strip()
                ]
                title = lines[0] if lines else ""

            if not title or len(title) < 5 or len(title) > 200:
                return None

            # Date extraction
            date_str, start_time, end_time = self._extract_date_time(text)
            if not date_str:
                return None

            # Check within lookahead window
            try:
                event_dt = datetime.strptime(date_str, "%Y-%m-%d")
                if event_dt > cutoff:
                    return None
                if event_dt < datetime.now() - timedelta(days=1):
                    return None
            except ValueError:
                return None

            # Location: look for park name or location info
            location = self._extract_location(container, text)

            # Description
            description = self._extract_description(container, title)

            # URL
            url = None
            link = container.select_one("a[href]")
            if link and link.get("href"):
                href = link["href"]
                if href.startswith("/"):
                    url = f"https://explore.gastateparks.org{href}"
                elif href.startswith("http"):
                    url = href

            return Event(
                title=title.strip(),
                date=date_str,
                start_time=start_time,
                end_time=end_time,
                location=location,
                description=description,
                url=url,
                category="parks & rec",
                source="Georgia State Parks",
                is_all_day=start_time is None,
            )
        except Exception as e:
            logger.debug(f"Error parsing GA State Parks event: {e}")
            return None

    def _extract_date_time(self, text: str):
        """Extract date and time from event text."""
        date_str = None
        start_time = None
        end_time = None

        # Try to find date patterns
        # Pattern: "March 15, 2026" or "Mar 15, 2026"
        date_match = re.search(
            r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*"
            r"\s+\d{1,2}(?:,?\s+\d{4})?)\b",
            text,
            re.IGNORECASE,
        )
        if date_match:
            raw = date_match.group(1)
            try:
                dt = dateutil_parser.parse(raw, fuzzy=True)
                # If no year was in the string, assume current/next year
                if not re.search(r"\d{4}", raw):
                    now = datetime.now()
                    dt = dt.replace(year=now.year)
                    if dt < now - timedelta(days=30):
                        dt = dt.replace(year=now.year + 1)
                date_str = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        # Fallback: "2026-03-15" ISO format
        if not date_str:
            iso_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
            if iso_match:
                date_str = iso_match.group(1)

        # Time extraction: "10:00 AM - 2:00 PM" or "10:00am-2:00pm"
        time_match = re.search(
            r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))"
            r"(?:\s*[-–]\s*(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)))?",
            text,
        )
        if time_match:
            start_time = time_match.group(1).strip().upper()
            if time_match.group(2):
                end_time = time_match.group(2).strip().upper()

        return date_str, start_time, end_time

    def _extract_location(self, container, text: str) -> Optional[str]:
        """Extract location/park name from event container."""
        # Look for explicit location elements
        loc_el = container.select_one(
            '[class*="location"], [class*="venue"], [class*="park"]'
        )
        if loc_el:
            return loc_el.get_text(strip=True)

        # Look for "State Park" mentions in text
        park_match = re.search(
            r"([\w\s]+(?:State Park|State Historic Site|Nature Center))",
            text,
            re.IGNORECASE,
        )
        if park_match:
            return park_match.group(1).strip()

        return None

    def _extract_description(self, container, title: str) -> Optional[str]:
        """Extract description text, excluding the title."""
        desc_el = container.select_one('p, [class*="description"], [class*="summary"]')
        if desc_el:
            desc = desc_el.get_text(strip=True)
            if desc and desc != title:
                if len(desc) > 200:
                    desc = desc[:197] + "..."
                return desc

        return None

    def validate(self) -> bool:
        """Check that GA State Parks page is reachable."""
        try:
            resp = self.session.head(self.url, timeout=10, allow_redirects=True)
            return resp.status_code < 400
        except requests.RequestException:
            return False
