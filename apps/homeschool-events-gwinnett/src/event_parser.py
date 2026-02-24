#!/usr/bin/env python3
"""
Event Parser Module

Parses Perplexity API responses into structured Event objects.
Handles JSON and regex-based text parsing with date normalization.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import quote

from dateutil import parser as dateutil_parser

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Structured homeschool event."""

    title: str
    date: str  # YYYY-MM-DD
    start_time: Optional[str] = None  # HH:MM AM/PM
    end_time: Optional[str] = None  # HH:MM AM/PM
    location: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    category: str = "General"
    source: Optional[str] = None
    is_all_day: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def to_calendar_url(self) -> str:
        """Generate a Google Calendar 'Add to Calendar' URL."""
        base = "https://calendar.google.com/calendar/event?action=TEMPLATE"

        # Title
        params = f"&text={quote(self.title)}"

        # Dates
        if self.is_all_day or not self.start_time:
            # All-day event
            try:
                dt = datetime.strptime(self.date, "%Y-%m-%d")
                next_day = dt + timedelta(days=1)
                date_str = dt.strftime("%Y%m%d")
                next_day_str = next_day.strftime("%Y%m%d")
                params += f"&dates={date_str}/{next_day_str}"
            except ValueError:
                params += (
                    f"&dates={self.date.replace('-', '')}/{self.date.replace('-', '')}"
                )
        else:
            # Timed event
            start_dt = self._parse_datetime(self.date, self.start_time)
            if start_dt:
                start_str = start_dt.strftime("%Y%m%dT%H%M%S")
                if self.end_time:
                    end_dt = self._parse_datetime(self.date, self.end_time)
                    if end_dt:
                        end_str = end_dt.strftime("%Y%m%dT%H%M%S")
                    else:
                        end_dt = start_dt + timedelta(hours=1)
                        end_str = end_dt.strftime("%Y%m%dT%H%M%S")
                else:
                    end_dt = start_dt + timedelta(hours=1)
                    end_str = end_dt.strftime("%Y%m%dT%H%M%S")
                params += f"&dates={start_str}/{end_str}"
            else:
                # Fallback to all-day
                date_str = self.date.replace("-", "")
                params += f"&dates={date_str}/{date_str}"

        # Details
        details_parts = []
        if self.description:
            details_parts.append(self.description)
        if self.url:
            details_parts.append(f"More info: {self.url}")
        if self.source:
            details_parts.append(f"Source: {self.source}")
        if details_parts:
            params += f"&details={quote(chr(10).join(details_parts))}"

        # Location
        if self.location:
            params += f"&location={quote(self.location)}"

        return base + params

    def _parse_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """Parse date and time strings into a datetime object."""
        try:
            # Normalize time string
            time_clean = time_str.strip().upper()
            # Try common formats
            for fmt in [
                "%Y-%m-%d %I:%M %p",
                "%Y-%m-%d %I:%M%p",
                "%Y-%m-%d %H:%M",
            ]:
                try:
                    return datetime.strptime(f"{date_str} {time_clean}", fmt)
                except ValueError:
                    continue
            # Fallback to dateutil
            return dateutil_parser.parse(f"{date_str} {time_clean}")
        except (ValueError, TypeError):
            logger.warning(f"Could not parse datetime: {date_str} {time_str}")
            return None


class EventParser:
    """Parses Perplexity API responses into Event objects."""

    def parse_response(self, response_text: str) -> List[Event]:
        """
        Parse API response text into Event objects.
        Tries JSON parsing first, falls back to regex text parsing.
        """
        events = []

        # Try JSON parsing first
        events = self._parse_json(response_text)
        if events:
            logger.info(f"Parsed {len(events)} events from JSON")
            return self.deduplicate_events(events)

        # Fallback to regex parsing
        events = self._parse_text(response_text)
        logger.info(f"Parsed {len(events)} events from text")
        return self.deduplicate_events(events)

    def _parse_json(self, text: str) -> List[Event]:
        """Try to parse events from JSON in the response."""
        events = []

        # Extract JSON from ```json ... ``` code blocks first
        code_block_matches = re.findall(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
        for block in code_block_matches:
            block = block.strip()
            try:
                data = json.loads(block)
                if isinstance(data, list):
                    for item in data:
                        event = self._dict_to_event(item)
                        if event:
                            events.append(event)
                    if events:
                        return events
            except (json.JSONDecodeError, TypeError):
                continue

        # Try to find a JSON array anywhere in the text
        # Use a greedy match for the outermost [ ... ]
        bracket_match = re.search(r"(\[[\s\S]*\])", text)
        if bracket_match:
            try:
                data = json.loads(bracket_match.group(1))
                if isinstance(data, list):
                    for item in data:
                        event = self._dict_to_event(item)
                        if event:
                            events.append(event)
                    if events:
                        return events
            except (json.JSONDecodeError, TypeError):
                pass

        # Try parsing the entire text as JSON
        try:
            data = json.loads(text.strip())
            if isinstance(data, list):
                for item in data:
                    event = self._dict_to_event(item)
                    if event:
                        events.append(event)
        except (json.JSONDecodeError, TypeError):
            pass

        return events

    def _dict_to_event(self, data: dict) -> Optional[Event]:
        """Convert a dictionary to an Event object."""
        if not isinstance(data, dict):
            return None

        title = data.get("title") or data.get("name") or data.get("event_name")
        if not title:
            return None

        # Parse date
        date_str = data.get("date") or data.get("event_date") or data.get("start_date")
        if not date_str:
            return None

        date_normalized = self._normalize_date(str(date_str))
        if not date_normalized:
            return None

        # Parse times
        start_time = data.get("start_time") or data.get("time")
        end_time = data.get("end_time")

        if start_time:
            start_time = self._normalize_time(str(start_time))
        if end_time:
            end_time = self._normalize_time(str(end_time))

        is_all_day = data.get("is_all_day", False)
        if not start_time:
            is_all_day = True

        return Event(
            title=str(title).strip(),
            date=date_normalized,
            start_time=start_time,
            end_time=end_time,
            location=str(data.get("location", "")).strip() or None,
            description=str(data.get("description", "")).strip() or None,
            url=str(data.get("url", "")).strip() or None,
            category=str(data.get("category", "General")).strip(),
            source=str(data.get("source", "")).strip() or None,
            is_all_day=is_all_day,
        )

    def _parse_text(self, text: str) -> List[Event]:
        """Fallback regex-based parsing for unstructured text responses."""
        events = []

        # Split by bold titles: **Title** at start of line
        # This handles the common Perplexity markdown format
        sections = re.split(r"\n(?=\*\*[^*]+\*\*\s*\n)", text)

        # Also try splitting by numbered items
        if len(sections) <= 1:
            sections = re.split(r"\n\s*(?:\d+[\.\)]\s+)", text)

        for section in sections:
            section = section.strip()
            if len(section) < 20:
                continue

            event = self._extract_event_from_markdown(section)
            if event:
                events.append(event)

        return events

    def _extract_event_from_markdown(self, text: str) -> Optional[Event]:
        """Extract event details from a markdown-formatted text block."""
        # Find title: **Title** at the start
        title_match = re.match(r"\s*\*\*(.+?)\*\*", text)
        if not title_match:
            # Try first non-empty line as title
            first_line = text.strip().split("\n")[0].strip()
            if len(first_line) < 5 or len(first_line) > 200:
                return None
            title = first_line
        else:
            title = title_match.group(1).strip()

        if len(title) < 5 or len(title) > 200:
            return None

        # Extract fields from **Field**: Value or - **Field**: Value patterns
        def get_field(field_name: str) -> Optional[str]:
            pattern = rf"\*\*{field_name}\*\*[:\s]*\s*(.+?)(?:\s*\n|$)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                # Skip "Not specified", "N/A", "None", etc.
                if val.lower() in (
                    "not specified",
                    "n/a",
                    "none",
                    "tbd",
                    "not available",
                ):
                    return None
                return val
            return None

        # Date
        date_raw = get_field("Date")
        if not date_raw:
            # Try finding date pattern anywhere in the text
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
            if date_match:
                date_raw = date_match.group(1)
            else:
                return None

        date_str = self._normalize_date(date_raw)
        if not date_str:
            return None

        # Times
        start_time_raw = get_field("Start time") or get_field("Time")
        end_time_raw = get_field("End time")

        start_time = self._normalize_time(start_time_raw) if start_time_raw else None
        end_time = self._normalize_time(end_time_raw) if end_time_raw else None

        # Location
        location = get_field("Location") or get_field("Venue") or get_field("Where")

        # Description
        description = get_field("Description")

        # URL
        url = get_field("URL") or get_field("Link")
        if not url:
            url_match = re.search(r"(https?://\S+)", text)
            if url_match:
                url = url_match.group(1).rstrip(".,;)]\n")

        # Category
        category = get_field("Category") or "General"
        # Normalize category to match our expected values
        category_lower = category.lower()
        valid_categories = [
            "field trips",
            "co-ops",
            "workshops",
            "classes",
            "meetups",
            "sports",
            "arts",
            "science fairs",
            "support groups",
            "library programs",
            "parks & rec",
        ]
        matched_cat = None
        for vc in valid_categories:
            if vc in category_lower:
                matched_cat = vc
                break
        if not matched_cat:
            # Map common alternatives
            cat_map = {
                "open house": "meetups",
                "informational": "meetups",
                "social": "meetups",
                "hangout": "meetups",
                "fair": "workshops",
                "expo": "workshops",
                "family": "meetups",
                "resource": "workshops",
            }
            for key, val in cat_map.items():
                if key in category_lower:
                    matched_cat = val
                    break
        category = matched_cat or "General"

        # Source
        source = get_field("Source")
        # Clean citation references like [7]
        if source:
            source = re.sub(r"\[\d+\]", "", source).strip()
            if not source:
                source = None

        return Event(
            title=title,
            date=date_str,
            start_time=start_time,
            end_time=end_time,
            location=location,
            description=description,
            url=url,
            category=category,
            source=source,
            is_all_day=start_time is None,
        )

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize various date formats to YYYY-MM-DD."""
        try:
            dt = dateutil_parser.parse(date_str, fuzzy=True)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    def _normalize_time(self, time_str: str) -> Optional[str]:
        """Normalize time to HH:MM AM/PM format."""
        if not time_str:
            return None

        time_str = time_str.strip()

        try:
            # Try parsing with dateutil
            dt = dateutil_parser.parse(time_str, fuzzy=True)
            return dt.strftime("%I:%M %p")
        except (ValueError, TypeError):
            pass

        # Manual parsing
        match = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)?", time_str)
        if match:
            hour = int(match.group(1))
            minute = match.group(2)
            period = match.group(3)
            if period:
                return f"{hour}:{minute} {period.upper()}"
            elif hour < 12:
                return f"{hour}:{minute} AM"
            else:
                return f"{hour - 12 if hour > 12 else hour}:{minute} PM"

        return None

    def deduplicate_events(self, events: List[Event]) -> List[Event]:
        """Remove duplicate events based on title similarity and date."""
        if not events:
            return events

        unique = []
        seen = set()

        for event in events:
            # Create a normalized key
            title_key = re.sub(r"[^a-z0-9]", "", event.title.lower())
            key = f"{title_key}_{event.date}"

            if key not in seen:
                seen.add(key)
                unique.append(event)
            else:
                logger.debug(f"Duplicate removed: {event.title} on {event.date}")

        removed = len(events) - len(unique)
        if removed > 0:
            logger.info(f"Removed {removed} duplicate events")

        return unique
