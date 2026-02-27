"""HTML builder for the Calendar tab in the gmail-email-actions dashboard.

Renders a single scrollable pane of event cards spanning the full workspace,
with reviewed state, Todoist buttons, and badge count postMessage support.
"""

import html
import logging
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

_EASTERN = ZoneInfo("America/New_York")

logger = logging.getLogger(__name__)

_FONT = (
    "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,"
    "'Segoe UI',Roboto,sans-serif"
)

_CAL_TYPE_LABELS = {
    "family": "Family",
    "medical": "Medical",
    "birthdays": "Birthday/Anniversary",
}

_CAL_TYPE_COLORS = {
    "family": "#818cf8",
    "medical": "#22c55e",
    "birthdays": "#eab308",
}


def _is_event_reviewed(event_id: str, state: dict) -> bool:
    ts = state.get("reviews", {}).get(event_id)
    if not ts:
        return False
    try:
        reviewed_at = datetime.fromisoformat(ts)
        if reviewed_at.tzinfo is None:
            reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - reviewed_at).days < 7
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
        return max(0, 7 - (datetime.now(timezone.utc) - reviewed_at).days)
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
                # Google Calendar all-day end date is exclusive (next day).
                # Only show a range if the event actually spans 2+ days.
                dt_end = datetime.strptime(end[:10], "%Y-%m-%d")
                actual_end = dt_end - timedelta(days=1)
                if actual_end > dt:
                    label += " \u2013 " + actual_end.strftime("%a %b %-d")
            return label + " (all day)"
        else:
            # Convert to Eastern Time for display
            dt_start = datetime.fromisoformat(start).astimezone(_EASTERN)
            dt_end = datetime.fromisoformat(end).astimezone(_EASTERN) if end else None
            date_label = dt_start.strftime("%a %b %-d")
            time_label = dt_start.strftime("%-I:%M %p")
            if dt_end:
                time_label += " \u2013 " + dt_end.strftime("%-I:%M %p")
            return f"{date_label} \u00b7 {time_label}"
    except Exception:
        return start


def _build_project_options_html(projects: List[Dict[str, Any]]) -> str:
    options = '<option value="">Move to project\u2026</option>'
    for p in projects:
        pid = html.escape(str(p.get("id", "")))
        name = html.escape(str(p.get("name", "")))
        options += f'<option value="{pid}">{name}</option>'
    return options


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
    description = html.escape(event.get("description", ""))
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
            f'<button id="rev-{idx}" '
            'style="background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-b);padding:5px 14px;'
            'border-radius:6px;font-size:12px;font-weight:600;cursor:default;font-family:inherit;">'
            f"\u2713 Reviewed ({days_remaining}d)</button>"
        )
        card_border_left = "border-left:3px solid var(--ok);"
        card_dim = "opacity:0.6;"
    else:
        rev_url = (
            function_url.rstrip("/")
            + "?action=calendar_reviewed"
            + "&event_id="
            + eid_enc
            + "&token="
            + action_token
        )
        review_btn = (
            f'<button id="rev-{idx}" '
            f"onclick=\"doReview(this,'{eid_safe}','{rev_url}')\" "
            'style="background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn-b);padding:5px 14px;'
            'border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;">'
            "Review \u25b6</button>"
        )
        card_border_left = "border-left:3px solid var(--warn);"
        card_dim = ""

    todoist_url_base = (
        function_url.rstrip("/")
        + "?action=calendar_create_todoist"
        + "&token="
        + action_token
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
        + "&token="
        + action_token
        + "&event_id="
        + eid_enc
        + "&event_title="
        + title_enc
        + "&event_date="
        + date_enc
        + "&event_location="
        + loc_enc
    )

    location_html = ""
    if location:
        location_html = (
            f'<div style="font-size:13px;color:var(--text-2);margin-bottom:4px;">'
            f"\U0001f4cd {location}</div>"
        )

    desc_html = ""
    if description:
        # Truncate long descriptions
        short = description[:200] + ("\u2026" if len(description) > 200 else "")
        desc_html = (
            f'<div style="font-size:13px;color:var(--text-2);line-height:1.5;'
            f"margin-top:8px;padding:8px 10px;background:var(--bg-s2);border-radius:6px;"
            f'white-space:pre-wrap;max-height:80px;overflow:hidden;">{short}</div>'
        )

    gcal_html = ""
    if html_link:
        safe_link = html.escape(html_link)
        gcal_html = (
            f'<a href="{safe_link}" target="_blank" rel="noopener" '
            f'style="color:var(--accent-l);font-size:12px;text-decoration:none;font-weight:500;">'
            f"Google Calendar \u2197</a>"
        )

    return (
        f'<div class="cal-card" id="card-{idx}" style="background:var(--bg-s1);border-radius:8px;'
        f"border:1px solid var(--border);padding:14px 16px;margin-bottom:10px;"
        f'{card_border_left}{card_dim}">'
        # Row 1: title + cal badge
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;'
        f'margin-bottom:4px;">'
        f'<div style="font-size:15px;font-weight:600;color:var(--text-1);line-height:1.35;'
        f'flex:1;min-width:0;">{title}</div>'
        f'<span style="font-size:11px;font-weight:700;color:#fff;background:{cal_color};'
        f'padding:2px 8px;border-radius:8px;white-space:nowrap;margin-left:10px;flex-shrink:0;">'
        f"{cal_label}</span>"
        f"</div>"
        # Row 2: date/time
        f'<div style="font-size:13px;color:var(--text-2);margin-bottom:4px;">{date_range}</div>'
        # Row 3: location
        + location_html
        # Row 4: description snippet
        + desc_html
        # Row 5: Todoist controls
        + f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:10px;">'
        f'<select id="proj-{idx}" class="ctl">{project_options_html}</select>'
        f'<input type="date" id="date-{idx}" class="ctl" />'
        f'<select id="pri-{idx}" class="ctl">'
        f'<option value="">Priority</option>'
        f'<option value="4">P1 \U0001f534</option>'
        f'<option value="3">P2 \U0001f7e0</option>'
        f'<option value="2">P3 \U0001f7e1</option>'
        f'<option value="1">P4</option>'
        f"</select>"
        f'<button id="tod-{idx}" '
        f"onclick=\"doTodoist(this,{idx},'{todoist_url_base}')\" "
        f'style="background:var(--accent-bg);color:var(--accent-l);border:1px solid var(--accent-b);padding:5px 14px;'
        f'border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;">'
        f"Add to Todoist</button>"
        f'<button id="cmt-{idx}" '
        f"onclick=\"doCommit(this,{idx},'{commit_url_base}')\" "
        f'style="background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn-b);padding:5px 14px;'
        f'border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;">'
        f"Commit</button>"
        f"</div>"
        # Row 6: Review button + GCal link
        + f'<div style="display:flex;gap:12px;align-items:center;margin-top:10px;">'
        f"{review_btn}"
        f"{gcal_html}"
        f"</div>"
        f"</div>"
    )


def build_calendar_html(
    events: List[Dict[str, Any]],
    reviewed_state: dict,
    function_url: str,
    action_token: str,
    projects: List[Dict[str, Any]],
    embed: bool = False,
) -> str:
    """Build the full single-pane HTML page for the Calendar tab."""
    project_options_html = _build_project_options_html(projects)

    unreviewed_count = sum(
        1 for ev in events if not _is_event_reviewed(ev.get("id", ""), reviewed_state)
    )

    cards_html = ""
    for idx, event in enumerate(events):
        eid = event.get("id", "")
        reviewed = _is_event_reviewed(eid, reviewed_state)
        days_remaining = _days_until_reviewed_reset(eid, reviewed_state)
        cards_html += _build_event_card(
            event,
            reviewed,
            days_remaining,
            function_url,
            action_token,
            project_options_html,
            idx,
        )

    if not cards_html:
        cards_html = (
            '<div style="text-align:center;color:var(--text-2);padding:40px 20px;">'
            "<p>No upcoming events in the next 90 days.</p></div>"
        )

    embed_css = ""
    page_height = "calc(100vh - 56px)"
    if embed:
        embed_css = ".top-bar{display:none;}"
        page_height = "100vh"

    post_message_js = ""
    if embed:
        post_message_js = (
            "var calendarCount=" + str(unreviewed_count) + ";"
            "function postCount(){"
            "window.parent.postMessage({type:'count',source:'calendar',count:calendarCount},'*');"
            "}"
            "postCount();"
        )

    count_label = f"{len(events)} event{'s' if len(events) != 1 else ''}"

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
        "--bg-base:#0e0e10;--bg-s0:#161618;--bg-s1:#1c1c1f;--bg-s2:#222225;"
        "--text-1:#ececef;--text-2:#8b8b93;--text-3:#56565e;"
        "--border:rgba(255,255,255,0.06);--border-h:rgba(255,255,255,0.10);"
        "--accent:#6366f1;--accent-l:#818cf8;"
        "--accent-bg:rgba(99,102,241,0.10);--accent-b:rgba(99,102,241,0.20);"
        "--accent-hbg:rgba(99,102,241,0.08);"
        "--ok:#22c55e;--ok-bg:rgba(34,197,94,0.10);--ok-b:rgba(34,197,94,0.20);"
        "--warn:#eab308;--warn-bg:rgba(234,179,8,0.10);--warn-b:rgba(234,179,8,0.20);"
        "--err:#ef4444;--err-bg:rgba(239,68,68,0.10);--err-b:rgba(239,68,68,0.20);"
        "--purple:#a78bfa;--purple-bg:rgba(167,139,250,0.10);--purple-b:rgba(167,139,250,0.20);"
        "--scrollbar:rgba(255,255,255,0.10);color-scheme:dark;}"
        "@media(prefers-color-scheme:light){:root{"
        "--bg-base:#f5f5f5;--bg-s0:#fff;--bg-s1:#fff;--bg-s2:#f8f9fa;"
        "--text-1:#202124;--text-2:#5f6368;--text-3:#80868b;"
        "--border:rgba(0,0,0,0.08);--border-h:rgba(0,0,0,0.15);"
        "--accent:#6366f1;--accent-l:#4f46e5;"
        "--accent-bg:rgba(99,102,241,0.08);--accent-b:rgba(99,102,241,0.15);"
        "--accent-hbg:rgba(99,102,241,0.06);"
        "--ok:#188038;--ok-bg:#e6f4ea;--ok-b:rgba(24,128,56,0.20);"
        "--warn:#e37400;--warn-bg:#fef7e0;--warn-b:rgba(227,116,0,0.20);"
        "--err:#d93025;--err-bg:#fce8e6;--err-b:rgba(217,48,37,0.20);"
        "--purple:#7c4dff;--purple-bg:#ede7f6;--purple-b:rgba(124,77,255,0.20);"
        "--scrollbar:rgba(0,0,0,0.12);color-scheme:light;}}"
        "*{box-sizing:border-box;}"
        "body{font-family:"
        + _FONT
        + ";background:var(--bg-base);color:var(--text-1);margin:0;padding:0;"
        "-webkit-font-smoothing:antialiased;}"
        ".top-bar{background:var(--bg-s0);border-bottom:1px solid var(--border);padding:18px 20px;display:flex;align-items:center;gap:12px;}"  # noqa: E501
        + embed_css
        + ".scroll-area{height:"
        + page_height
        + ";overflow-y:auto;padding:0;background:var(--bg-s0);}"
        ".ctl{font-family:inherit;font-size:12px;padding:5px 8px;border:1px solid var(--border);border-radius:6px;"
        "background:var(--bg-s2);color:var(--text-1);cursor:pointer;}"
        "::-webkit-scrollbar{width:6px;}"
        "::-webkit-scrollbar-track{background:transparent;}"
        "::-webkit-scrollbar-thumb{background:var(--scrollbar);border-radius:3px;}"
        "</style></head><body>"
        # Top bar (hidden in embed)
        '<div class="top-bar">'
        '<span style="color:var(--text-1);font-size:17px;font-weight:600;letter-spacing:-0.2px;">'
        "\U0001f4c5 Calendar</span>"
        '<button onclick="location.reload()" '
        'style="margin-left:auto;background:var(--border);border:1px solid var(--border);color:var(--text-1);'
        'font-size:13px;font-weight:600;padding:6px 14px;border-radius:6px;cursor:pointer;">'
        "&#8635; Refresh</button></div>"
        # Scrollable content
        '<div class="scroll-area">'
        '<div style="max-width:700px;margin:0 auto;padding:20px 24px;">'
        f'<div style="font-size:13px;color:var(--text-2);margin:0 0 12px;">'
        f'<span id="item-count">{count_label}</span>'
        f" &middot; Next 90 days &middot; "
        f'<span id="unrev-count">{unreviewed_count}</span> unreviewed</div>'
        '<div style="margin-top:14px;margin-bottom:16px;border-bottom:2px solid var(--accent);"></div>'
        + cards_html
        + "</div></div>"
        # JavaScript
        "<script>"
        "var _cs=getComputedStyle(document.documentElement);function cv(n){return _cs.getPropertyValue(n).trim();}"
        + post_message_js
        + "function doReview(btn,eid,url){"
        "btn.style.background=cv('--border');btn.style.pointerEvents='none';btn.innerHTML='Reviewing\\u2026';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){"
        "btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');btn.innerHTML='\\u2713 Reviewed (7d)';"
        "btn.style.cursor='default';"
        "var card=btn.closest('.cal-card');"
        "if(card){card.style.opacity='0.6';card.style.borderLeftColor=cv('--ok');}"
        "if(typeof calendarCount!=='undefined'){calendarCount=Math.max(0,calendarCount-1);"
        "if(typeof postCount==='function'){postCount();}}"
        "var el=document.getElementById('unrev-count');"
        "if(el&&typeof calendarCount!=='undefined'){el.textContent=calendarCount;}"
        "}else{"
        "btn.style.background=cv('--warn-bg');btn.style.color=cv('--warn');btn.style.pointerEvents='auto';btn.innerHTML='Review \\u25b6';"  # noqa: E501
        "}"
        "}).catch(function(){"
        "btn.style.background=cv('--warn-bg');btn.style.color=cv('--warn');btn.style.pointerEvents='auto';btn.innerHTML='Review \\u25b6';"  # noqa: E501
        "});}"
        "function doTodoist(btn,idx,baseUrl){"
        "var projEl=document.getElementById('proj-'+idx);"
        "var dateEl=document.getElementById('date-'+idx);"
        "var priEl=document.getElementById('pri-'+idx);"
        "var pid=projEl?projEl.value:'';"
        "if(!pid){alert('Please select a project first.');return;}"
        "btn.style.background=cv('--border');btn.style.pointerEvents='none';btn.innerHTML='Adding\\u2026';"
        "var url=baseUrl;"
        "if(pid){url+='&project_id='+encodeURIComponent(pid);}"
        "if(dateEl&&dateEl.value){url+='&due_date='+encodeURIComponent(dateEl.value);}"
        "if(priEl&&priEl.value){url+='&priority='+encodeURIComponent(priEl.value);}"
        "fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');btn.innerHTML='\\u2713 Added';"
        "setTimeout(function(){btn.style.background=cv('--accent-bg');btn.style.color=cv('--accent-l');btn.innerHTML='Add to Todoist';"  # noqa: E501
        "btn.style.pointerEvents='auto';},2000);}"
        "else{btn.style.background=cv('--err-bg');btn.style.color=cv('--err');btn.innerHTML='Failed \\u2013 retry';"
        "btn.style.pointerEvents='auto';"
        "setTimeout(function(){btn.style.background=cv('--accent-bg');btn.style.color=cv('--accent-l');btn.innerHTML='Add to Todoist';},2000);}"  # noqa: E501
        "}).catch(function(){btn.style.background=cv('--err-bg');btn.style.color=cv('--err');btn.innerHTML='Failed \\u2013 retry';"  # noqa: E501
        "btn.style.pointerEvents='auto';"
        "setTimeout(function(){btn.style.background=cv('--accent-bg');btn.style.color=cv('--accent-l');btn.innerHTML='Add to Todoist';},2000);});"  # noqa: E501
        "}"
        "function doCommit(btn,idx,baseUrl){"
        "btn.style.background=cv('--border');btn.style.pointerEvents='none';btn.innerHTML='Committing\\u2026';"
        "var url=baseUrl;"
        "fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');btn.innerHTML='\\u2713 Committed';"
        "btn.style.cursor='default';"
        "var revBtn=document.getElementById('rev-'+idx);"
        "if(revBtn&&revBtn.innerHTML.indexOf('Reviewed')===-1){revBtn.click();}}"
        "else{btn.style.background=cv('--warn-bg');btn.style.color=cv('--warn');btn.innerHTML='Failed \\u2013 retry';"
        "btn.style.pointerEvents='auto';"
        "setTimeout(function(){btn.style.background=cv('--warn-bg');btn.style.color=cv('--warn');btn.innerHTML='Commit';},2000);}"  # noqa: E501
        "}).catch(function(){btn.style.background=cv('--warn-bg');btn.style.color=cv('--warn');btn.innerHTML='Failed \\u2013 retry';"  # noqa: E501
        "btn.style.pointerEvents='auto';"
        "setTimeout(function(){btn.style.background=cv('--warn-bg');btn.style.color=cv('--warn');btn.innerHTML='Commit';},2000);});"  # noqa: E501
        "}"
        "</script>"
        "</body></html>"
    )
