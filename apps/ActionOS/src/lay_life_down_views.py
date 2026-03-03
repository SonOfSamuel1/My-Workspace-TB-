"""HTML builder for the Lay Life Down tab in the ActionOS dashboard.

Shows a 6-month forward view (today → ~180 days out) for five calendars:
  Love God, Love Brittany, Love Children, Love Friends & Family, Serve Least of These.

Events are grouped first by calendar, then by month within each calendar section.
"""

import html
from datetime import datetime, timezone
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

_EASTERN = ZoneInfo("America/New_York")

_FONT = (
    "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,"
    "'Segoe UI',Roboto,sans-serif"
)

# Ordered list of calendar types to display (determines section order)
LAY_LIFE_DOWN_CALENDARS = [
    "love_god",
    "love_brittany",
    "love_children",
    "love_friends_family",
    "serve_least_of_these",
]

_CAL_LABELS = {
    "love_god": "Love God",
    "love_brittany": "Love Brittany",
    "love_children": "Love Children",
    "love_friends_family": "Love Friends & Family",
    "serve_least_of_these": "Serve Least of These",
}

_CAL_COLORS = {
    "love_god": "#f59e0b",
    "love_brittany": "#a78bfa",
    "love_children": "#38bdf8",
    "love_friends_family": "#ec4899",
    "serve_least_of_these": "#f97316",
}

# SVG icons per calendar (cross, heart, children, people, hands)
_CAL_ICONS = {
    "love_god": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="12" y1="2" x2="12" y2="22"/>'
        '<line x1="2" y1="12" x2="22" y2="12"/>'
        "</svg>"
    ),
    "love_brittany": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">'
        '<path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>'
        "</svg>"
    ),
    "love_children": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="7" r="4"/>'
        '<path d="M5.5 21a8.38 8.38 0 0 1 13 0"/>'
        "</svg>"
    ),
    "love_friends_family": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/>'
        '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
        "</svg>"
    ),
    "serve_least_of_these": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z"/>'
        "</svg>"
    ),
}


def _fmt_date(start_str: str, is_all_day: bool) -> str:
    """Return a human-readable date string for an event."""
    if not start_str:
        return ""
    try:
        if is_all_day:
            dt = datetime.strptime(start_str[:10], "%Y-%m-%d")
            return dt.strftime("%a, %b %-d")
        else:
            dt = datetime.fromisoformat(start_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.astimezone(_EASTERN)
            return dt.strftime("%a, %b %-d · %-I:%M %p")
    except Exception:
        return start_str[:10]


def _month_key(start_str: str, is_all_day: bool) -> str:
    """Return 'YYYY-MM' for grouping events by month."""
    if not start_str:
        return "0000-00"
    return start_str[:7]


def _month_label(ym: str) -> str:
    """Convert 'YYYY-MM' to 'Month Year' label."""
    try:
        dt = datetime.strptime(ym, "%Y-%m")
        return dt.strftime("%B %Y")
    except Exception:
        return ym


def _event_card(ev: Dict[str, Any]) -> str:
    title = html.escape(ev.get("title", "(No title)"))
    date_str = _fmt_date(ev.get("start", ""), ev.get("is_all_day", True))
    location = html.escape(ev.get("location", ""))
    return (
        '<div class="lld-event">'
        f'<div class="lld-event-title">{title}</div>'
        f'<div class="lld-event-meta">{html.escape(date_str)}'
        + (f'<span class="lld-loc"> · {location}</span>' if location else "")
        + "</div>"
        "</div>"
    )


def _build_calendar_section(cal_type: str, events: List[Dict[str, Any]]) -> str:
    label = _CAL_LABELS.get(cal_type, cal_type)
    color = _CAL_COLORS.get(cal_type, "#6366f1")
    icon = _CAL_ICONS.get(cal_type, "")

    # Group events by month
    by_month: Dict[str, List[Dict[str, Any]]] = {}
    for ev in events:
        mk = _month_key(ev.get("start", ""), ev.get("is_all_day", True))
        by_month.setdefault(mk, []).append(ev)

    month_html = ""
    for ym in sorted(by_month.keys()):
        month_html += (
            f'<div class="lld-month-label">{html.escape(_month_label(ym))}</div>'
        )
        for ev in by_month[ym]:
            month_html += _event_card(ev)

    if not month_html:
        month_html = '<div class="lld-empty">No events in the next 6 months</div>'

    return (
        f'<div class="lld-section" style="--cal-color:{color}">'
        f'<div class="lld-section-header">'
        f'<span class="lld-icon" style="color:{color}">{icon}</span>'
        f'<span class="lld-section-title">{html.escape(label)}</span>'
        f"</div>"
        f'<div class="lld-section-body">{month_html}</div>'
        f"</div>"
    )


def build_lay_life_down_html(
    events: List[Dict[str, Any]],
    function_url: str,
    embed: bool = True,
) -> str:
    """Build the Lay Life Down view HTML.

    Args:
        events: Events fetched by CalendarService.get_events_for_types() for the
                5 Lay Life Down calendars.
        function_url: The ActionOS base URL (unused currently, kept for API parity).
        embed: If True, renders as an embeddable iframe page (no outer shell chrome).
    """
    # Split events by calendar type
    by_type: Dict[str, List[Dict[str, Any]]] = {t: [] for t in LAY_LIFE_DOWN_CALENDARS}
    for ev in events:
        ct = ev.get("calendar_type", "")
        if ct in by_type:
            by_type[ct].append(ev)

    sections_html = "".join(
        _build_calendar_section(cal_type, by_type[cal_type])
        for cal_type in LAY_LIFE_DOWN_CALENDARS
    )

    css = (
        "<style>"
        f"*{{box-sizing:border-box;margin:0;padding:0;}}"
        f"body{{font-family:{_FONT};background:#1a1a1a;color:#fff;padding:16px 12px 32px;}}"
        ".lld-page-title{"
        "font-size:22px;font-weight:700;margin-bottom:20px;color:#fff;"
        "display:flex;align-items:center;gap:8px;"
        "}"
        ".lld-section{"
        "background:#252528;border-radius:12px;margin-bottom:16px;"
        "border:1px solid rgba(255,255,255,0.07);overflow:hidden;"
        "}"
        ".lld-section-header{"
        "display:flex;align-items:center;gap:10px;padding:14px 16px;"
        "border-bottom:1px solid rgba(255,255,255,0.07);"
        "background:rgba(255,255,255,0.02);"
        "}"
        ".lld-icon{display:flex;align-items:center;flex-shrink:0;}"
        ".lld-section-title{font-size:15px;font-weight:600;color:#fff;}"
        ".lld-section-body{padding:8px 12px 12px;}"
        ".lld-month-label{"
        "font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;"
        "color:#8e8e93;padding:10px 4px 6px;"
        "}"
        ".lld-event{"
        "padding:10px 12px;border-radius:8px;margin-bottom:6px;"
        "background:#1c1c1e;border-left:3px solid var(--cal-color);"
        "}"
        ".lld-event:last-child{margin-bottom:0;}"
        ".lld-event-title{font-size:14px;font-weight:500;color:#f1f1f1;line-height:1.4;}"
        ".lld-event-meta{font-size:12px;color:#8e8e93;margin-top:3px;}"
        ".lld-loc{color:#6e6e73;}"
        ".lld-empty{padding:12px 4px;font-size:13px;color:#48484a;font-style:italic;}"
        "@media(prefers-color-scheme:light){"
        "body{background:#eeeef0;color:#202124;}"
        ".lld-section{background:#fff;border-color:rgba(0,0,0,0.08);}"
        ".lld-section-header{background:rgba(0,0,0,0.02);border-bottom-color:rgba(0,0,0,0.07);}"
        ".lld-section-title{color:#202124;}"
        ".lld-event{background:#f5f5f7;}"
        ".lld-event-title{color:#202124;}"
        ".lld-event-meta{color:#5f6368;}"
        "}"
        "</style>"
    )

    body_tag = '<body style="overscroll-behavior:none">' if embed else "<body>"

    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Lay Life Down</title>"
        + css
        + f"</head>{body_tag}"
        '<div class="lld-page-title">'
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'style="color:#a78bfa">'
        '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>'
        "</svg>"
        "Lay Life Down"
        "</div>"
        + sections_html
        + "</body></html>"
    )
