"""HTML builder for the Calendar tab in the ActionOS dashboard.

Renders sections: Not Reviewed, Today's Events, Love Brittany / Love Children,
Medical Appointments, Travel, Birthdays & Anniversaries, Everything Else.
Cards styled consistently with the other ActionOS views.
"""

import calendar
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


def _is_upcoming_timed_event(event: Dict[str, Any]) -> bool:
    """Return True if the event is a timed (non-all-day) event happening today or tomorrow."""
    if event.get("is_all_day", False):
        return False
    start = event.get("start", "")
    if not start:
        return False
    try:
        dt_start = datetime.fromisoformat(start).astimezone(_EASTERN)
        today = datetime.now(_EASTERN).date()
        tomorrow = today + timedelta(days=1)
        return dt_start.date() in (today, tomorrow)
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
) -> str:
    eid = event.get("id", "")
    eid_safe = html.escape(eid)
    eid_enc = urllib.parse.quote(eid)
    title = html.escape(event.get("title", "(No title)"))
    location = html.escape(event.get("location", ""))
    html_link = event.get("html_link", "")
    cal_type = event.get("calendar_type", "family")
    date_range = html.escape(_format_event_date_range(event))

    cal_label = html.escape(_CAL_TYPE_LABELS.get(cal_type, cal_type.capitalize()))
    cal_color = _CAL_TYPE_COLORS.get(cal_type, "#5f6368")

    title_enc = urllib.parse.quote(event.get("title", ""))
    date_enc = urllib.parse.quote(event.get("start", "")[:10])
    loc_enc = urllib.parse.quote(event.get("location", ""))

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
        timer_btn = (
            f'<button class="timer-btn" id="tmr-{idx}" '
            f'data-start="{start_iso}" '
            f'data-title="{title_for_timer}" '
            f'onclick="doPrepTimer(this)">'
            f'{_timer_svg} <span class="timer-label">Countdown</span></button>'
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

    card_extra = " reviewed-card" if reviewed else " unreviewed-card"

    if reviewed:
        # Reviewed: clean card with just badge + gcal link + timer + claude
        return (
            f'<div class="task-card{card_extra}" id="card-{idx}">'
            f'<div class="card-row">'
            f'<div class="card-content">'
            f'<div class="task-title">'
            f"{title}"
            f'<span class="cal-type-badge" style="background:{cal_color}">{cal_label}</span>'
            f"</div>"
            f'<div class="task-meta">{meta_line}</div>'
            f'<div class="task-actions">'
            f"{review_btn}"
            f"{timer_btn}"
            f"{gcal_html}"
            f"{cc_btn}"
            f"</div>"
            f"</div></div>"
            f"</div>"
        )

    # Unreviewed: Review + Add to Todoist + Commit + Timer + gcal + Claude
    return (
        f'<div class="task-card{card_extra}" id="card-{idx}">'
        f'<div class="card-row">'
        f'<div class="card-content">'
        f'<div class="task-title">'
        f"{title}"
        f'<span class="cal-type-badge" style="background:{cal_color}">{cal_label}</span>'
        f"</div>"
        f'<div class="task-meta">{meta_line}</div>'
        f'<div class="task-actions">'
        f"{review_btn}"
        f'<button class="todoist-btn" id="tod-{idx}" '
        f"onclick=\"doTodoist(this,{idx},'{todoist_url_base}')\">"
        f"Add to Todoist</button>"
        f'<button class="commit-btn" id="cmt-{idx}" '
        f"onclick=\"doCommit(this,{idx},'{commit_url_base}')\">"
        f"Commit</button>"
        f"{timer_btn}"
        f"{gcal_html}"
        f"{cc_btn}"
        f"</div>"
        f"</div></div>"
        f"</div>"
    )


def _build_12month_html(events: List[Dict[str, Any]]) -> str:
    """Build a 12-month mini-calendar grid with colored event dots."""
    now = datetime.now(_EASTERN)
    today = now.date()

    # Group events by date → list of calendar types
    events_by_date: Dict[str, List[str]] = {}
    for ev in events:
        start = ev.get("start", "")[:10]
        if not start:
            continue
        cal_type = ev.get("calendar_type", "family")
        events_by_date.setdefault(start, []).append(cal_type)

    months_html = ""
    for offset in range(12):
        month = ((now.month - 1 + offset) % 12) + 1
        year = now.year + ((now.month - 1 + offset) // 12)
        month_name = calendar.month_abbr[month]

        # Build weekday headers
        hdr = ""
        for d in ("S", "M", "T", "W", "T", "F", "S"):
            hdr += f'<span class="ym-hdr">{d}</span>'

        # Build day cells
        cal_obj = calendar.Calendar(firstweekday=6)  # Sunday start
        days_html = ""
        for dt in cal_obj.itermonthdates(year, month):
            if dt.month != month:
                days_html += '<span class="ym-day ym-other"></span>'
                continue

            date_str = dt.strftime("%Y-%m-%d")
            cal_types = events_by_date.get(date_str, [])

            is_today = dt == today
            today_cls = " ym-today" if is_today else ""

            if cal_types:
                # Show up to 3 colored dots
                dots = ""
                seen = []
                for ct in cal_types:
                    if ct not in seen:
                        seen.append(ct)
                    if len(seen) >= 3:
                        break
                for ct in seen:
                    c = _CAL_TYPE_COLORS.get(ct, "#5f6368")
                    dots += f'<span class="ym-dot" style="background:{c}"></span>'
                days_html += (
                    f'<span class="ym-day ym-has{today_cls}" title="{len(cal_types)} event(s)">'
                    f'{dt.day}<span class="ym-dots">{dots}</span></span>'
                )
            else:
                days_html += f'<span class="ym-day{today_cls}">{dt.day}</span>'

        months_html += (
            f'<div class="ym-month">'
            f'<div class="ym-month-title">{month_name} {year}</div>'
            f'<div class="ym-grid">{hdr}{days_html}</div>'
            f"</div>"
        )

    # Build legend
    legend = ""
    for cal_type, label in _CAL_TYPE_LABELS.items():
        color = _CAL_TYPE_COLORS.get(cal_type, "#5f6368")
        legend += (
            f'<span class="ym-legend-item">'
            f'<span class="ym-dot" style="background:{color}"></span>'
            f"{html.escape(label)}</span>"
        )

    return (
        f'<div class="ym-legend">{legend}</div>'
        f'<div class="ym-container">{months_html}</div>'
    )


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


def build_calendar_html(
    events: List[Dict[str, Any]],
    reviewed_state: dict,
    function_url: str,
    action_token: str,
    projects: List[Dict[str, Any]],
    embed: bool = False,
    checklists: dict = None,
) -> str:
    """Build the Calendar page with categorized sections."""
    project_options_html = _build_project_options_html(projects)
    checklists = checklists or {}

    # Filter out birthday/anniversary events beyond 90 days
    filtered_events = [
        ev for ev in events
        if not _is_birthday_event(ev) or _is_within_days(ev, 90)
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
            out += _build_event_card(
                event,
                r,
                days_rem,
                function_url,
                action_token,
                project_options_html,
                idx,
            )
        return out

    unreviewed_cards = _build_section_cards(unreviewed)
    if not unreviewed_cards:
        unreviewed_cards = '<div class="empty-state">All caught up \u2713</div>'

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
        reviewed_sections_html += (
            f'<div class="section-hdr" style="margin-top:24px;">'
            f'<span style="color:var({color_var});">{label}</span>'
            f'<span class="section-badge" style="background:var({badge_bg});'
            f'color:var({badge_color});border:1px solid var({badge_border});">'
            f"{len(bucket)}</span>"
            f"</div>" + checklist_html + cards
        )

    twelve_month_html = _build_12month_html(events)

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
        ".task-list{max-width:700px;margin:0 auto;padding:12px 16px;overflow:clip;}"
        ".section-hdr{display:flex;align-items:center;gap:8px;padding:16px 0 8px;"
        "font-size:11px;font-weight:600;color:var(--text-3);text-transform:uppercase;"
        "letter-spacing:0.6px;border-bottom:1px solid var(--border);margin-bottom:10px;"
        "position:sticky;top:0;z-index:10;background:var(--bg-base);}"
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
        "line-height:1.4;margin-bottom:4px;word-break:break-word;"
        "display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;}"
        ".cal-type-badge{font-size:10px;font-weight:700;color:#fff;"
        "padding:2px 7px;border-radius:6px;white-space:nowrap;flex-shrink:0;}"
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
        ".timer-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:var(--purple-bg);color:var(--purple);border:1px solid var(--purple-b);"
        "cursor:pointer;transition:background .15s;"
        "display:inline-flex;align-items:center;gap:5px;}"
        ".timer-btn:hover{background:var(--purple-b);}"
        ".timer-btn.expired{opacity:0.4;cursor:default;pointer-events:none;}"
        ".timer-icon{flex-shrink:0;vertical-align:middle;}"
        ".gcal-link{color:var(--accent-l);font-size:12px;font-weight:500;"
        "text-decoration:none;white-space:nowrap;}"
        ".gcal-link:hover{text-decoration:underline;}"
        ".assign-cc-btn{display:inline-flex;align-items:center;justify-content:center;"
        "padding:4px 10px;border-radius:6px;"
        "background:rgba(196,120,64,0.10);border:1px solid rgba(196,120,64,0.25);"
        "cursor:pointer;transition:background .15s;color:#c47840;font-size:13px;font-weight:600;}"
        ".assign-cc-btn:hover{background:rgba(196,120,64,0.25);}"
        ".empty-state{text-align:center;color:var(--text-2);padding:24px 20px;font-size:14px;}"
        "@media(max-width:768px){"
        ".task-actions{gap:6px;}"
        ".action-select,.review-btn,.todoist-btn,.commit-btn,.timer-btn,.assign-cc-btn{font-size:11px;padding:4px 6px;}"
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
        # View toggle bar
        ".view-toggle{display:flex;gap:4px;padding:8px 16px;max-width:700px;margin:0 auto;"
        "position:sticky;top:0;z-index:20;background:var(--bg-base);}"
        ".view-toggle-btn{flex:1;font-family:inherit;font-size:13px;font-weight:600;"
        "padding:8px 12px;border-radius:8px;border:1px solid var(--border);"
        "background:var(--bg-s1);color:var(--text-2);cursor:pointer;transition:all .15s;}"
        ".view-toggle-btn:hover{background:var(--bg-s2);color:var(--text-1);}"
        ".view-toggle-btn.active{background:var(--accent);color:#fff;border-color:var(--accent);}"
        "#view-events{display:block;}#view-12month{display:none;}"
        # 12-month grid styles
        ".ym-container{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;"
        "max-width:700px;margin:0 auto;padding:8px 16px 24px;}"
        ".ym-month{background:var(--bg-s1);border:1px solid var(--border);border-radius:8px;padding:10px;}"
        ".ym-month-title{font-size:13px;font-weight:700;color:var(--text-1);text-align:center;"
        "margin-bottom:6px;}"
        ".ym-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:1px;text-align:center;}"
        ".ym-hdr{font-size:9px;font-weight:600;color:var(--text-3);padding:2px 0;}"
        ".ym-day{font-size:11px;color:var(--text-2);padding:3px 0;position:relative;"
        "display:flex;flex-direction:column;align-items:center;min-height:24px;justify-content:center;}"
        ".ym-day.ym-other{visibility:hidden;}"
        ".ym-day.ym-today{color:var(--accent-l);font-weight:700;}"
        ".ym-day.ym-has{color:var(--text-1);font-weight:600;cursor:default;}"
        ".ym-dots{display:flex;gap:2px;justify-content:center;margin-top:1px;}"
        ".ym-dot{width:5px;height:5px;border-radius:50%;display:inline-block;flex-shrink:0;}"
        ".ym-legend{display:flex;flex-wrap:wrap;gap:10px;max-width:700px;margin:0 auto;"
        "padding:12px 16px 4px;}"
        ".ym-legend-item{display:flex;align-items:center;gap:4px;font-size:11px;color:var(--text-2);}"
        "@media(max-width:768px){"
        ".ym-container{grid-template-columns:repeat(2,1fr);gap:8px;padding:8px 8px 24px;}"
        ".ym-month{padding:8px;}"
        ".ym-day{font-size:10px;min-height:20px;padding:2px 0;}"
        ".ym-hdr{font-size:8px;}"
        ".ym-dot{width:4px;height:4px;}"
        ".ym-legend{padding:8px 8px 4px;gap:8px;}"
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
        # View toggle bar
        '<div class="view-toggle">'
        '<button class="view-toggle-btn active" id="btn-events" onclick="switchView(\'events\')">Events</button>'
        '<button class="view-toggle-btn" id="btn-12month" onclick="switchView(\'12month\')">12 Month</button>'
        "</div>"
        # Events view (default)
        '<div id="view-events"><div class="task-list">'
        # Section 1: Not Reviewed
        + (
            f'<div class="section-hdr">'
            f'<span style="color:var(--warn);">Not Reviewed</span>'
            f'<span class="section-badge" id="unrev-badge" style="background:var(--warn-bg);'
            f'color:var(--warn);border:1px solid var(--warn-b);">{unreviewed_count}</span>'
            f"</div>" + unreviewed_cards
            if unreviewed_count > 0
            else f'<div class="section-hdr">'
            f'<span style="color:var(--ok);">Fully Reviewed</span>'
            f'<span class="section-badge" id="unrev-badge" style="background:var(--ok-bg);'
            f'color:var(--ok);border:1px solid var(--ok-b);">0</span>'
            f"</div>"
        )
        # Categorized reviewed sections
        + reviewed_sections_html + "</div></div>"
        # 12-month view (hidden by default)
        '<div id="view-12month">' + twelve_month_html + "</div>"
        "</div>"
        "<script>"
        "var _cs=getComputedStyle(document.documentElement);"
        "function cv(n){return _cs.getPropertyValue(n).trim();}"
        "function switchView(v){"
        "var evts=document.getElementById('view-events');"
        "var ym=document.getElementById('view-12month');"
        "var be=document.getElementById('btn-events');"
        "var bm=document.getElementById('btn-12month');"
        "if(v==='12month'){"
        "evts.style.display='none';ym.style.display='block';"
        "be.classList.remove('active');bm.classList.add('active');"
        "}else{"
        "evts.style.display='block';ym.style.display='none';"
        "be.classList.add('active');bm.classList.remove('active');"
        "}}" + post_message_js + "function doReview(btn,eid,url){"
        "btn.style.pointerEvents='none';btn.textContent='Reviewing\u2026';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){"
        "btn.className='review-btn reviewed';btn.textContent='\u2713 Reviewed (7d)';"
        "btn.style.cursor='default';btn.style.pointerEvents='auto';"
        "var card=btn.closest('.task-card');"
        "if(card){card.classList.remove('unreviewed-card');card.classList.add('reviewed-card');"
        "var acts=card.querySelectorAll('.todoist-btn,.commit-btn');"
        "for(var i=0;i<acts.length;i++)acts[i].style.display='none';}"
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
        "btn.textContent='\u2713 Added';btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        "setTimeout(function(){btn.textContent='Add to Todoist';"
        "btn.style.background='';btn.style.color='';btn.style.pointerEvents='auto';},2000);}"
        "else{"
        "btn.textContent='Failed';btn.style.background=cv('--err-bg');btn.style.color=cv('--err');"
        "btn.style.pointerEvents='auto';"
        "setTimeout(function(){btn.textContent='Add to Todoist';btn.style.background='';btn.style.color='';},2000);}"
        "}).catch(function(){"
        "btn.textContent='Failed';btn.style.background=cv('--err-bg');btn.style.color=cv('--err');"
        "btn.style.pointerEvents='auto';"
        "setTimeout(function(){btn.textContent='Add to Todoist';btn.style.background='';btn.style.color='';},2000);});}"
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
        # --- Copy calendar event for Claude ---
        "function doCopyCalCC(btn,title,dateStr,location){"
        "var orig=btn.innerHTML;"
        "var msg='Calendar event:\\n\\nTitle: '+title+'\\nDate: '+dateStr+(location?'\\nLocation: '+location:'');"
        "navigator.clipboard.writeText(msg).then(function(){"
        "btn.textContent='\u2713';setTimeout(function(){btn.innerHTML=orig;},1500);"
        "}).catch(function(){btn.textContent='!';setTimeout(function(){btn.innerHTML=orig;},1500);});}"
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
        "var payload=secs+'|'+title;"
        "window.top.open('shortcuts://run-shortcut?name=Prep%20Timer&input=text&text='+encodeURIComponent(payload));"
        "setTimeout(function(){_setTimerText(btn,_timerLabel(_calcPrepSec(btn)));"
        "btn.style.background='';btn.style.color='';btn.style.borderColor='';},3000);}"
        "function _tickTimers(){"
        "var btns=document.querySelectorAll('.timer-btn');"
        "for(var i=0;i<btns.length;i++){"
        "if(btns[i].classList.contains('expired'))continue;"
        "var secs=_calcPrepSec(btns[i]);"
        "if(secs<=0){_setTimerText(btns[i],'Starting soon');btns[i].classList.add('expired');}"
        "else{_setTimerText(btns[i],_timerLabel(secs));}"
        "}}"
        "_tickTimers();"
        "setInterval(_tickTimers,1000);"
        "</script>"
        "</body></html>"
    )
