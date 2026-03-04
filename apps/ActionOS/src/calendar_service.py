"""Google Calendar API client for the gmail-email-actions dashboard.

Parses Node.js-format JSON credentials (not Python pickle) stored in SSM.
Fetches upcoming events from the three Brandon family calendars.
"""

import json
import logging
import time
import zoneinfo
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

_EASTERN_TZ = zoneinfo.ZoneInfo("America/New_York")

logger = logging.getLogger(__name__)

CALENDAR_IDS = {
    "primary": "primary",
    "family": "e8b8ac59c51a37cace65afd1eb320b01080d6eda9a67f8437c9360ad6d575a57@group.calendar.google.com",
    "medical": "b7a90e6b97885cfa08b5d3964631dc4a7e880f0c12fff722c503447faab3f4fc@group.calendar.google.com",
    "birthdays": "33c41f9c4db1bb4a5132d46ed878d0e9ee287b4a7967714be4bb4cb0d6693802@group.calendar.google.com",
    "love_god": "c_93bed550f40faec815845038ffd8824ab9811425b23190e8aa04ce04c2c317dd@group.calendar.google.com",
    "love_brittany": "c_e0b980d5bd2f705404aec5b07d9ff4a4c4bbe06b3f1154affabffd7b6ed1bba2@group.calendar.google.com",
    "love_children": "c_6155d15ab0546a6fd88727f0b2e8453352090a9f91e12ee134c7a0aa54f1dca4@group.calendar.google.com",
    "love_friends_family": "c_9183bb2ea0a3796318b63a580818ac22dcdf2a5c22bf770b430fc8bc83623d1e@group.calendar.google.com",
    "fishing_for_men": "c_0971bcbca44be72f8cbfb8cca0607ac51f73448726708bca096df5900e002d9d@group.calendar.google.com",
    # serve_least_of_these ID is created on first use and stored in calendar state
    "serve_least_of_these": "",
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

    def get_upcoming_events(
        self, days: int = 90, lookback_days: int = 0
    ) -> List[Dict[str, Any]]:
        """Fetch from all calendars in parallel, deduplicate by event ID, sort by start time.

        Args:
            days: How many days forward to fetch.
            lookback_days: How many days back to also include (for prev-occurrence lookups).

        Returns a list of dicts:
          {id, title, start, end, is_all_day, location, description, html_link, calendar_type}
        """
        now = datetime.now(timezone.utc)
        if lookback_days > 0:
            time_min = (now - timedelta(days=lookback_days)).isoformat()
        else:
            # Use start of today (Eastern) so timed events that already started
            # earlier today are still returned by the Google Calendar API.
            local_now = now.astimezone(_EASTERN_TZ)
            today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
            time_min = today_start.isoformat()

        def _fetch_one(cal_type, cal_id):
            if not cal_id:
                return []
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

                # Skip events created by the Schedule Work button
                _private = item.get("extendedProperties", {}).get("private", {})
                if _private.get("actionos_source") == "scheduled_work":
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

    def create_calendar(self, summary: str) -> str:
        """Create a new Google Calendar and return its calendar ID."""
        result = self.service.calendars().insert(body={"summary": summary}).execute()
        return result.get("id", "")

    def get_or_create_calendar(self, summary: str) -> str:
        """Return the ID of the first calendar with the given name, creating it if missing.

        Prevents duplicate calendars when state persistence is unreliable.
        """
        try:
            items = []
            page_token = None
            while True:
                resp = self.service.calendarList().list(pageToken=page_token).execute()
                items.extend(resp.get("items", []))
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
            for cal in items:
                if cal.get("summary", "") == summary:
                    return cal["id"]
        except Exception as e:
            logger.warning(f"get_or_create_calendar: list failed: {e}")
        return self.create_calendar(summary)

    def fetch_events_for_calendar(
        self, cal_type: str, cal_id: str, days: int = 180
    ) -> List[Dict[str, Any]]:
        """Fetch events for a single calendar by its ID."""
        now = datetime.now(timezone.utc)
        local_now = now.astimezone(_EASTERN_TZ)
        today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        time_min = today_start.isoformat()
        time_max = (now + timedelta(days=days)).isoformat()
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
        events: List[Dict[str, Any]] = []
        for item in result.get("items", []):
            event_id = item.get("id", "")
            if not event_id:
                continue
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

        # Fetch existing [FFM] events in Family calendar to avoid duplicates.
        # NOTE: Do NOT use the `q` search parameter here — Google Calendar's
        # full-text index has eventual-consistency lag, so recently-inserted
        # events may not appear in search results yet.  Instead fetch all
        # family events and filter by the prefix in Python.
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
                )
                .execute()
            )
        except Exception as e:
            logger.warning(f"FFM sync: failed to fetch family events: {e}")
            return {"synced": 0, "skipped": 0}

        # Group existing [FFM] family events by (title, start) — delete extras
        # to clean up any duplicates created by prior eventual-consistency races.
        existing_keys: set = set()
        seen: Dict[tuple, str] = {}  # (title, start) -> first event_id to keep
        deleted = 0
        for ev in family_result.get("items", []):
            title = ev.get("summary", "")
            if not title.startswith(self._FFM_SYNC_PREFIX):
                continue
            start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get(
                "date", ""
            )
            key = (title, start)
            ev_id = ev.get("id", "")
            if key not in seen:
                seen[key] = ev_id
                existing_keys.add(key)
            else:
                # Duplicate — delete it
                try:
                    self.service.events().delete(
                        calendarId=family_id, eventId=ev_id
                    ).execute()
                    deleted += 1
                    logger.info(f"FFM sync: deleted duplicate '{title}' @ {start}")
                except Exception as e:
                    logger.warning(
                        f"FFM sync: failed to delete duplicate '{title}': {e}"
                    )

        if deleted:
            logger.info(
                f"FFM sync: removed {deleted} duplicate(s) from Family calendar"
            )

        synced = 0
        skipped = 0
        for ev in ffm_events:
            new_title = self._FFM_SYNC_PREFIX + ev.get("summary", "")
            start = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get(
                "date", ""
            )
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

        logger.info(
            f"FFM sync complete: {synced} synced, {skipped} skipped, {deleted} duplicates removed"
        )
        return {"synced": synced, "skipped": skipped, "deleted": deleted}

    def create_schedule_events(
        self,
        title: str,
        duration_minutes: int,
        calendar_id: str = "primary",
    ) -> List[Dict[str, Any]]:
        """Create consecutive 30-min calendar blocks starting at the next half-hour slot.

        For example, 60 min → 2 blocks at T and T+30; 120 min → 4 blocks.
        Returns a list of created event dicts.
        """
        num_events = max(1, duration_minutes // 30)
        now = datetime.now(timezone.utc)

        # Find user's local timezone from the calendar settings
        try:
            settings = self.service.settings().get(setting="timezone").execute()
            tz_name = settings.get("value", "America/New_York")
        except Exception:
            tz_name = "America/New_York"

        local_tz = zoneinfo.ZoneInfo(tz_name)
        local_now = now.astimezone(local_tz)

        # Round up to next 30-min boundary
        minute = local_now.minute
        if minute == 0 or minute == 30:
            start = local_now.replace(second=0, microsecond=0)
        elif minute < 30:
            start = local_now.replace(minute=30, second=0, microsecond=0)
        else:
            start = (local_now + timedelta(hours=1)).replace(
                minute=0, second=0, microsecond=0
            )

        # Enforce minimum 30-minute buffer from now
        min_start = local_now + timedelta(minutes=30)
        while start < min_start:
            start += timedelta(minutes=30)

        created = []
        for i in range(num_events):
            ev_start = start + timedelta(minutes=30 * i)
            ev_end = ev_start + timedelta(minutes=30)
            body = {
                "summary": title,
                "start": {
                    "dateTime": ev_start.isoformat(),
                    "timeZone": tz_name,
                },
                "end": {
                    "dateTime": ev_end.isoformat(),
                    "timeZone": tz_name,
                },
                "extendedProperties": {
                    "private": {"actionos_source": "scheduled_work"}
                },
            }
            try:
                result = (
                    self.service.events()
                    .insert(calendarId=calendar_id, body=body)
                    .execute()
                )
                created.append(result)
                logger.info(
                    f"Created event '{title}' {ev_start.strftime('%H:%M')}-{ev_end.strftime('%H:%M')}"
                )
            except Exception as e:
                logger.error(f"Failed to create event slot {i + 1}: {e}")

        return created

    def create_travel_time_event(
        self,
        title: str,
        event_start_iso: str,
        travel_minutes: int = 30,
        calendar_id: str = "primary",
        destination: str = "",
        drive_seconds: int = 0,
    ) -> str:
        """Create a travel-buffer event that ends when the main event starts.

        Returns the htmlLink of the created Google Calendar event.
        """
        try:
            event_start = datetime.fromisoformat(event_start_iso)
        except Exception:
            raise ValueError(f"Invalid event_start_iso: {event_start_iso!r}")

        travel_end = event_start
        travel_start = event_start - timedelta(minutes=travel_minutes)

        # Determine timezone name from calendar settings
        try:
            settings = self.service.settings().get(setting="timezone").execute()
            tz_name = settings.get("value", "America/New_York")
        except Exception:
            tz_name = "America/New_York"

        desc_parts = [f"For: {title}"]
        if destination:
            desc_parts.append(f"Destination: {destination}")
        drive_min_raw = drive_seconds // 60 if drive_seconds else travel_minutes
        desc_parts.append(
            f"Estimated drive: {drive_min_raw} min (+10 min buffer = {travel_minutes} min total)"
        )

        body = {
            "summary": f"Travel Time: {title}",
            "description": "\n".join(desc_parts),
            "start": {
                "dateTime": travel_start.isoformat(),
                "timeZone": tz_name,
            },
            "end": {
                "dateTime": travel_end.isoformat(),
                "timeZone": tz_name,
            },
            "colorId": "2",  # sage green
        }
        result = (
            self.service.events().insert(calendarId=calendar_id, body=body).execute()
        )
        logger.info(
            f"Created travel time event for '{title}': "
            f"{travel_start.strftime('%H:%M')} – {travel_end.strftime('%H:%M')}"
            f" ({travel_minutes} min)"
        )
        return result.get("htmlLink", "")

    def update_event(
        self,
        calendar_type: str,
        event_id: str,
        title: str = "",
        start: str = "",
        end: str = "",
        location: str = "",
        description: str = "",
    ) -> Dict[str, Any]:
        """Patch a Google Calendar event's fields.

        start/end can be:
          - ISO date string "YYYY-MM-DD" for all-day events
          - ISO datetime string "YYYY-MM-DDTHH:MM" (no tz) for timed events,
            which will be interpreted as America/New_York
        """
        from zoneinfo import ZoneInfo

        cal_id = CALENDAR_IDS.get(calendar_type, "primary")
        patch: Dict[str, Any] = {}

        if title is not None:
            patch["summary"] = title

        if start:
            is_all_day = "T" not in start
            if is_all_day:
                patch["start"] = {"date": start}
            else:
                dt = datetime.fromisoformat(start)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=_EASTERN_TZ)
                patch["start"] = {"dateTime": dt.isoformat(), "timeZone": "America/New_York"}

        if end:
            is_all_day = "T" not in end
            if is_all_day:
                patch["end"] = {"date": end}
            else:
                dt = datetime.fromisoformat(end)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=_EASTERN_TZ)
                patch["end"] = {"dateTime": dt.isoformat(), "timeZone": "America/New_York"}

        patch["location"] = location or ""
        patch["description"] = description or ""

        result = (
            self.service.events()
            .patch(calendarId=cal_id, eventId=event_id, body=patch)
            .execute()
        )
        logger.info(f"Updated event {event_id} in calendar '{calendar_type}'")
        return result

    def delete_event(self, event_id: str, calendar_type: str) -> None:
        """Delete a calendar event by ID from the given calendar type."""
        cal_id = CALENDAR_IDS.get(calendar_type)
        if not cal_id:
            raise ValueError(f"Unknown calendar_type: {calendar_type!r}")
        self.service.events().delete(calendarId=cal_id, eventId=event_id).execute()
        logger.info(f"Deleted event {event_id!r} from calendar {calendar_type!r}")

    def get_upcoming_events_cached(self, days: int = 90) -> List[Dict[str, Any]]:
        """TTL-cached wrapper around get_upcoming_events (60s cache)."""
        now_ts = time.time()
        if (
            _events_cache["data"] is not None
            and (now_ts - _events_cache["ts"]) < _EVENTS_TTL
        ):
            logger.info(f"Using cached events ({len(_events_cache['data'])} events)")
            return _events_cache["data"]
        events = self.get_upcoming_events(days)
        _events_cache["data"] = events
        _events_cache["ts"] = now_ts
        logger.info(f"Fetched {len(events)} events (cached for {_EVENTS_TTL}s)")
        return events

    def set_calendar_color(self, cal_id: str, color_id: str) -> None:
        """Set the background color of a calendar in the user's calendar list.

        color_id values (Google Calendar palette):
          "11" = Tomato (red), "9" = Blueberry, "6" = Sage, "3" = Grape, etc.
        """
        self.service.calendarList().patch(
            calendarId=cal_id, body={"colorId": color_id}
        ).execute()
        logger.info(f"Set color {color_id!r} on calendar {cal_id!r}")

    # ------------------------------------------------------------------
    # Lay Life Down — fetch events for a specific subset of calendars
    # ------------------------------------------------------------------

    def get_events_for_types(
        self,
        calendar_types: List[str],
        days: int = 180,
        extra_ids: Dict[str, str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch events for a specific subset of calendar types over the next N days.

        Args:
            calendar_types: List of calendar type keys to include.
            days: How many days forward to fetch (default 180 = ~6 months).
            extra_ids: Optional override mapping {cal_type: cal_id} (e.g. for
                       newly created calendars whose IDs aren't in CALENDAR_IDS yet).
        """
        merged_ids = {**CALENDAR_IDS, **(extra_ids or {})}

        now = datetime.now(timezone.utc)
        local_now = now.astimezone(_EASTERN_TZ)
        today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        time_min = today_start.isoformat()
        time_max = (now + timedelta(days=days)).isoformat()

        def _fetch_one(cal_type: str, cal_id: str) -> List[Dict[str, Any]]:
            if not cal_id:
                return []
            try:
                result = (
                    self.service.events()
                    .list(
                        calendarId=cal_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        singleEvents=True,
                        orderBy="startTime",
                        maxResults=200,
                    )
                    .execute()
                )
            except Exception as e:
                logger.warning(f"get_events_for_types: failed {cal_type}: {e}")
                return []

            cal_events = []
            for item in result.get("items", []):
                event_id = item.get("id", "")
                if not event_id:
                    continue
                start = item.get("start", {})
                end = item.get("end", {})
                is_all_day = "date" in start and "dateTime" not in start
                cal_events.append(
                    {
                        "id": event_id,
                        "title": item.get("summary", "(No title)"),
                        "start": start.get("dateTime") or start.get("date", ""),
                        "end": end.get("dateTime") or end.get("date", ""),
                        "is_all_day": is_all_day,
                        "location": item.get("location", ""),
                        "calendar_type": cal_type,
                    }
                )
            return cal_events

        seen_ids: set = set()
        events: List[Dict[str, Any]] = []
        for cal_type in calendar_types:
            cal_id = merged_ids.get(cal_type, "")
            for ev in _fetch_one(cal_type, cal_id):
                if ev["id"] not in seen_ids:
                    seen_ids.add(ev["id"])
                    events.append(ev)

        events.sort(key=lambda e: e.get("start", ""))
        return events
