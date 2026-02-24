"""Gwinnett County Public Library events via Communico JSON API."""

import json
import logging
from datetime import datetime
from typing import List, Optional

import requests
from event_parser import Event
from event_sources.base import BaseEventSource

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Map Communico tags to app categories
TAG_CATEGORY_MAP = {
    "stem": "science fairs",
    "science": "science fairs",
    "education": "classes",
    "community": "meetups",
    "arts": "arts",
    "art": "arts",
    "craft": "arts",
}


class GwinnettLibrarySource(BaseEventSource):
    """Gwinnett County Public Library events via Communico JSON API."""

    def __init__(
        self,
        base_url: str = "https://gwinnettpl.libnet.info",
        search_term: str = "homeschool",
    ):
        self.base_url = base_url.rstrip("/")
        self.search_term = search_term

    @property
    def name(self) -> str:
        return "Gwinnett County Library"

    def fetch_events(self, lookahead_days: int = 30) -> List[Event]:
        """Fetch library events. Never raises — returns [] on failure."""
        try:
            return self._fetch_events_inner(lookahead_days)
        except Exception as e:
            logger.error(f"Gwinnett Library fetch failed: {e}", exc_info=True)
            return []

    def _fetch_events_inner(self, lookahead_days: int) -> List[Event]:
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")

        req_payload = json.dumps(
            {
                "private": False,
                "search": self.search_term,
                "date": today_str,
                "days": lookahead_days,
                "locations": [],
                "ages": [],
                "types": [],
            }
        )

        url = f"{self.base_url}/eeventcaldata?event_type=0&req={req_payload}"
        logger.info(f"Fetching Gwinnett Library events: {url}")

        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        resp.raise_for_status()

        data = resp.json()
        if not isinstance(data, list):
            logger.warning(f"Gwinnett Library: unexpected response type {type(data)}")
            return []

        events: List[Event] = []
        for item in data:
            event = self._item_to_event(item, today)
            if event:
                events.append(event)

        logger.info(f"Gwinnett Library: found {len(events)} events")
        return events

    def _item_to_event(self, item: dict, cutoff: datetime) -> Optional[Event]:
        """Convert a Communico JSON item to an Event."""
        try:
            title = item.get("title", "").strip()
            if not title:
                return None

            sub_title = item.get("sub_title", "").strip()
            if sub_title:
                title = f"{title} - {sub_title}"

            # Parse date from raw_start_time "YYYY-MM-DD HH:MM:SS"
            raw_start = item.get("raw_start_time", "")
            if not raw_start:
                return None

            date_str = raw_start[:10]  # "YYYY-MM-DD"
            try:
                event_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return None

            # Skip past events
            if event_date.date() < cutoff.date():
                return None

            start_time = item.get("start_time")  # Already "12:30pm" format
            end_time = item.get("end_time")

            location = item.get("location", "").strip() or None
            description = item.get("description", "").strip() or None

            # Fix double-slash in URL
            raw_url = item.get("url", "")
            if raw_url:
                raw_url = raw_url.replace("//event/", "/event/")

            category = self._map_category(item.get("tags", ""), title)

            return Event(
                title=title,
                date=date_str,
                start_time=start_time,
                end_time=end_time,
                location=location,
                description=description,
                url=raw_url or None,
                category=category,
                source="Gwinnett County Library",
                is_all_day=not start_time,
                latitude=None,
                longitude=None,
            )
        except Exception as e:
            logger.debug(f"Error parsing Gwinnett Library item: {e}")
            return None

    def _map_category(self, tags: str, title: str) -> str:
        """Map Communico tags to app categories."""
        combined = f"{tags} {title}".lower()
        for keyword, cat in TAG_CATEGORY_MAP.items():
            if keyword in combined:
                return cat
        return "library programs"

    def validate(self) -> bool:
        """Check that the library site is reachable."""
        try:
            resp = requests.head(self.base_url, timeout=10)
            return resp.status_code < 400
        except requests.RequestException:
            return False
