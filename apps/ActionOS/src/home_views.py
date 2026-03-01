"""HTML builder for the Home tab in the ActionOS dashboard.

Renders a single-page aggregated view of 8 action item sections:
commit tasks, best-case tasks, calendar events, P1 tasks, starred emails,
unread emails, follow-up emails, and inbox tasks. Each section is a
collapsible accordion with review-state tracking.
"""

import html
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

_EASTERN = ZoneInfo("America/New_York")

# Priority display: API value -> (label, color)
PRIORITY_MAP = {
    4: ("P1", "#ef4444"),
    3: ("P2", "#eab308"),
    2: ("P3", "#818cf8"),
    1: ("P4", "#56565e"),
}

_FONT = (
    "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,"
    "'Segoe UI',Roboto,sans-serif"
)

# Section display config: key -> (label, left-border color, cycle_days)
_SECTION_CONFIG = {
    "commit":   ("@Commit",    "#6366f1", 1),
    "bestcase": ("Best Case",  "#a78bfa", 1),
    "calendar": ("Calendar",   "#eab308", 7),
    "p1":       ("P1",         "#ef4444", 7),
    "starred":  ("Starred",    "#eab308", 1),
    "unread":   ("Unread",     "#8e8e93", 0),
    "followup": ("Follow-up",  "#8e8e93", 0),
    "inbox":    ("Inbox",      "#22c55e", 1),
}

_SECTION_ORDER = [
    "commit", "bestcase", "calendar", "p1",
    "starred", "unread", "followup", "inbox",
]


# ---------------------------------------------------------------------------
# Review-state helpers
# ---------------------------------------------------------------------------

def _is_home_item_reviewed(item_id: str, section: str, state: dict, cycle_days: int) -> bool:
    """Return True if item_id has been reviewed within cycle_days."""
    if cycle_days <= 0:
        return False
    ts = state.get(section, {}).get(item_id)
    if not ts:
        return False
    try:
        reviewed_at = datetime.fromisoformat(ts)
        if reviewed_at.tzinfo is None:
            reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
        elapsed_days = (datetime.now(timezone.utc) - reviewed_at).total_seconds() / 86400
        return elapsed_days < cycle_days
    except Exception:
        return False


def _time_until_review_reset(item_id: str, section: str, state: dict, cycle_days: int) -> str:
    """Return a human-readable string for when the review resets, e.g. '18h' or '5d'."""
    if cycle_days <= 0:
        return ""
    ts = state.get(section, {}).get(item_id)
    if not ts:
        return ""
    try:
        reviewed_at = datetime.fromisoformat(ts)
        if reviewed_at.tzinfo is None:
            reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
        elapsed_seconds = (datetime.now(timezone.utc) - reviewed_at).total_seconds()
        remaining_seconds = max(0, cycle_days * 86400 - elapsed_seconds)
        remaining_hours = remaining_seconds / 3600
        if remaining_hours >= 24:
            return f"{int(remaining_hours // 24)}d"
        return f"{int(remaining_hours)}h"
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _relative_age(added_at: str) -> str:
    """Return a short relative age string like '3d' or '2h' from an ISO timestamp."""
    if not added_at:
        return ""
    try:
        created = datetime.fromisoformat(added_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - created
        days = delta.days
        if days > 0:
            return f"{days}d"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}h"
        minutes = delta.seconds // 60
        return f"{minutes}m"
    except Exception:
        return ""


def _due_date_display(due_date_str: str):
    """Return (text, color) for a due date string 'YYYY-MM-DD'."""
    if not due_date_str:
        return ("no date", "#56565e")
    try:
        due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        diff = (due - today).days
        if diff < 0:
            return ("overdue", "#ef4444")
        elif diff == 0:
            return ("due today", "#22c55e")
        elif diff == 1:
            return ("due tomorrow", "#818cf8")
        else:
            return ("due " + due.strftime("%b %-d"), "#8b8b93")
    except Exception:
        return (due_date_str, "#8b8b93")


_CC_LABEL = "Claude"


def _build_projects_by_id(projects: List[Dict[str, Any]]) -> Dict[str, str]:
    return {str(p.get("id", "")): p.get("name", "Unknown") for p in projects}


def _build_project_options_html(projects_by_id: Dict[str, str], current_project_id: str = "") -> str:
    opts = '<option value="" disabled selected>Move to...</option>'
    for pid, pname in sorted(projects_by_id.items(), key=lambda x: x[1].lower()):
        disabled = " disabled" if pid == current_project_id else ""
        opts += f'<option value="{html.escape(pid)}"{disabled}>{html.escape(pname)}</option>'
    return opts


def _extract_gmail_link(description: str) -> str:
    match = re.search(
        r"\[Open in Gmail\]\((https://mail\.google\.com[^\)]+)\)", description
    )
    return match.group(1) if match else ""


def _extract_msg_id(description: str) -> str:
    match = re.search(r"\U0001f194 \*\*Msg ID:\*\*\s*(\S+)", description)
    return match.group(1).strip() if match else ""


def _is_upcoming_timed_event(event: Dict[str, Any]) -> bool:
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


# ---------------------------------------------------------------------------
# Card builders
# ---------------------------------------------------------------------------

def _build_task_card(
    task: Dict[str, Any],
    section: str,
    reviewed: bool,
    time_remaining: str,
    function_url: str,
    projects_by_id: Dict[str, str],
    idx: int,
    email_actions_url: str = "",
    email_actions_token: str = "",
) -> str:
    """Build a task card with full action buttons for Home view."""
    task_id = html.escape(str(task.get("id", "")))
    title = html.escape(task.get("content", "(no title)"))
    raw_content = task.get("content", "(no title)")
    description = task.get("description", "")
    priority = task.get("priority", 1)
    project_id = str(task.get("project_id", ""))
    labels = task.get("labels", [])
    added_at = task.get("added_at", "") or task.get("created_at", "")
    age = _relative_age(added_at)

    p_label, p_color = PRIORITY_MAP.get(priority, ("P4", "#56565e"))
    project_name = html.escape(projects_by_id.get(project_id, ""))

    due_obj = task.get("due")
    due_date = (due_obj.get("date", "") or "")[:10] if due_obj else ""
    due_text, due_color = _due_date_display(due_date)

    # Priority badge
    priority_badge = ""
    if priority > 1:
        priority_badge = (
            f'<span class="pri-badge" style="background:{p_color}22;'
            f'color:{p_color};border:1px solid {p_color}44;">{p_label}</span>'
        )

    # Meta line
    meta_parts = []
    if age:
        meta_parts.append(age)
    if project_name:
        meta_parts.append(project_name)
    meta_parts.append(
        f'<span style="color:{due_color};font-weight:500;">{html.escape(due_text)}</span>'
    )
    meta_line = " &middot; ".join(meta_parts)

    # Review button
    section_safe = html.escape(section)
    if reviewed:
        review_btn = (
            f'<button class="review-btn reviewed" style="cursor:default;" '
            f'onclick="event.stopPropagation()">'
            f"\u2713 Reviewed ({time_remaining})</button>"
        )
    else:
        review_btn = (
            f'<button class="review-btn" '
            f"onclick=\"event.stopPropagation();doHomeReview(this,'{section_safe}','{task_id}',{idx})\">"
            "Review</button>"
        )

    # Move dropdown
    _move_icon = (
        '<svg class="move-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/>'
        '<line x1="8" y1="18" x2="21" y2="18"/>'
        '<line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/>'
        '<line x1="3" y1="18" x2="3.01" y2="18"/></svg>'
    )
    move_opts = _build_project_options_html(projects_by_id, project_id)
    move_select = (
        f'<div class="move-pill">'
        f'{_move_icon}'
        f'<select class="move-pill-select" '
        f"onclick=\"event.stopPropagation()\" "
        f"onchange=\"event.stopPropagation();doMove('{task_id}',this.value,this)\">"
        f'{move_opts}</select></div>'
    )

    # Priority dropdown
    priority_options = ""
    for pval in [4, 3, 2, 1]:
        pl, _ = PRIORITY_MAP[pval]
        sel = " selected" if pval == priority else ""
        priority_options += f'<option value="{pval}"{sel}>{pl}</option>'
    priority_select = (
        f'<select class="action-select" '
        f'onclick="event.stopPropagation()" '
        f"onchange=\"event.stopPropagation();doSetPriority('{task_id}',this.value,this)\">"
        f'{priority_options}</select>'
    )

    # Due date input
    _date_icon = (
        '<svg class="date-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="3" width="18" height="18" rx="3"/>'
        '<line x1="3" y1="9" x2="21" y2="9"/>'
        '<circle cx="12" cy="15.5" r="1.2" fill="currentColor" stroke="none"/></svg>'
    )
    has_date = bool(due_date)
    icon_display = ' style="display:none"' if has_date else ""
    input_display = "" if has_date else ' style="display:none"'
    due_date_input = (
        f"<div class=\"date-pill\" onclick=\"event.stopPropagation();var i=this.querySelector('input');var w=this.querySelector('.date-icon-wrap');var l=this.querySelector('.date-label');i.style.display='';if(w)w.style.display='none';if(l)l.style.display='none';i.showPicker?i.showPicker():i.focus()\">"
        f'<span class="date-icon-wrap"{icon_display}>{_date_icon}</span>'
        f'<span class="date-label"{icon_display}>Date</span>'
        f'<input type="date" class="date-pill-input" value="{html.escape(due_date)}" '
        f'{input_display} '
        f'onclick="event.stopPropagation()" '
        f"onchange=\"event.stopPropagation();doSetDueDate('{task_id}',this.value,this)\">"
        f"</div>"
    )

    # Complete button
    complete_btn = (
        f'<button class="complete-btn" '
        f"onclick=\"event.stopPropagation();doComplete('{task_id}',this)\">"
        "Complete</button>"
    )

    # Context-aware Commit/Best Case buttons
    is_committed = "Commit" in labels
    is_bestcase = "Best Case" in labels

    if section == "commit":
        commit_btn = (
            f'<button class="commit-btn remove" '
            f"onclick=\"event.stopPropagation();doRemoveCommit('{task_id}',this)\">"
            "Remove Commit</button>"
        )
    elif is_committed:
        commit_btn = (
            '<button class="commit-btn committed" disabled>'
            "\u2713 Committed</button>"
        )
    else:
        commit_btn = (
            f'<button class="commit-btn" '
            f"onclick=\"event.stopPropagation();doCommitLabel('{task_id}',this)\">"
            "Commit</button>"
        )

    if section == "bestcase":
        bestcase_btn = (
            f'<button class="bestcase-btn remove" '
            f"onclick=\"event.stopPropagation();doRemoveBestCase('{task_id}',this)\">"
            "Remove Best Case</button>"
        )
    elif is_bestcase:
        bestcase_btn = (
            f'<button class="bestcase-btn remove" '
            f"onclick=\"event.stopPropagation();doRemoveBestCase('{task_id}',this)\">"
            "\u2713 Best Case \u2715</button>"
        )
    else:
        bestcase_btn = (
            f'<button class="bestcase-btn" '
            f"onclick=\"event.stopPropagation();doBestCaseLabel('{task_id}',this)\">"
            "Best Case</button>"
        )

    # CC icon button
    safe_content = title.replace("'", "\\'")
    cc_btn = (
        f'<button class="assign-cc-btn" title="Assign CC" '
        f"onclick=\"event.stopPropagation();doCopyCC('{task_id}','{safe_content}',this)\">"
        + _CC_LABEL
        + "</button>"
    )

    # Data attributes for detail pane
    gmail_link = _extract_gmail_link(description)
    msg_id_field = _extract_msg_id(description)
    data_open_url = ""
    if gmail_link and email_actions_url and email_actions_token:
        thread_id = gmail_link.split("#inbox/")[-1] if "#inbox/" in gmail_link else ""
        lookup_id = msg_id_field or thread_id
        if lookup_id:
            data_open_url = (
                email_actions_url.rstrip("/")
                + "?action=open&msg_id=" + lookup_id
                + ("&thread_id=" + thread_id if thread_id else "")
                + "&token=" + email_actions_token
            )

    labels_str = ",".join(labels) if labels else ""
    data_attrs = (
        f' data-task-id="{task_id}"'
        f' data-content="{title}"'
        f' data-description="{html.escape(description)}"'
        f' data-project-id="{html.escape(project_id)}"'
        f' data-priority="{priority}"'
        f' data-priority-label="{p_label}"'
        f' data-priority-color="{p_color}"'
        f' data-due-date="{html.escape(due_date)}"'
        f' data-due-text="{html.escape(due_text)}"'
        f' data-due-color="{html.escape(due_color)}"'
        f' data-labels="{html.escape(labels_str)}"'
        f' data-project-name="{project_name}"'
        f' data-section="{html.escape(section)}"'
    )
    if data_open_url:
        data_attrs += f' data-open-url="{html.escape(data_open_url)}"'

    card_class = "task-card reviewed-card" if reviewed else "task-card"
    opacity = ' style="opacity:0.65;"' if reviewed else ""

    return (
        f'<div class="{card_class}" id="hcard-{idx}"{opacity}{data_attrs}'
        f' onclick="openHomeDetail(this)">'
        f'<div class="card-row">'
        f'<div class="card-content">'
        f'<div class="task-title">{title}{priority_badge}</div>'
        f'<div class="task-meta">{meta_line}</div>'
        f'<div class="task-actions">'
        f'{review_btn}{move_select}{priority_select}{due_date_input}'
        f'{complete_btn}{commit_btn}{bestcase_btn}{cc_btn}'
        f'</div>'
        f"</div></div>"
        f"</div>"
    )


def _build_email_card(
    email: Dict[str, Any],
    section: str,
    reviewed: bool,
    time_remaining: str,
    function_url: str,
    idx: int,
    email_actions_url: str = "",
    email_actions_token: str = "",
) -> str:
    """Build a starred email card with full action buttons."""
    msg_id = html.escape(str(email.get("id", email.get("msg_id", ""))))
    msg_id_enc = urllib.parse.quote(str(email.get("id", email.get("msg_id", ""))))
    subject = html.escape(email.get("subject", "(no subject)"))
    sender = html.escape(email.get("sender", email.get("from", "")))
    from_raw = email.get("sender", email.get("from", ""))
    gmail_link = email.get("gmail_link", "")
    date_raw = email.get("date", "")
    date_display = html.escape(date_raw[:10] if date_raw else "")

    section_safe = html.escape(section)
    base_url = function_url.rstrip("/")

    # Build open URL for email viewer
    open_url = ""
    if gmail_link and email_actions_url and email_actions_token:
        thread_id = gmail_link.split("#inbox/")[-1] if "#inbox/" in gmail_link else ""
        lookup_id = msg_id or thread_id
        if lookup_id:
            open_url = (
                email_actions_url.rstrip("/")
                + "?action=open&msg_id=" + urllib.parse.quote(str(lookup_id))
                + ("&thread_id=" + thread_id if thread_id else "")
                + "&token=" + email_actions_token
            )

    # Review button
    if reviewed:
        review_btn = (
            f'<button class="review-btn reviewed" style="cursor:default;" '
            f'onclick="event.stopPropagation()">'
            f"\u2713 Reviewed ({time_remaining})</button>"
        )
    else:
        review_btn = (
            f'<button class="review-btn" '
            f"onclick=\"event.stopPropagation();doHomeReview(this,'{section_safe}','{msg_id}',{idx})\">"
            "Review</button>"
        )

    # Unstar button
    unstar_btn = (
        f'<button class="markread-btn" '
        f"onclick=\"event.stopPropagation();doUnstar('{msg_id}',this)\">"
        "Unstar</button>"
    )

    # Create Todoist button
    safe_subject = subject.replace("'", "\\'")
    create_todoist_btn = (
        f'<button class="todoist-btn" '
        f"onclick=\"event.stopPropagation();doCreateTodoistFromEmail('{msg_id}','{safe_subject}',this)\">"
        "Create Todoist</button>"
    )

    # Skip Inbox button
    skip_inbox_btn = ""
    if from_raw:
        import re as _re
        _email_match = _re.search(r"<([^>]+)>", from_raw)
        _sender_email = _email_match.group(1) if _email_match else from_raw.strip()
        if _sender_email:
            safe_from_email = html.escape(_sender_email).replace("'", "\\'")
            skip_inbox_btn = (
                f'<button class="skip-inbox-btn" '
                f"onclick=\"event.stopPropagation();doSkipInbox('{safe_from_email}',this)\">"
                "Skip Inbox</button>"
            )

    meta_parts = []
    if sender:
        meta_parts.append(sender)
    if date_display:
        meta_parts.append(date_display)
    meta_line = " &middot; ".join(meta_parts)

    card_class = "task-card reviewed-card" if reviewed else "task-card"
    opacity = ' style="opacity:0.65;"' if reviewed else ""

    data_attrs = f' data-msg-id="{msg_id}"'
    if open_url:
        data_attrs += f' data-open-url="{html.escape(open_url)}"'
    data_attrs += f' data-from="{html.escape(from_raw)}" data-subject="{subject}"'

    return (
        f'<div class="{card_class}" id="hcard-{idx}"{opacity}{data_attrs}'
        f' onclick="openHomeEmail(this)">'
        f'<div class="card-row">'
        f'<div class="card-content">'
        f'<div class="task-title">{subject}</div>'
        f'<div class="task-meta">{meta_line}</div>'
        f'<div class="task-actions">'
        f'{review_btn}{unstar_btn}{create_todoist_btn}{skip_inbox_btn}'
        f'</div>'
        f"</div></div>"
        f"</div>"
    )


def _build_calendar_card(
    event: Dict[str, Any],
    reviewed: bool,
    days_remaining: int,
    function_url: str,
    idx: int,
) -> str:
    """Build a calendar event card with full action buttons."""
    eid = html.escape(str(event.get("id", "")))
    eid_enc = urllib.parse.quote(str(event.get("id", "")))
    title = html.escape(event.get("title", "(No title)"))
    location = html.escape(event.get("location", ""))
    html_link = event.get("html_link", "")

    start = event.get("start", "")
    end = event.get("end", "")
    is_all_day = event.get("is_all_day", False)
    date_display = ""
    try:
        if is_all_day:
            dt = datetime.strptime(start[:10], "%Y-%m-%d")
            date_display = dt.strftime("%a %b %-d") + " (all day)"
        elif start:
            dt_start = datetime.fromisoformat(start).astimezone(_EASTERN)
            date_display = dt_start.strftime("%a %b %-d \u00b7 %-I:%M %p")
    except Exception:
        date_display = start[:10] if start else ""
    date_display = html.escape(date_display)

    cal_type = event.get("calendar_type", "family")
    _cal_labels = {
        "family": "Family", "medical": "Medical", "birthdays": "Birthday",
        "love_god": "Love God", "love_brittany": "Love Brittany",
        "love_children": "Love Children",
        "love_friends_family": "Love Friends & Family",
        "fishing_for_men": "Fishing For Men",
    }
    _cal_colors = {
        "family": "#818cf8", "medical": "#22c55e", "birthdays": "#eab308",
        "love_god": "#f59e0b", "love_brittany": "#a78bfa",
        "love_children": "#a78bfa",
        "love_friends_family": "#ec4899", "fishing_for_men": "#06b6d4",
    }
    cal_label = html.escape(_cal_labels.get(cal_type, cal_type.capitalize()))
    cal_color = _cal_colors.get(cal_type, "#5f6368")

    base_url = function_url.rstrip("/")
    title_enc = urllib.parse.quote(event.get("title", ""))
    date_enc = urllib.parse.quote(event.get("start", "")[:10])
    loc_enc = urllib.parse.quote(event.get("location", ""))

    # Review button
    if reviewed:
        review_btn = (
            f'<button class="review-btn reviewed" style="cursor:default;" '
            f'onclick="event.stopPropagation()">'
            f"\u2713 Reviewed ({days_remaining}d)</button>"
        )
    else:
        rev_url = base_url + "?action=calendar_reviewed&event_id=" + eid_enc
        review_btn = (
            f'<button class="review-btn" '
            f"onclick=\"event.stopPropagation();doCalReview(this,'{eid}','{html.escape(rev_url)}')\">"
            "Review</button>"
        )

    # Add to Todoist button
    todoist_url = html.escape(
        base_url + "?action=calendar_create_todoist"
        + "&event_id=" + eid_enc
        + "&event_title=" + title_enc
        + "&event_date=" + date_enc
        + "&event_location=" + loc_enc
    )
    todoist_btn = "" if reviewed else (
        f'<button class="todoist-btn" '
        f"onclick=\"event.stopPropagation();doCalTodoist(this,{idx},'{todoist_url}')\">"
        "Add to Todoist</button>"
    )

    # Commit button
    commit_url = html.escape(
        base_url + "?action=calendar_commit"
        + "&event_id=" + eid_enc
        + "&event_title=" + title_enc
        + "&event_date=" + date_enc
        + "&event_location=" + loc_enc
    )
    commit_btn = "" if reviewed else (
        f'<button class="commit-btn" '
        f"onclick=\"event.stopPropagation();doCalCommit(this,{idx},'{commit_url}')\">"
        "Commit</button>"
    )

    # Prep Timer button (today/tomorrow timed events only)
    timer_btn = ""
    if _is_upcoming_timed_event(event):
        start_iso = html.escape(event.get("start", ""))
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
            f'<button class="timer-btn" '
            f'data-start="{start_iso}" '
            f'onclick="event.stopPropagation();doPrepTimer(this)">'
            f'{_timer_svg} <span class="timer-label">Prep Timer</span></button>'
        )

    # Open in Calendar link
    gcal_html = ""
    if html_link:
        safe_link = html.escape(html_link)
        gcal_html = (
            f'<a href="{safe_link}" target="_blank" rel="noopener" class="gcal-link" '
            f'onclick="event.stopPropagation()">'
            f"Open in Calendar \u2197</a>"
        )

    # Meta line
    meta_parts = [date_display]
    if location:
        meta_parts.append(location)
    meta_line = " \u00b7 ".join(meta_parts)

    card_class = "task-card reviewed-card" if reviewed else "task-card"
    opacity = ' style="opacity:0.65;"' if reviewed else ""

    return (
        f'<div class="{card_class}" id="hcard-{idx}"{opacity}>'
        f'<div class="card-row">'
        f'<div class="card-content">'
        f'<div class="task-title">'
        f'{title}'
        f'<span class="cal-type-badge" style="background:{cal_color};">{cal_label}</span>'
        f"</div>"
        f'<div class="task-meta">{meta_line}</div>'
        f'<div class="task-actions">'
        f'{review_btn}{todoist_btn}{commit_btn}{timer_btn}{gcal_html}'
        f'</div>'
        f"</div></div>"
        f"</div>"
    )


def _build_unread_email_card(
    email: Dict[str, Any],
    function_url: str,
    idx: int,
    email_actions_url: str = "",
    email_actions_token: str = "",
) -> str:
    """Build a card for unread emails with Mark Read + Skip Inbox + Create Todoist."""
    msg_id = html.escape(str(email.get("id", email.get("msg_id", ""))))
    msg_id_enc = urllib.parse.quote(str(email.get("id", email.get("msg_id", ""))))
    subject = html.escape(email.get("subject", "(no subject)"))
    sender = html.escape(email.get("sender", email.get("from", "")))
    from_raw = email.get("sender", email.get("from", ""))
    gmail_link = email.get("gmail_link", "")
    date_raw = email.get("date", "")
    date_display = html.escape(date_raw[:10] if date_raw else "")

    base_url = function_url.rstrip("/")

    markread_url = base_url + "?action=markread&msg_id=" + msg_id_enc
    markread_btn = (
        f'<button class="markread-btn" id="mr-{idx}" '
        f"onclick=\"event.stopPropagation();doMarkRead(this,'{msg_id}','{html.escape(markread_url)}',{idx})\">"
        "Mark Read</button>"
    )

    # Skip Inbox button
    skip_inbox_btn = ""
    if from_raw:
        import re as _re
        _email_match = _re.search(r"<([^>]+)>", from_raw)
        _sender_email = _email_match.group(1) if _email_match else from_raw.strip()
        if _sender_email:
            safe_from_email = html.escape(_sender_email).replace("'", "\\'")
            skip_inbox_btn = (
                f'<button class="skip-inbox-btn" '
                f"onclick=\"event.stopPropagation();doSkipInbox('{safe_from_email}',this)\">"
                "Skip Inbox</button>"
            )

    # Create Todoist button
    safe_subject = subject.replace("'", "\\'")
    create_todoist_btn = (
        f'<button class="todoist-btn" '
        f"onclick=\"event.stopPropagation();doCreateTodoistFromEmail('{msg_id}','{safe_subject}',this)\">"
        "Create Todoist</button>"
    )

    # Build open URL for email viewer
    open_url = ""
    if gmail_link and email_actions_url and email_actions_token:
        thread_id = gmail_link.split("#inbox/")[-1] if "#inbox/" in gmail_link else ""
        lookup_id = msg_id or thread_id
        if lookup_id:
            open_url = (
                email_actions_url.rstrip("/")
                + "?action=open&msg_id=" + urllib.parse.quote(str(lookup_id))
                + ("&thread_id=" + thread_id if thread_id else "")
                + "&token=" + email_actions_token
            )

    meta_parts = []
    if sender:
        meta_parts.append(sender)
    if date_display:
        meta_parts.append(date_display)
    meta_line = " &middot; ".join(meta_parts)

    data_attrs = f' data-msg-id="{msg_id}"'
    if open_url:
        data_attrs += f' data-open-url="{html.escape(open_url)}"'
    data_attrs += f' data-from="{html.escape(from_raw)}"'

    return (
        f'<div class="task-card" id="hcard-{idx}"{data_attrs}'
        f' onclick="openHomeEmail(this)">'
        f'<div class="card-row">'
        f'<div class="card-content">'
        f'<div class="task-title">{subject}</div>'
        f'<div class="task-meta">{meta_line}</div>'
        f'<div class="task-actions">'
        f'{markread_btn}{skip_inbox_btn}{create_todoist_btn}'
        f'</div>'
        f"</div></div>"
        f"</div>"
    )


def _build_followup_email_card(
    email: Dict[str, Any],
    function_url: str,
    idx: int,
    followup_reviews: dict = None,
    email_actions_url: str = "",
    email_actions_token: str = "",
) -> str:
    """Build a follow-up email card with review, resolve, and open actions."""
    tid = email.get("threadId", "")
    msg_id = email.get("id", "")
    tid_safe = html.escape(tid)
    tid_enc = urllib.parse.quote(tid)
    msg_id_enc = urllib.parse.quote(msg_id)
    subject = html.escape(email.get("subject", "(no subject)"))
    sender = html.escape(email.get("sender", email.get("from", "")))
    snippet = html.escape((email.get("snippet", "") or "")[:120])
    gmail_link = email.get("gmail_link", "")
    followup_reviews = followup_reviews or {}

    base_url = function_url.rstrip("/")

    # Check if reviewed
    reviewed = False
    days_rem = 0
    ts = followup_reviews.get(tid)
    if ts:
        try:
            reviewed_at = datetime.fromisoformat(ts)
            if reviewed_at.tzinfo is None:
                reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - reviewed_at).days
            reviewed = elapsed < 7
            days_rem = max(0, 7 - elapsed)
        except Exception:
            pass

    # Review button
    if reviewed:
        review_btn = (
            f'<button class="review-btn reviewed" style="cursor:default;" '
            f'onclick="event.stopPropagation()">'
            f"\u2713 Reviewed ({days_rem}d)</button>"
        )
    else:
        rev_url = html.escape(base_url + "?action=followup_reviewed&thread_id=" + tid_enc)
        review_btn = (
            f'<button class="review-btn" '
            f"onclick=\"event.stopPropagation();doFollowupReview(this,'{tid_safe}','{rev_url}')\">"
            "Review</button>"
        )

    # Resolved button
    resolve_btn = ""
    if not reviewed:
        res_url = html.escape(base_url + "?action=followup_resolved&thread_id=" + tid_enc)
        resolve_btn = (
            f'<button class="resolve-btn" '
            f"onclick=\"event.stopPropagation();doResolve(this,'{tid_safe}','{res_url}')\">"
            "Resolved</button>"
        )

    # Open in Gmail link — use window.top.open so iOS universal links
    # route to the Gmail app with the specific thread (iframe links don't
    # trigger universal links).
    gmail_btn = ""
    if gmail_link:
        gmail_btn = (
            f'<a href="{html.escape(gmail_link)}" class="gcal-link" '
            f"onclick=\"event.preventDefault();event.stopPropagation();"
            f"window.top.open('{html.escape(gmail_link)}','_blank')\">"
            f"Open in Gmail \u2197</a>"
        )

    # Build open URL for email viewer
    open_url = ""
    if email_actions_url and email_actions_token and msg_id:
        open_url = (
            email_actions_url.rstrip("/")
            + "?action=open&msg_id=" + msg_id_enc
            + "&token=" + email_actions_token
        )

    meta_parts = []
    if sender:
        meta_parts.append(sender)
    meta_line = " &middot; ".join(meta_parts)

    snippet_html = ""
    if snippet:
        snippet_html = f'<div class="task-snippet">{snippet}</div>'

    data_attrs = f' data-msg-id="{html.escape(msg_id)}"'
    if open_url:
        data_attrs += f' data-open-url="{html.escape(open_url)}"'

    card_extra = " reviewed-card" if reviewed else ""

    return (
        f'<div class="task-card{card_extra}" id="hcard-{idx}"{data_attrs}'
        f' onclick="openHomeEmail(this)">'
        f'<div class="card-row">'
        f'<div class="card-content">'
        f'<div class="task-title">{subject}</div>'
        f'<div class="task-meta">{meta_line}</div>'
        f"{snippet_html}"
        f'<div class="task-actions">'
        f'{review_btn}{resolve_btn}{gmail_btn}'
        f'</div>'
        f"</div></div>"
        f"</div>"
    )


# ---------------------------------------------------------------------------
# Section builder
# ---------------------------------------------------------------------------

def _build_section_html(
    key: str,
    label: str,
    cards_html: str,
    needs_review_count: int,
    total: int,
    collapsed: bool,
    border_color: str,
) -> str:
    """Build a flat section with sticky header (calendar style)."""
    # Badge: "N NEEDS REVIEW" (warn) or "FULLY REVIEWED" (ok)
    if needs_review_count > 0:
        badge_html = (
            f'<span class="section-badge section-needs-badge" id="sbadge-{key}">'
            f"{needs_review_count} NEEDS REVIEW</span>"
        )
    else:
        badge_html = (
            f'<span class="section-badge section-ok-badge" id="sbadge-{key}">'
            f"FULLY REVIEWED</span>"
            if total > 0
            else ""
        )

    if not cards_html:
        cards_html = '<div class="empty-state">Nothing here \u2713</div>'

    return (
        f'<div class="section-hdr" style="color:{border_color};">'
        f'<span>{html.escape(label.upper())}</span>'
        f"{badge_html}"
        f"</div>"
        f'<div class="section-cards" id="body-{key}">'
        f"{cards_html}"
        f"</div>"
    )


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_home_html(
    commit_tasks: List[Dict[str, Any]],
    bestcase_tasks: List[Dict[str, Any]],
    calendar_events: List[Dict[str, Any]],
    p1_tasks: List[Dict[str, Any]],
    starred_emails: List[Dict[str, Any]],
    unread_emails: List[Dict[str, Any]],
    followup_emails: List[Dict[str, Any]],
    inbox_tasks: List[Dict[str, Any]],
    projects: List[Dict[str, Any]],
    home_state: dict,
    cal_state: dict,
    followup_state: dict,
    function_url: str,
    action_token: str,
    embed: bool = False,
    email_actions_url: str = "",
    email_actions_token: str = "",
) -> str:
    """Build the Home aggregated view HTML."""
    projects_by_id = _build_projects_by_id(projects)
    home_state = home_state or {}
    cal_state = cal_state or {}
    followup_state = followup_state or {}
    followup_reviews = followup_state.get("reviews", {})

    _card_idx = [0]

    def next_idx() -> int:
        i = _card_idx[0]
        _card_idx[0] += 1
        return i

    _today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _is_future_dated(task):
        """Return True if task has a due date strictly in the future."""
        due_obj = task.get("due")
        if not due_obj:
            return False
        due_date = (due_obj.get("date", "") or "")[:10]
        return due_date > _today_str if due_date else False

    def _build_task_section(tasks, key):
        label, border_color, cycle_days = _SECTION_CONFIG[key]
        cards = ""
        needs_review = 0
        reviewed_cards = ""
        for task in tasks:
            tid = str(task.get("id", ""))
            rev = _is_home_item_reviewed(tid, key, home_state, cycle_days)
            # Future-dated tasks don't need review
            if not rev and _is_future_dated(task):
                rev = True
            tr = _time_until_review_reset(tid, key, home_state, cycle_days)
            idx = next_idx()
            card = _build_task_card(
                task, key, rev, tr, function_url, projects_by_id, idx,
                email_actions_url=email_actions_url,
                email_actions_token=email_actions_token,
            )
            if rev:
                reviewed_cards += card
            else:
                needs_review += 1
                cards += card
        # Inbox and Commit show all cards; other sections hide reviewed items
        if key in ("inbox", "commit"):
            cards += reviewed_cards
        return cards, needs_review, len(tasks), label, border_color

    sections_html = ""
    total_unreviewed = 0

    # --- commit ---
    cards, needs_review, total, label, border_color = _build_task_section(commit_tasks, "commit")
    total_unreviewed += needs_review
    sections_html += _build_section_html(
        "commit", label, cards, needs_review, total,
        collapsed=(needs_review == 0), border_color=border_color,
    )

    # --- bestcase ---
    cards, needs_review, total, label, border_color = _build_task_section(bestcase_tasks, "bestcase")
    total_unreviewed += needs_review
    sections_html += _build_section_html(
        "bestcase", label, cards, needs_review, total,
        collapsed=(needs_review == 0), border_color=border_color,
    )

    # --- calendar (uses cal_state with 7-day cycle) ---
    key = "calendar"
    label, border_color, cycle_days = _SECTION_CONFIG[key]
    cal_reviews = cal_state.get("reviews", {})
    cards = ""
    needs_review = 0
    reviewed_cards = ""
    for event in calendar_events:
        eid = str(event.get("id", ""))
        # Check cal_state directly (same pattern as calendar_views._is_event_reviewed)
        ts = cal_reviews.get(eid)
        rev = False
        days_rem = 0
        if ts:
            try:
                reviewed_at = datetime.fromisoformat(ts)
                if reviewed_at.tzinfo is None:
                    reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
                elapsed_days = (datetime.now(timezone.utc) - reviewed_at).days
                rev = elapsed_days < cycle_days
                days_rem = max(0, cycle_days - elapsed_days)
            except Exception:
                pass
        idx = next_idx()
        card = _build_calendar_card(event, rev, days_rem, function_url, idx)
        if rev:
            pass  # Hide reviewed calendar events
        else:
            needs_review += 1
            cards += card
    total_unreviewed += needs_review
    sections_html += _build_section_html(
        key, label, cards, needs_review, len(calendar_events),
        collapsed=(needs_review == 0), border_color=border_color,
    )

    # --- p1 ---
    cards, needs_review, total, label, border_color = _build_task_section(p1_tasks, "p1")
    total_unreviewed += needs_review
    sections_html += _build_section_html(
        "p1", label, cards, needs_review, total,
        collapsed=(needs_review == 0), border_color=border_color,
    )

    # --- starred ---
    key = "starred"
    label, border_color, cycle_days = _SECTION_CONFIG[key]
    cards = ""
    needs_review = 0
    reviewed_cards = ""
    for email in starred_emails:
        mid = str(email.get("id", email.get("msg_id", "")))
        rev = _is_home_item_reviewed(mid, key, home_state, cycle_days)
        tr = _time_until_review_reset(mid, key, home_state, cycle_days)
        idx = next_idx()
        card = _build_email_card(
            email, key, rev, tr, function_url, idx,
            email_actions_url=email_actions_url,
            email_actions_token=email_actions_token,
        )
        if rev:
            pass  # Hide reviewed starred emails
        else:
            needs_review += 1
            cards += card
    total_unreviewed += needs_review
    sections_html += _build_section_html(
        key, label, cards, needs_review, len(starred_emails),
        collapsed=(needs_review == 0), border_color=border_color,
    )

    # --- unread (no review tracking) ---
    key = "unread"
    label, border_color, _ = _SECTION_CONFIG[key]
    cards = ""
    for email in unread_emails:
        idx = next_idx()
        cards += _build_unread_email_card(
            email, function_url, idx,
            email_actions_url=email_actions_url,
            email_actions_token=email_actions_token,
        )
    unread_count = len(unread_emails)
    total_unreviewed += unread_count
    sections_html += _build_section_html(
        key, label, cards, unread_count, unread_count,
        collapsed=(unread_count == 0), border_color=border_color,
    )

    # --- followup ---
    key = "followup"
    label, border_color, _ = _SECTION_CONFIG[key]
    cards = ""
    followup_unreviewed = 0
    for email in followup_emails:
        idx = next_idx()
        cards += _build_followup_email_card(
            email, function_url, idx,
            followup_reviews=followup_reviews,
            email_actions_url=email_actions_url,
            email_actions_token=email_actions_token,
        )
        tid = email.get("threadId", "")
        if not followup_reviews.get(tid):
            followup_unreviewed += 1
    followup_count = len(followup_emails)
    sections_html += _build_section_html(
        key, label, cards, followup_unreviewed, followup_count,
        collapsed=(followup_unreviewed == 0), border_color=border_color,
    )

    # --- inbox (always show all cards; don't count in Home nav badge) ---
    cards, needs_review, total, label, border_color = _build_task_section(inbox_tasks, "inbox")
    sections_html += _build_section_html(
        "inbox", label, cards, needs_review, total,
        collapsed=(needs_review == 0), border_color=border_color,
    )

    # -----------------------------------------------------------------------
    # Page assembly
    # -----------------------------------------------------------------------
    embed_css = ".top-bar{display:none;}" if embed else ""
    page_height = "100vh" if embed else "calc(100vh - 57px)"
    func_url_safe = html.escape(function_url.rstrip("/"))

    post_message_js = ""
    if embed:
        post_message_js = (
            "var homeCount=" + str(total_unreviewed) + ";"
            "function postHomeCount(){"
            "window.parent.postMessage({type:'count',source:'home',count:homeCount},'*');"
            "}"
            "postHomeCount();"
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
        "<title>Home</title>"
        "<style>"
        ":root{"
        "--bg-base:#1a1a1a;--bg-s0:#1c1c1e;--bg-s1:#252528;--bg-s2:#2c2c2e;"
        "--text-1:#ffffff;--text-2:#8e8e93;--text-3:#48484a;"
        "--border:rgba(255,255,255,0.08);--border-h:rgba(255,255,255,0.12);"
        "--accent:#6366f1;--accent-l:#818cf8;"
        "--accent-bg:rgba(99,102,241,0.10);--accent-b:rgba(99,102,241,0.20);"
        "--ok:#22c55e;--ok-bg:rgba(34,197,94,0.10);--ok-b:rgba(34,197,94,0.20);"
        "--warn:#eab308;--warn-bg:rgba(234,179,8,0.10);--warn-b:rgba(234,179,8,0.20);"
        "--err:#ef4444;--err-bg:rgba(239,68,68,0.10);--err-b:rgba(239,68,68,0.20);"
        "--purple:#a78bfa;--purple-bg:rgba(167,139,250,0.10);--purple-b:rgba(167,139,250,0.20);"
        "--scrollbar:rgba(255,255,255,0.10);color-scheme:dark;}"
        "@media(prefers-color-scheme:light){:root{"
        "--bg-base:#eeeef0;--bg-s0:#fff;--bg-s1:#fff;--bg-s2:#f5f5f7;"
        "--text-1:#202124;--text-2:#5f6368;--text-3:#80868b;"
        "--border:rgba(0,0,0,0.08);--border-h:rgba(0,0,0,0.15);"
        "--accent:#6366f1;--accent-l:#4f46e5;"
        "--accent-bg:rgba(99,102,241,0.08);--accent-b:rgba(99,102,241,0.15);"
        "--ok:#188038;--ok-bg:#e6f4ea;--ok-b:rgba(24,128,56,0.20);"
        "--warn:#e37400;--warn-bg:#fef7e0;--warn-b:rgba(227,116,0,0.20);"
        "--err:#d93025;--err-bg:#fce8e6;--err-b:rgba(217,48,37,0.20);"
        "--purple:#7c4dff;--purple-bg:#ede7f6;--purple-b:rgba(124,77,255,0.20);"
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
        ".scroll-area{height:" + page_height + ";overflow-y:auto;overflow-x:hidden;background:var(--bg-base);}"
        ".home-list{max-width:700px;margin:0 auto;padding:12px 16px;overflow:hidden;}"
        # Section headers (flat, calendar-style)
        ".section-hdr{display:flex;align-items:center;gap:8px;padding:16px 0 8px;"
        "font-size:11px;font-weight:600;text-transform:uppercase;"
        "letter-spacing:0.6px;border-bottom:1px solid var(--border);margin-bottom:10px;"
        "position:sticky;top:0;z-index:10;background:var(--bg-base);}"
        ".section-hdr+.section-hdr{margin-top:14px;}"
        ".section-badge{background:var(--border);color:var(--text-2);font-size:11px;"
        "font-weight:700;padding:2px 7px;border-radius:8px;}"
        ".section-needs-badge{background:var(--warn-bg);color:var(--warn);"
        "border:1px solid var(--warn-b);}"
        ".section-ok-badge{background:var(--ok-bg);color:var(--ok);"
        "border:1px solid var(--ok-b);}"
        ".section-cards{margin-bottom:6px;}"
        # Task/email cards
        ".task-card{background:var(--bg-s1);border-radius:8px;"
        "border:1px solid var(--border);padding:14px 16px;"
        "margin-bottom:10px;transition:border-color .15s ease-out,opacity .3s;overflow:hidden;cursor:pointer;}"
        ".task-card:last-child{margin-bottom:0;}"
        ".task-card:hover{border-color:var(--border-h);}"
        ".reviewed-card{opacity:0.65;}"
        ".card-row{display:flex;align-items:flex-start;gap:10px;}"
        ".card-content{flex:1;min-width:0;overflow:hidden;}"
        ".task-title{font-size:15px;font-weight:600;color:var(--text-1);"
        "line-height:1.4;margin-bottom:4px;word-break:break-word;"
        "display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;}"
        ".task-title a{color:var(--accent,#4a9eff);text-decoration:underline;"
        "word-break:break-all;font-weight:500;}"
        ".cal-type-badge{font-size:10px;font-weight:700;color:#fff;"
        "padding:2px 6px;border-radius:5px;white-space:nowrap;flex-shrink:0;}"
        ".pri-badge{font-size:10px;font-weight:700;"
        "padding:2px 6px;border-radius:5px;white-space:nowrap;flex-shrink:0;}"
        ".task-meta{font-size:12px;color:var(--text-2);margin-bottom:10px;line-height:1.5;"
        "word-break:break-word;overflow-wrap:break-word;}"
        ".task-snippet{font-size:12px;color:var(--text-3);margin-bottom:8px;"
        "line-height:1.4;word-break:break-word;font-style:italic;}"
        ".task-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center;}"
        # Review button
        ".review-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:4px 12px;border-radius:6px;"
        "background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn-b);cursor:pointer;"
        "transition:background .15s;}"
        ".review-btn:hover{background:var(--warn-b);}"
        ".review-btn.reviewed{background:var(--ok-bg);color:var(--ok);"
        "border-color:var(--ok-b);cursor:default;}"
        # Mark Read button
        ".markread-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:4px 12px;border-radius:6px;"
        "background:var(--border);color:var(--text-2);border:1px solid var(--border);"
        "cursor:pointer;transition:background .15s;}"
        ".markread-btn:hover{background:var(--border-h);color:var(--text-1);}"
        # Complete button
        ".complete-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:4px 12px;border-radius:6px;"
        "background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-b);"
        "cursor:pointer;transition:background .15s;}"
        ".complete-btn:hover{background:var(--ok-b);}"
        # Commit button
        ".commit-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:4px 12px;border-radius:6px;"
        "background:var(--border);color:var(--text-2);border:1px solid var(--border);"
        "cursor:pointer;transition:background .15s;}"
        ".commit-btn:hover{background:var(--border-h);color:var(--text-1);}"
        ".commit-btn.committed{background:var(--ok-bg);color:var(--ok);border-color:var(--ok-b);cursor:default;}"
        ".commit-btn.remove{background:var(--err-bg);color:var(--err);border-color:var(--err-b);}"
        # Best Case button
        ".bestcase-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:4px 12px;border-radius:6px;"
        "background:var(--purple-bg);color:var(--purple);border:1px solid var(--purple-b);"
        "cursor:pointer;transition:background .15s;}"
        ".bestcase-btn:hover{background:var(--purple-b);}"
        ".bestcase-btn.remove{background:var(--err-bg);color:var(--err);border-color:var(--err-b);}"
        # Todoist button
        ".todoist-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:4px 12px;border-radius:6px;"
        "background:var(--accent-bg);color:var(--accent-l);border:1px solid var(--accent-b);"
        "cursor:pointer;transition:background .15s;}"
        ".todoist-btn:hover{background:var(--accent-b);}"
        # Skip Inbox button
        ".skip-inbox-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:4px 12px;border-radius:6px;"
        "background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn-b);"
        "cursor:pointer;transition:background .15s;}"
        ".skip-inbox-btn:hover{background:var(--warn-b);}"
        # Resolve button
        ".resolve-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:4px 12px;border-radius:6px;"
        "background:var(--border);color:var(--text-2);border:1px solid var(--border);"
        "cursor:pointer;transition:background .15s;}"
        ".resolve-btn:hover{background:var(--border-h);color:var(--text-1);}"
        # Timer button
        ".timer-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:4px 12px;border-radius:6px;"
        "background:var(--purple-bg);color:var(--purple);border:1px solid var(--purple-b);"
        "cursor:pointer;transition:background .15s;"
        "display:inline-flex;align-items:center;gap:5px;}"
        ".timer-btn:hover{background:var(--purple-b);}"
        ".timer-btn.expired{opacity:0.4;cursor:default;pointer-events:none;}"
        ".timer-icon{flex-shrink:0;vertical-align:middle;}"
        # GCal link
        ".gcal-link{color:var(--accent-l);font-size:12px;font-weight:500;"
        "text-decoration:none;white-space:nowrap;}"
        ".gcal-link:hover{text-decoration:underline;}"
        # Move pill
        ".move-pill{display:inline-flex;align-items:center;gap:4px;"
        "background:var(--bg-s1);border:1px solid var(--border);border-radius:6px;"
        "padding:2px 4px;cursor:pointer;}"
        ".move-pill:hover{border-color:var(--border-h);}"
        ".move-pill-select{font-family:inherit;font-size:11px;"
        "background:transparent;border:none;color:var(--text-2);cursor:pointer;"
        "outline:none;max-width:90px;}"
        ".move-icon{color:var(--text-3);flex-shrink:0;}"
        # Action select (priority)
        ".action-select{font-family:inherit;font-size:11px;padding:4px 6px;"
        "border:1px solid var(--border);border-radius:6px;background:var(--bg-s1);"
        "color:var(--text-1);cursor:pointer;}"
        # Date pill
        ".date-pill{display:inline-flex;align-items:center;gap:4px;"
        "background:var(--bg-s1);border:1px solid var(--border);border-radius:6px;"
        "padding:2px 6px;cursor:pointer;}"
        ".date-pill:hover{border-color:var(--border-h);}"
        ".date-icon-wrap{display:inline-flex;align-items:center;}"
        ".date-icon{color:var(--text-3);}"
        ".date-label{font-size:11px;color:var(--text-3);}"
        ".date-pill-input{font-family:inherit;font-size:11px;"
        "background:transparent;border:none;color:var(--text-1);cursor:pointer;"
        "outline:none;width:100px;}"
        # CC button
        ".assign-cc-btn{display:inline-flex;align-items:center;justify-content:center;"
        "padding:4px 10px;border-radius:6px;"
        "background:rgba(196,120,64,0.10);border:1px solid rgba(196,120,64,0.25);"
        "cursor:pointer;transition:background .15s;color:#c47840;font-size:13px;font-weight:600;}"
        ".assign-cc-btn:hover{background:rgba(196,120,64,0.25);}"
        # Detail pane
        "#home-detail-pane{display:none;}"
        ".viewer-mobile-header{display:none;}"
        ".viewer-back-btn{display:flex;align-items:center;gap:6px;background:none;border:none;"
        "color:var(--accent-l);font-family:inherit;font-size:15px;font-weight:600;"
        "cursor:pointer;padding:8px 4px;touch-action:manipulation;}"
        "#home-detail-content{padding:16px;overflow-y:auto;}"
        "#home-detail-frame{width:100%;height:100%;border:none;display:none;}"
        # Detail pane inner styles (rich detail view)
        ".detail-title{font-size:20px;font-weight:700;color:var(--text-1);"
        "line-height:1.4;margin-bottom:16px;}"
        ".detail-title-editable{outline:none;border-radius:4px;padding:2px 4px;margin:-2px -4px;"
        "transition:background .15s;}"
        ".detail-title-editable:hover{background:var(--bg-s2);}"
        ".detail-title-editable:focus{background:var(--bg-s2);box-shadow:0 0 0 2px rgba(99,102,241,0.3);}"
        ".detail-meta{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;}"
        ".detail-meta-tag{display:inline-block;padding:4px 10px;border-radius:6px;"
        "font-size:12px;font-weight:600;background:var(--border);color:var(--text-2);}"
        ".detail-section-label{font-size:11px;font-weight:600;text-transform:uppercase;"
        "color:var(--text-3);letter-spacing:0.5px;margin-bottom:6px;}"
        ".detail-desc-editable{width:100%;box-sizing:border-box;font-family:inherit;font-size:14px;color:var(--text-1);"
        "background:var(--bg-s2);border:1px solid var(--border);border-radius:6px;"
        "padding:8px 10px;resize:vertical;line-height:1.5;margin-bottom:8px;min-height:100px;}"
        ".detail-desc-editable:focus{outline:none;border-color:rgba(99,102,241,0.5);}"
        ".detail-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px;"
        "padding-top:16px;border-top:1px solid var(--border);}"
        ".detail-action-btn{font-family:inherit;font-size:13px;font-weight:600;"
        "padding:8px 18px;border:none;border-radius:8px;cursor:pointer;}"
        # Empty state
        ".empty-state{text-align:center;color:var(--text-2);padding:20px;font-size:13px;}"
        "@media(max-width:768px){"
        ".section-cards{margin-bottom:4px;}"
        ".task-actions{gap:6px;}"
        ".review-btn,.markread-btn,.complete-btn,.commit-btn,.bestcase-btn,.todoist-btn,"
        ".skip-inbox-btn,.resolve-btn,.timer-btn{font-size:11px;padding:3px 8px;}"
        ".move-pill-select{font-size:10px;max-width:70px;}"
        ".action-select{font-size:10px;padding:3px 4px;}"
        ".date-pill-input{font-size:10px;width:80px;}"
        "#home-detail-pane.open{display:flex!important;flex-direction:column;"
        "position:fixed;inset:0;z-index:200;background:var(--bg-base);}"
        ".viewer-mobile-header{display:flex!important;align-items:center;"
        "background:var(--bg-s0);border-bottom:1px solid var(--border);"
        "padding:0 12px;height:52px;flex-shrink:0;z-index:12;}"
        "#home-detail-content{flex:1;overflow-y:auto;}"
        "#home-detail-frame{flex:1;}"
        "}"
        "::-webkit-scrollbar{width:6px;}"
        "::-webkit-scrollbar-track{background:transparent;}"
        "::-webkit-scrollbar-thumb{background:var(--scrollbar);border-radius:3px;}"
        "</style></head><body>"
        + (
            ""
            if embed
            else '<div class="top-bar">'
            '<span class="top-bar-title">Home</span>'
            '<button class="refresh-btn" onclick="location.reload()">&#8635; Refresh</button>'
            "</div>"
        )
        + '<div class="scroll-area"><div class="home-list">'
        + sections_html
        + "</div></div>"
        # Detail pane (mobile fullscreen overlay)
        '<div id="home-detail-pane">'
        '<div class="viewer-mobile-header">'
        '<button class="viewer-back-btn" onclick="closeHomeDetail()">&#8592; Back</button>'
        '</div>'
        '<div id="home-detail-content"></div>'
        '<iframe id="home-detail-frame" src="about:blank"></iframe>'
        '</div>'
        "<script>"
        "var _homeUrl='" + func_url_safe + "';"
        "var _cs=getComputedStyle(document.documentElement);"
        "function cv(n){return _cs.getPropertyValue(n).trim();}"
        + post_message_js
        +
        # --- Section toggle ---
        "function toggleSection(key){}"
        # --- Helper: fade card ---
        "function _fadeCard(btn){"
        "var card=btn.closest('.task-card');"
        "if(card){card.style.opacity='0.3';card.style.pointerEvents='none';}}"
        # --- Helper: get section key from element ---
        "function _sectionOf(el){"
        "var sc=el.closest('.section-cards');"
        "return sc?sc.id.replace('body-',''):'';}"
        # --- Helper: fade + update badge on disposition (Complete/Commit/Best Case) ---
        "function _disposeCard(btn){"
        "var card=btn.closest('.task-card');"
        "if(card&&!card.classList.contains('reviewed-card')){"
        "_updateBadge(_sectionOf(btn));}"
        "_fadeCard(btn);}"
        # --- Helper: update section badge ---
        "function _updateBadge(section){"
        "var badge=document.getElementById('sbadge-'+section);"
        "if(badge){var cur=parseInt(badge.textContent)||0;"
        "var nxt=Math.max(0,cur-1);"
        "if(nxt>0){badge.textContent=nxt+' NEEDS REVIEW';}"
        "else{badge.textContent='FULLY REVIEWED';"
        "badge.className='section-badge section-ok-badge';}}"
        "if(typeof homeCount!=='undefined'){homeCount=Math.max(0,homeCount-1);"
        "if(typeof postHomeCount==='function')postHomeCount();}}"
        # --- Home Review (task sections) ---
        "function doHomeReview(btn,section,itemId,idx){"
        "btn.style.pointerEvents='none';btn.textContent='Reviewing\u2026';"
        "var url=_homeUrl+'?action=home_reviewed&section='+encodeURIComponent(section)+'&item_id='+encodeURIComponent(itemId);"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){"
        "btn.className='review-btn reviewed';"
        "btn.textContent='\u2713 Reviewed';"
        "btn.style.cursor='default';"
        "var card=btn.closest('.task-card');"
        "if(card){card.classList.add('reviewed-card');card.style.opacity='0.65';}"
        "_updateBadge(section);"
        "}else{btn.textContent='Review';btn.style.pointerEvents='auto';}"
        "}).catch(function(){btn.textContent='Review';btn.style.pointerEvents='auto';});}"
        # --- Calendar Review ---
        "function doCalReview(btn,eid,url){"
        "btn.style.pointerEvents='none';btn.textContent='Reviewing\u2026';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){"
        "btn.className='review-btn reviewed';btn.textContent='\u2713 Reviewed (7d)';"
        "btn.style.cursor='default';btn.style.pointerEvents='auto';"
        "var card=btn.closest('.task-card');"
        "if(card){card.classList.add('reviewed-card');card.style.opacity='0.65';"
        "var acts=card.querySelectorAll('.todoist-btn,.commit-btn');"
        "for(var i=0;i<acts.length;i++)acts[i].style.display='none';}"
        "_updateBadge('calendar');"
        "}else{btn.textContent='Review';btn.style.pointerEvents='auto';}"
        "}).catch(function(){btn.textContent='Review';btn.style.pointerEvents='auto';});}"
        # --- Mark Read ---
        "function doMarkRead(btn,msgId,url,idx){"
        "btn.style.pointerEvents='none';btn.textContent='Marking\u2026';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){"
        "_fadeCard(btn);"
        "btn.textContent='\u2713 Read';btn.style.cursor='default';"
        "_updateBadge('unread');"
        "}else{btn.textContent='Mark Read';btn.style.pointerEvents='auto';}"
        "}).catch(function(){btn.textContent='Mark Read';btn.style.pointerEvents='auto';});}"
        # --- Move task ---
        "function doMove(taskId,projectId,sel){"
        "sel.disabled=true;"
        "fetch(_homeUrl+'?action=move&task_id='+encodeURIComponent(taskId)+'&project_id='+encodeURIComponent(projectId))"
        ".then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){_fadeCard(sel);}"
        "else{sel.disabled=false;}"
        "}).catch(function(){sel.disabled=false;});}"
        # --- Set Priority ---
        "function doSetPriority(taskId,pri,sel){"
        "fetch(_homeUrl+'?action=priority&task_id='+encodeURIComponent(taskId)+'&priority='+encodeURIComponent(pri))"
        ".then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){sel.style.borderColor=cv('--ok-b');setTimeout(function(){sel.style.borderColor='';},1500);}"
        "}).catch(function(){});}"
        # --- Set Due Date ---
        "function doSetDueDate(taskId,date,input){"
        "fetch(_homeUrl+'?action=due_date&task_id='+encodeURIComponent(taskId)+'&date='+encodeURIComponent(date))"
        ".then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){input.style.borderColor=cv('--ok-b');setTimeout(function(){input.style.borderColor='';},1500);}"
        "}).catch(function(){});}"
        # --- Complete task ---
        "function doComplete(taskId,btn){"
        "btn.style.pointerEvents='none';btn.textContent='Completing\u2026';"
        "fetch(_homeUrl+'?action=complete&task_id='+encodeURIComponent(taskId))"
        ".then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){btn.textContent='\u2713 Done';_disposeCard(btn);}"
        "else{btn.textContent='Complete';btn.style.pointerEvents='auto';}"
        "}).catch(function(){btn.textContent='Complete';btn.style.pointerEvents='auto';});}"
        # --- Commit label ---
        "function doCommitLabel(taskId,btn){"
        "btn.style.pointerEvents='none';btn.textContent='Committing\u2026';"
        "fetch(_homeUrl+'?action=commit_label&task_id='+encodeURIComponent(taskId))"
        ".then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){btn.textContent='\u2713 Committed';btn.className='commit-btn committed';btn.style.cursor='default';_disposeCard(btn);}"
        "else{btn.textContent='Commit';btn.style.pointerEvents='auto';}"
        "}).catch(function(){btn.textContent='Commit';btn.style.pointerEvents='auto';});}"
        # --- Remove Commit ---
        "function doRemoveCommit(taskId,btn){"
        "btn.style.pointerEvents='none';btn.textContent='Removing\u2026';"
        "fetch(_homeUrl+'?action=remove_commit&task_id='+encodeURIComponent(taskId))"
        ".then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){_fadeCard(btn);}"
        "else{btn.textContent='Remove Commit';btn.style.pointerEvents='auto';}"
        "}).catch(function(){btn.textContent='Remove Commit';btn.style.pointerEvents='auto';});}"
        # --- Best Case label ---
        "function doBestCaseLabel(taskId,btn){"
        "btn.style.pointerEvents='none';btn.textContent='Adding\u2026';"
        "fetch(_homeUrl+'?action=bestcase_label&task_id='+encodeURIComponent(taskId))"
        ".then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){btn.textContent='\u2713 Best Case';btn.className='bestcase-btn remove';btn.style.cursor='default';_disposeCard(btn);}"
        "else{btn.textContent='Best Case';btn.style.pointerEvents='auto';}"
        "}).catch(function(){btn.textContent='Best Case';btn.style.pointerEvents='auto';});}"
        # --- Remove Best Case ---
        "function doRemoveBestCase(taskId,btn){"
        "btn.style.pointerEvents='none';btn.textContent='Removing\u2026';"
        "fetch(_homeUrl+'?action=remove_bestcase&task_id='+encodeURIComponent(taskId))"
        ".then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){_fadeCard(btn);}"
        "else{btn.textContent='Remove Best Case';btn.style.pointerEvents='auto';}"
        "}).catch(function(){btn.textContent='Remove Best Case';btn.style.pointerEvents='auto';});}"
        # --- Copy CC ---
        "function doCopyCC(taskId,content,btn){"
        "var orig=btn.innerHTML;"
        "var msg='Task: '+content+'\\nID: '+taskId;"
        "navigator.clipboard.writeText(msg).then(function(){"
        "btn.textContent='\u2713';setTimeout(function(){btn.innerHTML=orig;},1500);"
        "}).catch(function(){btn.textContent='!';setTimeout(function(){btn.innerHTML=orig;},1500);});}"
        # --- Unstar email ---
        "function doUnstar(msgId,btn){"
        "btn.style.pointerEvents='none';btn.textContent='Unstarring\u2026';"
        "fetch(_homeUrl+'?action=unstar&msg_id='+encodeURIComponent(msgId))"
        ".then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){_fadeCard(btn);_updateBadge('starred');}"
        "else{btn.textContent='Unstar';btn.style.pointerEvents='auto';}"
        "}).catch(function(){btn.textContent='Unstar';btn.style.pointerEvents='auto';});}"
        # --- Skip Inbox ---
        "function doSkipInbox(fromEmail,btn){"
        "btn.style.pointerEvents='none';btn.textContent='Skipping\u2026';"
        "fetch(_homeUrl+'?action=create_filter&from_email='+encodeURIComponent(fromEmail))"
        ".then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){btn.textContent='\u2713 Skipped';btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        "btn.style.cursor='default';}"
        "else{btn.textContent='Skip Inbox';btn.style.pointerEvents='auto';}"
        "}).catch(function(){btn.textContent='Skip Inbox';btn.style.pointerEvents='auto';});}"
        # --- Create Todoist from email ---
        "function doCreateTodoistFromEmail(msgId,subject,btn){"
        "btn.style.pointerEvents='none';btn.textContent='Creating\u2026';"
        "fetch(_homeUrl+'?action=starred_to_todoist',{method:'POST',"
        "headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({msg_id:msgId,subject:subject})})"
        ".then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){btn.textContent='\u2713 Created';btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        "setTimeout(function(){btn.textContent='Create Todoist';btn.style.background='';btn.style.color='';btn.style.pointerEvents='auto';},2000);}"
        "else{btn.textContent='Failed';btn.style.pointerEvents='auto';"
        "setTimeout(function(){btn.textContent='Create Todoist';},2000);}"
        "}).catch(function(){btn.textContent='Create Todoist';btn.style.pointerEvents='auto';});}"
        # --- Calendar: Add to Todoist ---
        "function doCalTodoist(btn,idx,url){"
        "btn.style.pointerEvents='none';btn.textContent='Adding\u2026';"
        "fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})"
        ".then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){btn.textContent='\u2713 Added';btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        "setTimeout(function(){btn.textContent='Add to Todoist';btn.style.background='';btn.style.color='';btn.style.pointerEvents='auto';},2000);}"
        "else{btn.textContent='Failed';btn.style.pointerEvents='auto';"
        "setTimeout(function(){btn.textContent='Add to Todoist';},2000);}"
        "}).catch(function(){btn.textContent='Add to Todoist';btn.style.pointerEvents='auto';});}"
        # --- Calendar: Commit ---
        "function doCalCommit(btn,idx,url){"
        "btn.style.pointerEvents='none';btn.textContent='Committing\u2026';"
        "fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})"
        ".then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        "btn.textContent='\u2713 Committed';btn.style.cursor='default';}"
        "else{btn.textContent='Commit';btn.style.background='';btn.style.color='';btn.style.pointerEvents='auto';}"
        "}).catch(function(){btn.textContent='Commit';btn.style.pointerEvents='auto';});}"
        # --- Prep Timer ---
        "function _timerLabel(secs){"
        "if(secs<=0)return 'Starting soon';"
        "var h=Math.floor(secs/3600);var m=Math.floor((secs%3600)/60);var s=secs%60;"
        "if(h>0)return h+'h '+m+'m '+s+'s';"
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
        "if(secs<=0){_setTimerText(btn,'Starting soon');btn.classList.add('expired');return;}"
        "_setTimerText(btn,_timerLabel(secs)+' set');"
        "btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');btn.style.borderColor=cv('--ok-b');"
        "window.top.location.href='shortcuts://run-shortcut?name=Prep%20Timer&input=text&text='+secs;"
        "setTimeout(function(){_setTimerText(btn,_timerLabel(_calcPrepSec(btn)));"
        "btn.style.background='';btn.style.color='';btn.style.borderColor='';},3000);}"
        # Init timer buttons
        "function initTimerBtns(){"
        "var btns=document.querySelectorAll('.timer-btn');"
        "for(var i=0;i<btns.length;i++){"
        "var s=btns[i].getAttribute('data-start');"
        "if(!s)continue;"
        "var secs=_calcPrepSec(btns[i]);"
        "if(secs<=0){_setTimerText(btns[i],'Starting soon');btns[i].classList.add('expired');}"
        "else{_setTimerText(btns[i],_timerLabel(secs));}"
        "}}"
        "initTimerBtns();"
        # --- Followup Review ---
        "function doFollowupReview(btn,tid,url){"
        "btn.style.pointerEvents='none';btn.textContent='Reviewing\u2026';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){"
        "btn.className='review-btn reviewed';btn.textContent='\u2713 Reviewed (7d)';"
        "btn.style.cursor='default';btn.style.pointerEvents='auto';"
        "var card=btn.closest('.task-card');"
        "if(card){card.classList.add('reviewed-card');"
        "var acts=card.querySelectorAll('.resolve-btn');"
        "for(var i=0;i<acts.length;i++)acts[i].style.display='none';}"
        "_updateBadge('followup');"
        "}else{btn.textContent='Review';btn.style.pointerEvents='auto';}"
        "}).catch(function(){btn.textContent='Review';btn.style.pointerEvents='auto';});}"
        # --- Followup Resolve ---
        "function doResolve(btn,tid,url){"
        "btn.style.pointerEvents='none';btn.textContent='Resolving\u2026';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){_fadeCard(btn);_updateBadge('followup');}"
        "else{btn.textContent='Resolved';btn.style.pointerEvents='auto';}"
        "}).catch(function(){btn.textContent='Resolved';btn.style.pointerEvents='auto';});}"
        # --- Detail pane helpers ---
        # NOTE: esc() sanitizes all user content before DOM insertion (XSS-safe)
        # This matches the existing pattern in todoist_views.py
        "function esc(s){var d=document.createElement('div');"
        "d.appendChild(document.createTextNode(String(s)));return d.innerHTML;}"
        "function linkify(t){"
        "t=t.replace(/\\[([^\\]]+)\\]\\(((?:https?|obsidian):\\/\\/[^)]+)\\)/g,"
        "'<a href=\"$2\" target=\"_blank\" rel=\"noopener\" style=\"color:'+cv('--accent-l')+';text-decoration:underline;\">$1</a>');"
        "t=t.replace(/(?<!href=\")(?<!\">)((?:https?|obsidian):\\/\\/[^\\s<)]+)/g,"
        "'<a href=\"$1\" target=\"_blank\" rel=\"noopener\" style=\"color:'+cv('--accent-l')+';text-decoration:underline;\">$1</a>');"
        "return t;}"
        "function doHomeUpdateTask(taskId,payload,callback){"
        "payload.task_id=taskId;"
        "fetch(_homeUrl+'?action=update_task',{method:'POST',"
        "headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify(payload)})"
        ".then(function(r){return r.json();})"
        ".then(function(d){if(callback)callback(d.ok||false);})"
        ".catch(function(){if(callback)callback(false);});}"
        "function loadHomeAttachments(taskId,container){"
        "fetch(_homeUrl+'?action=task_comments&task_id='+encodeURIComponent(taskId))"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(!d.ok||!d.comments||!d.comments.length)return;"
        "var wrap=document.createElement('div');"
        "wrap.style.marginTop='16px';"
        "var lbl=document.createElement('div');lbl.className='detail-section-label';"
        "lbl.textContent='Attachments & Comments';wrap.appendChild(lbl);"
        "d.comments.forEach(function(c){"
        "var fa=c.file_attachment;"
        "if(fa){"
        "var ft=fa.file_type||'';var fn=fa.file_name||'File';var fu=fa.file_url||'';var img=fa.image||'';"
        "if(ft.indexOf('image/')===0&&(img||fu)){"
        "var imgDiv=document.createElement('div');imgDiv.style.marginBottom='8px';"
        "var imgEl=document.createElement('img');imgEl.src=img||fu;imgEl.alt=fn;"
        "imgEl.style.cssText='max-width:100%;border-radius:8px;border:1px solid var(--border);';"
        "imgDiv.appendChild(imgEl);wrap.appendChild(imgDiv);"
        "}else if(fu){"
        "var linkDiv=document.createElement('div');linkDiv.style.marginBottom='8px';"
        "var a=document.createElement('a');a.href=fu;a.target='_blank';a.textContent=fn;"
        "a.style.cssText='color:var(--accent-l);text-decoration:underline;';"
        "linkDiv.appendChild(a);wrap.appendChild(linkDiv);"
        "}}"
        "if(c.content){"
        "var cDiv=document.createElement('div');"
        "cDiv.style.cssText='font-size:13px;color:var(--text-2);padding:8px 10px;background:var(--bg-s2);border-radius:6px;margin-bottom:6px;';"
        "cDiv.textContent=c.content;wrap.appendChild(cDiv);}"
        "});"
        "container.appendChild(wrap);"
        "}).catch(function(){});}"
        # --- Detail pane (rich view matching todoist_views) ---
        # All user content is sanitized via esc() before DOM insertion
        "function openHomeDetail(card){"
        "if(window.innerWidth>768)return;"
        "var url=card.getAttribute('data-open-url');"
        "if(url){openHomeEmail(card);return;}"
        "var taskId=card.getAttribute('data-task-id')||'';"
        "var title=card.getAttribute('data-content')||'(no title)';"
        "var description=card.getAttribute('data-description')||'';"
        "var projectName=card.getAttribute('data-project-name')||'';"
        "var priority=parseInt(card.getAttribute('data-priority')||'1');"
        "var pLabel=card.getAttribute('data-priority-label')||'P4';"
        "var pColor=card.getAttribute('data-priority-color')||'#56565e';"
        "var labels=card.getAttribute('data-labels')||'';"
        "var dueDate=card.getAttribute('data-due-date')||'';"
        "var dueText=card.getAttribute('data-due-text')||'';"
        "var dueColor=card.getAttribute('data-due-color')||'#5f6368';"
        "var section=card.getAttribute('data-section')||'';"
        "var dc=document.getElementById('home-detail-content');"
        "dc.textContent='';"
        # Build detail DOM safely
        "var titleEl=document.createElement('div');"
        "titleEl.className='detail-title detail-title-editable';"
        "titleEl.contentEditable='true';"
        "titleEl.setAttribute('data-task-id',taskId);"
        "titleEl.setAttribute('data-orig',title);"
        "titleEl.textContent=title;dc.appendChild(titleEl);"
        # Meta tags
        "var meta=document.createElement('div');meta.className='detail-meta';"
        "var priTag=document.createElement('span');priTag.className='detail-meta-tag';"
        "priTag.style.background=pColor+'26';priTag.style.color=pColor;"
        "priTag.textContent=pLabel;meta.appendChild(priTag);"
        "if(projectName){var pTag=document.createElement('span');pTag.className='detail-meta-tag';"
        "pTag.textContent=projectName;meta.appendChild(pTag);}"
        "if(dueText){var dTag=document.createElement('span');dTag.className='detail-meta-tag';"
        "dTag.style.color=dueColor;dTag.textContent=dueText;meta.appendChild(dTag);}"
        "if(labels){labels.split(',').forEach(function(lbl){"
        "lbl=lbl.trim();if(lbl){var lTag=document.createElement('span');lTag.className='detail-meta-tag';"
        "lTag.style.color=cv('--purple');lTag.textContent='@'+lbl;meta.appendChild(lTag);}});}"
        "dc.appendChild(meta);"
        # Description section
        "var descLbl=document.createElement('div');descLbl.className='detail-section-label';"
        "descLbl.textContent='Description';dc.appendChild(descLbl);"
        "var descArea=document.createElement('textarea');descArea.className='detail-desc-editable';"
        "descArea.setAttribute('data-task-id',taskId);descArea.rows=4;"
        "descArea.placeholder='Add description...';descArea.value=description;"
        "dc.appendChild(descArea);"
        "var descSave=document.createElement('button');descSave.className='detail-action-btn detail-desc-save-btn';"
        "descSave.style.cssText='margin-bottom:8px;background:var(--accent-bg);color:var(--accent-l);border:1px solid var(--accent-b);';"
        "descSave.textContent='Save Description';dc.appendChild(descSave);"
        # Actions bar
        "var actions=document.createElement('div');actions.className='detail-actions';"
        # Priority select
        "var pSel=document.createElement('select');pSel.className='action-select detail-priority-sel';"
        "[[4,'P1'],[3,'P2'],[2,'P3'],[1,'P4']].forEach(function(p){"
        "var o=document.createElement('option');o.value=p[0];o.textContent=p[1];"
        "if(p[0]===priority)o.selected=true;pSel.appendChild(o);});"
        "actions.appendChild(pSel);"
        # Due date input
        "var dInput=document.createElement('input');dInput.type='date';dInput.className='action-select detail-due-input';"
        "dInput.value=dueDate;actions.appendChild(dInput);"
        # Complete button
        "var compBtn=document.createElement('button');compBtn.className='detail-action-btn detail-complete-btn';"
        "compBtn.style.cssText='background:rgba(34,197,94,0.10);color:#22c55e;border:1px solid rgba(34,197,94,0.20);';"
        "compBtn.textContent='Complete';actions.appendChild(compBtn);"
        # Commit/BestCase buttons
        "var labelsArr=labels?labels.split(','):[];"
        "var isCommitted=labelsArr.indexOf('Commit')!==-1;"
        "var isBestCase=labelsArr.indexOf('Best Case')!==-1;"
        "var cmBtn=document.createElement('button');cmBtn.className='detail-action-btn detail-commit-btn commit';"
        "if(isCommitted){cmBtn.style.cssText='background:rgba(34,197,94,0.10);color:#22c55e;border:1px solid rgba(34,197,94,0.20);cursor:default;';"
        "cmBtn.textContent='\\u2713 Committed';cmBtn.disabled=true;"
        "}else{cmBtn.style.cssText='background:rgba(234,179,8,0.10);color:#eab308;border:1px solid rgba(234,179,8,0.20);';"
        "cmBtn.textContent='Commit';}"
        "actions.appendChild(cmBtn);"
        "var bcBtn=document.createElement('button');bcBtn.className='detail-action-btn detail-commit-btn bestcase';"
        "if(isBestCase){bcBtn.style.cssText='background:rgba(34,197,94,0.10);color:#22c55e;border:1px solid rgba(34,197,94,0.20);';"
        "bcBtn.textContent='\\u2713 Best Case \\u2715';"
        "}else{bcBtn.style.cssText='background:rgba(167,139,250,0.10);color:#a78bfa;border:1px solid rgba(167,139,250,0.20);';"
        "bcBtn.textContent='Best Case';}"
        "actions.appendChild(bcBtn);"
        "dc.appendChild(actions);"
        # Wire up event listeners
        "pSel.addEventListener('change',function(){doSetPriority(taskId,this.value,this);});"
        "dInput.addEventListener('change',function(){doSetDueDate(taskId,this.value,this);});"
        "compBtn.addEventListener('click',function(){doComplete(taskId,compBtn);closeHomeDetail();});"
        "if(!isCommitted)cmBtn.addEventListener('click',function(){doCommitLabel(taskId,cmBtn);});"
        "if(isBestCase){bcBtn.addEventListener('click',function(){doRemoveBestCase(taskId,bcBtn);});"
        "}else{bcBtn.addEventListener('click',function(){doBestCaseLabel(taskId,bcBtn);});}"
        # Title blur-to-save
        "titleEl.addEventListener('blur',function(){"
        "var newTitle=this.textContent.trim();"
        "var orig=this.getAttribute('data-orig');"
        "if(newTitle&&newTitle!==orig){"
        "this.setAttribute('data-orig',newTitle);"
        "doHomeUpdateTask(taskId,{content:newTitle});"
        "card.setAttribute('data-content',newTitle);"
        "var ct=card.querySelector('.task-title');"
        "if(ct){ct.childNodes.forEach(function(n){if(n.nodeType===3)n.textContent=newTitle;});}"
        "}});"
        # Description save
        "descSave.addEventListener('click',function(){"
        "var newDesc=descArea.value;"
        "descSave.disabled=true;descSave.textContent='Saving...';"
        "doHomeUpdateTask(taskId,{description:newDesc},function(ok){"
        "if(ok){descSave.textContent='\\u2713 Saved';"
        "card.setAttribute('data-description',newDesc);"
        "setTimeout(function(){descSave.textContent='Save Description';descSave.disabled=false;},1500);"
        "}else{descSave.textContent='Failed';descSave.disabled=false;}"
        "});});"
        # Auto-expand description textarea
        "descArea.style.height='auto';descArea.style.height=descArea.scrollHeight+'px';"
        "var _resizeTimer;descArea.addEventListener('input',function(){var el=this;clearTimeout(_resizeTimer);"
        "_resizeTimer=setTimeout(function(){el.style.height='auto';el.style.height=el.scrollHeight+'px';},50);});"
        "dc.style.display='block';"
        "document.getElementById('home-detail-frame').style.display='none';"
        "document.getElementById('home-detail-pane').classList.add('open');"
        # Load attachments/comments
        "loadHomeAttachments(taskId,dc);"
        "}"
        "function openHomeEmail(card){"
        "if(window.innerWidth>768)return;"
        "var url=card.getAttribute('data-open-url');"
        "if(!url)return;"
        "var frame=document.getElementById('home-detail-frame');"
        "frame.src=url+'&embed=1';"
        "frame.style.display='block';"
        "document.getElementById('home-detail-content').style.display='none';"
        "document.getElementById('home-detail-pane').classList.add('open');"
        "try{window.parent.postMessage({type:'viewer-open'},'*');}catch(e){}}"
        "function closeHomeDetail(){"
        "var frame=document.getElementById('home-detail-frame');"
        "frame.src='about:blank';frame.style.display='none';"
        "document.getElementById('home-detail-content').style.display='block';"
        "document.getElementById('home-detail-content').textContent='';"
        "document.getElementById('home-detail-pane').classList.remove('open');"
        "try{window.parent.postMessage({type:'viewer-close'},'*');}catch(e){}}"
        "function closeDetailView(){closeHomeDetail();}"
        "function linkifyTitles(){"
        "document.querySelectorAll('.task-title').forEach(function(el){"
        "el.childNodes.forEach(function(node){"
        "if(node.nodeType===3){"
        "var text=node.textContent;"
        "var urlRe=/(https?:\\/\\/[^\\s\\)\\]<>]+)/g;"
        "if(urlRe.test(text)){"
        "var frag=document.createDocumentFragment();"
        "var lastIdx=0;urlRe.lastIndex=0;"
        "var m;"
        "while((m=urlRe.exec(text))!==null){"
        "if(m.index>lastIdx)frag.appendChild(document.createTextNode(text.slice(lastIdx,m.index)));"
        "var a=document.createElement('a');"
        "a.href=m[1];a.target='_blank';a.rel='noopener';"
        "a.textContent=m[1];a.onclick=function(e){e.stopPropagation();};"
        "frag.appendChild(a);"
        "lastIdx=urlRe.lastIndex;}"
        "if(lastIdx<text.length)frag.appendChild(document.createTextNode(text.slice(lastIdx)));"
        "node.parentNode.replaceChild(frag,node);"
        "}}});});}linkifyTitles();"
        "</script>"
        "</body></html>"
    )
