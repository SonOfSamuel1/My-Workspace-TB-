"""HTML view builder for Todoist views in the unified ActionOS dashboard.

Renders task cards with inline disposition controls (Move, Priority, Complete,
Due Date) for Inbox, Commit, P1, and Best Case views. Includes split-pane
email viewer for email-originated tasks and multi-select with bulk actions.
"""

import html
import re
from datetime import datetime, timezone

# Priority display: API value -> (label, color)
PRIORITY_MAP = {
    4: ("P1", "#ef4444"),
    3: ("P2", "#eab308"),
    2: ("P3", "#818cf8"),
    1: ("P4", "#56565e"),
}

VIEW_TITLES = {
    "inbox": "Inbox",
    "commit": "@commit Today",
    "p1": "Priority 1",
    "p1nodate": "P1 — No Date",
    "bestcase": "Best Case Today",
    "sabbath": "Sabbath",
}

_FONT = (
    "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,"
    "'Segoe UI',Roboto,sans-serif"
)

_CC_LABEL = "Claude"


def _relative_age(added_at):
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


def _due_date_display(due_date_str):
    """Return (text, color) for a due date string.

    Args:
        due_date_str: 'YYYY-MM-DD' or empty string.

    Returns:
        (display_text, css_color)
    """
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


def _linkify(text):
    """Convert URLs and markdown links in html-escaped text into clickable <a> tags.

    Handles:
    - Bare URLs: https://example.com, obsidian://open?vault=...
    - Todoist markdown links: [Title](https://example.com)
    - Todoist markdown links: [Title](obsidian://open?...)
      (after html-escape these appear as [Title](scheme://...)  )
    """
    _URL_SCHEMES = r"(?:https?|obsidian)"
    # First, handle markdown-style links: [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\((" + _URL_SCHEMES + r"://[^\)]+)\)",
        r'<a href="\2" target="_blank" rel="noopener" '
        r'style="color:var(--accent-l);text-decoration:underline;">\1</a>',
        text,
    )

    # Then, linkify bare URLs not already inside an href="..."
    def _replace_bare_url(m):
        url = m.group(0)
        return (
            f'<a href="{url}" target="_blank" rel="noopener" '
            f'style="color:var(--accent-l);text-decoration:underline;">{url}</a>'
        )

    text = re.sub(
        r'(?<!href=")(?<!">)(' + _URL_SCHEMES + r"://[^\s<\)]+)",
        _replace_bare_url,
        text,
    )
    return text


def _extract_gmail_link(description):
    """Pull the Gmail deep link out of a task description markdown."""
    match = re.search(
        r"\[Open in Gmail\]\(((?:https://mail\.google\.com|googlegmail://)[^\)]+)\)", description
    )
    if not match:
        return ""
    url = match.group(1)
    if url.startswith("https://mail.google.com"):
        url = url.replace("https://mail.google.com", "googlegmail://", 1)
    return url


def _extract_msg_id(description):
    """Extract the Gmail message ID from the task description."""
    match = re.search(r"🆔 \*\*Msg ID:\*\*\s*(\S+)", description)
    if match:
        return match.group(1).strip()
    return ""


def _build_task_card(
    task,
    projects_by_id,
    function_url,
    action_token,
    email_actions_url="",
    email_actions_token="",
    view_name="",
):
    """Build HTML for a single task card with disposition controls."""
    task_id = task.get("id", "")
    raw_content = task.get("content", "(no title)")
    content = html.escape(raw_content)
    content_linked = _linkify(content)
    description = task.get("description", "")
    priority = task.get("priority", 1)
    project_id = task.get("project_id", "")
    labels = task.get("labels", [])
    added_at = task.get("added_at", "") or task.get("created_at", "")

    p_label, p_color = PRIORITY_MAP.get(priority, ("P4", "#5f6368"))
    project_name = html.escape(projects_by_id.get(project_id, "Unknown"))
    age = _relative_age(added_at)

    # Due date
    due_obj = task.get("due")
    due_date = (due_obj.get("date", "") or "")[:10] if due_obj else ""
    due_text, due_color = _due_date_display(due_date)

    # Meta line: age + project + priority + due + labels
    meta_parts = []
    if age:
        meta_parts.append(age)
    meta_parts.append(project_name)
    meta_parts.append(
        f'<span style="color:{p_color};font-weight:600;">{p_label}</span>'
    )
    meta_parts.append(
        f'<span style="color:{due_color};font-weight:500;">{html.escape(due_text)}</span>'
    )
    for lbl in labels:
        meta_parts.append(
            f'<span style="color:var(--purple);">@{html.escape(lbl)}</span>'
        )
    meta_line = " &middot; ".join(meta_parts)

    # Move to project dropdown
    move_options = ['<option value="" disabled selected>Move to...</option>']
    for pid, pname in sorted(projects_by_id.items(), key=lambda x: x[1].lower()):
        selected = " disabled" if pid == project_id else ""
        move_options.append(
            f'<option value="{html.escape(pid)}"{selected}>'
            f"{html.escape(pname)}</option>"
        )
    _move_icon = (
        '<svg class="move-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/>'
        '<line x1="8" y1="18" x2="21" y2="18"/>'
        '<line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/>'
        '<line x1="3" y1="18" x2="3.01" y2="18"/></svg>'
    )
    move_select = (
        f'<div class="move-pill">'
        f"{_move_icon}"
        f'<select class="move-pill-select" '
        f"onchange=\"event.stopPropagation();doMove('{task_id}',this.value,this)\">"
        + "".join(move_options)
        + "</select>"
        f"</div>"
    )

    # Priority dropdown
    priority_options = []
    for pval in [4, 3, 2, 1]:
        pl, pc = PRIORITY_MAP[pval]
        sel = " selected" if pval == priority else ""
        priority_options.append(f'<option value="{pval}"{sel}>{pl}</option>')
    priority_select = (
        f'<select class="action-select" '
        f"onchange=\"event.stopPropagation();doSetPriority('{task_id}',this.value,this,'{p_color}')\">"
        + "".join(priority_options)
        + "</select>"
    )

    # Due date input
    _date_icon = (
        '<svg class="date-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="3" width="18" height="18" rx="3"/>'
        '<line x1="3" y1="9" x2="21" y2="9"/>'
        '<circle cx="12" cy="15.5" r="1.2" fill="currentColor" stroke="none"/></svg>'
    )
    has_date = bool(due_date)
    icon_display = ' style="display:none"' if has_date else ""
    input_display = "" if has_date else ' style="display:none"'
    due_date_input = (
        f"<div class=\"date-pill\" onclick=\"var i=this.querySelector('input');var w=this.querySelector('.date-icon-wrap');var l=this.querySelector('.date-label');i.style.display='';if(w)w.style.display='none';if(l)l.style.display='none';i.showPicker?i.showPicker():i.focus()\">"
        f'<span class="date-icon-wrap"{icon_display}>{_date_icon}</span>'
        f'<span class="date-label"{icon_display}>Date</span>'
        f'<input type="date" class="date-pill-input" value="{html.escape(due_date)}" '
        f"{input_display} "
        f'onclick="event.stopPropagation()" '
        f"onchange=\"event.stopPropagation();dateChanged(this,'{task_id}')\">"
        f"</div>"
    )

    # Complete button
    complete_btn = (
        f'<button class="complete-btn" '
        f"onclick=\"event.stopPropagation();doComplete('{task_id}',this)\">"
        "Complete</button>"
    )

    # Status buttons — code view uses Planned/In Progress/Backlog; others use Commit/Best Case
    is_committed = "Commit" in labels
    is_bestcase = "Best Case" in labels
    is_planned = "Planned" in labels
    is_in_progress = "In Progress" in labels
    is_backlog = "Backlog" in labels

    if view_name == "code":
        # Planned button
        if is_planned:
            commit_btn = (
                f'<button class="commit-btn committed" '
                f"onclick=\"event.stopPropagation();doRemovePlanned('{task_id}',this)\">"
                "\u2713 Planned</button>"
            )
        else:
            commit_btn = (
                f'<button class="commit-btn" '
                f"onclick=\"event.stopPropagation();doPlanned('{task_id}',this)\">"
                "Planned</button>"
            )
        # In Progress button
        if is_in_progress:
            bestcase_btn = (
                f'<button class="bestcase-btn remove" '
                f"onclick=\"event.stopPropagation();doRemoveInProgress('{task_id}',this)\">"
                "\u2713 In Progress</button>"
            )
        else:
            bestcase_btn = (
                f'<button class="bestcase-btn" '
                f"onclick=\"event.stopPropagation();doInProgress('{task_id}',this)\">"
                "In Progress</button>"
            )
        # Backlog button
        backlog_btn = ""
        if is_backlog:
            backlog_btn = (
                f'<button class="commit-btn remove" '
                f"onclick=\"event.stopPropagation();doRemoveBacklog('{task_id}',this)\">"
                "\u2713 Backlog</button>"
            )
        else:
            backlog_btn = (
                f'<button class="commit-btn" '
                f'style="background:var(--border);color:var(--text-2);border-color:var(--border-h);" '
                f"onclick=\"event.stopPropagation();doBacklog('{task_id}',this)\">"
                "Backlog</button>"
            )
    else:
        backlog_btn = ""
        # Commit button (on commit view: show "Remove Commit" instead of disabled)
        if is_committed and view_name == "commit":
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
                f"onclick=\"event.stopPropagation();doCommit('{task_id}',this)\">"
                "Commit</button>"
            )
        # Best Case button (on bestcase view: show "Remove Best Case" instead of toggle)
        if is_bestcase and view_name == "bestcase":
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
                f"onclick=\"event.stopPropagation();doBestCase('{task_id}',this)\">"
                "Best Case</button>"
            )

    # Schedule button — opens duration picker modal to create calendar events
    schedule_btn = (
        f'<button class="schedule-btn" '
        f"onclick=\"event.stopPropagation();openScheduleModal('{task_id}')\">"
        '<svg class="schedule-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01M16 18h.01"/></svg>'
        " Schedule</button>"
    )

    # Assign CC button — copy task info to clipboard for Claude Code (all views)
    copy_claude_btn = (
        f'<button class="assign-cc-btn" title="Assign CC" '
        f"onclick=\"event.stopPropagation();doCopyForClaude('{task_id}','{content}',this)\">"
        + _CC_LABEL
        + "</button>"
    )

    # Detect email-originated tasks for split-pane viewer
    gmail_link = _extract_gmail_link(description)
    msg_id_field = _extract_msg_id(description)
    data_viewer_attrs = ""
    if gmail_link and email_actions_url and email_actions_token:
        thread_id = gmail_link.split("#inbox/")[-1] if "#inbox/" in gmail_link else ""
        lookup_id = msg_id_field or thread_id
        if lookup_id:
            viewer_url = (
                email_actions_url.rstrip("/")
                + "?action=open&msg_id="
                + lookup_id
                + ("&thread_id=" + thread_id if thread_id else "")
                + "&token="
                + email_actions_token
                + "&embed=1"
            )
            data_viewer_attrs = (
                f' data-open-url="{html.escape(viewer_url)}"'
                f' data-msg-id="{html.escape(lookup_id)}"'
            )
    card_click = ' onclick="openTaskDetail(this)"'

    # Checkbox for multi-select
    checkbox = (
        '<input type="checkbox" class="select-cb" style="display:none" '
        'onclick="event.stopPropagation();updateSelection()">'
    )

    return (
        f'<div class="task-card" id="card-{task_id}"'
        f' data-task-id="{task_id}"'
        f' data-project-id="{html.escape(project_id)}"'
        f' data-content="{content}"'
        f' data-description="{html.escape(description)}"'
        f' data-project-name="{project_name}"'
        f' data-priority="{priority}"'
        f' data-priority-label="{p_label}"'
        f' data-priority-color="{p_color}"'
        f' data-labels="{html.escape(",".join(labels))}"'
        f' data-due-date="{html.escape(due_date)}"'
        f' data-due-text="{html.escape(due_text)}"'
        f' data-due-color="{due_color}"'
        f' data-created="{html.escape(added_at)}"'
        f"{data_viewer_attrs}{card_click}>"
        f'<div class="card-row">'
        f"{checkbox}"
        f'<div class="card-content">'
        f'<div class="task-title">{content_linked}</div>'
        f'<div class="task-meta">{meta_line}</div>'
        f'<div class="task-actions">{move_select}{priority_select}{due_date_input}{complete_btn}{commit_btn}{bestcase_btn}{backlog_btn}{schedule_btn}{copy_claude_btn}</div>'
        f"</div></div>"
        f'<div class="undo-bar" style="display:none;"></div>'
        f"</div>"
    )


def build_view_html(
    tasks,
    projects,
    view_name,
    function_url,
    action_token,
    embed=False,
    email_actions_url="",
    email_actions_token="",
    checklists=None,
):
    """Build the full HTML page for a Todoist view.

    Args:
        tasks: List of task dicts from Todoist API.
        projects: List of project dicts from Todoist API.
        view_name: One of 'inbox', 'commit', 'p1'.
        function_url: Base Lambda function URL for action requests.
        action_token: Secret token for authenticating action requests.
        embed: If True, hides header and posts count to parent via postMessage.
        email_actions_url: Gmail email-actions Lambda Function URL.
        email_actions_token: Auth token for email-actions Lambda.
    """
    title = VIEW_TITLES.get(view_name, view_name.title())
    count = len(tasks)

    # Build project lookup
    projects_by_id = {p["id"]: p.get("name", "Unknown") for p in projects}

    # Build project options JSON for bulk move toolbar
    project_options_html = '<option value="" disabled selected>Move to...</option>'
    for pid, pname in sorted(projects_by_id.items(), key=lambda x: x[1].lower()):
        project_options_html += (
            f'<option value="{html.escape(pid)}">{html.escape(pname)}</option>'
        )

    # Build task cards
    cards_html = ""
    if tasks:
        for task in tasks:
            cards_html += _build_task_card(
                task,
                projects_by_id,
                function_url,
                action_token,
                email_actions_url=email_actions_url,
                email_actions_token=email_actions_token,
                view_name=view_name,
            )
    else:
        cards_html = (
            '<div style="text-align:center;padding:60px 20px;color:var(--text-2);">'
            '<div style="font-size:36px;margin-bottom:12px;">&#10003;</div>'
            f'<div style="font-size:16px;">No {title.lower()} items</div>'
            "</div>"
        )

    # Action base URL
    base_action_url = function_url.rstrip("/")

    # Header bar (hidden in embed mode)
    header_html = ""
    if not embed:
        header_html = (
            '<div class="top-bar">'
            f'<span class="top-bar-title">{title}</span>'
            f'<span class="top-bar-count">{count} tasks</span>'
            '<button class="refresh-btn" onclick="location.reload()">&#8635; Refresh</button>'
            "</div>"
        )

    # Subheader with count + select all
    subheader_html = ""
    if tasks:
        subheader_html = (
            '<div class="subheader">'
            '<label class="select-all-label" style="display:none">'
            '<input type="checkbox" id="select-all-cb" onclick="toggleSelectAll()">'
            " Select All</label>"
            f'<span id="task-count-display" style="margin-left:auto;font-size:12px;color:var(--text-2);">'
            f"{count} tasks</span>"
            "</div>"
        )

    # postMessage script for embed mode
    post_message_js = ""
    if embed:
        post_message_js = (
            f'window.parent.postMessage({{type:"count",source:"{view_name}",'
            f'count:{count}}},"*");'
        )

    # Checklist card for commit view
    checklist_card_html = ""
    checklist_css = ""
    checklist_js = ""
    if view_name == "commit" and checklists is not None:
        cl_key = "remember_power_christ"
        cl_content = html.escape(checklists.get(cl_key, ""))
        checklist_card_html = (
            f'<div class="checklist-card" data-section="{cl_key}">'
            f'<div class="checklist-header">'
            f'<span class="checklist-title">Remember Your Power in Christ</span>'
            f'<button class="checklist-edit-btn" id="cl-btn-{cl_key}" '
            f"onclick=\"toggleChecklist('{cl_key}')\">"
            f"Edit</button>"
            f"</div>"
            f'<div class="checklist-body" id="cl-body-{cl_key}" contenteditable="false">'
            f"{cl_content}"
            f"</div></div>"
        )
        checklist_css = (
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
        )
        save_url = base_action_url + "?action=calendar_save_checklist"
        checklist_js = (
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
            f"var url='{save_url}';"
            "fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},"
            "body:JSON.stringify({section:section,content:content})})"
            ".then(function(r){return r.json();})"
            ".then(function(d){"
            "if(!d.ok){alert('Save failed');}"
            "}).catch(function(){alert('Save failed');});}"
        )

    # Determine split-pane height
    split_height = "calc(100vh - 56px)" if not embed else "100vh"

    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Cache-Control" content="no-cache,no-store,must-revalidate">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700'
        '&display=swap" rel="stylesheet">'
        f"<title>{html.escape(title)}</title>"
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
        "--scrollbar:rgba(0,0,0,0.12);color-scheme:light;}}"
        "*{box-sizing:border-box;margin:0;padding:0;}"
        f"body{{font-family:{_FONT};background:var(--bg-base);color:var(--text-1);"
        "-webkit-font-smoothing:antialiased;}"
        + (".top-bar{display:none;}" if embed else "")
        + ".top-bar{background:var(--bg-s0);border-bottom:1px solid var(--border);padding:14px 20px;display:flex;"
        "align-items:center;gap:12px;}"
        ".top-bar-title{color:var(--text-1);font-size:17px;font-weight:600;"
        "letter-spacing:-0.2px;}"
        ".top-bar-count{color:var(--text-2);font-size:13px;}"
        ".refresh-btn{margin-left:auto;background:var(--border);"
        "border:1px solid var(--border);color:var(--text-1);font-size:13px;font-weight:600;"
        "padding:6px 14px;border-radius:6px;cursor:pointer;}"
        ".refresh-btn:hover{background:var(--border-h);}"
        # Subheader
        ".subheader{display:none;}"
        ".select-all-label{display:none;}"
        # Split-pane layout
        f".split-wrap{{display:flex;height:{split_height};overflow:hidden;}}"
        ".left-pane{flex:0 0 45%;overflow-y:auto;}"
        "#viewer-pane{display:flex;flex-direction:column;flex:1 1 55%;"
        "border-left:1px solid var(--border);background:var(--bg-base);position:relative;}"
        "#viewer-frame{flex:1;border:none;width:100%;display:none;}"
        "#detail-content{flex:1;overflow-y:auto;padding:24px;display:none;}"
        ".close-btn{position:absolute;top:10px;right:14px;z-index:10;"
        "background:var(--border);border:none;font-size:22px;cursor:pointer;"
        "width:36px;height:36px;border-radius:50%;display:flex;"
        "align-items:center;justify-content:center;color:var(--text-2);}"
        ".close-btn:hover{background:var(--border-h);}"
        ".viewer-mobile-header{display:none;}"
        ".viewer-back-btn{display:flex;align-items:center;gap:6px;background:none;border:none;"
        "color:var(--accent-l);font-family:inherit;font-size:15px;font-weight:600;"
        "cursor:pointer;padding:8px 4px;touch-action:manipulation;}"
        # Task list
        ".task-list{max-width:700px;margin:0 auto;padding:12px 16px;}"
        ".task-card{background:var(--bg-s1);border-radius:8px;"
        "border:1px solid var(--border);padding:14px 16px;"
        "margin-bottom:10px;transition:opacity .15s ease-out,transform .15s ease-out,border-color .15s ease-out,background .15s ease-out;cursor:pointer;}"
        ".task-card:hover{border-color:var(--border-h);background:var(--bg-s2);}"
        ".task-card.active-card{background:var(--accent-hbg);border-color:var(--accent-b);}"
        ".task-card.removing{opacity:0;transform:translateX(60px);"
        "margin-bottom:0;padding-top:0;padding-bottom:0;max-height:0;"
        "overflow:hidden;}"
        ".card-row{display:flex;align-items:flex-start;gap:10px;}"
        ".card-content{flex:1;min-width:0;}"
        ".select-cb{display:none;}"
        ".task-title{font-size:15px;font-weight:600;color:var(--text-1);"
        "line-height:1.4;margin-bottom:4px;word-break:break-word;}"
        ".task-title a{font-weight:500;}"
        ".task-meta{font-size:12px;color:var(--text-2);margin-bottom:10px;"
        "line-height:1.5;}"
        ".task-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center;}"
        ".action-select{font-family:inherit;font-size:12px;padding:5px 8px;"
        "border:1px solid var(--border);border-radius:6px;background:var(--bg-s2);"
        "color:var(--text-1);cursor:pointer;}"
        ".action-select:focus{outline:none;border-color:rgba(99,102,241,0.5);box-shadow:0 0 0 2px rgba(99,102,241,0.15);}"
        ".move-pill{display:inline-flex;align-items:center;gap:6px;"
        "background:var(--bg-s2);border:1px solid var(--border-h);border-radius:100px;"
        "padding:6px 12px;cursor:pointer;transition:border-color .15s;flex-shrink:0;}"
        ".move-pill:hover{border-color:var(--text-3);}"
        ".move-icon{flex-shrink:0;color:var(--text-2);}"
        ".move-pill-select{font-family:inherit;font-size:12px;font-weight:500;"
        "background:transparent;border:none;color:var(--text-2);cursor:pointer;"
        "-webkit-appearance:none;appearance:none;outline:none;padding:0;"
        "max-width:90px;}"
        ".date-pill{display:inline-flex;align-items:center;gap:6px;position:relative;"
        "background:var(--bg-s2);border:1px solid var(--border-h);border-radius:100px;"
        "padding:6px 12px;cursor:pointer;transition:border-color .15s;flex-shrink:0;}"
        ".date-pill:hover{border-color:var(--text-3);}"
        ".date-icon-wrap{display:inline-flex;align-items:center;flex-shrink:0;}"
        ".date-icon{color:var(--text-2);}"
        ".date-label{font-size:12px;font-weight:500;color:var(--text-2);}"
        ".date-pill-input{font-family:inherit;font-size:12px;font-weight:500;"
        "background:transparent;border:none;color:var(--text-2);cursor:pointer;"
        "-webkit-appearance:none;appearance:none;outline:none;padding:0;"
        "color-scheme:dark;max-width:110px;}"
        ".date-pill-input::-webkit-calendar-picker-indicator{opacity:0;position:absolute;"
        "right:0;width:100%;height:100%;cursor:pointer;}"
        "@media(prefers-color-scheme:light){.date-pill-input{color-scheme:light;}}"
        ".complete-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-b);cursor:pointer;"
        "transition:background .15s ease-out;}"
        ".complete-btn:hover{background:var(--ok-b);}"
        ".complete-btn:disabled{background:rgba(34,197,94,0.05);color:rgba(34,197,94,0.4);border-color:var(--ok-bg);cursor:default;}"
        ".commit-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn-b);cursor:pointer;"
        "transition:background .15s ease-out;}"
        ".commit-btn:hover{background:var(--warn-b);}"
        ".commit-btn.committed{background:var(--ok-bg);color:var(--ok);border-color:var(--ok-b);cursor:default;}"
        ".commit-btn.remove{background:var(--err-bg);color:var(--err);border-color:var(--err-b);}"
        ".commit-btn.remove:hover{background:var(--err-b);}"
        ".bestcase-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:var(--purple-bg);color:var(--purple);border:1px solid var(--purple-b);cursor:pointer;"
        "transition:background .15s ease-out;}"
        ".bestcase-btn:hover{background:var(--purple-b);}"
        ".bestcase-btn.active{background:var(--ok-bg);color:var(--ok);border-color:var(--ok-b);cursor:default;}"
        ".bestcase-btn.remove{background:var(--ok-bg);color:var(--ok);border-color:var(--ok-b);}"
        ".bestcase-btn.remove:hover{background:var(--err-bg);color:var(--err);border-color:var(--err-b);}"
        ".assign-cc-btn{display:inline-flex;align-items:center;justify-content:center;"
        "padding:5px 10px;border-radius:6px;"
        "background:rgba(196,120,64,0.10);border:1px solid rgba(196,120,64,0.25);"
        "cursor:pointer;transition:background .15s;color:#c47840;font-size:13px;font-weight:600;}"
        ".assign-cc-btn:hover{background:rgba(196,120,64,0.25);}"
        # Schedule button
        ".schedule-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:rgba(56,189,248,0.10);color:#38bdf8;border:1px solid rgba(56,189,248,0.20);cursor:pointer;"
        "transition:background .15s ease-out;display:inline-flex;align-items:center;gap:4px;}"
        ".schedule-btn:hover{background:rgba(56,189,248,0.25);}"
        ".schedule-icon{flex-shrink:0;}"
        # Schedule modal
        "#schedule-overlay{display:none;position:fixed;top:0;left:0;right:0;bottom:0;"
        "z-index:2000;background:rgba(0,0,0,0.6);align-items:center;justify-content:center;}"
        "#schedule-overlay.open{display:flex;}"
        "#schedule-modal{background:var(--bg-s1);border:1px solid var(--border);border-radius:14px;"
        "padding:24px;width:320px;max-width:90vw;box-shadow:0 8px 32px rgba(0,0,0,0.4);}"
        "#schedule-modal h3{font-size:16px;font-weight:700;color:var(--text-1);margin-bottom:4px;}"
        "#schedule-modal p{font-size:13px;color:var(--text-2);margin-bottom:16px;}"
        ".duration-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px;}"
        ".duration-opt{font-family:inherit;font-size:14px;font-weight:600;"
        "padding:12px 8px;border-radius:8px;border:1px solid var(--border);"
        "background:var(--bg-s2);color:var(--text-1);cursor:pointer;"
        "transition:all .15s;text-align:center;}"
        ".duration-opt:hover{border-color:rgba(56,189,248,0.4);background:rgba(56,189,248,0.08);color:#38bdf8;}"
        ".duration-opt.selected{border-color:#38bdf8;background:rgba(56,189,248,0.15);color:#38bdf8;}"
        "#schedule-confirm{width:100%;font-family:inherit;font-size:14px;font-weight:700;"
        "padding:12px;border-radius:8px;border:none;cursor:pointer;"
        "background:#38bdf8;color:#0e0e10;transition:opacity .15s;}"
        "#schedule-confirm:hover{opacity:0.85;}"
        "#schedule-confirm:disabled{opacity:0.4;cursor:default;}"
        "#schedule-cancel{width:100%;font-family:inherit;font-size:13px;font-weight:600;"
        "padding:8px;border-radius:8px;border:none;cursor:pointer;margin-top:8px;"
        "background:transparent;color:var(--text-2);}"
        "#schedule-cancel:hover{color:var(--text-1);}"
        ".task-card.undo-state .card-row{display:none;}"
        ".undo-bar{display:flex;align-items:center;justify-content:center;"
        "gap:10px;padding:12px 0;font-size:13px;color:var(--text-2);}"
        ".undo-bar a{color:var(--accent-l);font-weight:600;cursor:pointer;"
        "text-decoration:none;}"
        ".undo-bar a:hover{text-decoration:underline;}"
        # Bulk toolbar
        "#bulk-toolbar{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);"
        "background:#16161af2;border:1px solid var(--border);color:var(--text-1);padding:10px 18px;border-radius:12px;"
        "box-shadow:0 4px 16px rgba(0,0,0,.25);display:none;align-items:center;gap:10px;"
        "z-index:500;font-size:13px;font-weight:500;}"
        "#bulk-toolbar select{font-size:12px;padding:5px 8px;border-radius:6px;border:1px solid var(--border-h);"
        "background:var(--bg-s2);color:var(--text-1);}"
        "#bulk-toolbar button{font-size:12px;font-weight:600;padding:6px 14px;"
        "border:none;border-radius:6px;cursor:pointer;}"
        ".bulk-complete-btn{background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-b);}"
        ".bulk-complete-btn:hover{background:var(--ok-b);}"
        ".bulk-date-input{font-size:12px;padding:5px 8px;border-radius:6px;"
        "border:1px solid var(--border-h);background:var(--bg-s2);color:var(--text-1);}"
        ".detail-title{font-size:20px;font-weight:700;color:var(--text-1);"
        "line-height:1.4;margin-bottom:16px;}"
        ".detail-title-editable{outline:none;border-radius:4px;padding:2px 4px;margin:-2px -4px;"
        "transition:background .15s;}"
        ".detail-title-editable:hover{background:var(--bg-s2);}"
        ".detail-title-editable:focus{background:var(--bg-s2);box-shadow:0 0 0 2px rgba(99,102,241,0.3);}"
        ".detail-desc-editable{width:100%;font-family:inherit;font-size:14px;color:var(--text-1);"
        "background:var(--bg-s2);border:1px solid var(--border);border-radius:6px;"
        "padding:8px 10px;resize:vertical;line-height:1.5;margin-bottom:8px;min-height:100px;}"
        ".detail-desc-editable:focus{outline:none;border-color:rgba(99,102,241,0.5);}"
        ".detail-meta{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;}"
        ".detail-meta-tag{display:inline-block;padding:4px 10px;border-radius:6px;"
        "font-size:12px;font-weight:600;background:var(--border);color:var(--text-2);}"
        ".detail-section-label{font-size:11px;font-weight:600;text-transform:uppercase;"
        "color:var(--text-3);letter-spacing:0.5px;margin-bottom:6px;}"
        ".detail-description{font-size:14px;line-height:1.7;color:var(--text-2);"
        "white-space:pre-wrap;margin-bottom:20px;padding:16px;background:var(--bg-s2);"
        "border-radius:8px;border:1px solid var(--border);}"
        ".detail-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px;"
        "padding-top:16px;border-top:1px solid var(--border);}"
        ".detail-action-btn{font-family:inherit;font-size:13px;font-weight:600;"
        "padding:8px 18px;border:none;border-radius:8px;cursor:pointer;}"
        ".view-email-btn{background:var(--accent-bg);color:var(--accent-l);border:1px solid var(--accent-b);}"
        ".detail-attachments{margin-top:16px;}"
        ".detail-attachments .detail-section-label{margin-bottom:10px;}"
        ".attachment-grid{display:flex;flex-wrap:wrap;gap:10px;}"
        ".attachment-item{border-radius:8px;border:1px solid var(--border);overflow:hidden;"
        "background:var(--bg-s2);}"
        ".attachment-item img{display:block;max-width:100%;height:auto;cursor:pointer;}"
        ".attachment-item a{display:flex;align-items:center;gap:8px;padding:10px 14px;"
        "color:var(--accent-l);text-decoration:none;font-size:13px;font-weight:500;}"
        ".attachment-item a:hover{background:var(--border);}"
        ".attachment-file-icon{width:20px;height:20px;flex-shrink:0;}"
        ".comment-text{font-size:13px;color:var(--text-2);padding:8px 0;line-height:1.5;}"
        "#lb-overlay{display:none;position:fixed;top:0;left:0;right:0;bottom:0;"
        "z-index:1000;background:rgba(0,0,0,0.92);flex-direction:column;"
        "align-items:center;justify-content:center;touch-action:none;}"
        "#lb-overlay.lb-open{display:flex;}"
        "#lb-img{max-width:95vw;max-height:85vh;object-fit:contain;"
        "border-radius:4px;-webkit-user-drag:none;}"
        "#lb-close{position:absolute;top:14px;right:18px;font-size:32px;"
        "color:#fff;background:none;border:none;cursor:pointer;line-height:1;opacity:0.85;}"
        "#lb-close:hover{opacity:1;}"
        "#lb-prev,#lb-next{position:absolute;top:50%;transform:translateY(-50%);"
        "font-size:28px;color:rgba(255,255,255,0.7);background:none;border:none;"
        "cursor:pointer;padding:12px 16px;-webkit-user-select:none;user-select:none;}"
        "#lb-prev{left:4px;}#lb-next{right:4px;}"
        "#lb-prev:hover,#lb-next:hover{color:#fff;}"
        "#lb-counter{position:absolute;bottom:16px;color:rgba(255,255,255,0.6);"
        "font-size:13px;font-family:inherit;}"
        "@media(max-width:768px){"
        ".task-actions{gap:6px;}"
        ".action-select,.complete-btn{font-size:11px;padding:4px 6px;}"
        ".move-pill{padding:4px 10px 4px 8px;}"
        ".move-pill-select{font-size:11px;}"
        ".date-pill{padding:4px 10px 4px 8px;}"
        ".date-pill-input{font-size:11px;}"
        ".left-pane{flex:1 1 100%!important;}"
        "#viewer-pane{display:none;position:fixed;top:0;left:0;right:0;bottom:0;z-index:200;"
        "border-left:none;}"
        ".close-btn{display:none!important;}"
        ".viewer-mobile-header{display:flex;align-items:center;background:transparent;"
        "padding:0 12px;height:52px;flex-shrink:0;z-index:12;}"
        "#bulk-toolbar{left:10px;right:10px;transform:none;flex-wrap:wrap;"
        "justify-content:center;}"
        "}"
        "::-webkit-scrollbar{width:6px;}"
        "::-webkit-scrollbar-track{background:transparent;}"
        "::-webkit-scrollbar-thumb{background:var(--scrollbar);border-radius:3px;}"
        + checklist_css
        + "</style>"
        "</head><body>" + header_html + '<div class="split-wrap" id="split-wrap">'
        # Left pane — task list
        + '<div class="left-pane">'
        + subheader_html
        + '<div class="task-list">'
        + checklist_card_html
        + cards_html
        + "</div></div>"
        # Right pane — task detail / email viewer
        + '<div id="viewer-pane">'
        '<div class="viewer-mobile-header">'
        '<button class="viewer-back-btn" onclick="closeViewer()">&#8592; Back to list</button>'
        "</div>"
        '<button class="close-btn" onclick="closeViewer()" title="Close">&times;</button>'
        '<div id="viewer-placeholder" style="'
        "flex:1;display:flex;flex-direction:column;align-items:center;"
        'justify-content:center;color:var(--text-3);font-size:15px;gap:12px;">'
        '<span style="font-size:40px;">&#9776;</span>'
        "<span>Select a task to view details</span>"
        "</div>"
        '<div id="detail-content"></div>'
        '<iframe id="viewer-frame" src="about:blank"></iframe>'
        '<div id="lb-overlay" role="dialog" aria-modal="true"'
        ' onclick="if(event.target===this)closeLightbox()">'
        '<button id="lb-close" onclick="closeLightbox()" aria-label="Close">&times;</button>'
        '<button id="lb-prev" onclick="lightboxNav(-1)" aria-label="Previous"'
        ' style="display:none;">&#8249;</button>'
        '<img id="lb-img" src="" alt="">'
        '<button id="lb-next" onclick="lightboxNav(1)" aria-label="Next"'
        ' style="display:none;">&#8250;</button>'
        '<span id="lb-counter"></span>'
        "</div>"
        "</div>" + "</div>"  # end split-wrap
        # Bulk toolbar
        + '<div id="bulk-toolbar">'
        '<span id="bulk-count">0 selected</span>'
        f'<select id="bulk-move-select" onchange="bulkMove(this.value);this.selectedIndex=0;">'
        f"{project_options_html}</select>"
        '<input type="date" class="bulk-date-input" id="bulk-date-input" '
        'onchange="bulkSetDueDate(this.value);this.value=\'\';" title="Set due date">'
        '<button class="bulk-complete-btn" onclick="bulkComplete()">Complete</button>'
        "</div>"
        # Schedule duration picker modal
        + '<div id="schedule-overlay" onclick="if(event.target===this)closeScheduleModal()">'
        '<div id="schedule-modal">'
        "<h3>Schedule Action</h3>"
        '<p id="schedule-task-label">How long will this take?</p>'
        '<div class="duration-grid">'
        '<button class="duration-opt" data-mins="30">30 min</button>'
        '<button class="duration-opt" data-mins="60">1 hr</button>'
        '<button class="duration-opt" data-mins="90">1.5 hrs</button>'
        '<button class="duration-opt" data-mins="120">2 hrs</button>'
        '<button class="duration-opt" data-mins="150">2.5 hrs</button>'
        '<button class="duration-opt" data-mins="180">3 hrs</button>'
        '<button class="duration-opt" data-mins="210">3.5 hrs</button>'
        '<button class="duration-opt" data-mins="240">4 hrs</button>'
        '<button class="duration-opt" data-mins="270">4.5 hrs</button>'
        '<button class="duration-opt" data-mins="300">5 hrs</button>'
        "</div>"
        '<button id="schedule-confirm" disabled>Schedule</button>'
        '<button id="schedule-cancel" onclick="closeScheduleModal()">Cancel</button>'
        "</div></div>"
        # JavaScript
        + "<script>"
        "var _cs=getComputedStyle(document.documentElement);function cv(n){return _cs.getPropertyValue(n).trim();}"
        "var _ccIcon='Claude';"
        f'var viewName="{view_name}";'
        "var taskCount="
        + str(count)
        + ";"
        + post_message_js
        + "function updateCount(){"
        "taskCount--;"
        "if(taskCount<0)taskCount=0;"
        + (
            f'window.parent.postMessage({{type:"count",source:"{view_name}",'
            'count:taskCount},"*");'
            if embed
            else ""
        )
        + "var el=document.getElementById('task-count-display');"
        "if(el){el.textContent=taskCount+' tasks';}"
        "}"
        "function undoCount(){"
        "taskCount++;"
        + (
            f'window.parent.postMessage({{type:"count",source:"{view_name}",'
            'count:taskCount},"*");'
            if embed
            else ""
        )
        + "var el=document.getElementById('task-count-display');"
        "if(el){el.textContent=taskCount+' tasks';}"
        "}"
        "var undoTimers={};"
        "function removeCard(id){"
        "var card=document.getElementById('card-'+id);"
        "if(card){card.classList.add('removing');"
        "setTimeout(function(){card.remove();},350);}"
        "}"
        "function showUndo(taskId,msg,onUndo){"
        "var card=document.getElementById('card-'+taskId);"
        "if(!card)return;"
        "card.classList.add('undo-state');"
        "var bar=card.querySelector('.undo-bar');"
        "bar.innerHTML=msg+' <a onclick=\"undoTimers[\\''+taskId+'\\'].undo()\">Undo</a>';"
        "bar.style.display='flex';"
        "updateCount();"
        "var timer=setTimeout(function(){delete undoTimers[taskId];removeCard(taskId);},5000);"
        "undoTimers[taskId]={timer:timer,undo:function(){"
        "clearTimeout(timer);delete undoTimers[taskId];"
        "bar.innerHTML='Undoing...';onUndo();}};"
        "}"
        "function restoreCard(taskId){"
        "var card=document.getElementById('card-'+taskId);"
        "if(!card)return;"
        "card.classList.remove('undo-state');"
        "var bar=card.querySelector('.undo-bar');"
        "bar.style.display='none';bar.innerHTML='';"
        "undoCount();"
        "}"
        # Move action
        "function doMove(taskId,projectId,sel){"
        "if(!projectId)return;"
        "var card=document.getElementById('card-'+taskId);"
        "var origProjectId=card?card.getAttribute('data-project-id'):'';"
        "var projName=sel.options[sel.selectedIndex].text;"
        "sel.disabled=true;"
        f'fetch("{base_action_url}?action=move&task_id="+taskId+"&project_id="+projectId)'
        ".then(function(r){if(r.ok){"
        "showUndo(taskId,'Moved to '+projName+'.',function(){"
        f'fetch("{base_action_url}?action=move&task_id="+taskId+"&project_id="+origProjectId)'
        ".then(function(r2){if(r2.ok){sel.disabled=false;sel.selectedIndex=0;"
        "restoreCard(taskId);}else{removeCard(taskId);}})"
        ".catch(function(){removeCard(taskId);});});"
        '}else{sel.disabled=false;alert("Move failed");}})'
        '.catch(function(){sel.disabled=false;alert("Move failed");});'
        "}"
        # Priority action
        "function doSetPriority(taskId,priority,sel){"
        "sel.disabled=true;"
        f'fetch("{base_action_url}?action=priority&task_id="+taskId+"&priority="+priority)'
        ".then(function(r){if(r.ok){"
        "sel.disabled=false;"
        "}else{"
        'sel.disabled=false;alert("Priority update failed");}})'
        '.catch(function(){sel.disabled=false;alert("Priority update failed");});'
        "}"
        # Due date action
        "function dateChanged(input,taskId){"
        "var pill=input.closest('.date-pill');"
        "var ico=pill.querySelector('.date-icon-wrap');"
        "var lbl=pill.querySelector('.date-label');"
        "if(input.value){"
        "input.style.display='';if(ico)ico.style.display='none';if(lbl)lbl.style.display='none';"
        "}else{"
        "input.style.display='none';if(ico)ico.style.display='';if(lbl)lbl.style.display='';"
        "}"
        "doSetDueDate(taskId,input.value,input);}"
        "function doSetDueDate(taskId,dateValue,input){"
        "input.disabled=true;"
        f'fetch("{base_action_url}?action=due_date&task_id="+taskId+"&date="+encodeURIComponent(dateValue))'
        ".then(function(r){return r.json();})"
        ".then(function(d){if(d.ok){"
        "input.disabled=false;"
        "input.style.borderColor='rgba(34,197,94,0.5)';"
        "setTimeout(function(){input.style.borderColor='';},1500);"
        # Commit view: auto-remove card when date pushed to future
        "if(viewName==='commit'&&dateValue){"
        "var today=new Date().toISOString().slice(0,10);"
        "if(dateValue>today){"
        "showUndo(taskId,'Moved to '+dateValue+'.',function(){"
        f'fetch("{base_action_url}?action=due_date&task_id="+taskId+"&date="+encodeURIComponent(today))'
        ".then(function(r2){return r2.json();})"
        ".then(function(d2){if(d2.ok){input.disabled=false;input.value=today;"
        "restoreCard(taskId);}else{removeCard(taskId);}})"
        ".catch(function(){removeCard(taskId);});});"
        "updateCount();}}"
        "}else{"
        'input.disabled=false;alert("Due date update failed");}})'
        '.catch(function(){input.disabled=false;alert("Due date update failed");});'
        "}"
        # Complete action
        "function doComplete(taskId,btn){"
        "btn.disabled=true;btn.textContent='...';"
        f'fetch("{base_action_url}?action=complete&task_id="+taskId)'
        ".then(function(r){if(r.ok){"
        "showUndo(taskId,'Completed.',function(){"
        f'fetch("{base_action_url}?action=reopen&task_id="+taskId)'
        ".then(function(r2){if(r2.ok){btn.disabled=false;btn.textContent='Complete';"
        "restoreCard(taskId);}else{removeCard(taskId);}})"
        ".catch(function(){removeCard(taskId);});});"
        '}else{btn.disabled=false;btn.textContent="Complete";alert("Complete failed");}})'
        '.catch(function(){btn.disabled=false;btn.textContent="Complete";'
        'alert("Complete failed");});'
        "}"
        # Commit action
        "function doCommit(taskId,btn){"
        "btn.disabled=true;btn.textContent='...';"
        f'fetch("{base_action_url}?action=commit_label&task_id="+taskId)'
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "btn.textContent='\\u2713 Committed';"
        "btn.classList.add('committed');"
        "btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        # Reset sibling Best Case button since labels are mutually exclusive
        "var card=btn.closest('.task-card');"
        "if(card){var bc=card.querySelector('.bestcase-btn');"
        "if(bc){bc.textContent='Best Case';bc.classList.remove('active');"
        "bc.style.background=cv('--purple-bg');bc.style.color=cv('--purple');bc.disabled=false;}}"
        # Also reset detail pane Best Case button
        "var dbc=document.querySelector('.detail-commit-btn.bestcase');"
        "if(dbc){dbc.textContent='Best Case';dbc.style.background=cv('--purple-bg');dbc.style.color=cv('--purple');dbc.disabled=false;}"
        "}else{"
        "btn.disabled=false;btn.textContent='Commit';"
        'alert("Commit failed");}'
        "})"
        '.catch(function(){btn.disabled=false;btn.textContent="Commit";'
        'alert("Commit failed");});'
        "}"
        # Best Case action
        "function doBestCase(taskId,btn){"
        "btn.disabled=true;btn.textContent='...';"
        f'fetch("{base_action_url}?action=bestcase_label&task_id="+taskId)'
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "btn.textContent='\\u2713 Best Case';"
        "btn.classList.add('active');"
        "btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        # Reset sibling Commit button since labels are mutually exclusive
        "var card=btn.closest('.task-card');"
        "if(card){var cb=card.querySelector('.commit-btn');"
        "if(cb){cb.textContent='Commit';cb.classList.remove('committed');"
        "cb.style.background=cv('--warn-bg');cb.style.color=cv('--warn');cb.disabled=false;}}"
        "var dcb=document.querySelector('.detail-commit-btn.commit');"
        "if(dcb){dcb.textContent='Commit';dcb.style.background=cv('--warn-bg');dcb.style.color=cv('--warn');dcb.disabled=false;}"
        "}else{"
        "btn.disabled=false;btn.textContent='Best Case';"
        'alert("Best Case failed");}'
        "})"
        '.catch(function(){btn.disabled=false;btn.textContent="Best Case";'
        'alert("Best Case failed");});'
        "}"
        # Remove Best Case action
        "function doRemoveBestCase(taskId,btn){"
        "btn.disabled=true;btn.textContent='...';"
        f'fetch("{base_action_url}?action=remove_bestcase&task_id="+taskId)'
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "btn.textContent='Best Case';"
        "btn.classList.remove('remove','active');"
        "btn.style.background=cv('--purple-bg');btn.style.color=cv('--purple');"
        "btn.disabled=false;"
        "btn.onclick=function(e){e.stopPropagation();doBestCase(taskId,btn);};"
        "}else{"
        "btn.disabled=false;btn.textContent='\\u2713 Best Case \\u2715';"
        'alert("Remove failed");}'
        "})"
        '.catch(function(){btn.disabled=false;btn.textContent="\\u2713 Best Case \\u2715";'
        'alert("Remove failed");});'
        "}"
        # Remove Commit action
        "function doRemoveCommit(taskId,btn){"
        "btn.disabled=true;btn.textContent='...';"
        f'fetch("{base_action_url}?action=remove_commit&task_id="+taskId)'
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        # In commit view: show undo then remove; otherwise just toggle button back
        "if(viewName==='commit'){"
        "showUndo(taskId,'Commit removed.',function(){"
        f'fetch("{base_action_url}?action=commit_label&task_id="+taskId)'
        ".then(function(r2){if(r2.ok){btn.disabled=false;btn.textContent='Remove Commit';"
        "restoreCard(taskId);}else{removeCard(taskId);}})"
        ".catch(function(){removeCard(taskId);});});"
        "updateCount();}else{"
        "btn.textContent='Commit';"
        "btn.classList.remove('remove','committed');"
        "btn.style.background=cv('--warn-bg');btn.style.color=cv('--warn');"
        "btn.disabled=false;"
        "btn.onclick=function(e){e.stopPropagation();doCommit(taskId,btn);};}"
        "}else{"
        "btn.disabled=false;btn.textContent='Remove Commit';"
        'alert("Remove failed");}'
        "})"
        '.catch(function(){btn.disabled=false;btn.textContent="Remove Commit";'
        'alert("Remove failed");});'
        "}"
        # Task detail pane
        "function esc(s){var d=document.createElement('div');"
        "d.appendChild(document.createTextNode(String(s)));return d.innerHTML;}"
        "function doCopyForClaude(taskId,taskTitle,btn){"
        "var orig=btn.innerHTML;"
        "var url='https://app.todoist.com/app/task/'+taskId;"
        "var msg='Look at this task on Todoist and complete it: '+url;"
        "navigator.clipboard.writeText(msg).then(function(){"
        "btn.textContent='\\u2713';setTimeout(function(){btn.innerHTML=orig;},1500);"
        f'fetch("{base_action_url}?action=planned_label&task_id="+taskId)'
        ".then(function(r){return r.json();})"
        ".then(function(d){if(d.ok){"
        "var card=document.getElementById('card-'+taskId);"
        "if(card){"
        "var cb=card.querySelector('.commit-btn');"
        "if(cb){cb.textContent='\\u2713 Planned';cb.classList.add('committed');"
        "cb.style.background=cv('--ok-bg');cb.style.color=cv('--ok');}"
        "_moveCardToSection(card,'list-planned');"
        "}"
        "}});"
        "}).catch(function(){btn.textContent='!';setTimeout(function(){btn.innerHTML=orig;},1500);});}"
        # Update task title/description
        f"function doUpdateTask(taskId,payload,callback){{"
        f"payload.task_id=taskId;"
        f'fetch("{base_action_url}?action=update_task",{{method:"POST",'
        f'headers:{{"Content-Type":"application/json"}},'
        f"body:JSON.stringify(payload)}})"
        f".then(function(r){{return r.json();}})"
        f".then(function(d){{if(callback)callback(d.ok||false);}}"
        f").catch(function(){{if(callback)callback(false);}});}}"
        "function linkify(t){"
        "t=t.replace(/\\[([^\\]]+)\\]\\(((?:https?|obsidian):\\/\\/[^)]+)\\)/g,"
        '\'<a href="$2" target="_blank" rel="noopener" style="color:\'+cv(\'--accent-l\')+\';text-decoration:underline;">$1</a>\');'
        't=t.replace(/(?<!href=")(?<!">)((?:https?|obsidian):\\/\\/[^\\s<)]+)/g,'
        '\'<a href="$1" target="_blank" rel="noopener" style="color:\'+cv(\'--accent-l\')+\';text-decoration:underline;">$1</a>\');'
        "return t;}"
        "function openTaskDetail(card){"
        "if(event&&event.target&&event.target.closest('a'))return;"
        "var cbs=card.querySelector('.select-cb');"
        "if(cbs&&document.activeElement===cbs)return;"
        "var taskId=card.getAttribute('data-task-id')||'';"
        "var title=card.getAttribute('data-content')||'(no title)';"
        "var description=card.getAttribute('data-description')||'';"
        "var projectName=card.getAttribute('data-project-name')||'';"
        "var priority=parseInt(card.getAttribute('data-priority')||'1');"
        "var pLabel=card.getAttribute('data-priority-label')||'P4';"
        "var pColor=card.getAttribute('data-priority-color')||'#5f6368';"
        "var labels=card.getAttribute('data-labels')||'';"
        "var dueDate=card.getAttribute('data-due-date')||'';"
        "var dueText=card.getAttribute('data-due-text')||'';"
        "var dueColor=card.getAttribute('data-due-color')||'#5f6368';"
        "var openUrl=card.getAttribute('data-open-url')||'';"
        "document.querySelectorAll('.task-card').forEach(function(c){"
        "c.classList.remove('active-card');});"
        "card.classList.add('active-card');"
        "var h='';"
        # Editable title
        "h+='<div contenteditable=\"true\" class=\"detail-title detail-title-editable\" data-task-id=\"'+esc(taskId)+'\" data-orig=\"'+esc(title)+'\">'+esc(title)+'</div>';"
        "h+='<div class=\"detail-meta\">';"
        "h+='<span class=\"detail-meta-tag\" style=\"background:'+esc(pColor)+'26;color:'+"
        "esc(pColor)+';\">'+esc(pLabel)+'</span>';"
        "if(projectName)h+='<span class=\"detail-meta-tag\">'+esc(projectName)+'</span>';"
        "if(dueText)h+='<span class=\"detail-meta-tag\" style=\"color:'+esc(dueColor)+';\">'"
        "+esc(dueText)+'</span>';"
        "if(labels){labels.split(',').forEach(function(lbl){"
        "lbl=lbl.trim();if(lbl)h+='<span class=\"detail-meta-tag\" style=\"color:'+cv('--purple')+';\">'"
        "+'@'+esc(lbl)+'</span>';});}"
        "h+='</div>';"
        # Editable description
        "h+='<div class=\"detail-section-label\">Description</div>';"
        'h+=\'<textarea class="detail-desc-editable" data-task-id="\'+esc(taskId)+\'" rows="4" placeholder="Add description...">\'+esc(description)+\'</textarea>\';'
        'h+=\'<button class="detail-action-btn detail-desc-save-btn" '
        'style="margin-bottom:8px;background:var(--accent-bg);color:var(--accent-l);border:1px solid var(--accent-b);">Save Description</button>\';'
        "h+='<div class=\"detail-actions\">';"
        "var pOpts=[[4,'P1'],[3,'P2'],[2,'P3'],[1,'P4']];"
        "h+='<select class=\"action-select detail-priority-sel\">';"
        "pOpts.forEach(function(p){"
        "var sel=p[0]===priority?' selected':'';h+='<option value=\"'+p[0]+'\"'+sel+'>'+p[1]+'</option>';});"
        "h+='</select>';"
        'h+=\'<input type="date" class="action-select detail-due-input" value="\'+esc(dueDate)+\'">\';'
        'h+=\'<button class="detail-action-btn detail-complete-btn" '
        'style="background:rgba(34,197,94,0.10);color:#22c55e;border:1px solid rgba(34,197,94,0.20);">Complete</button>\';'
        "var labelsArr=labels?labels.split(','):[];"
        "var isCommitted=labelsArr.indexOf('Commit')!==-1;"
        "var isBestCase=labelsArr.indexOf('Best Case')!==-1;"
        "if(isCommitted){"
        'h+=\'<button class="detail-action-btn detail-commit-btn commit" '
        'style="background:rgba(34,197,94,0.10);color:#22c55e;border:1px solid rgba(34,197,94,0.20);cursor:default;" disabled>\\u2713 Committed</button>\';'
        "}else{"
        'h+=\'<button class="detail-action-btn detail-commit-btn commit" '
        'style="background:rgba(234,179,8,0.10);color:#eab308;border:1px solid rgba(234,179,8,0.20);">Commit</button>\';'
        "}"
        "if(isBestCase){"
        'h+=\'<button class="detail-action-btn detail-commit-btn bestcase" '
        'style="background:rgba(34,197,94,0.10);color:#22c55e;border:1px solid rgba(34,197,94,0.20);">\\u2713 Best Case \\u2715</button>\';'
        "}else{"
        'h+=\'<button class="detail-action-btn detail-commit-btn bestcase" '
        'style="background:rgba(167,139,250,0.10);color:#a78bfa;border:1px solid rgba(167,139,250,0.20);">Best Case</button>\';'
        "}"
        "if(openUrl)h+='<button class=\"detail-action-btn view-email-btn\">View Email</button>';"
        'h+=\'<button class="detail-action-btn assign-cc-btn" title="Assign CC" '
        "onclick=\"doCopyForClaude(\\x27'+esc(taskId)+'\\x27,\\x27'+esc(title).replace(/'/g,'\\\\\\x27')+'\\x27,this)\">'+_ccIcon+'</button>';"
        "h+='</div>';"
        "var dc=document.getElementById('detail-content');"
        "dc.innerHTML=h;"
        "var ps=dc.querySelector('.detail-priority-sel');"
        "if(ps)ps.addEventListener('change',function(){doSetPriority(taskId,this.value,this,pColor);});"
        "var di=dc.querySelector('.detail-due-input');"
        "if(di)di.addEventListener('change',function(){doSetDueDate(taskId,this.value,this);});"
        "var cb=dc.querySelector('.detail-complete-btn');"
        "if(cb)cb.addEventListener('click',function(){doComplete(taskId,cb);});"
        "var cmb=dc.querySelector('.detail-commit-btn.commit');"
        "if(cmb&&!isCommitted)cmb.addEventListener('click',function(){doCommit(taskId,cmb);});"
        "var bcb=dc.querySelector('.detail-commit-btn.bestcase');"
        "if(bcb){if(isBestCase){bcb.addEventListener('click',function(){doRemoveBestCase(taskId,bcb);});"
        "}else{bcb.addEventListener('click',function(){doBestCase(taskId,bcb);});}}"
        "if(openUrl){var eb=dc.querySelector('.view-email-btn');"
        "if(eb)eb.addEventListener('click',function(){showEmailInPane(openUrl);});}"
        # Editable title blur-to-save
        "var titleEl=dc.querySelector('.detail-title-editable');"
        "if(titleEl){titleEl.addEventListener('blur',function(){"
        "var newTitle=this.textContent.trim();"
        "var orig=this.getAttribute('data-orig');"
        "if(newTitle&&newTitle!==orig){"
        "this.setAttribute('data-orig',newTitle);"
        "doUpdateTask(taskId,{content:newTitle});"
        # Also update card data attribute
        "var card=document.getElementById('card-'+taskId);"
        "if(card){card.setAttribute('data-content',newTitle);"
        "var titleDiv=card.querySelector('.task-title');"
        "if(titleDiv)titleDiv.textContent=newTitle;}"
        "}});}"
        # Description save button
        "var descSave=dc.querySelector('.detail-desc-save-btn');"
        "var descArea=dc.querySelector('.detail-desc-editable');"
        "if(descSave&&descArea){descSave.addEventListener('click',function(){"
        "var newDesc=descArea.value;"
        "descSave.disabled=true;descSave.textContent='Saving...';"
        "doUpdateTask(taskId,{description:newDesc},function(ok){"
        "if(ok){descSave.textContent='\\u2713 Saved';"
        "var card=document.getElementById('card-'+taskId);"
        "if(card)card.setAttribute('data-description',newDesc);"
        "setTimeout(function(){descSave.textContent='Save Description';descSave.disabled=false;},1500);"
        "}else{descSave.textContent='Failed';descSave.disabled=false;}"
        "});});}"
        # Auto-expand description textarea to fit content
        "if(descArea){descArea.style.height='auto';descArea.style.height=descArea.scrollHeight+'px';"
        "var _resizeTimer;descArea.addEventListener('input',function(){var el=this;clearTimeout(_resizeTimer);_resizeTimer=setTimeout(function(){el.style.height='auto';el.style.height=el.scrollHeight+'px';},50);});}"
        "dc.style.display='block';"
        "var vf=document.getElementById('viewer-frame');"
        "vf.src='about:blank';vf.style.display='none';"
        "document.getElementById('viewer-placeholder').style.display='none';"
        "if(window.innerWidth<=768){"
        "document.getElementById('viewer-pane').style.display='flex';"
        "}"
        # Fetch and render attachments/comments
        "loadTaskAttachments(taskId,dc);"
        "}"
        "function loadTaskAttachments(taskId,container){"
        f"fetch('{base_action_url}?action=task_comments&task_id='+encodeURIComponent(taskId))"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(!d.ok||!d.comments||!d.comments.length)return;"
        "var ah='<div class=\"detail-attachments\">';"
        "ah+='<div class=\"detail-section-label\">Attachments &amp; Comments</div>';"
        "ah+='<div class=\"attachment-grid\">';"
        "window._lbImgs=[];"
        "d.comments.forEach(function(c){"
        "var fa=c.file_attachment;"
        "if(fa){"
        "var ft=fa.file_type||'';"
        "var fn=fa.file_name||'File';"
        "var fu=fa.file_url||'';"
        "var img=fa.image||'';"
        "if(ft.indexOf('image/')===0&&(img||fu)){"
        "var lbIdx=window._lbImgs.length;"
        "window._lbImgs.push(fu||img);"
        'ah+=\'<div class="attachment-item" style="cursor:pointer;" onclick="openLightbox(window._lbImgs,\'+lbIdx+\')">\';'
        "ah+='<img src=\"'+(img||fu)+'\" alt=\"'+esc(fn)+'\" style=\"max-height:300px;\">';"
        "ah+='</div>';"
        "}else if(fu){"
        "ah+='<div class=\"attachment-item\">';"
        "ah+='<a href=\"'+fu+'\" target=\"_blank\">';"
        'ah+=\'<svg class="attachment-file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>\';'
        "ah+=esc(fn)+'</a></div>';"
        "}"
        "}"
        "if(c.content){"
        "ah+='<div class=\"comment-text\">'+esc(c.content)+'</div>';"
        "}"
        "});"
        "ah+='</div></div>';"
        "container.insertAdjacentHTML('beforeend',ah);"
        "}).catch(function(){});"
        "}"
        "var _lbUrls=[],_lbIdx=0;"
        "function _lbRender(){"
        "document.getElementById('lb-img').src=_lbUrls[_lbIdx];"
        "var c=document.getElementById('lb-counter');"
        "var p=document.getElementById('lb-prev');"
        "var n=document.getElementById('lb-next');"
        "if(_lbUrls.length>1){"
        "c.textContent=(_lbIdx+1)+' / '+_lbUrls.length;"
        "p.style.display='';n.style.display='';}"
        "else{c.textContent='';p.style.display='none';n.style.display='none';}}"
        "function _lbKey(e){"
        "if(e.key==='Escape')closeLightbox();"
        "if(e.key==='ArrowRight')lightboxNav(1);"
        "if(e.key==='ArrowLeft')lightboxNav(-1);}"
        "function openLightbox(urls,idx){"
        "_lbUrls=urls;_lbIdx=idx;_lbRender();"
        "document.getElementById('lb-overlay').classList.add('lb-open');"
        "document.addEventListener('keydown',_lbKey);"
        "window._lbTx=null;"
        "window._lbTouchStart=function(e){window._lbTx=e.touches[0].clientX;};"
        "window._lbTouchEnd=function(e){"
        "if(window._lbTx===null)return;"
        "var dx=e.changedTouches[0].clientX-window._lbTx;"
        "if(Math.abs(dx)>50)lightboxNav(dx<0?1:-1);"
        "window._lbTx=null;};"
        "var ov=document.getElementById('lb-overlay');"
        "ov.addEventListener('touchstart',window._lbTouchStart,{passive:true});"
        "ov.addEventListener('touchend',window._lbTouchEnd,{passive:true});}"
        "function closeLightbox(){"
        "var ov=document.getElementById('lb-overlay');"
        "ov.classList.remove('lb-open');"
        "document.removeEventListener('keydown',_lbKey);"
        "ov.removeEventListener('touchstart',window._lbTouchStart);"
        "ov.removeEventListener('touchend',window._lbTouchEnd);}"
        "function lightboxNav(dir){"
        "_lbIdx=(_lbIdx+dir+_lbUrls.length)%_lbUrls.length;"
        "_lbRender();}"
        "function showEmailInPane(url){"
        "document.getElementById('detail-content').style.display='none';"
        "document.getElementById('viewer-placeholder').style.display='none';"
        "var vf=document.getElementById('viewer-frame');"
        "vf.src=url;vf.style.display='block';"
        "}"
        "function closeViewer(){"
        "var vf=document.getElementById('viewer-frame');"
        "vf.src='about:blank';vf.style.display='none';"
        "var dc=document.getElementById('detail-content');"
        "dc.style.display='none';dc.innerHTML='';"
        "document.getElementById('viewer-placeholder').style.display='flex';"
        "document.querySelectorAll('.task-card').forEach(function(c){"
        "c.classList.remove('active-card');});"
        "if(window.innerWidth<=768){"
        "document.getElementById('viewer-pane').style.display='none';"
        "}"
        "}"
        # Multi-select functions
        "function getSelectedCards(){"
        "var cards=[];"
        "document.querySelectorAll('.select-cb:checked').forEach(function(cb){"
        "var card=cb.closest('.task-card');"
        "if(card)cards.push(card);"
        "});"
        "return cards;"
        "}"
        "function updateSelection(){"
        "var sel=getSelectedCards();"
        "var toolbar=document.getElementById('bulk-toolbar');"
        "var countEl=document.getElementById('bulk-count');"
        "if(sel.length>0){"
        "toolbar.style.display='flex';"
        "countEl.textContent=sel.length+' selected';"
        "}else{"
        "toolbar.style.display='none';"
        "}"
        "var allCbs=document.querySelectorAll('.select-cb');"
        "var allChecked=allCbs.length>0;"
        "allCbs.forEach(function(cb){if(!cb.checked)allChecked=false;});"
        "var sa=document.getElementById('select-all-cb');"
        "if(sa)sa.checked=allChecked;"
        "}"
        "function toggleSelectAll(){"
        "var sa=document.getElementById('select-all-cb');"
        "var checked=sa?sa.checked:false;"
        "document.querySelectorAll('.select-cb').forEach(function(cb){cb.checked=checked;});"
        "updateSelection();"
        "}"
        # Bulk move
        "function bulkMove(projectId){"
        "if(!projectId)return;"
        "var cards=getSelectedCards();"
        "cards.forEach(function(card){"
        "var taskId=card.getAttribute('data-task-id');"
        f'fetch("{base_action_url}?action=move&task_id="+taskId+"&project_id="+projectId)'
        ".then(function(r){if(r.ok){card.classList.add('removing');"
        "setTimeout(function(){card.remove();updateCount();updateSelection();},350);"
        "}});"
        "});"
        "}"
        # Bulk complete
        "function bulkComplete(){"
        "var cards=getSelectedCards();"
        "cards.forEach(function(card){"
        "var taskId=card.getAttribute('data-task-id');"
        f'fetch("{base_action_url}?action=complete&task_id="+taskId)'
        ".then(function(r){if(r.ok){card.classList.add('removing');"
        "setTimeout(function(){card.remove();updateCount();updateSelection();},350);"
        "}});"
        "});"
        "}"
        # Bulk set due date
        "function bulkSetDueDate(dateValue){"
        "var cards=getSelectedCards();"
        "cards.forEach(function(card){"
        "var taskId=card.getAttribute('data-task-id');"
        "var input=card.querySelector('input[type=date]');"
        f'fetch("{base_action_url}?action=due_date&task_id="+taskId+"&date="+encodeURIComponent(dateValue))'
        ".then(function(r){if(r.ok&&input){"
        "input.value=dateValue;"
        "input.style.borderColor='rgba(34,197,94,0.5)';"
        "setTimeout(function(){input.style.borderColor='';},1500);"
        "}});"
        "});"
        "document.querySelectorAll('.select-cb:checked').forEach(function(cb){cb.checked=false;});"
        "updateSelection();"
        "}" + checklist_js
        # Schedule modal JS
        + "var _schedTaskId=null,_schedMins=0;"
        "function openScheduleModal(taskId){"
        "_schedTaskId=taskId;_schedMins=0;"
        "document.querySelectorAll('.duration-opt').forEach(function(b){"
        "b.classList.remove('selected');});"
        "var btn=document.getElementById('schedule-confirm');"
        "btn.disabled=true;btn.textContent='Schedule';"
        "document.getElementById('schedule-overlay').classList.add('open');"
        "}"
        "function closeScheduleModal(){"
        "document.getElementById('schedule-overlay').classList.remove('open');"
        "_schedTaskId=null;_schedMins=0;"
        "}"
        "document.querySelectorAll('.duration-opt').forEach(function(b){"
        "b.addEventListener('click',function(){"
        "document.querySelectorAll('.duration-opt').forEach(function(x){x.classList.remove('selected');});"
        "this.classList.add('selected');"
        "_schedMins=parseInt(this.getAttribute('data-mins'));"
        "var n=_schedMins/30;"
        "document.getElementById('schedule-confirm').disabled=false;"
        "document.getElementById('schedule-confirm').textContent="
        "'Schedule '+n+' event'+(n>1?'s':'');"
        "});});"
        "document.getElementById('schedule-confirm').addEventListener('click',function(){"
        "if(!_schedTaskId||!_schedMins)return;"
        "var btn=this;btn.disabled=true;btn.textContent='Scheduling...';"
        f'fetch("{base_action_url}?action=schedule_action&task_id="+_schedTaskId+"&duration="+_schedMins)'
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "btn.textContent='\\u2713 '+d.events_created+' events created!';"
        "btn.style.background='#22c55e';"
        "setTimeout(function(){closeScheduleModal();btn.style.background='';},1500);"
        "}else{"
        "btn.textContent='Failed: '+(d.error||'Unknown error');"
        "btn.disabled=false;btn.style.background='#ef4444';"
        "setTimeout(function(){btn.style.background='';btn.textContent='Schedule';},2000);"
        "}"
        "})"
        ".catch(function(e){"
        "btn.textContent='Error';btn.disabled=false;"
        "setTimeout(function(){btn.textContent='Schedule';},2000);"
        "});"
        "});" + "</script>"
        "</body></html>"
    )
