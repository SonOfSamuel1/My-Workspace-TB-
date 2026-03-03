"""HTML builder for the Calendar tab in the ActionOS dashboard.

Renders sections: Not Reviewed, Today's Events, Love Brittany / Love Children,
Medical Appointments, Travel, Birthdays & Anniversaries, Everything Else.
Cards styled consistently with the other ActionOS views.
"""

import html
import logging
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

_EASTERN = ZoneInfo("America/New_York")

logger = logging.getLogger(__name__)

_CC_LABEL = "Claude"

_FONT = (
    "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,"
    "'Segoe UI',Roboto,sans-serif"
)

_CAL_TYPE_LABELS = {
    "family": "Family",
    "medical": "Medical",
    "birthdays": "Birthday",
    "love_god": "Love God",
    "love_brittany": "Love Brittany",
    "love_children": "Love Children",
    "love_friends_family": "Love Friends & Family",
    "fishing_for_men": "Fishing For Men",
}

_CAL_TYPE_COLORS = {
    "family": "#818cf8",
    "medical": "#22c55e",
    "birthdays": "#eab308",
    "love_god": "#f59e0b",
    "love_brittany": "#a78bfa",
    "love_children": "#a78bfa",
    "love_friends_family": "#ec4899",
    "fishing_for_men": "#06b6d4",
}


def _is_event_reviewed(event_id: str, state: dict) -> bool:
    ts = state.get("reviews", {}).get(event_id)
    if not ts:
        return False
    try:
        reviewed_at = datetime.fromisoformat(ts)
        if reviewed_at.tzinfo is None:
            reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
        reviewed_date = reviewed_at.astimezone(_EASTERN).date()
        today = datetime.now(_EASTERN).date()
        return (today - reviewed_date).days < 7
    except Exception:
        return False


def _days_until_reviewed_reset(event_id: str, state: dict) -> int:
    ts = state.get("reviews", {}).get(event_id)
    if not ts:
        return 0
    try:
        reviewed_at = datetime.fromisoformat(ts)
        if reviewed_at.tzinfo is None:
            reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
        reviewed_date = reviewed_at.astimezone(_EASTERN).date()
        today = datetime.now(_EASTERN).date()
        return max(0, 7 - (today - reviewed_date).days)
    except Exception:
        return 0


def _format_event_date_range(event: Dict[str, Any]) -> str:
    start = event.get("start", "")
    end = event.get("end", "")
    is_all_day = event.get("is_all_day", False)
    if not start:
        return ""
    try:
        if is_all_day:
            dt = datetime.strptime(start[:10], "%Y-%m-%d")
            label = dt.strftime("%a %b %-d")
            if end and end != start:
                dt_end = datetime.strptime(end[:10], "%Y-%m-%d")
                actual_end = dt_end - timedelta(days=1)
                if actual_end > dt:
                    label += " \u2013 " + actual_end.strftime("%a %b %-d")
            return label + " (all day)"
        else:
            dt_start = datetime.fromisoformat(start).astimezone(_EASTERN)
            dt_end = datetime.fromisoformat(end).astimezone(_EASTERN) if end else None
            date_label = dt_start.strftime("%a %b %-d")
            time_label = dt_start.strftime("%-I:%M %p")
            if dt_end:
                time_label += " \u2013 " + dt_end.strftime("%-I:%M %p")
            return f"{date_label} \u00b7 {time_label}"
    except Exception:
        return start


def _categorize_event(event: Dict[str, Any]) -> str:
    """Return a category key for a reviewed event."""
    title_lower = (event.get("title", "") or "").lower()
    cal_type = event.get("calendar_type", "")
    start = event.get("start", "")[:10]

    # Today's events first
    now_eastern = datetime.now(_EASTERN)
    today = now_eastern.strftime("%Y-%m-%d")
    tomorrow = (now_eastern + timedelta(days=1)).strftime("%Y-%m-%d")
    if start == today:
        return "today"
    if start == tomorrow:
        return "tomorrow"

    # Calendar-type routing (dedicated calendars)
    if cal_type == "love_god":
        return "love_god"
    if cal_type == "love_brittany":
        return "love_brittany"
    if cal_type == "love_children":
        return "love_children"
    if cal_type == "love_friends_family":
        return "love_friends_family"
    if cal_type == "fishing_for_men":
        return "fishing_for_men"
    if cal_type == "medical":
        return "medical"
    if cal_type == "birthdays":
        return "birthdays"

    # Title-based fallback for medical keywords
    if (
        "doctor" in title_lower
        or "appointment" in title_lower
        or "medical" in title_lower
        or "dentist" in title_lower
        or "therapy" in title_lower
        or "health" in title_lower
    ):
        return "medical"

    # Travel
    if (
        "travel" in title_lower
        or "flight" in title_lower
        or "hotel" in title_lower
        or "trip" in title_lower
        or "airport" in title_lower
        or "vacation" in title_lower
    ):
        return "travel"

    # Title-based fallback for birthdays
    if "birthday" in title_lower or "anniversary" in title_lower:
        return "birthdays"

    return "other"


# Section display config: (key, label, color_var, badge_bg, badge_color, badge_border)
_REVIEWED_SECTIONS = [
    (
        "today",
        "Today\u2019s Events",
        "--accent-l",
        "--accent-bg",
        "--accent-l",
        "--accent-b",
    ),
    (
        "tomorrow",
        "Tomorrow\u2019s Events",
        "--text-1",
        "--border",
        "--text-1",
        "--border-h",
    ),
    (
        "love_god",
        "Love God",
        "--gold",
        "--gold-bg",
        "--gold",
        "--gold-b",
    ),
    (
        "love_brittany",
        "Love Brittany",
        "--purple",
        "--purple-bg",
        "--purple",
        "--purple-b",
    ),
    (
        "love_children",
        "Love Children",
        "--purple",
        "--purple-bg",
        "--purple",
        "--purple-b",
    ),
    (
        "love_friends_family",
        "Love Friends & Family",
        "--pink",
        "--pink-bg",
        "--pink",
        "--pink-b",
    ),
    (
        "fishing_for_men",
        "Fishing For Men",
        "--teal",
        "--teal-bg",
        "--teal",
        "--teal-b",
    ),
    ("medical", "Medical Appointments", "--ok", "--ok-bg", "--ok", "--ok-b"),
    ("travel", "Travel", "--warn", "--warn-bg", "--warn", "--warn-b"),
    (
        "birthdays",
        "Birthdays & Anniversaries",
        "--warn",
        "--warn-bg",
        "--warn",
        "--warn-b",
    ),
    ("other", "Everything Else", "--text-2", "--border", "--text-2", "--border-h"),
]


def _build_project_options_html(projects: List[Dict[str, Any]]) -> str:
    options = '<option value="">Project\u2026</option>'
    for p in projects:
        pid = html.escape(str(p.get("id", "")))
        name = html.escape(str(p.get("name", "")))
        options += f'<option value="{pid}">{name}</option>'
    return options


def _format_short_date(iso: str) -> str:
    """Format an ISO datetime/date string as 'Feb 3' (short month + day)."""
    try:
        if len(iso) > 10:
            dt = datetime.fromisoformat(iso).astimezone(_EASTERN)
        else:
            dt = datetime.strptime(iso, "%Y-%m-%d")
        return dt.strftime("%b %-d")
    except Exception:
        return iso[:10]


def _is_upcoming_timed_event(event: Dict[str, Any]) -> bool:
    """Return True if the event is a timed (non-all-day) event within the next 7 days."""
    if event.get("is_all_day", False):
        return False
    start = event.get("start", "")
    if not start:
        return False
    try:
        dt_start = datetime.fromisoformat(start).astimezone(_EASTERN)
        now = datetime.now(_EASTERN)
        cutoff = now + timedelta(days=7)
        return now <= dt_start <= cutoff
    except Exception:
        return False


def _build_event_card(
    event: Dict[str, Any],
    reviewed: bool,
    days_remaining: int,
    function_url: str,
    action_token: str,
    project_options_html: str,
    idx: int,
    has_todoist_action: bool = False,
    todoist_task_id: str = "",
    has_prep_action: bool = False,
    prep_task_id: str = "",
    prep_completed: bool = False,
    last_date: str = "",
    next_date: str = "",
    has_travel_time: bool = False,
    travel_event_link: str = "",
    is_birthday: bool = False,
) -> str:
    eid = event.get("id", "")
    eid_safe = html.escape(eid)
    eid_enc = urllib.parse.quote(eid)
    title = html.escape(event.get("title", "(No title)"))
    location = html.escape(event.get("location", ""))
    html_link = event.get("html_link", "")
    cal_type = event.get("calendar_type", "family")
    cal_type_enc = urllib.parse.quote(cal_type)
    date_range = html.escape(_format_event_date_range(event))

    cal_label = html.escape(_CAL_TYPE_LABELS.get(cal_type, cal_type.capitalize()))
    cal_color = _CAL_TYPE_COLORS.get(cal_type, "#5f6368")

    title_enc = urllib.parse.quote(event.get("title", ""))
    date_enc = urllib.parse.quote(event.get("start", "")[:10])
    loc_enc = urllib.parse.quote(event.get("location", ""))
    start_enc = urllib.parse.quote(event.get("start", ""))
    end_enc = urllib.parse.quote(event.get("end", ""))
    html_link_enc = urllib.parse.quote(html_link)

    # Review button
    if reviewed:
        review_btn = (
            f'<button class="review-btn reviewed" id="rev-{idx}" style="cursor:default;">'
            f"\u2713 Reviewed ({days_remaining}d)</button>"
        )
    else:
        rev_url = (
            function_url.rstrip("/")
            + "?action=calendar_reviewed"
            + "&event_id="
            + eid_enc
        )
        review_btn = (
            f'<button class="review-btn" id="rev-{idx}" '
            f"onclick=\"doReview(this,'{eid_safe}','{rev_url}')\">"
            "Review</button>"
        )

    if is_birthday:
        todoist_url_base = (
            function_url.rstrip("/")
            + "?action=calendar_create_sms_reminder"
            + "&event_id="
            + eid_enc
            + "&event_title="
            + title_enc
            + "&event_date="
            + date_enc
            + "&event_location="
            + loc_enc
        )
    else:
        todoist_url_base = (
            function_url.rstrip("/")
            + "?action=calendar_create_todoist"
            + "&event_id="
            + eid_enc
            + "&event_title="
            + title_enc
            + "&event_date="
            + date_enc
            + "&event_location="
            + loc_enc
        )

    commit_url_base = (
        function_url.rstrip("/")
        + "?action=calendar_commit"
        + "&event_id="
        + eid_enc
        + "&event_title="
        + title_enc
        + "&event_date="
        + date_enc
        + "&event_location="
        + loc_enc
    )

    # Schedule Prep URL + button (only shown when no prep task exists)
    prep_url_base = (
        function_url.rstrip("/")
        + "?action=calendar_schedule_prep"
        + "&event_id="
        + eid_enc
        + "&event_title="
        + title_enc
        + "&event_date="
        + date_enc
        + "&event_location="
        + loc_enc
        + "&event_link="
        + html_link_enc
    )
    if has_prep_action:
        schedule_prep_btn = ""
    else:
        schedule_prep_btn = (
            f'<button class="schedule-prep-btn" id="prep-{idx}" '
            f"onclick=\"doSchedulePrep(this,{idx},'{prep_url_base}')\">"
            "Schedule Prep</button>"
        )

    # Travel time URL + button (only for timed events with a location)
    is_timed_with_location = (not event.get("is_all_day", False)) and bool(
        event.get("location", "")
    )
    travel_url_base = (
        function_url.rstrip("/")
        + "?action=calendar_travel_time"
        + "&event_id="
        + eid_enc
        + "&event_title="
        + title_enc
        + "&event_start="
        + start_enc
        + "&event_date="
        + date_enc
        + "&event_location="
        + loc_enc
    )
    if has_travel_time:
        _trv_href = html.escape(travel_event_link) if travel_event_link else "#"
        travel_indicator = (
            f'<a class="travel-indicator" href="{_trv_href}" target="_blank"'
            ' onclick="event.stopPropagation()">'
            "Travel Time Scheduled</a>"
        )
        travel_time_btn = ""
    elif is_timed_with_location:
        travel_indicator = ""
        travel_time_btn = (
            f'<button class="travel-time-btn" id="trv-{idx}" '
            f"onclick=\"doTravelTime(this,{idx},'{travel_url_base}')\">"
            "Add travel time</button>"
        )
    else:
        travel_indicator = ""
        travel_time_btn = ""

    # Badge-row indicators (appear under title)
    _indicator_label = "Reminder to Text Scheduled" if is_birthday else "Event Action"
    todoist_indicator = ""
    if has_todoist_action:
        _td_href = (
            f"https://app.todoist.com/app/task/{todoist_task_id}"
            if todoist_task_id
            else "#"
        )
        todoist_indicator = (
            f'<a class="todoist-indicator" href="{_td_href}" target="_blank"'
            ' onclick="event.stopPropagation()">'
            f"{_indicator_label}</a>"
        )

    prep_indicator = ""
    if has_prep_action:
        _prep_href = (
            f"https://app.todoist.com/app/task/{prep_task_id}" if prep_task_id else "#"
        )
        _prep_class = "prep-indicator prep-done" if prep_completed else "prep-indicator"
        _prep_label = "Prep Completed" if prep_completed else "Prep Scheduled"
        prep_indicator = (
            f'<a class="{_prep_class}" href="{_prep_href}" target="_blank"'
            ' onclick="event.stopPropagation()">'
            f"{_prep_label}</a>"
        )

    # Travel time button and badge
    travel_url_base = (
        function_url.rstrip("/")
        + "?action=calendar_travel_time"
        + "&event_id="
        + eid_enc
        + "&event_title="
        + title_enc
        + "&event_date="
        + date_enc
        + "&event_location="
        + loc_enc
        + "&event_start="
        + start_enc
    )
    is_timed_with_location = (not event.get("is_all_day", False)) and bool(location)
    travel_indicator = ""
    if has_travel_time:
        _travel_href = html.escape(travel_event_link) if travel_event_link else "#"
        travel_indicator = (
            f'<a class="travel-indicator" href="{_travel_href}" target="_blank"'
            ' onclick="event.stopPropagation()">'
            "Travel Time Scheduled</a>"
        )
    if has_travel_time or not is_timed_with_location:
        travel_time_btn = ""
    else:
        travel_time_btn = (
            f'<button class="travel-time-btn" id="trv-{idx}" '
            f"onclick=\"doTravelTime(this,{idx},'{travel_url_base}')\">"
            "Add travel time</button>"
        )

    # Schedule badges (last / next occurrence, shown with green event badge style)
    schedule_badges = ""
    if last_date:
        schedule_badges += f'<span class="event-schedule-badge">Last: {html.escape(_format_short_date(last_date))}</span>'
    if next_date:
        schedule_badges += f'<span class="event-schedule-badge">Next: {html.escape(_format_short_date(next_date))}</span>'

    # Meta line: date · location
    meta_parts = [date_range]
    if location:
        meta_parts.append(location)
    meta_line = " \u00b7 ".join(meta_parts)

    gcal_html = ""
    if html_link:
        safe_link = html.escape(html_link)
        gcal_html = (
            f'<a href="{safe_link}" target="_blank" rel="noopener" class="gcal-link">'
            f"Open in Calendar \u2197</a>"
        )

    # Countdown timer button for today's timed events (triggers iOS Live Activity)
    timer_btn = ""
    if _is_upcoming_timed_event(event):
        start_iso = html.escape(event.get("start", ""))
        title_for_timer = html.escape(event.get("title", "Event"))
        _timer_svg = (
            '<svg class="timer-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="12" cy="13" r="8"/>'
            '<path d="M12 9v4l2.5 1.5"/>'
            '<path d="M5 3l2 2"/><path d="M19 3l-2 2"/>'
            '<line x1="12" y1="1" x2="12" y2="4"/>'
            "</svg>"
        )
        gcal_link_safe = html.escape(html_link) if html_link else ""
        timer_btn = (
            f'<button class="timer-btn" id="tmr-{idx}" '
            f'data-start="{start_iso}" '
            f'data-title="{title_for_timer}" '
            f'data-gcal="{gcal_link_safe}" '
            f'onclick="doPrepTimer(this)">'
            f'{_timer_svg} <span class="timer-label">Countdown</span></button>'
        )

    # Toggl log button (only for timed events with a known duration)
    toggl_log_btn = ""
    if not event.get("is_all_day", False) and event.get("end"):
        toggl_log_url = (
            function_url.rstrip("/")
            + "?action=toggl_log_event"
            + "&event_title="
            + title_enc
            + "&event_start="
            + start_enc
            + "&event_end="
            + end_enc
        )
        toggl_log_btn = (
            f'<button class="toggl-log-btn" id="tgl-{idx}" '
            f"onclick=\"doTogglLog(this,'{toggl_log_url}')\">"
            "Log in Toggl</button>"
        )

    # Claude button
    safe_title = title.replace("'", "\\'")
    safe_date = date_range.replace("'", "\\'")
    safe_location = location.replace("'", "\\'")
    cc_btn = (
        f'<button class="assign-cc-btn" title="Assign CC" '
        f"onclick=\"event.stopPropagation();doCopyCalCC(this,'{safe_title}','{safe_date}','{safe_location}')\">"
        + _CC_LABEL
        + "</button>"
    )

    # Delete button
    delete_url = (
        function_url.rstrip("/")
        + "?action=calendar_delete_event"
        + "&event_id="
        + eid_enc
        + "&calendar_type="
        + cal_type_enc
    )
    delete_btn = (
        f'<button class="delete-event-btn" id="del-{idx}" '
        f"onclick=\"doDeleteEvent(this,{idx},'{delete_url}')\">"
        "Delete</button>"
    )

    card_extra = " reviewed-card" if reviewed else " unreviewed-card"

    # Data attributes for the click-to-edit modal
    _title_attr = html.escape(event.get("title", "(No title)"), quote=True)
    _loc_attr = html.escape(event.get("location", ""), quote=True)
    _desc_attr = html.escape(event.get("description", ""), quote=True)
    _gcal_attr = html.escape(event.get("html_link", ""), quote=True)
    _start_attr = html.escape(event.get("start", ""), quote=True)
    _end_attr = html.escape(event.get("end", ""), quote=True)
    _is_all_day_attr = "1" if event.get("is_all_day", False) else "0"
    _cal_type_attr = html.escape(cal_type, quote=True)

    # Build action buttons — birthday/anniversary cards omit Commit and use SMS reminder
    if is_birthday:
        _todoist_btn_label = "Reminder to Text"
        _action_buttons = (
            f'<button class="todoist-btn" id="tod-{idx}" '
            f'data-indicator-label="Reminder to Text Scheduled" '
            f"onclick=\"doTodoist(this,{idx},'{todoist_url_base}')\">"
            f"{_todoist_btn_label}</button>"
        )
    else:
        _action_buttons = (
            f'<button class="todoist-btn" id="tod-{idx}" '
            f'data-indicator-label="Event Action" '
            f"onclick=\"doTodoist(this,{idx},'{todoist_url_base}')\">"
            f"Add to Todoist</button>"
            f'<button class="commit-btn" id="cmt-{idx}" '
            f"onclick=\"doCommit(this,{idx},'{commit_url_base}')\">"
            f"Commit</button>"
        )

    # Always show all buttons regardless of review status
    return (
        f'<div class="task-card{card_extra}" id="card-{idx}" onclick="openEventDetail(event,this)"'
        f' data-eid="{eid_safe}"'
        f' data-cal-type="{_cal_type_attr}"'
        f' data-title="{_title_attr}"'
        f' data-start="{_start_attr}"'
        f' data-end="{_end_attr}"'
        f' data-is-all-day="{_is_all_day_attr}"'
        f' data-location="{_loc_attr}"'
        f' data-description="{_desc_attr}"'
        f' data-gcal="{_gcal_attr}">'
        f'<div class="card-row">'
        f'<div class="card-content">'
        f'<div class="task-title">{title}</div>'
        f'<div class="badge-row">'
        f'<span class="cal-type-badge" style="background:{cal_color}">{cal_label}</span>'
        f"{todoist_indicator}"
        f"{prep_indicator}"
        f"{travel_indicator}"
        f"{schedule_badges}"
        f"</div>"
        f'<div class="task-meta">{meta_line}</div>'
        f'<div class="task-actions">'
        f"{review_btn}"
        f"{_action_buttons}"
        f"{schedule_prep_btn}"
        f"{travel_time_btn}"
        f"{timer_btn}"
        f"{toggl_log_btn}"
        f"{cc_btn}"
        f"{delete_btn}"
        f"{gcal_html}"
        f"</div>"
        f"</div></div>"
        f"</div>"
    )


def _build_next7days_html(events: List[Dict[str, Any]]) -> str:
    """Build a next-7-days event list grouped by date."""
    now = datetime.now(_EASTERN)
    today = now.date()

    # Build 7-day date buckets
    day_index = {today + timedelta(days=i): i for i in range(7)}
    buckets: List[List[Dict[str, Any]]] = [[] for _ in range(7)]

    for ev in events:
        start = ev.get("start", "")[:10]
        if not start:
            continue
        try:
            ev_date = datetime.strptime(start, "%Y-%m-%d").date()
        except Exception:
            continue
        if ev_date in day_index:
            buckets[day_index[ev_date]].append(ev)

    # Sort events within each day by start time
    for bucket in buckets:
        bucket.sort(key=lambda e: e.get("start", ""))

    rows_html = ""
    for i in range(7):
        d = today + timedelta(days=i)
        evs = buckets[i]

        if i == 0:
            day_label = "Today"
            full_date = d.strftime("%A, %B %-d")
        elif i == 1:
            day_label = "Tomorrow"
            full_date = d.strftime("%A, %B %-d")
        else:
            day_label = d.strftime("%a")
            full_date = d.strftime("%B %-d")

        count_badge = f'<span class="sd-event-count">{len(evs)}</span>' if evs else ""
        rows_html += (
            f'<div class="sd-day">'
            f'<div class="sd-day-hdr">'
            f'<span class="sd-day-label">{html.escape(day_label)}</span>'
            f'<span class="sd-day-full">{html.escape(full_date)}</span>'
            f"{count_badge}"
            f"</div>"
        )

        if not evs:
            rows_html += '<div class="sd-no-events">No events</div>'
        else:
            for ev in evs:
                title = html.escape(ev.get("title", "(No title)"))
                cal_type = ev.get("calendar_type", "family")
                cal_color = _CAL_TYPE_COLORS.get(cal_type, "#5f6368")
                ev_html_link = ev.get("html_link", "")

                if ev.get("is_all_day", False):
                    time_str = "All Day"
                    time_cls = "sd-allday"
                else:
                    start_iso = ev.get("start", "")
                    try:
                        dt_s = datetime.fromisoformat(start_iso).astimezone(_EASTERN)
                        time_str = dt_s.strftime("%-I:%M %p")
                    except Exception:
                        time_str = start_iso[11:16] if len(start_iso) > 10 else ""
                    time_cls = "sd-time"

                title_html = (
                    f'<a class="sd-title" href="{html.escape(ev_html_link)}" target="_blank">{title}</a>'
                    if ev_html_link
                    else f'<span class="sd-title">{title}</span>'
                )

                rows_html += (
                    f'<div class="sd-event">'
                    f'<span class="{time_cls}">{html.escape(time_str)}</span>'
                    f'<span class="sd-cal-dot" style="background:{cal_color}"></span>'
                    f"{title_html}"
                    f"</div>"
                )

        rows_html += "</div>"

    return f'<div class="sd-container">{rows_html}</div>'


def _is_birthday_event(event: Dict[str, Any]) -> bool:
    """Return True if this event would be categorized as a birthday/anniversary."""
    cal_type = event.get("calendar_type", "")
    if cal_type == "birthdays":
        return True
    title_lower = (event.get("title", "") or "").lower()
    return "birthday" in title_lower or "anniversary" in title_lower


def _is_within_days(event: Dict[str, Any], days: int) -> bool:
    """Return True if the event starts within the given number of days from now."""
    start = event.get("start", "")[:10]
    if not start:
        return True
    try:
        event_date = datetime.strptime(start, "%Y-%m-%d").date()
        today = datetime.now(_EASTERN).date()
        return (event_date - today).days <= days
    except Exception:
        return True


def _build_ffm_action_cards(
    ffm_tasks: List[Dict[str, Any]],
    function_url: str,
) -> str:
    """Build action item cards for Fishing for Men Todoist tasks with outreach buttons."""
    if not ffm_tasks:
        return ""
    cards = ""
    for task in ffm_tasks:
        task_id = html.escape(task.get("id", ""))
        content = html.escape(task.get("content", ""))
        description = html.escape(task.get("description", ""))
        person_enc = urllib.parse.quote(task.get("content", ""))
        base_url = function_url.rstrip("/")

        meta_html = ""
        if description:
            meta_html = f'<div class="task-meta">{description}</div>'

        buttons = ""
        for meal, icon in [
            ("coffee", "\u2615"),
            ("lunch", "\ud83c\udf7d"),
            ("dinner", "\ud83c\udf1f"),
        ]:
            meal_enc = urllib.parse.quote(meal)
            buttons += (
                f'<button class="ffm-meal-btn ffm-{meal}" '
                f"onclick=\"doFfmOutreach(this,'{person_enc}','{meal_enc}')\">"
                f"{icon} {meal.capitalize()}</button>"
            )

        cards += (
            f'<div class="task-card ffm-action-card">'
            f'<div class="card-row"><div class="card-content">'
            f'<div class="task-title">{content}</div>'
            f"{meta_html}"
            f'<div class="task-actions">{buttons}</div>'
            f"</div></div></div>"
        )
    return cards


_CAL_NAV_CONFIG = [
    ("not-reviewed",        "Not Reviewed",  "var(--warn)",    "var(--warn-bg)"),
    ("today",               "Today",         "var(--accent-l)","var(--accent-bg)"),
    ("tomorrow",            "Tomorrow",      "var(--text-2)",  "rgba(142,142,147,0.10)"),
    ("love_god",            "Love God",      "var(--gold)",    "var(--gold-bg)"),
    ("love_brittany",       "Love Brittany", "var(--purple)",  "var(--purple-bg)"),
    ("love_children",       "Love Children", "var(--purple)",  "var(--purple-bg)"),
    ("love_friends_family", "Love Friends",  "var(--pink)",    "var(--pink-bg)"),
    ("fishing_for_men",     "Fishing",       "var(--teal)",    "var(--teal-bg)"),
    ("medical",             "Medical",       "var(--ok)",      "var(--ok-bg)"),
    ("travel",              "Travel",        "var(--warn)",    "var(--warn-bg)"),
    ("birthdays",           "Birthdays",     "var(--warn)",    "var(--warn-bg)"),
    ("other",               "Other",         "var(--text-2)",  "rgba(142,142,147,0.10)"),
]


def _build_cal_nav_bar(section_counts: Dict[str, int]) -> str:
    pills = ""
    for key, label, color, bg in _CAL_NAV_CONFIG:
        count = section_counts.get(key, 0)
        pills += (
            f'<button class="sec-pill" '
            f'style="color:{color};border-color:{color};background:{bg};" '
            f"onclick=\"scrollToCalSec('{key}')\">"
            f"{html.escape(label)}"
            f'<span class="sec-pill-count">{count}</span>'
            f"</button>"
        )
    return f'<div class="sec-nav" id="cal-sec-nav">{pills}</div>'


def build_calendar_html(
    events: List[Dict[str, Any]],
    reviewed_state: dict,
    function_url: str,
    action_token: str,
    projects: List[Dict[str, Any]],
    embed: bool = False,
    checklists: dict = None,
    ffm_tasks: List[Dict[str, Any]] = None,
    ffm_project_id: str = None,
    todoist_tasks: List[Dict[str, Any]] = None,
    all_events: List[Dict[str, Any]] = None,
) -> str:
    """Build the Calendar page with categorized sections."""
    project_options_html = _build_project_options_html(projects)
    checklists = checklists or {}
    todoist_tasks = todoist_tasks or []
    _travel_time_state = reviewed_state.get("travel_time", {})

    # Build title → sorted start-date list for prev/next occurrence lookup.
    # all_events may include past occurrences (fetched with lookback_days).
    _schedule_source = all_events if all_events is not None else events
    _title_dates: Dict[str, List[str]] = {}
    for ev in _schedule_source:
        t = (ev.get("title") or "").strip().lower()
        s = (ev.get("start") or "")[:19]
        if t and s:
            _title_dates.setdefault(t, []).append(s)
    for t in _title_dates:
        _title_dates[t].sort()

    def _get_schedule(title: str, start: str):
        """Return (last_date, next_date) ISO strings relative to *start*."""
        dates = _title_dates.get((title or "").strip().lower(), [])
        s = (start or "")[:19]
        last = next_occ = ""
        for d in dates:
            if d < s:
                last = d
            elif d > s:
                next_occ = d
                break
        return last, next_occ

    # Build lookup sets for calendar-todoist matching
    _todoist_title_map = {}  # content_lower → task_id
    _todoist_prep_map = {}  # event_title_lower → task_id
    _todoist_prep_completed_map = {}  # event_title_lower → bool
    for t in todoist_tasks:
        c = (t.get("content") or "").strip()
        _todoist_title_map.setdefault(c.lower(), t.get("id", ""))
        if c.lower().startswith("event prep: "):
            event_key = c[len("Event Prep: ") :].strip().lower()
            _todoist_prep_map.setdefault(event_key, t.get("id", ""))
            _todoist_prep_completed_map.setdefault(
                event_key, bool(t.get("checked", False))
            )

    # Filter out birthday/anniversary events beyond 90 days
    filtered_events = [
        ev for ev in events if not _is_birthday_event(ev) or _is_within_days(ev, 90)
    ]

    # Split events: unreviewed vs reviewed
    unreviewed = []
    reviewed_events = []
    for ev in filtered_events:
        if _is_event_reviewed(ev.get("id", ""), reviewed_state):
            reviewed_events.append(ev)
        else:
            unreviewed.append(ev)

    unreviewed_count = len(unreviewed)

    # Categorize reviewed events into buckets
    reviewed_buckets: Dict[str, List[Dict[str, Any]]] = {
        key: [] for key, *_ in _REVIEWED_SECTIONS
    }
    for ev in reviewed_events:
        cat = _categorize_event(ev)
        reviewed_buckets[cat].append(ev)

    # Travel time state: event_id → {travel_event_link, ...}
    _travel_time_state = reviewed_state.get("travel_time", {})

    # Card index counter (continuous across all sections)
    _card_idx = [0]

    def _build_section_cards(event_list):
        out = ""
        for event in event_list:
            idx = _card_idx[0]
            _card_idx[0] += 1
            eid = event.get("id", "")
            r = _is_event_reviewed(eid, reviewed_state)
            days_rem = _days_until_reviewed_reset(eid, reviewed_state)
            ev_title_lower = (event.get("title") or "").strip().lower()
            last_date, next_date = _get_schedule(
                event.get("title", ""), event.get("start", "")
            )
            _travel_data = _travel_time_state.get(eid, {})
            out += _build_event_card(
                event,
                r,
                days_rem,
                function_url,
                action_token,
                project_options_html,
                idx,
                has_todoist_action=bool(_todoist_title_map.get(ev_title_lower)),
                todoist_task_id=_todoist_title_map.get(ev_title_lower, ""),
                has_prep_action=bool(_todoist_prep_map.get(ev_title_lower)),
                prep_task_id=_todoist_prep_map.get(ev_title_lower, ""),
                prep_completed=_todoist_prep_completed_map.get(ev_title_lower, False),
                last_date=last_date,
                next_date=next_date,
                has_travel_time=bool(_travel_data),
                travel_event_link=_travel_data.get("travel_event_link", ""),
                is_birthday=_is_birthday_event(event),
            )
        return out

    unreviewed_cards = _build_section_cards(unreviewed)
    if not unreviewed_cards:
        unreviewed_cards = '<div class="empty-state">All caught up \u2713</div>'

    # Build FFM action items HTML
    ffm_tasks = ffm_tasks or []
    ffm_action_html = _build_ffm_action_cards(ffm_tasks, function_url)

    # Build each reviewed sub-section
    reviewed_sections_html = ""
    for (
        key,
        label,
        color_var,
        badge_bg,
        badge_color,
        badge_border,
    ) in _REVIEWED_SECTIONS:
        bucket = reviewed_buckets[key]
        cards = (
            _build_section_cards(bucket)
            if bucket
            else (f'<div class="empty-state">No {label.lower()}</div>')
        )
        checklist_html = ""
        if key in ("love_god", "love_brittany", "love_children", "love_friends_family"):
            cl_content = html.escape(checklists.get(key, ""))
            save_url = html.escape(
                function_url.rstrip("/") + "?action=calendar_save_checklist"
            )
            checklist_html = (
                f'<div class="checklist-card" data-section="{key}">'
                f'<div class="checklist-header">'
                f'<span class="checklist-title">Checklist</span>'
                f'<button class="checklist-edit-btn" id="cl-btn-{key}" '
                f"onclick=\"toggleChecklist('{key}')\">"
                f"Edit</button>"
                f"</div>"
                f'<div class="checklist-body" id="cl-body-{key}" contenteditable="false">'
                f"{cl_content}"
                f"</div></div>"
            )
        # Inject FFM action items after the Fishing For Men section header
        extra_html = ""
        if key == "fishing_for_men" and ffm_action_html:
            ffm_count = len(ffm_tasks)
            extra_html = (
                f'<div class="ffm-actions-hdr">'
                f'<span class="ffm-actions-label">Action Items</span>'
                f'<span class="section-badge" style="background:var(--teal-bg);'
                f'color:var(--teal);border:1px solid var(--teal-b);">'
                f"{ffm_count}</span>"
                f"</div>" + ffm_action_html
            )
        reviewed_sections_html += (
            f'<div class="section-hdr" id="cal-sec-{key}" style="margin-top:24px;">'
            f'<span style="color:var({color_var});">{label}</span>'
            f'<span class="section-badge" style="background:var({badge_bg});'
            f'color:var({badge_color});border:1px solid var({badge_border});">'
            f"{len(bucket)}</span>"
            f"</div>" + checklist_html + extra_html + cards
        )

    # Build calendar nav bar counts
    _cal_nav_counts = {"not-reviewed": unreviewed_count}
    for key, *_ in _REVIEWED_SECTIONS:
        _cal_nav_counts[key] = len(reviewed_buckets[key])

    seven_day_html = _build_next7days_html(events)

    embed_css = ".top-bar{display:none;}" if embed else ""
    page_height = "100vh" if embed else "calc(100vh - 57px)"

    post_message_js = ""
    if embed:
        post_message_js = (
            "var calendarCount=" + str(unreviewed_count) + ";"
            "function postCount(){"
            "window.parent.postMessage({type:'count',source:'calendar',count:calendarCount},'*');"
            "}"
            "postCount();"
        )

    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Cache-Control" content="no-cache,no-store,must-revalidate">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700'
        '&display=swap" rel="stylesheet">'
        "<title>Calendar</title>"
        "<style>"
        ":root{"
        "--bg-base:#1a1a1a;--bg-s0:#1c1c1e;--bg-s1:#252528;--bg-s2:#2c2c2e;"
        "--text-1:#ffffff;--text-2:#8e8e93;--text-3:#48484a;"
        "--border:rgba(255,255,255,0.08);--border-h:rgba(255,255,255,0.12);"
        "--accent:#6366f1;--accent-l:#818cf8;"
        "--accent-bg:rgba(99,102,241,0.10);--accent-b:rgba(99,102,241,0.20);"
        "--accent-hbg:rgba(99,102,241,0.08);"
        "--ok:#22c55e;--ok-bg:rgba(34,197,94,0.10);--ok-b:rgba(34,197,94,0.20);"
        "--warn:#eab308;--warn-bg:rgba(234,179,8,0.10);--warn-b:rgba(234,179,8,0.20);"
        "--err:#ef4444;--err-bg:rgba(239,68,68,0.10);--err-b:rgba(239,68,68,0.20);"
        "--purple:#a78bfa;--purple-bg:rgba(167,139,250,0.10);--purple-b:rgba(167,139,250,0.20);"
        "--teal:#06b6d4;--teal-bg:rgba(6,182,212,0.10);--teal-b:rgba(6,182,212,0.20);"
        "--gold:#f59e0b;--gold-bg:rgba(245,158,11,0.10);--gold-b:rgba(245,158,11,0.20);"
        "--pink:#ec4899;--pink-bg:rgba(236,72,153,0.10);--pink-b:rgba(236,72,153,0.20);"
        "--scrollbar:rgba(255,255,255,0.10);color-scheme:dark;}"
        "@media(prefers-color-scheme:light){:root{"
        "--bg-base:#eeeef0;--bg-s0:#fff;--bg-s1:#fff;--bg-s2:#f5f5f7;"
        "--text-1:#202124;--text-2:#5f6368;--text-3:#80868b;"
        "--border:rgba(0,0,0,0.08);--border-h:rgba(0,0,0,0.15);"
        "--accent:#6366f1;--accent-l:#4f46e5;"
        "--accent-bg:rgba(99,102,241,0.08);--accent-b:rgba(99,102,241,0.15);"
        "--accent-hbg:rgba(99,102,241,0.06);"
        "--ok:#188038;--ok-bg:#e6f4ea;--ok-b:rgba(24,128,56,0.20);"
        "--warn:#e37400;--warn-bg:#fef7e0;--warn-b:rgba(227,116,0,0.20);"
        "--err:#d93025;--err-bg:#fce8e6;--err-b:rgba(217,48,37,0.20);"
        "--purple:#7c4dff;--purple-bg:#ede7f6;--purple-b:rgba(124,77,255,0.20);"
        "--teal:#0891b2;--teal-bg:#ecfeff;--teal-b:rgba(8,145,178,0.20);"
        "--gold:#d97706;--gold-bg:#fffbeb;--gold-b:rgba(217,119,6,0.20);"
        "--pink:#db2777;--pink-bg:#fdf2f8;--pink-b:rgba(219,39,119,0.20);"
        "--scrollbar:rgba(0,0,0,0.12);color-scheme:light;}}"
        "*{box-sizing:border-box;margin:0;padding:0;}"
        "body{font-family:" + _FONT + ";background:var(--bg-base);color:var(--text-1);"
        "-webkit-font-smoothing:antialiased;}"
        + embed_css
        + ".top-bar{background:var(--bg-s0);border-bottom:1px solid var(--border);padding:14px 20px;"
        "display:flex;align-items:center;gap:12px;}"
        ".top-bar-title{color:var(--text-1);font-size:17px;font-weight:600;letter-spacing:-0.2px;}"
        ".refresh-btn{margin-left:auto;background:var(--border);border:1px solid var(--border);"
        "color:var(--text-1);font-size:13px;font-weight:600;padding:6px 14px;border-radius:6px;cursor:pointer;}"
        ".refresh-btn:hover{background:var(--border-h);}"
        ".scroll-area{height:"
        + page_height
        + ";overflow-y:auto;overflow-x:hidden;background:var(--bg-base);}"
        ".task-list{max-width:700px;margin:0 auto;padding:0 16px 12px;overflow:clip;}"
        # Section nav bar
        ".cal-sticky-top{position:sticky;top:0;z-index:20;background:var(--bg-base);}"
        ".sec-nav{display:flex;gap:8px;overflow-x:auto;padding:10px 16px 10px;"
        "border-bottom:1px solid var(--border);margin-bottom:12px;"
        "-webkit-overflow-scrolling:touch;-ms-overflow-style:none;scrollbar-width:none;}"
        ".sec-nav::-webkit-scrollbar{display:none;}"
        ".sec-pill{display:inline-flex;align-items:center;gap:7px;white-space:nowrap;"
        "border-radius:10px;border:1.5px solid;padding:7px 12px;cursor:pointer;min-height:44px;"
        "font-size:13px;font-weight:600;font-family:inherit;flex-shrink:0;"
        "transition:opacity .15s;background:transparent;}"
        ".sec-pill:hover{opacity:0.72;}"
        ".sec-pill-count{background:rgba(0,0,0,0.35);border-radius:999px;"
        "min-width:20px;height:20px;display:inline-flex;align-items:center;"
        "justify-content:center;font-size:11px;font-weight:700;color:#fff;padding:0 5px;}"
        ".section-hdr{display:flex;align-items:center;gap:8px;padding:16px 0 8px;"
        "font-size:11px;font-weight:600;color:var(--text-3);text-transform:uppercase;"
        "letter-spacing:0.6px;border-bottom:1px solid var(--border);margin-bottom:10px;"
        "position:sticky;top:116px;z-index:10;background:var(--bg-base);"
        "scroll-margin-top:116px;}"
        ".section-hdr+.section-hdr{margin-top:24px;}"
        ".section-badge{background:var(--border);color:var(--text-2);font-size:11px;"
        "font-weight:700;padding:2px 7px;border-radius:8px;}"
        ".task-card{background:var(--bg-s1);border-radius:8px;"
        "border:1px solid var(--border);padding:14px 16px;"
        "margin-bottom:10px;transition:border-color .15s ease-out,background .15s ease-out;"
        "overflow:hidden;}"
        ".task-card:hover{border-color:var(--border-h);background:var(--bg-s2);}"
        ".unreviewed-card{border-left:3px solid var(--warn);}"
        ".reviewed-card{opacity:0.65;}"
        ".card-row{display:flex;align-items:flex-start;gap:10px;}"
        ".card-content{flex:1;min-width:0;overflow:hidden;}"
        ".task-title{font-size:15px;font-weight:600;color:var(--text-1);"
        "line-height:1.4;margin-bottom:2px;word-break:break-word;}"
        ".badge-row{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:4px;}"
        ".cal-type-badge{font-size:10px;font-weight:700;color:#fff;"
        "padding:2px 7px;border-radius:6px;white-space:nowrap;flex-shrink:0;}"
        ".todoist-indicator{font-size:10px;font-weight:600;text-decoration:none;"
        "background:var(--ok-bg,#16382a);color:var(--ok,#22c55e);"
        "padding:2px 7px;border-radius:6px;white-space:nowrap;}"
        ".prep-indicator{font-size:10px;font-weight:600;text-decoration:none;"
        "background:var(--warn-bg);color:var(--warn);"
        "padding:2px 7px;border-radius:6px;white-space:nowrap;}"
        ".prep-indicator.prep-done{background:var(--ok-bg);color:var(--ok);}"
        ".event-schedule-badge{font-size:10px;font-weight:700;text-decoration:none;"
        "background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-b);"
        "padding:2px 7px;border-radius:6px;white-space:nowrap;}"
        ".task-meta{font-size:12px;color:var(--text-2);margin-bottom:10px;line-height:1.5;"
        "word-break:break-word;overflow-wrap:break-word;}"
        ".task-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center;}"
        ".action-select{font-family:inherit;font-size:12px;padding:5px 8px;"
        "border:1px solid var(--border);border-radius:6px;background:var(--bg-s2);"
        "color:var(--text-1);cursor:pointer;}"
        ".review-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn-b);cursor:pointer;"
        "transition:background .15s;}"
        ".review-btn:hover{background:var(--warn-b);}"
        ".review-btn.reviewed{background:var(--ok-bg);color:var(--ok);"
        "border-color:var(--ok-b);cursor:default;}"
        ".todoist-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:var(--accent-bg);color:var(--accent-l);border:1px solid var(--accent-b);"
        "cursor:pointer;transition:background .15s;}"
        ".todoist-btn:hover{background:var(--accent-b);}"
        ".commit-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:var(--border);color:var(--text-2);border:1px solid var(--border);"
        "cursor:pointer;transition:background .15s;}"
        ".commit-btn:hover{background:var(--border-h);color:var(--text-1);}"
        ".schedule-prep-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:var(--border);color:var(--text-2);border:1px solid var(--border);"
        "cursor:pointer;transition:background .15s;}"
        ".schedule-prep-btn:hover{background:var(--border-h);}"
        ".travel-time-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-b);"
        "cursor:pointer;transition:background .15s;}"
        ".travel-time-btn:hover{background:var(--ok-b);}"
        ".travel-indicator{font-size:10px;font-weight:600;text-decoration:none;"
        "background:var(--ok-bg,#16382a);color:var(--ok,#22c55e);padding:2px 7px;"
        "border-radius:6px;white-space:nowrap;}"
        ".timer-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:var(--purple-bg);color:var(--purple);border:1px solid var(--purple-b);"
        "cursor:pointer;transition:background .15s;"
        "display:inline-flex;align-items:center;gap:5px;}"
        ".timer-btn:hover{background:var(--purple-b);}"
        ".timer-btn.expired{opacity:0.4;cursor:default;pointer-events:none;}"
        ".toggl-log-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:var(--err-bg);color:var(--err);border:1px solid var(--err-b);"
        "cursor:pointer;transition:background .15s;}"
        ".toggl-log-btn:hover{background:var(--err-b);}"
        ".timer-icon{flex-shrink:0;vertical-align:middle;}"
        ".gcal-link{color:var(--accent-l);font-size:12px;font-weight:500;"
        "text-decoration:none;white-space:nowrap;}"
        ".gcal-link:hover{text-decoration:underline;}"
        ".assign-cc-btn{display:inline-flex;align-items:center;justify-content:center;"
        "padding:4px 10px;border-radius:6px;"
        "background:var(--border);border:1px solid var(--border);"
        "cursor:pointer;transition:background .15s;color:var(--text-2);font-size:13px;font-weight:600;}"
        ".assign-cc-btn:hover{background:var(--border-h);}"
        ".delete-event-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:transparent;color:var(--err);border:1px solid var(--err-b);"
        "cursor:pointer;transition:background .15s,color .15s;}"
        ".delete-event-btn:hover{background:var(--err-bg);}"
        ".empty-state{text-align:center;color:var(--text-2);padding:24px 20px;font-size:14px;}"
        # Task card cursor pointer (clickable to open detail)
        ".task-card{cursor:pointer;}"
        # Event detail modal
        ".ev-modal-overlay{display:none;position:fixed;inset:0;z-index:1000;"
        "background:rgba(0,0,0,0.55);backdrop-filter:blur(4px);"
        "align-items:center;justify-content:center;padding:16px;}"
        ".ev-modal-box{background:var(--bg-s1);border:1px solid var(--border-h);"
        "border-radius:12px;width:100%;max-width:480px;max-height:90vh;"
        "display:flex;flex-direction:column;overflow:hidden;"
        "box-shadow:0 24px 64px rgba(0,0,0,0.45);}"
        ".ev-modal-hdr{display:flex;align-items:center;justify-content:space-between;"
        "padding:16px 20px 12px;border-bottom:1px solid var(--border);flex-shrink:0;}"
        ".ev-modal-title{font-size:15px;font-weight:700;color:var(--text-1);}"
        ".ev-modal-close{background:none;border:none;color:var(--text-2);"
        "font-size:22px;line-height:1;cursor:pointer;padding:0 4px;}"
        ".ev-modal-close:hover{color:var(--text-1);}"
        ".ev-modal-body{padding:16px 20px;overflow-y:auto;flex:1;display:flex;"
        "flex-direction:column;gap:12px;}"
        ".ev-field-label{font-size:11px;font-weight:600;color:var(--text-2);"
        "text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;display:block;}"
        ".ev-field-input{width:100%;font-family:inherit;font-size:14px;padding:9px 12px;"
        "background:var(--bg-s2);border:1px solid var(--border);border-radius:7px;"
        "color:var(--text-1);outline:none;transition:border-color .15s;}"
        ".ev-field-input:focus{border-color:var(--accent);}"
        ".ev-field-textarea{width:100%;font-family:inherit;font-size:14px;padding:9px 12px;"
        "background:var(--bg-s2);border:1px solid var(--border);border-radius:7px;"
        "color:var(--text-1);outline:none;resize:vertical;min-height:80px;"
        "transition:border-color .15s;line-height:1.5;}"
        ".ev-field-textarea:focus{border-color:var(--accent);}"
        ".ev-datetime-row{display:grid;grid-template-columns:1fr 1fr;gap:10px;}"
        ".ev-modal-footer{padding:12px 20px 16px;border-top:1px solid var(--border);"
        "display:flex;align-items:center;justify-content:space-between;flex-shrink:0;flex-wrap:wrap;gap:8px;}"
        ".ev-gcal-btn{font-size:12px;font-weight:500;color:var(--accent-l);"
        "text-decoration:none;white-space:nowrap;}"
        ".ev-gcal-btn:hover{text-decoration:underline;}"
        ".ev-modal-actions{display:flex;gap:8px;}"
        ".ev-cancel-btn{font-family:inherit;font-size:13px;font-weight:600;"
        "padding:7px 16px;border-radius:7px;min-height:44px;"
        "background:var(--bg-s2);color:var(--text-2);border:1px solid var(--border);"
        "cursor:pointer;transition:background .15s;}"
        ".ev-cancel-btn:hover{background:var(--border);}"
        ".ev-save-btn{font-family:inherit;font-size:13px;font-weight:600;"
        "padding:7px 18px;border-radius:7px;min-height:44px;"
        "background:var(--accent);color:#fff;border:1px solid var(--accent);"
        "cursor:pointer;transition:opacity .15s;}"
        ".ev-save-btn:hover{opacity:0.88;}"
        "@media(max-width:768px){"
        ".task-actions{gap:6px;}"
        ".action-select,.review-btn,.todoist-btn,.commit-btn,.schedule-prep-btn,.travel-time-btn,.timer-btn,.toggl-log-btn,.assign-cc-btn,.delete-event-btn,.ffm-meal-btn{font-size:11px;padding:4px 6px;}"
        ".ev-datetime-row{grid-template-columns:1fr;}"
        "}"
        "::-webkit-scrollbar{width:6px;}"
        "::-webkit-scrollbar-track{background:transparent;}"
        "::-webkit-scrollbar-thumb{background:var(--scrollbar);border-radius:3px;}"
        ".checklist-card{background:var(--bg-s1);border:1px solid var(--border);border-radius:8px;"
        "padding:14px 16px;margin-bottom:10px;}"
        ".checklist-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;}"
        ".checklist-title{font-size:12px;font-weight:700;color:var(--text-2);text-transform:uppercase;letter-spacing:.5px;}"
        ".checklist-edit-btn{font-family:inherit;font-size:12px;font-weight:600;padding:4px 12px;"
        "border-radius:6px;border:1px solid var(--accent-b);background:var(--accent-bg);"
        "color:var(--accent-l);cursor:pointer;}"
        ".checklist-body{font-size:14px;color:var(--text-1);line-height:1.6;min-height:40px;"
        "outline:none;border-radius:4px;padding:4px;}"
        ".checklist-body[contenteditable=true]{background:var(--bg-s2);border:1px solid var(--accent-b);}"
        # FFM action items
        ".ffm-actions-hdr{display:flex;align-items:center;gap:8px;padding:8px 0 6px;"
        "font-size:11px;font-weight:600;color:var(--teal);letter-spacing:0.4px;}"
        ".ffm-actions-label{text-transform:uppercase;}"
        ".ffm-action-card{border-left:3px solid var(--teal);}"
        ".ffm-meal-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;cursor:pointer;transition:all .15s;"
        "border:1px solid var(--border);}"
        ".ffm-coffee{background:var(--gold-bg);color:var(--gold);border-color:var(--gold-b);}"
        ".ffm-coffee:hover{background:var(--gold-b);}"
        ".ffm-lunch{background:var(--ok-bg);color:var(--ok);border-color:var(--ok-b);}"
        ".ffm-lunch:hover{background:var(--ok-b);}"
        ".ffm-dinner{background:var(--purple-bg);color:var(--purple);border-color:var(--purple-b);}"
        ".ffm-dinner:hover{background:var(--purple-b);}"
        # View toggle bar
        ".view-toggle{display:flex;gap:4px;padding:8px 16px;max-width:700px;margin:0 auto;}"
        ".view-toggle-btn{flex:1;font-family:inherit;font-size:13px;font-weight:600;"
        "padding:8px 12px;border-radius:8px;border:1px solid var(--border);"
        "background:var(--bg-s1);color:var(--text-2);cursor:pointer;transition:all .15s;}"
        ".view-toggle-btn:hover{background:var(--bg-s2);color:var(--text-1);}"
        ".view-toggle-btn.active{background:var(--accent);color:#fff;border-color:var(--accent);}"
        "#view-events{display:block;}#view-7days{display:none;}"
        # Next-7-days list styles
        ".sd-container{max-width:700px;margin:0 auto;padding:8px 16px 24px;}"
        ".sd-day{margin-bottom:4px;}"
        ".sd-day-hdr{display:flex;align-items:center;gap:8px;padding:10px 0 6px;"
        "border-bottom:1px solid var(--border);margin-bottom:6px;"
        "position:sticky;top:44px;z-index:10;background:var(--bg-base);}"
        ".sd-day-label{font-size:13px;font-weight:700;color:var(--text-1);min-width:72px;}"
        ".sd-day-full{font-size:12px;color:var(--text-2);}"
        ".sd-event-count{margin-left:auto;font-size:11px;font-weight:700;"
        "color:var(--text-2);background:var(--border);padding:2px 7px;border-radius:8px;}"
        ".sd-no-events{font-size:13px;color:var(--text-3);padding:8px 0 10px;}"
        ".sd-event{display:flex;align-items:center;gap:8px;padding:8px 0;"
        "border-bottom:1px solid var(--border);}"
        ".sd-event:last-child{border-bottom:none;}"
        ".sd-time{font-size:12px;font-weight:600;color:var(--text-2);"
        "min-width:72px;flex-shrink:0;white-space:nowrap;}"
        ".sd-allday{font-size:11px;font-weight:600;color:var(--accent-l);"
        "background:var(--accent-bg);padding:2px 7px;border-radius:5px;"
        "flex-shrink:0;white-space:nowrap;min-width:72px;text-align:center;}"
        ".sd-cal-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;}"
        ".sd-title{font-size:14px;font-weight:500;color:var(--text-1);"
        "text-decoration:none;flex:1;min-width:0;overflow:hidden;"
        "text-overflow:ellipsis;white-space:nowrap;}"
        "a.sd-title:hover{color:var(--accent-l);text-decoration:underline;}"
        "@media(max-width:768px){"
        ".sd-container{padding:8px 8px 24px;}"
        ".sd-time,.sd-allday{min-width:58px;font-size:11px;}"
        ".sd-title{font-size:13px;}"
        ".view-toggle{padding:8px 8px;}"
        "}"
        "</style></head><body>"
        + (
            ""
            if embed
            else '<div class="top-bar">'
            '<span class="top-bar-title">Calendar</span>'
            '<button class="refresh-btn" onclick="location.reload()">&#8635; Refresh</button>'
            "</div>"
        )
        + '<div class="scroll-area">'
        # Sticky header: view toggle + section nav bar together (no gap)
        '<div class="cal-sticky-top">'
        '<div class="view-toggle">'
        '<button class="view-toggle-btn active" id="btn-events" onclick="switchView(\'events\')">Events</button>'
        '<button class="view-toggle-btn" id="btn-7days" onclick="switchView(\'7days\')">Next 7 Days</button>'
        "</div>"
        + _build_cal_nav_bar(_cal_nav_counts)
        + "</div>"
        # Events view (default)
        '<div id="view-events"><div class="task-list">'
        # Section 1: Not Reviewed
        + (
            f'<div class="section-hdr" id="cal-sec-not-reviewed">'
            f'<span style="color:var(--warn);">Not Reviewed</span>'
            f'<span class="section-badge" id="unrev-badge" style="background:var(--warn-bg);'
            f'color:var(--warn);border:1px solid var(--warn-b);">{unreviewed_count}</span>'
            f"</div>" + unreviewed_cards
            if unreviewed_count > 0
            else f'<div id="cal-sec-not-reviewed"></div>'
        )
        # Categorized reviewed sections
        + reviewed_sections_html + "</div></div>"
        # Next-7-days view (hidden by default)
        '<div id="view-7days">' + seven_day_html + "</div>"
        "</div>"
        # Event detail modal
        '<div class="ev-modal-overlay" id="ev-modal" onclick="if(event.target===this)closeEventDetail()">'
        '<div class="ev-modal-box">'
        '<div class="ev-modal-hdr">'
        '<span class="ev-modal-title">Edit Event</span>'
        '<button class="ev-modal-close" onclick="closeEventDetail()">\u00d7</button>'
        "</div>"
        '<div class="ev-modal-body">'
        '<div><label class="ev-field-label">Title</label>'
        '<input type="text" id="ev-edit-title" class="ev-field-input" /></div>'
        '<div class="ev-datetime-row">'
        '<div><label class="ev-field-label">Start</label>'
        '<input id="ev-edit-start" class="ev-field-input" /></div>'
        '<div><label class="ev-field-label" id="ev-end-label">End</label>'
        '<input id="ev-edit-end" class="ev-field-input" /></div>'
        "</div>"
        '<div><label class="ev-field-label">Location</label>'
        '<input type="text" id="ev-edit-location" class="ev-field-input" /></div>'
        '<div><label class="ev-field-label">Description</label>'
        '<textarea id="ev-edit-description" class="ev-field-textarea"></textarea></div>'
        "</div>"
        '<div class="ev-modal-footer">'
        '<a id="ev-gcal-link" href="#" target="_blank" class="ev-gcal-btn">Open in Google Calendar \u2197</a>'
        '<div class="ev-modal-actions">'
        '<button class="ev-cancel-btn" onclick="closeEventDetail()">Cancel</button>'
        '<button id="ev-save-btn" class="ev-save-btn" onclick="saveEventDetail()">Save Changes</button>'
        "</div></div>"
        "</div></div>"
        "<script>"
        "var _cs=getComputedStyle(document.documentElement);"
        "function cv(n){return _cs.getPropertyValue(n).trim();}"
        "var _FNURL='" + function_url.rstrip("/") + "';"
        "var _evModalEid='';"
        "var _evModalCalType='';"
        "var _evModalIsAllDay=false;"
        "function openEventDetail(e,card){"
        "if(e.target.closest('button')||e.target.closest('a'))return;"
        "_evModalEid=card.getAttribute('data-eid');"
        "_evModalCalType=card.getAttribute('data-cal-type');"
        "_evModalIsAllDay=card.getAttribute('data-is-all-day')==='1';"
        "var title=card.getAttribute('data-title')||'';"
        "var start=card.getAttribute('data-start')||'';"
        "var end=card.getAttribute('data-end')||'';"
        "var loc=card.getAttribute('data-location')||'';"
        "var desc=card.getAttribute('data-description')||'';"
        "var gcal=card.getAttribute('data-gcal')||'';"
        "document.getElementById('ev-edit-title').value=title;"
        "document.getElementById('ev-edit-location').value=loc;"
        "document.getElementById('ev-edit-description').value=desc;"
        "var si=document.getElementById('ev-edit-start');"
        "var ei=document.getElementById('ev-edit-end');"
        "var elbl=document.getElementById('ev-end-label');"
        "if(_evModalIsAllDay){"
        "si.type='date';ei.type='date';"
        "si.value=start?start.substring(0,10):'';"
        # For all-day events, Google end is exclusive (next day) — subtract 1 for display
        "if(end){"
        "var ed=new Date(end.substring(0,10)+'T12:00:00');"
        "ed.setDate(ed.getDate()-1);"
        "ei.value=ed.getFullYear()+'-'+String(ed.getMonth()+1).padStart(2,'0')+'-'+String(ed.getDate()).padStart(2,'0');"
        "}else{ei.value='';}"
        "elbl.textContent='End (inclusive)';"
        "}else{"
        "si.type='datetime-local';ei.type='datetime-local';"
        "si.value=start?start.substring(0,16):'';"
        "ei.value=end?end.substring(0,16):'';"
        "elbl.textContent='End';"
        "}"
        "var gl=document.getElementById('ev-gcal-link');"
        "gl.href=gcal||'#';gl.style.display=gcal?'':'none';"
        "var modal=document.getElementById('ev-modal');"
        "modal.style.display='flex';"
        "document.body.style.overflow='hidden';}"
        "function closeEventDetail(){"
        "document.getElementById('ev-modal').style.display='none';"
        "document.body.style.overflow='';}"
        "function saveEventDetail(){"
        "var btn=document.getElementById('ev-save-btn');"
        "btn.style.pointerEvents='none';btn.textContent='Saving\u2026';"
        "var title=document.getElementById('ev-edit-title').value;"
        "var startVal=document.getElementById('ev-edit-start').value;"
        "var endVal=document.getElementById('ev-edit-end').value;"
        "var loc=document.getElementById('ev-edit-location').value;"
        "var desc=document.getElementById('ev-edit-description').value;"
        # For all-day events, add 1 day to end to restore exclusive end for Google Calendar
        "var endToSend=endVal;"
        "if(_evModalIsAllDay&&endVal){"
        "var ed=new Date(endVal+'T12:00:00');"
        "ed.setDate(ed.getDate()+1);"
        "endToSend=ed.getFullYear()+'-'+String(ed.getMonth()+1).padStart(2,'0')+'-'+String(ed.getDate()).padStart(2,'0');"
        "}"
        "fetch(_FNURL+'?action=calendar_update_event',{"
        "method:'POST',"
        "headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({"
        "event_id:_evModalEid,cal_type:_evModalCalType,"
        "title:title,start:startVal,end:endToSend,location:loc,description:desc})})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        "btn.textContent='\u2713 Saved';"
        "setTimeout(function(){closeEventDetail();window.location.reload();},800);"
        "}else{"
        "btn.textContent='Failed';btn.style.pointerEvents='auto';"
        "setTimeout(function(){btn.textContent='Save Changes';},2500);}"
        "}).catch(function(){"
        "btn.textContent='Failed';btn.style.pointerEvents='auto';"
        "setTimeout(function(){btn.textContent='Save Changes';},2500);});}"
        "function scrollToCalSec(key){"
        "var el=document.getElementById('cal-sec-'+key);"
        "if(el){el.scrollIntoView({behavior:'smooth',block:'start'});}}"
        "function switchView(v){"
        "var evts=document.getElementById('view-events');"
        "var sd=document.getElementById('view-7days');"
        "var be=document.getElementById('btn-events');"
        "var bs=document.getElementById('btn-7days');"
        "var sn=document.getElementById('cal-sec-nav');"
        "if(v==='7days'){"
        "evts.style.display='none';sd.style.display='block';"
        "be.classList.remove('active');bs.classList.add('active');"
        "if(sn)sn.style.display='none';"
        "}else{"
        "evts.style.display='block';sd.style.display='none';"
        "be.classList.add('active');bs.classList.remove('active');"
        "if(sn)sn.style.display='';"
        "}}" + post_message_js + "function doReview(btn,eid,url){"
        "btn.style.pointerEvents='none';btn.textContent='Reviewing\u2026';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){"
        "btn.className='review-btn reviewed';btn.textContent='\u2713 Reviewed (7d)';"
        "btn.style.cursor='default';btn.style.pointerEvents='auto';"
        "var card=btn.closest('.task-card');"
        "if(card){card.classList.remove('unreviewed-card');card.classList.add('reviewed-card');}"
        "if(typeof calendarCount!=='undefined'){calendarCount=Math.max(0,calendarCount-1);"
        "if(typeof postCount==='function')postCount();}"
        "var b=document.getElementById('unrev-badge');"
        "if(b&&typeof calendarCount!=='undefined')b.textContent=calendarCount;"
        "}else{"
        "btn.textContent='Review';btn.style.pointerEvents='auto';"
        "}"
        "}).catch(function(){btn.textContent='Review';btn.style.pointerEvents='auto';});}"
        "function doTodoist(btn,idx,baseUrl){"
        "var pid=document.getElementById('proj-'+idx);"
        "var dt=document.getElementById('date-'+idx);"
        "var pri=document.getElementById('pri-'+idx);"
        "btn.style.pointerEvents='none';btn.textContent='Adding\u2026';"
        "var url=baseUrl;"
        "if(pid&&pid.value)url+='&project_id='+encodeURIComponent(pid.value);"
        "if(dt&&dt.value)url+='&due_date='+encodeURIComponent(dt.value);"
        "if(pri&&pri.value)url+='&priority='+encodeURIComponent(pri.value);"
        "fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "btn.style.display='none';"
        "var card=btn.closest('.task-card');"
        "var br=card&&card.querySelector('.badge-row');"
        "if(br){var a=document.createElement('a');a.className='todoist-indicator';"
        "var lbl=btn.getAttribute('data-indicator-label')||'Event Action';"
        "a.textContent=lbl;a.target='_blank';"
        "a.href=d.task_id?'https://app.todoist.com/app/task/'+d.task_id:'#';"
        "a.onclick=function(e){e.stopPropagation();};"
        "var cb=br.querySelector('.cal-type-badge');"
        "if(cb&&cb.nextSibling){br.insertBefore(a,cb.nextSibling);}else{br.appendChild(a);}}}"
        "else{"
        "var origLbl=btn.getAttribute('data-indicator-label')==='Reminder to Text Scheduled'?'Reminder to Text':'Add to Todoist';"
        "btn.textContent='Failed';btn.style.background=cv('--err-bg');btn.style.color=cv('--err');"
        "btn.style.pointerEvents='auto';"
        "setTimeout(function(){btn.textContent=origLbl;btn.style.background='';btn.style.color='';},2000);}"
        "}).catch(function(){"
        "var origLbl2=btn.getAttribute('data-indicator-label')==='Reminder to Text Scheduled'?'Reminder to Text':'Add to Todoist';"
        "btn.textContent='Failed';btn.style.background=cv('--err-bg');btn.style.color=cv('--err');"
        "btn.style.pointerEvents='auto';"
        "setTimeout(function(){btn.textContent=origLbl2;btn.style.background='';btn.style.color='';},2000);});}"
        "function doCommit(btn,idx,baseUrl){"
        "btn.style.pointerEvents='none';btn.textContent='Committing\u2026';"
        "fetch(baseUrl,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        "btn.textContent='\u2713 Committed';btn.style.cursor='default';"
        "var rv=document.getElementById('rev-'+idx);"
        "if(rv&&rv.textContent.indexOf('Reviewed')===-1)rv.click();}"
        "else{"
        "btn.textContent='Commit';btn.style.background='';btn.style.color='';"
        "btn.style.pointerEvents='auto';}"
        "}).catch(function(){"
        "btn.textContent='Commit';btn.style.background='';btn.style.color='';"
        "btn.style.pointerEvents='auto';});}"
        # --- Copy calendar event for Claude (uses innerHTML for SVG icon restore) ---
        "function doCopyCalCC(btn,title,dateStr,location){"
        "var orig=btn.innerHTML;"
        "var msg='Calendar event:\\n\\nTitle: '+title+'\\nDate: '+dateStr+(location?'\\nLocation: '+location:'');"
        "navigator.clipboard.writeText(msg).then(function(){"
        "btn.textContent='\u2713';setTimeout(function(){btn.innerHTML=orig;},1500);"
        "}).catch(function(){btn.textContent='!';setTimeout(function(){btn.innerHTML=orig;},1500);});}"
        "function doSchedulePrep(btn,idx,baseUrl){"
        "btn.style.pointerEvents='none';btn.textContent='Scheduling\u2026';"
        "fetch(baseUrl,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "btn.style.display='none';"
        "var card=btn.closest('.task-card');"
        "var br=card&&card.querySelector('.badge-row');"
        "if(br){var a=document.createElement('a');a.className='prep-indicator';"
        "a.textContent='Prep Scheduled';a.target='_blank';"
        "a.href=d.task_id?'https://app.todoist.com/app/task/'+d.task_id:'#';"
        "a.onclick=function(e){e.stopPropagation();};br.appendChild(a);}}"
        "else{"
        "btn.textContent='Schedule Prep';btn.style.pointerEvents='auto';}"
        "}).catch(function(){"
        "btn.textContent='Schedule Prep';btn.style.pointerEvents='auto';});}"
        "function doTravelTime(btn,idx,baseUrl){"
        "btn.style.pointerEvents='none';btn.textContent='Calculating\u2026';"
        "fetch(baseUrl,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "btn.style.display='none';"
        "var card=btn.closest('.task-card');"
        "var br=card&&card.querySelector('.badge-row');"
        "if(br){var a=document.createElement('a');a.className='travel-indicator';"
        "a.textContent='Travel Time Scheduled';a.target='_blank';"
        "a.href=d.travel_event_link||'#';"
        "a.onclick=function(e){e.stopPropagation();};br.appendChild(a);}}"
        "else{"
        "btn.textContent='Add travel time';btn.style.background=cv('--err-bg');"
        "btn.style.color=cv('--err');btn.style.borderColor=cv('--err-b');"
        "setTimeout(function(){btn.textContent='Add travel time';"
        "btn.style.background='';btn.style.color='';btn.style.borderColor='';"
        "btn.style.pointerEvents='auto';},3000);}"
        "}).catch(function(){"
        "btn.textContent='Add travel time';btn.style.background=cv('--err-bg');"
        "btn.style.color=cv('--err');"
        "setTimeout(function(){btn.textContent='Add travel time';"
        "btn.style.background='';btn.style.color='';btn.style.pointerEvents='auto';},3000);});}"
        "function doTogglLog(btn,url){"
        "btn.style.pointerEvents='none';btn.textContent='Logging\u2026';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){"
        "btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        "btn.style.borderColor=cv('--ok-b');btn.textContent='\u2713 Logged';"
        "btn.style.cursor='default';"
        "}else{"
        "btn.textContent='Failed';btn.style.background=cv('--err-bg');btn.style.color=cv('--err');"
        "btn.style.pointerEvents='auto';"
        "setTimeout(function(){btn.textContent='Log in Toggl';btn.style.background='';btn.style.color='';btn.style.borderColor='';},2000);}"
        "}).catch(function(){"
        "btn.textContent='Failed';btn.style.background=cv('--err-bg');btn.style.color=cv('--err');"
        "btn.style.pointerEvents='auto';"
        "setTimeout(function(){btn.textContent='Log in Toggl';btn.style.background='';btn.style.color='';btn.style.borderColor='';},2000);});}"
        "function toggleChecklist(section){"
        "var body=document.getElementById('cl-body-'+section);"
        "var btn=document.getElementById('cl-btn-'+section);"
        "if(body.contentEditable==='true'){"
        "saveChecklist(section);body.contentEditable='false';btn.textContent='Edit';"
        "}else{"
        "body.contentEditable='true';btn.textContent='Save';body.focus();"
        "}}"
        "function saveChecklist(section){"
        "var body=document.getElementById('cl-body-'+section);"
        "var content=body.innerText;"
        "var url='" + function_url.rstrip("/") + "?action=calendar_save_checklist';"
        "fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({section:section,content:content})})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(!d.ok){alert('Save failed');}"
        "}).catch(function(){alert('Save failed');});}"
        "function doFfmOutreach(btn,person,meal){"
        "btn.style.pointerEvents='none';var orig=btn.textContent;btn.textContent='Creating\u2026';"
        "var url='" + function_url.rstrip("/") + "?action=ffm_outreach"
        "&person='+person+'&meal_type='+meal;"
        "fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "btn.textContent='\u2713 Created';btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        "btn.style.borderColor=cv('--ok-b');"
        "setTimeout(function(){btn.textContent=orig;btn.style.background='';btn.style.color='';"
        "btn.style.borderColor='';btn.style.pointerEvents='auto';},2500);}"
        "else{"
        "btn.textContent='Failed';btn.style.background=cv('--err-bg');btn.style.color=cv('--err');"
        "setTimeout(function(){btn.textContent=orig;btn.style.background='';btn.style.color='';"
        "btn.style.pointerEvents='auto';},2000);}"
        "}).catch(function(){"
        "btn.textContent='Failed';btn.style.background=cv('--err-bg');btn.style.color=cv('--err');"
        "setTimeout(function(){btn.textContent=orig;btn.style.background='';btn.style.color='';"
        "btn.style.pointerEvents='auto';},2000);});}"
        "function doDeleteEvent(btn,idx,url){"
        "if(!confirm('Delete this calendar event? This cannot be undone.'))return;"
        "btn.style.pointerEvents='none';btn.textContent='Deleting\u2026';"
        "fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "var card=btn.closest('.task-card');"
        "if(card){card.style.transition='opacity .3s';card.style.opacity='0';"
        "setTimeout(function(){card.remove();},300);}"
        "}else{"
        "btn.textContent='Delete';btn.style.pointerEvents='auto';"
        "alert('Delete failed: '+(d.error||'Unknown error'));}"
        "}).catch(function(){"
        "btn.textContent='Delete';btn.style.pointerEvents='auto';"
        "alert('Delete failed — check network connection.');});}"
        "function _timerLabel(secs){"
        "if(secs<=0)return 'Starting soon';"
        "var h=Math.floor(secs/3600);var m=Math.floor((secs%3600)/60);var s=secs%60;"
        "if(h>0)return h+'h '+m+'m';"
        "if(m>0)return m+'m '+s+'s';"
        "return s+'s';}"
        "function _setTimerText(btn,txt){"
        "var lbl=btn.querySelector('.timer-label');"
        "if(lbl)lbl.textContent=txt;else btn.lastChild.textContent=txt;}"
        "function _calcPrepSec(btn){"
        "var s=btn.getAttribute('data-start');"
        "if(!s)return 0;"
        "var ev=new Date(s);"
        "return Math.floor((ev.getTime()-Date.now()-(5*60*1000))/1000);}"
        "function doPrepTimer(btn){"
        "var secs=_calcPrepSec(btn);"
        "if(secs<=0){"
        "_setTimerText(btn,'Starting soon');btn.classList.add('expired');"
        "return;}"
        "var title=btn.getAttribute('data-title')||'Event';"
        "_setTimerText(btn,_timerLabel(secs)+' \u2713');"
        "btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        "btn.style.borderColor=cv('--ok-b');"
        "btn.classList.add('scheduled');"
        "var h=Math.floor(secs/3600);var rm=Math.floor((secs%3600)/60);var rs=secs%60;"
        "window.top.open('timerplus://app/quick-timers/new?hours='+h+'&minutes='+rm+'&seconds='+rs+'&name='+encodeURIComponent(title));}"
        "function _tickTimers(){"
        "var btns=document.querySelectorAll('.timer-btn');"
        "for(var i=0;i<btns.length;i++){"
        "if(btns[i].classList.contains('expired'))continue;"
        "var secs=_calcPrepSec(btns[i]);"
        "if(secs<=0){_setTimerText(btns[i],'Starting soon');btns[i].classList.add('expired');}"
        "else if(btns[i].classList.contains('scheduled')){"
        "_setTimerText(btns[i],_timerLabel(secs)+' \u2713');}"
        "else{_setTimerText(btns[i],_timerLabel(secs));}"
        "}}"
        "_tickTimers();"
        "setInterval(_tickTimers,1000);"
        "</script>"
        "</body></html>"
    )
