"""Google Calendar API client for the gmail-email-actions dashboard.

Parses Node.js-format JSON credentials (not Python pickle) stored in SSM.
Fetches upcoming events from the three Brandon family calendars.
"""

import json
import logging
import time

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

CALENDAR_IDS = {
    "family": "e8b8ac59c51a37cace65afd1eb320b01080d6eda9a67f8437c9360ad6d575a57@group.calendar.google.com",
    "medical": "b7a90e6b97885cfa08b5d3964631dc4a7e880f0c12fff722c503447faab3f4fc@group.calendar.google.com",
    "birthdays": "33c41f9c4db1bb4a5132d46ed878d0e9ee287b4a7967714be4bb4cb0d6693802@group.calendar.google.com",
    "love_god": "c_93bed550f40faec815845038ffd8824ab9811425b23190e8aa04ce04c2c317dd@group.calendar.google.com",
    "love_brittany": "c_e0b980d5bd2f705404aec5b07d9ff4a4c4bbe06b3f1154affabffd7b6ed1bba2@group.calendar.google.com",
    "love_children": "c_6155d15ab0546a6fd88727f0b2e8453352090a9f91e12ee134c7a0aa54f1dca4@group.calendar.google.com",
    "love_friends_family": "c_9183bb2ea0a3796318b63a580818ac22dcdf2a5c22bf770b430fc8bc83623d1e@group.calendar.google.com",
    "fishing_for_men": "c_0971bcbca44be72f8cbfb8cca0607ac51f73448726708bca096df5900e002d9d@group.calendar.google.com",
}

_CALENDAR_DAY_OVERRIDES = {
    "love_god": 180,
    "love_brittany": 180,
    "love_children": 180,
    "love_friends_family": 180,
}
_DEFAULT_DAYS = 90

_events_cache: dict = {"data": None, "ts": 0}
_EVENTS_TTL = 60  # seconds


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
            scopes=["https://www.googleapis.com/auth/calendar"],
        )

        self.service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    def get_upcoming_events(self, days: int = 90) -> List[Dict[str, Any]]:
        """Fetch from all calendars in parallel, deduplicate by event ID, sort by start time.

        Returns a list of dicts:
          {id, title, start, end, is_all_day, location, description, html_link, calendar_type}
        """
        now = datetime.now(timezone.utc)
        time_min = now.isoformat()

        def _fetch_one(cal_type, cal_id):
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
                return []

            cal_events = []
            for item in result.get("items", []):
                event_id = item.get("id", "")
                if not event_id:
                    continue

                start = item.get("start", {})
                end = item.get("end", {})

                is_all_day = "date" in start and "dateTime" not in start
                start_val = start.get("dateTime") or start.get("date", "")
                end_val = end.get("dateTime") or end.get("date", "")

                cal_events.append(
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
            return cal_events

        # Fetch all calendars sequentially (httplib2 is not thread-safe)
        seen_ids: set = set()
        seen_title_start: set = set()
        events: List[Dict[str, Any]] = []

        # Prefixes used by the auto-sync to copy events across calendars
        _SYNC_PREFIXES = ("[FFM] ",)

        for cal_type, cal_id in CALENDAR_IDS.items():
            for ev in _fetch_one(cal_type, cal_id):
                if ev["id"] in seen_ids:
                    continue
                # Skip sync-created copies (e.g. [FFM] events in the family cal)
                if any(ev["title"].startswith(p) for p in _SYNC_PREFIXES):
                    continue
                # Deduplicate cross-calendar copies (same title + start time)
                dedup_key = (ev["title"], ev["start"])
                if dedup_key in seen_title_start:
                    continue
                seen_ids.add(ev["id"])
                seen_title_start.add(dedup_key)
                events.append(ev)

        # Sort by start time ascending
        def _sort_key(ev: Dict[str, Any]) -> str:
            return ev.get("start", "")

        events.sort(key=_sort_key)
        return events

    # ------------------------------------------------------------------
    # FFM → Family calendar auto-sync
    # ------------------------------------------------------------------

    _FFM_SYNC_PREFIX = "[FFM] "

    def sync_ffm_to_family(self) -> Dict[str, int]:
        """Copy new Fishing For Men events to the Family calendar.

        Returns {"synced": N, "skipped": N}.
        """
        ffm_id = CALENDAR_IDS.get("fishing_for_men")
        family_id = CALENDAR_IDS.get("family")
        if not ffm_id or not family_id:
            return {"synced": 0, "skipped": 0}

        now = datetime.now(timezone.utc)
        time_min = now.isoformat()
        time_max = (now + timedelta(days=180)).isoformat()

        # Fetch FFM events
        try:
            ffm_result = (
                self.service.events()
                .list(
                    calendarId=ffm_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=250,
                )
                .execute()
            )
        except Exception as e:
            logger.warning(f"FFM sync: failed to fetch FFM events: {e}")
            return {"synced": 0, "skipped": 0}

        ffm_events = ffm_result.get("items", [])
        if not ffm_events:
            return {"synced": 0, "skipped": 0}

        # Fetch existing [FFM] events in Family calendar to avoid duplicates
        try:
            family_result = (
                self.service.events()
                .list(
                    calendarId=family_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=500,
                    q=self._FFM_SYNC_PREFIX,
                )
                .execute()
            )
        except Exception as e:
            logger.warning(f"FFM sync: failed to fetch family events: {e}")
            return {"synced": 0, "skipped": 0}

        existing_keys = set()
        for ev in family_result.get("items", []):
            title = ev.get("summary", "")
            if title.startswith(self._FFM_SYNC_PREFIX):
                start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date", "")
                existing_keys.add((title, start))

        synced = 0
        skipped = 0
        for ev in ffm_events:
            new_title = self._FFM_SYNC_PREFIX + ev.get("summary", "")
            start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date", "")
            if (new_title, start) in existing_keys:
                skipped += 1
                continue

            body = {
                "summary": new_title,
                "description": ev.get("description", ""),
                "location": ev.get("location", ""),
                "start": ev.get("start", {}),
                "end": ev.get("end", {}),
            }
            try:
                self.service.events().insert(calendarId=family_id, body=body).execute()
                synced += 1
                logger.info(f"FFM sync: created '{new_title}'")
            except Exception as e:
                logger.warning(f"FFM sync: failed to create '{new_title}': {e}")

        logger.info(f"FFM sync complete: {synced} synced, {skipped} skipped")
        return {"synced": synced, "skipped": skipped}

    def get_upcoming_events_cached(self, days: int = 90) -> List[Dict[str, Any]]:
        """TTL-cached wrapper around get_upcoming_events (60s cache)."""
        now_ts = time.time()
        if (
            _events_cache["data"] is not None
            and (now_ts - _events_cache["ts"]) < _EVENTS_TTL
        ):
            logger.info(
                f"Using cached events ({len(_events_cache['data'])} events)"
            )
            return _events_cache["data"]
        events = self.get_upcoming_events(days)
        _events_cache["data"] = events
        _events_cache["ts"] = now_ts
        logger.info(f"Fetched {len(events)} events (cached for {_EVENTS_TTL}s)")
        return events
