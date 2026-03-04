"""ActionOS Activity Log — persistent archive of all Toggl time entries."""
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

_FONT = (
    "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,"
    "'Segoe UI',Roboto,sans-serif"
)


def _fmt_secs(secs: int) -> str:
    h = secs // 3600
    m = (secs % 3600) // 60
    if h > 0:
        return f"{h}h {m:02d}m"
    return f"{m}m"


def _fmt_time(iso: str) -> str:
    """Convert UTC ISO string to Eastern local time like '2:34 PM'."""
    try:
        from zoneinfo import ZoneInfo
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        eastern = dt.astimezone(ZoneInfo("America/New_York"))
        return eastern.strftime("%-I:%M %p")
    except Exception:
        return ""


def _eastern_date(iso: str) -> str:
    """Convert UTC ISO string to Eastern date string like '2026-03-04'."""
    try:
        from zoneinfo import ZoneInfo
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    except Exception:
        return ""


def _friendly_date(date_str: str) -> str:
    """Turn '2026-03-04' into 'Tue, Mar 4' or 'Today'/'Yesterday'."""
    try:
        from zoneinfo import ZoneInfo
        eastern = ZoneInfo("America/New_York")
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = datetime.now(eastern).date()
        if d == today:
            return "Today"
        if d == today - timedelta(days=1):
            return "Yesterday"
        return d.strftime("%a, %b %-d")
    except Exception:
        return date_str


def _get_today_str() -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()


def _get_week_cutoff_str() -> str:
    try:
        from zoneinfo import ZoneInfo
        today = datetime.now(ZoneInfo("America/New_York")).date()
        return (today - timedelta(days=6)).isoformat()
    except Exception:
        today = datetime.now(timezone.utc).date()
        return (today - timedelta(days=6)).isoformat()


def fetch_toggl_entries(toggl_token: str) -> list:
    """Fetch all available time entries from Toggl (last ~90 days)."""
    try:
        import base64
        import requests
        auth = base64.b64encode(f"{toggl_token}:api_token".encode()).decode()
        headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
        resp = requests.get(
            "https://api.track.toggl.com/api/v9/me/time_entries",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        entries = resp.json()
        result = []
        for e in entries:
            dur = e.get("duration", 0)
            if dur <= 0:
                continue
            result.append({
                "id": e.get("id"),
                "description": e.get("description") or "Untitled",
                "start": e.get("start", ""),
                "stop": e.get("stop", ""),
                "duration": dur,
                "project_id": e.get("project_id"),
                "tags": e.get("tags") or [],
            })
        return result
    except Exception:
        return []


def merge_entries(saved: list, fresh: list) -> list:
    """Merge saved archive with fresh Toggl entries, deduplicating by id."""
    by_id = {}
    for entry in saved:
        eid = entry.get("id")
        if eid:
            by_id[eid] = entry
    for entry in fresh:
        eid = entry.get("id")
        if eid:
            by_id[eid] = entry
    entries = list(by_id.values())
    entries.sort(key=lambda e: e.get("start", ""), reverse=True)
    return entries


def _build_day_sections(by_date: dict, sorted_dates: list) -> str:
    """Build HTML for day sections from grouped entries."""
    day_sections = ""
    for date_str in sorted_dates:
        day_entries = by_date[date_str]
        day_total = sum(e.get("duration", 0) for e in day_entries)

        rows = ""
        for e in day_entries:
            desc = e.get("description") or "Untitled"
            start_time = _fmt_time(e.get("start", ""))
            stop_time = _fmt_time(e.get("stop", ""))
            dur = _fmt_secs(e.get("duration", 0))
            tags_html = ""
            for tag in e.get("tags", []):
                tags_html += f'<span class="al-tag">{tag}</span>'
            time_range = f"{start_time} — {stop_time}" if start_time and stop_time else start_time
            rows += (
                '<div class="al-entry">'
                '<div class="al-entry-left">'
                f'<span class="al-desc">{desc}</span>'
                f'<span class="al-time">{time_range}{tags_html}</span>'
                '</div>'
                f'<span class="al-dur">{dur}</span>'
                '</div>'
            )

        friendly = _friendly_date(date_str)
        day_sections += (
            '<div class="al-day">'
            '<div class="al-day-header">'
            f'<span class="al-day-label">{friendly}</span>'
            f'<span class="al-day-total">{_fmt_secs(day_total)}</span>'
            '</div>'
            f'{rows}'
            '</div>'
        )
    return day_sections


def _build_stats_html(entries: list, days_count: int, stat_id_prefix: str) -> str:
    """Build the 3-stat row HTML."""
    total_entries = len(entries)
    total_secs = sum(e.get("duration", 0) for e in entries)
    return (
        f'<div class="al-stats" id="stats-{stat_id_prefix}">'
        '<div class="al-stat">'
        f'<div class="al-stat-val">{total_entries}</div>'
        '<div class="al-stat-lbl">Entries</div>'
        '</div>'
        '<div class="al-stat">'
        f'<div class="al-stat-val">{_fmt_secs(total_secs)}</div>'
        '<div class="al-stat-lbl">Total Time</div>'
        '</div>'
        '<div class="al-stat">'
        f'<div class="al-stat-val">{days_count}</div>'
        '<div class="al-stat-lbl">Days</div>'
        '</div>'
        '</div>'
    )


def build_activity_log_html(entries: list, last_synced: str = "") -> str:
    """Build the Activity Log HTML with Today / Past 7 Days tabs."""
    today_str = _get_today_str()
    week_cutoff = _get_week_cutoff_str()

    # Group all entries by Eastern date
    by_date = defaultdict(list)
    for e in entries:
        d = _eastern_date(e.get("start", ""))
        if d:
            by_date[d].append(e)

    # Split into today vs past 7 days
    today_dates = [d for d in sorted(by_date.keys(), reverse=True) if d == today_str]
    week_dates = [d for d in sorted(by_date.keys(), reverse=True) if week_cutoff <= d <= today_str]

    today_entries = []
    for d in today_dates:
        today_entries.extend(by_date[d])

    week_entries = []
    for d in week_dates:
        week_entries.extend(by_date[d])

    # Build day sections for each tab
    today_sections = _build_day_sections(by_date, today_dates)
    if not today_sections:
        today_sections = '<div class="al-empty">No entries yet today. Start a timer from the Home tab.</div>'

    week_sections = _build_day_sections(by_date, week_dates)
    if not week_sections:
        week_sections = '<div class="al-empty">No entries in the past 7 days.</div>'

    # Stats for each tab
    today_stats = _build_stats_html(today_entries, len(today_dates), "today")
    week_stats = _build_stats_html(week_entries, len(week_dates), "week")

    sync_text = f"Last synced: {last_synced}" if last_synced else "Not yet synced"

    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Activity Log</title>"
        "<style>"
        f":root{{--bg-base:#1a1a1a;--bg-s0:#1c1c1e;--bg-s1:#252528;--bg-s2:#2c2c2e;"
        "--text-1:#ffffff;--text-2:#8e8e93;--text-3:#48484a;"
        "--border:rgba(255,255,255,0.08);--border-h:rgba(255,255,255,0.12);"
        "--accent:#6366f1;--accent-l:#818cf8;"
        "--ok:#22c55e;--ok-bg:rgba(34,197,94,0.10);--ok-b:rgba(34,197,94,0.20);"
        "--warn:#eab308;--err:#ef4444;color-scheme:dark;}"
        "@media(prefers-color-scheme:light){:root{"
        "--bg-base:#eeeef0;--bg-s0:#fff;--bg-s1:#fff;--bg-s2:#f5f5f7;"
        "--text-1:#202124;--text-2:#5f6368;--text-3:#80868b;"
        "--border:rgba(0,0,0,0.08);--border-h:rgba(0,0,0,0.15);"
        "--accent:#6366f1;--accent-l:#4f46e5;"
        "--ok:#188038;--ok-bg:#e6f4ea;--ok-b:rgba(24,128,56,0.20);"
        "color-scheme:light;}}"
        "*{box-sizing:border-box;margin:0;padding:0;}"
        f"body{{font-family:{_FONT};background:var(--bg-base);color:var(--text-1);"
        "-webkit-font-smoothing:antialiased;padding:20px 16px 40px;max-width:600px;margin:0 auto;}"
        # Header
        ".al-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;}"
        ".al-title{font-size:20px;font-weight:800;letter-spacing:-0.5px;}"
        ".al-sync-info{font-size:11px;color:var(--text-2);}"
        # Tab bar
        ".al-tabs{display:flex;gap:0;margin-bottom:16px;background:var(--bg-s1);"
        "border:1px solid var(--border);border-radius:10px;padding:3px;}"
        ".al-tab{flex:1;padding:10px 0;font-size:13px;font-weight:600;text-align:center;"
        "border-radius:8px;cursor:pointer;transition:all .15s;color:var(--text-2);"
        "min-height:44px;display:flex;align-items:center;justify-content:center;}"
        ".al-tab.active{background:var(--accent);color:#fff;}"
        ".al-tab:not(.active):hover{color:var(--text-1);}"
        # Tab panels
        ".al-panel{display:none;}"
        ".al-panel.active{display:block;}"
        # Stats row
        ".al-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px;}"
        ".al-stat{background:var(--bg-s1);border:1px solid var(--border);border-radius:10px;"
        "padding:12px;text-align:center;}"
        ".al-stat-val{font-size:20px;font-weight:700;color:var(--text-1);}"
        ".al-stat-lbl{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;"
        "color:var(--text-2);margin-top:3px;}"
        # Day sections
        ".al-day{margin-bottom:20px;}"
        ".al-day-header{display:flex;justify-content:space-between;align-items:center;"
        "padding:8px 0;border-bottom:1px solid var(--border);margin-bottom:8px;}"
        ".al-day-label{font-size:14px;font-weight:700;color:var(--text-1);}"
        ".al-day-total{font-size:13px;font-weight:700;color:var(--accent);font-variant-numeric:tabular-nums;}"
        # Entry rows
        ".al-entry{display:flex;justify-content:space-between;align-items:center;"
        "padding:10px 12px;background:var(--bg-s1);border:1px solid var(--border);"
        "border-radius:10px;margin-bottom:6px;}"
        ".al-entry-left{display:flex;flex-direction:column;gap:3px;flex:1;min-width:0;margin-right:12px;}"
        ".al-desc{font-size:13px;font-weight:500;color:var(--text-1);"
        "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
        ".al-time{font-size:11px;color:var(--text-2);display:flex;align-items:center;gap:6px;flex-wrap:wrap;}"
        ".al-tag{font-size:9px;font-weight:600;color:var(--accent);background:rgba(99,102,241,0.10);"
        "border:1px solid rgba(99,102,241,0.20);border-radius:4px;padding:1px 5px;}"
        ".al-dur{font-size:14px;font-weight:700;color:var(--accent);flex-shrink:0;font-variant-numeric:tabular-nums;}"
        ".al-empty{font-size:14px;color:var(--text-2);text-align:center;padding:32px 0;}"
        # Search
        ".al-search{width:100%;padding:12px 12px;font-size:14px;min-height:44px;font-family:inherit;"
        "background:var(--bg-s1);color:var(--text-1);border:1px solid var(--border);"
        "border-radius:10px;outline:none;margin-bottom:16px;}"
        ".al-search:focus{border-color:var(--accent);}"
        ".al-search::placeholder{color:var(--text-3);}"
        "</style></head><body>"
        # Header
        '<div class="al-header">'
        '<span class="al-title">Activity Log</span>'
        f'<span class="al-sync-info">{sync_text}</span>'
        '</div>'
        # Tab bar
        '<div class="al-tabs">'
        '<div class="al-tab active" id="tab-today" onclick="switchAlTab(\'today\')">Today</div>'
        '<div class="al-tab" id="tab-week" onclick="switchAlTab(\'week\')">Past 7 Days</div>'
        '</div>'
        # Today panel
        '<div class="al-panel active" id="panel-today">'
        f'{today_stats}'
        '<input class="al-search" type="text" placeholder="Search today..." '
        'oninput="filterEntries(this.value,\'panel-today\')">'
        f'<div class="al-days">{today_sections}</div>'
        '</div>'
        # Week panel
        '<div class="al-panel" id="panel-week">'
        f'{week_stats}'
        '<input class="al-search" type="text" placeholder="Search past 7 days..." '
        'oninput="filterEntries(this.value,\'panel-week\')">'
        f'<div class="al-days">{week_sections}</div>'
        '</div>'
        # JS
        "<script>"
        "function switchAlTab(tab){"
        "document.querySelectorAll('.al-tab').forEach(function(t){t.classList.remove('active')});"
        "document.querySelectorAll('.al-panel').forEach(function(p){p.classList.remove('active')});"
        "document.getElementById('tab-'+tab).classList.add('active');"
        "document.getElementById('panel-'+tab).classList.add('active');"
        "}"
        "function filterEntries(q,panelId){"
        "q=q.toLowerCase();"
        "var panel=document.getElementById(panelId);"
        "panel.querySelectorAll('.al-day').forEach(function(day){"
        "var entries=day.querySelectorAll('.al-entry');"
        "var anyVisible=false;"
        "entries.forEach(function(e){"
        "var text=e.textContent.toLowerCase();"
        "var show=!q||text.indexOf(q)!==-1;"
        "e.style.display=show?'':'none';"
        "if(show)anyVisible=true;"
        "});"
        "day.style.display=anyVisible?'':'none';"
        "});"
        "}"
        "</script>"
        "</body></html>"
    )
