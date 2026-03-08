"""ActionOS Focus tab — comprehensive Toggl time-tracking view."""
import json
from datetime import datetime, timezone


_DAILY_GOAL_SECS = 6 * 3600  # 6-hour goal
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
    """Convert UTC ISO string to Eastern local time string like '2:34 PM'."""
    try:
        from zoneinfo import ZoneInfo
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        eastern = dt.astimezone(ZoneInfo("America/New_York"))
        return eastern.strftime("%-I:%M %p")
    except Exception:
        return ""


_DILIGENT_PROJECTS = [
    "Scripture Study",
    "Scheduled Committed",
    "Scheduled Best Case",
    "Unscheduled Urgent",
    "Unscheduled Good Samaritan",
    "Life Group Meeting",
    "Life Group Prep",
]


def build_focus_html(
    toggl_local: dict,
    function_url: str = "",
    action_token: str = "",
    toggl_daily_total_secs: int = 0,
    diligent_work_secs: int = 0,
    committed_cal_secs: int = 0,
    toggl_entries: list | None = None,
    committed_events: list | None = None,
) -> str:
    """Build the Focus tab HTML from toggl_local state."""
    from zoneinfo import ZoneInfo
    _today_et = datetime.now(ZoneInfo("America/New_York")).date().isoformat()

    tl = toggl_local or {}

    # Only include sessions from today
    def _is_today(s: dict) -> bool:
        start = s.get("start_iso", "")
        if not start:
            return False
        try:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            return dt.astimezone(ZoneInfo("America/New_York")).date().isoformat() == _today_et
        except Exception:
            return False

    sessions = [s for s in (tl.get("sessions") or []) if _is_today(s)]
    # Only use completed_secs if toggl_local is for today
    completed_secs = (tl.get("completed_secs") or 0) if tl.get("date") == _today_et else 0
    active_iso = tl.get("active_start_iso")

    # Only treat active_iso as live if it's from today
    if active_iso:
        try:
            _astart = datetime.fromisoformat(active_iso.replace("Z", "+00:00"))
            if _astart.tzinfo is None:
                _astart = _astart.replace(tzinfo=timezone.utc)
            if _astart.astimezone(ZoneInfo("America/New_York")).date().isoformat() != _today_et:
                active_iso = None  # stale from a previous day — ignore
        except Exception:
            active_iso = None

    # Compute active elapsed (approximation — JS will do live updates)
    active_elapsed = 0
    if active_iso:
        try:
            start_dt = datetime.fromisoformat(active_iso)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            active_elapsed = min(
                max(0, int((datetime.now(timezone.utc) - start_dt).total_seconds())),
                28800,
            )
        except Exception:
            pass

    total_secs = completed_secs + active_elapsed

    # Dynamic goal = committed calendar time + Scripture Study / *Love* logged entries
    _scripture_love_secs = 0
    for te in (toggl_entries or []):
        _pn = te.get("project_name") or ""
        if _pn == "Scripture Study" or "love" in _pn.lower():
            _scripture_love_secs += te.get("duration_secs", 0)
    _dynamic_goal_secs = committed_cal_secs + _scripture_love_secs
    # Use dynamic goal if any committed/scripture/love data exists, otherwise fall back to 6h
    goal_secs = _dynamic_goal_secs if _dynamic_goal_secs > 0 else _DAILY_GOAL_SECS

    pct = min(100, round(total_secs / goal_secs * 100)) if goal_secs > 0 else 0
    remaining_secs = max(0, goal_secs - total_secs)
    goal_reached = total_secs >= goal_secs

    # Stats
    completed_sessions = [s for s in sessions if s.get("duration_secs") is not None]
    avg_secs = (
        sum(s["duration_secs"] for s in completed_sessions) // len(completed_sessions)
        if completed_sessions else 0
    )

    # Embed JSON for live JS updates
    sessions_json = json.dumps(sessions)
    active_iso_json = json.dumps(active_iso)

    # Build session rows (newest first)
    session_rows = ""
    _update_url = (function_url.rstrip("/") + "?action=toggl_update_entry_project") if function_url else ""
    for s in reversed(sessions):
        dur = s.get("duration_secs")
        is_active = dur is None and s.get("start_iso") == active_iso
        if dur is not None:
            dur_display = _fmt_secs(dur)
        elif is_active:
            dur_display = _fmt_secs(active_elapsed)
        else:
            try:
                _sd = datetime.fromisoformat(s.get("start_iso", "").replace("Z", "+00:00"))
                if _sd.tzinfo is None:
                    _sd = _sd.replace(tzinfo=timezone.utc)
                dur_display = _fmt_secs(min(max(0, int((datetime.now(timezone.utc) - _sd).total_seconds())), 28800))
            except Exception:
                dur_display = "?"
        start_display = _fmt_time(s.get("start_iso", ""))
        desc = s.get("description") or "Untitled"
        proj = s.get("project_name", "")
        entry_id = s.get("entry_id", "")
        start_iso = s.get("start_iso", "")
        active_class = " fsr-active" if is_active else ""
        active_badge = '<span class="fsr-live-badge">LIVE</span>' if is_active else ""
        proj_badge = (
            f'<span class="fsr-proj" onclick="event.stopPropagation();openProjPicker(this)" '
            f'data-entry-id="{entry_id}" data-start-iso="{start_iso}">'
            + (proj if proj else "Set project")
            + "</span>"
        )
        session_rows += (
            f'<div class="fsr{active_class}" data-start="{start_iso}" data-dur="{dur if dur is not None else ""}" data-active="{1 if is_active else 0}">'
            f'<div class="fsr-left">'
            f'<span class="fsr-desc">{desc}</span>'
            f'<span class="fsr-meta">{start_display}{active_badge}</span>'
            f'{proj_badge}'
            f"</div>"
            f'<span class="fsr-dur" id="fsr-dur-{sessions.index(s)}">{dur_display}</span>'
            f"</div>"
        )

    if not session_rows:
        session_rows = '<div class="fs-empty">No sessions tracked today. Start a timer from the Home tab.</div>'

    # Split Toggl API entries into diligent vs other
    _toggl_entries = toggl_entries or []
    _diligent_entries = []
    _other_entries = []
    for te in _toggl_entries:
        _pname = te.get("project_name") or ""
        if _pname in _DILIGENT_PROJECTS or "love" in _pname.lower():
            _diligent_entries.append(te)
        else:
            _other_entries.append(te)

    def _build_entry_rows(entries: list) -> str:
        rows = ""
        for te in reversed(entries):
            _te_dur = te.get("duration_secs", 0)
            _te_running = te.get("is_running", False)
            _te_dur_display = "LIVE" if _te_running else _fmt_secs(_te_dur)
            _te_start = _fmt_time(te.get("start", ""))
            _te_desc = te.get("description") or "Untitled"
            _te_proj = te.get("project_name") or ""
            _te_entry_id = te.get("entry_id", "")
            _te_start_iso = te.get("start", "")
            _te_active_class = " fsr-active" if _te_running else ""
            _te_proj_html = (
                f'<span class="fsr-proj" onclick="event.stopPropagation();openProjPicker(this)" '
                f'data-entry-id="{_te_entry_id}" data-start-iso="{_te_start_iso}">'
                + (_te_proj if _te_proj else "Set project")
                + "</span>"
            )
            _te_live_badge = '<span class="fsr-live-badge">LIVE</span>' if _te_running else ""
            rows += (
                f'<div class="fsr{_te_active_class}">'
                f'<div class="fsr-left">'
                f'<span class="fsr-desc">{_te_desc}</span>'
                f'<span class="fsr-meta">{_te_start}{_te_live_badge}</span>'
                f'{_te_proj_html}'
                f"</div>"
                f'<span class="fsr-dur">{_te_dur_display}</span>'
                f"</div>"
            )
        return rows

    diligent_entry_rows = _build_entry_rows(_diligent_entries)
    if not diligent_entry_rows:
        diligent_entry_rows = '<div class="fs-empty">No diligent work logged today.</div>'

    other_entry_rows = _build_entry_rows(_other_entries)
    if not other_entry_rows:
        other_entry_rows = '<div class="fs-empty">No other work logged today.</div>'

    # Build committed calendar event rows
    committed_rows = ""
    _cal_events = committed_events or []
    _filtered_events = []
    for ev in _cal_events:
        if ev.get("is_all_day"):
            continue
        _ev_start = ev.get("start", "")
        _ev_end = ev.get("end", "")
        if not _ev_start or not _ev_end:
            continue
        try:
            from zoneinfo import ZoneInfo as _ZI2
            _s_dt = datetime.fromisoformat(_ev_start.replace("Z", "+00:00"))
            if _s_dt.astimezone(_ZI2("America/New_York")).date().isoformat() != _today_et:
                continue
            _e_dt = datetime.fromisoformat(_ev_end.replace("Z", "+00:00"))
            _ev_dur = max(0, int((_e_dt - _s_dt).total_seconds()))
            _filtered_events.append({
                "summary": ev.get("summary") or ev.get("title") or "Untitled",
                "start": _ev_start,
                "duration_secs": _ev_dur,
            })
        except Exception:
            continue
    _filtered_events.sort(key=lambda e: e["start"])
    for ce in _filtered_events:
        _ce_start = _fmt_time(ce["start"])
        _ce_dur = _fmt_secs(ce["duration_secs"])
        _ce_desc = ce["summary"]
        committed_rows += (
            f'<div class="fsr fsr-cal">'
            f'<div class="fsr-left">'
            f'<span class="fsr-desc">{_ce_desc}</span>'
            f'<span class="fsr-meta">{_ce_start}</span>'
            f"</div>"
            f'<span class="fsr-dur fsr-dur-cal">{_ce_dur}</span>'
            f"</div>"
        )
    if not committed_rows:
        committed_rows = '<div class="fs-empty">No committed actions scheduled today.</div>'

    goal_text = "Goal reached!" if goal_reached else f"{_fmt_secs(remaining_secs)} to go"
    fill_color = "var(--ok)" if goal_reached else "var(--accent)"

    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Focus</title>"
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
        f"*{{box-sizing:border-box;margin:0;padding:0;}}"
        f"body{{font-family:{_FONT};background:var(--bg-base);color:var(--text-1);"
        "-webkit-font-smoothing:antialiased;padding:20px 16px 40px;max-width:520px;margin:0 auto;}"
        # Header
        ".fs-label{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;"
        "color:var(--text-2);margin-bottom:4px;}"
        # Big timer
        ".fs-hero{text-align:center;padding:24px 0 20px;}"
        ".fs-total{font-size:52px;font-weight:800;letter-spacing:-2px;line-height:1;"
        "color:var(--text-1);font-variant-numeric:tabular-nums;}"
        ".fs-goal-text{font-size:14px;color:var(--text-2);margin-top:6px;}"
        # Progress ring area — linear bar
        ".fs-bar-wrap{margin:0 0 24px;}"
        ".fs-bar-track{width:100%;height:8px;background:var(--bg-s2);border-radius:4px;overflow:hidden;}"
        f".fs-bar-fill{{height:100%;border-radius:4px;background:{fill_color};"
        "transition:width .6s ease;}"
        ".fs-bar-footer{display:flex;justify-content:space-between;margin-top:6px;font-size:12px;color:var(--text-2);}"
        # Stats row
        ".fs-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:24px;}"
        ".fs-stat{background:var(--bg-s1);border:1px solid var(--border);border-radius:10px;"
        "padding:12px;text-align:center;}"
        ".fs-stat-val{font-size:20px;font-weight:700;color:var(--text-1);}"
        ".fs-stat-lbl{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;"
        "color:var(--text-2);margin-top:3px;}"
        # Active timer card
        ".fs-active-card{background:var(--ok-bg);border:1px solid var(--ok-b);border-radius:12px;"
        "padding:14px 16px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center;}"
        ".fs-active-dot{width:8px;height:8px;border-radius:50%;background:var(--ok);"
        "animation:pulse 1.4s ease-in-out infinite;margin-right:8px;flex-shrink:0;}"
        "@keyframes pulse{0%,100%{opacity:1;}50%{opacity:.3;}}"
        ".fs-active-info{display:flex;align-items:center;flex:1;min-width:0;}"
        ".fs-active-desc{font-size:13px;font-weight:600;color:var(--text-1);"
        "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
        ".fs-active-elapsed{font-size:16px;font-weight:700;color:var(--ok);"
        "flex-shrink:0;font-variant-numeric:tabular-nums;}"
        # Sessions list
        ".fs-sessions-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;}"
        ".fs-sessions-count{font-size:12px;color:var(--text-2);}"
        ".fsr{display:flex;justify-content:space-between;align-items:center;"
        "padding:10px 12px;background:var(--bg-s1);border:1px solid var(--border);"
        "border-radius:10px;margin-bottom:6px;}"
        ".fsr-active{border-color:var(--ok-b);background:var(--ok-bg);}"
        ".fsr-left{display:flex;flex-direction:column;gap:3px;flex:1;min-width:0;margin-right:12px;}"
        ".fsr-desc{font-size:13px;font-weight:500;color:var(--text-1);"
        "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
        ".fsr-meta{font-size:11px;color:var(--text-2);display:flex;align-items:center;gap:6px;}"
        ".fsr-live-badge{font-size:9px;font-weight:700;color:var(--ok);"
        "background:var(--ok-bg);border:1px solid var(--ok-b);"
        "border-radius:4px;padding:1px 4px;letter-spacing:0.5px;}"
        ".fsr-dur{font-size:14px;font-weight:700;color:var(--accent);"
        "flex-shrink:0;font-variant-numeric:tabular-nums;}"
        ".fsr-active .fsr-dur{color:var(--ok);}"
        ".fsr-proj{display:inline-block;margin-top:3px;font-size:12px;font-weight:600;"
        "padding:10px 14px;min-height:44px;border-radius:4px;cursor:pointer;"
        "background:var(--bg-s2);border:1px solid var(--border);color:var(--text-2);"
        "transition:border-color .15s,color .15s;}"
        ".fsr-proj:hover{border-color:var(--accent);color:var(--accent);}"
        ".fs-empty{font-size:14px;color:var(--text-2);text-align:center;padding:32px 0;}"
".fsr-cal{border-left:3px solid var(--accent);}"
".fsr-dur-cal{color:var(--text-2);}"
".fsr-proj-ro{display:inline-block;margin-top:3px;font-size:12px;font-weight:600;"
"padding:2px 6px;border-radius:4px;background:var(--bg-s2);color:var(--text-2);}"
        "</style></head><body>"
        # Hero
        '<div class="fs-hero">'
        '<div class="fs-label">Today\'s Focus</div>'
        f'<div class="fs-total" id="fs-total">{_fmt_secs(total_secs)}</div>'
        f'<div class="fs-goal-text">{goal_text}</div>'
        "</div>"
        # Progress bar
        '<div class="fs-bar-wrap">'
        '<div class="fs-bar-track">'
        f'<div class="fs-bar-fill" id="fs-bar" style="width:{pct}%"></div>'
        "</div>"
        '<div class="fs-bar-footer">'
        "<span>0h</span>"
        f'<span id="fs-pct">{pct}% of {_fmt_secs(goal_secs)} goal</span>'
        f"<span>{_fmt_secs(goal_secs)}</span>"
        "</div>"
        "</div>"
        # Stats row — total tracked / committed / diligent work
        + (
            f'<div class="fs-stats">'
            f'<div class="fs-stat">'
            f'<div class="fs-stat-val">{_fmt_secs(toggl_daily_total_secs) if toggl_daily_total_secs else "—"}</div>'
            f'<div class="fs-stat-lbl">Total Tracked</div>'
            f"</div>"
            f'<div class="fs-stat">'
            f'<div class="fs-stat-val">{_fmt_secs(committed_cal_secs) if committed_cal_secs else "—"}</div>'
            f'<div class="fs-stat-lbl">Committed</div>'
            f"</div>"
            f'<div class="fs-stat">'
            f'<div class="fs-stat-val" id="stat-diligent">{_fmt_secs(diligent_work_secs) if diligent_work_secs else "—"}</div>'
            f'<div class="fs-stat-lbl">Diligent Work</div>'
            f"</div>"
            f"</div>"
        )
        # Active timer card (hidden if none)
        + (
            '<div class="fs-active-card" id="fs-active-card">'
            '<div class="fs-active-info">'
            '<div class="fs-active-dot"></div>'
            f'<div class="fs-active-desc">{sessions[-1]["description"] if sessions and sessions[-1].get("duration_secs") is None else ""}</div>'
            "</div>"
            f'<div class="fs-active-elapsed" id="fs-active-elapsed">{_fmt_secs(active_elapsed)}</div>'
            "</div>"
            if active_iso else
            '<div id="fs-active-card" style="display:none"></div>'
        )
        # Diligent Work (from Toggl API — diligent projects only)
        + '<div class="fs-sessions-header">'
        '<div class="fs-label">Diligent Work</div>'
        f'<div class="fs-sessions-count">{len(_diligent_entries)} today</div>'
        "</div>"
        + diligent_entry_rows
        # Other Work (from Toggl API — non-diligent projects)
        + '<div class="fs-sessions-header" style="margin-top:20px;">'
        '<div class="fs-label">Other Work</div>'
        f'<div class="fs-sessions-count">{len(_other_entries)} today</div>'
        "</div>"
        + other_entry_rows
        # Committed Actions (from Google Calendar)
        + '<div class="fs-sessions-header" style="margin-top:20px;">'
        '<div class="fs-label">Committed Actions</div>'
        f'<div class="fs-sessions-count">{len(_filtered_events)} scheduled</div>'
        "</div>"
        + committed_rows
        # JS for live updates
        + "<script>"
        f"var _tlSessions={sessions_json};"
        f"var _tlActiveIso={active_iso_json};"
        f"var _GOAL={goal_secs};"
        "function _fmtSecs(s){"
        "var h=Math.floor(s/3600),m=Math.floor((s%3600)/60);"
        "return h>0?h+'h '+String(m).padStart(2,'0')+'m':m+'m';}"
        "function _tick(){"
        "if(!_tlActiveIso)return;"
        "var elapsed=Math.max(0,Math.floor((Date.now()-new Date(_tlActiveIso).getTime())/1000));"
        "elapsed=Math.min(elapsed,28800);"
        # Update active card
        "var ae=document.getElementById('fs-active-elapsed');"
        "if(ae)ae.textContent=_fmtSecs(elapsed);"
        # Update total
        "var completedSecs=(_tlSessions||[]).filter(function(s){return s.duration_secs!==null&&s.duration_secs!==undefined;}).reduce(function(a,s){return a+s.duration_secs;},0);"
        "var total=completedSecs+elapsed;"
        "var totalEl=document.getElementById('fs-total');if(totalEl)totalEl.textContent=_fmtSecs(total);"
        # Update bar
        "var pct=Math.min(100,Math.round(total/_GOAL*100));"
        "var bar=document.getElementById('fs-bar');if(bar)bar.style.width=pct+'%';"
        "var pctEl=document.getElementById('fs-pct');if(pctEl){var gh=Math.floor(_GOAL/3600),gm=Math.floor((_GOAL%3600)/60);var gl=gh>0?gh+'h '+String(gm).padStart(2,'0')+'m':gm+'m';pctEl.textContent=pct+'% of '+gl+' goal';}"
        # Update remaining
        "var rem=document.getElementById('stat-remain');"
        "if(rem){var r=Math.max(0,_GOAL-total);rem.textContent=r===0?'\\u2713':_fmtSecs(r);}"
        # Update active session row duration
        "var rows=document.querySelectorAll('.fsr[data-active=\"1\"] .fsr-dur');"
        "rows.forEach(function(el){el.textContent=_fmtSecs(elapsed);});"
        "}"
        "if(_tlActiveIso){setInterval(_tick,1000);_tick();}"
        # Project picker
        f"var _updateUrl='{_update_url}';"
        "var _projList=["
        + ",".join(f"'{p}'" for p in _DILIGENT_PROJECTS)
        + "];"
        "function openProjPicker(badge){"
        "var existing=document.getElementById('focus-proj-modal');"
        "if(existing)existing.remove();"
        "var entryId=badge.getAttribute('data-entry-id')||'';"
        "var startIso=badge.getAttribute('data-start-iso')||'';"
        "var overlay=document.createElement('div');"
        "overlay.id='focus-proj-modal';"
        "overlay.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9999;display:flex;align-items:center;justify-content:center;';"
        "var box=document.createElement('div');"
        "box.style.cssText='background:var(--bg-s1);border:1px solid var(--border);border-radius:10px;padding:20px 24px;min-width:240px;max-width:320px;';"
        "var title=document.createElement('p');"
        "title.textContent='Set Toggl project';"
        "title.style.cssText='margin:0 0 14px;font-weight:600;font-size:.95rem;';"
        "box.appendChild(title);"
        "_projList.forEach(function(name){"
        "var b=document.createElement('button');"
        "b.textContent=name;"
        "b.style.cssText='display:block;width:100%;text-align:left;padding:8px 10px;margin-bottom:6px;"
        "background:var(--bg-s2);border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:.88rem;';"
        "b.onclick=function(){"
        "overlay.remove();"
        "badge.textContent='Saving\u2026';"
        "fetch(_updateUrl,{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({project_name:name,entry_id:entryId,start_iso:startIso})})"
        ".then(function(r){return r.json();})"
        ".then(function(d){badge.textContent=d.ok?name:'Error';});"
        "};"
        "box.appendChild(b);"
        "});"
        "overlay.appendChild(box);"
        "overlay.onclick=function(e){if(e.target===overlay)overlay.remove();};"
        "document.body.appendChild(overlay);"
        "}"
        "</script>"
        "</body></html>"
    )
