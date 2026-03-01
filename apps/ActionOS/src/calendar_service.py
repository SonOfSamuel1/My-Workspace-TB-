"""Google Calendar API client for the gmail-email-actions dashboard.

Parses Node.js-format JSON credentials (not Python pickle) stored in SSM.
Fetches upcoming events from the three Brandon family calendars.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

CALENDAR_IDS = {
    "family": "e8b8ac59c51a37cace65afd1eb320b01080d6eda9a67f8437c9360ad6d575a57@group.calendar.google.com",
    "medical": "b7a90e6b97885cfa08b5d3964631dc4a7e880f0c12fff722c503447faab3f4fc@group.calendar.google.com",
    "birthdays": "33c41f9c4db1bb4a5132d46ed878d0e9ee287b4a7967714be4bb4cb0d6693802@group.calendar.google.com",
    "love_brittany": "c_e0b980d5bd2f705404aec5b07d9ff4a4c4bbe06b3f1154affabffd7b6ed1bba2@group.calendar.google.com",
    "love_children": "c_6155d15ab0546a6fd88727f0b2e8453352090a9f91e12ee134c7a0aa54f1dca4@group.calendar.google.com",
}

_CALENDAR_DAY_OVERRIDES = {
    "love_brittany": 180,
    "love_children": 180,
}
_DEFAULT_DAYS = 90


class CalendarService:
    """Google Calendar API client using JSON credentials from SSM."""

    def __init__(self, credentials_json: str, token_json: str):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds_data = json.loads(credentials_json)
        token_data = json.loads(token_json)

        client_cfg = creds_data.get("installed", creds_data.get("web", {}))

        creds = Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_cfg.get("client_id"),
            client_secret=client_cfg.get("client_secret"),
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        )

        self.service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    def get_upcoming_events(self, days: int = 90) -> List[Dict[str, Any]]:
        """Fetch from all 3 calendars, deduplicate by event ID, sort by start time.

        Returns a list of dicts:
          {id, title, start, end, is_all_day, location, description, html_link, calendar_type}
        """
        now = datetime.now(timezone.utc)
        time_min = now.isoformat()

        seen_ids: set = set()
        events: List[Dict[str, Any]] = []

        for cal_type, cal_id in CALENDAR_IDS.items():
            cal_days = _CALENDAR_DAY_OVERRIDES.get(cal_type, days)
            time_max = (now + timedelta(days=cal_days)).isoformat()
            try:
                result = (
                    self.service.events()
                    .list(
                        calendarId=cal_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        singleEvents=True,
                        orderBy="startTime",
                        maxResults=100,
                    )
                    .execute()
                )
            except Exception as e:
                logger.warning(f"Failed to fetch calendar {cal_type} ({cal_id}): {e}")
                continue

            for item in result.get("items", []):
                event_id = item.get("id", "")
                if not event_id or event_id in seen_ids:
                    continue
                seen_ids.add(event_id)

                start = item.get("start", {})
                end = item.get("end", {})

                is_all_day = "date" in start and "dateTime" not in start
                start_val = start.get("dateTime") or start.get("date", "")
                end_val = end.get("dateTime") or end.get("date", "")

                events.append(
                    {
                        "id": event_id,
                        "title": item.get("summary", "(No title)"),
                        "start": start_val,
                        "end": end_val,
                        "is_all_day": is_all_day,
                        "location": item.get("location", ""),
                        "description": item.get("description", ""),
                        "html_link": item.get("htmlLink", ""),
                        "calendar_type": cal_type,
                    }
                )

        # Sort by start time ascending
        def _sort_key(ev: Dict[str, Any]) -> str:
            return ev.get("start", "")

        events.sort(key=_sort_key)
        return events
