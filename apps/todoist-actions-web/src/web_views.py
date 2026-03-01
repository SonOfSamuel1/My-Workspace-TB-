"""HTML view builder for Todoist actions web interface.

Renders task cards with inline disposition controls (Move, Priority, Complete,
Due Date) for Inbox, Commit, and P1 views. Includes split-pane email viewer
for email-originated tasks and multi-select with bulk actions.
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
    "bestcase": "Best Case Today",
}

_FONT = (
    "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,"
    "'Segoe UI',Roboto,sans-serif"
)


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
        r"\[Open in Gmail\]\((https://mail\.google\.com[^\)]+)\)", description
    )
    if match:
        return match.group(1)
    return ""


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
    move_select = (
        f'<select class="action-select" '
        f"onchange=\"event.stopPropagation();doMove('{task_id}',this.value,this)\" "
        f'style="max-width:140px;">' + "".join(move_options) + "</select>"
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
    due_date_input = (
        f'<input type="date" class="action-select" value="{html.escape(due_date)}" '
        f'onclick="event.stopPropagation()" '
        f"onchange=\"event.stopPropagation();doSetDueDate('{task_id}',this.value,this)\" "
        f'style="max-width:140px;">'
    )

    # Complete button
    complete_btn = (
        f'<button class="complete-btn" '
        f"onclick=\"event.stopPropagation();doComplete('{task_id}',this)\">"
        "Complete</button>"
    )

    # Commit button (on commit view: show "Remove Commit" instead of disabled)
    is_committed = "Commit" in labels
    if is_committed and view_name == "commit":
        commit_btn = (
            f'<button class="commit-btn remove" '
            f"onclick=\"event.stopPropagation();doRemoveCommit('{task_id}',this)\">"
            "Remove Commit</button>"
        )
    elif is_committed:
        commit_btn = (
            '<button class="commit-btn committed" disabled>' "\u2713 Committed</button>"
        )
    else:
        commit_btn = (
            f'<button class="commit-btn" '
            f"onclick=\"event.stopPropagation();doCommit('{task_id}',this)\">"
            "Commit</button>"
        )

    # Best Case button (on bestcase view: show "Remove Best Case" instead of toggle)
    is_bestcase = "Best Case" in labels
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
        '<input type="checkbox" class="select-cb" '
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
        f'<div class="task-actions">{move_select}{priority_select}{due_date_input}{complete_btn}{commit_btn}{bestcase_btn}</div>'  # noqa: E501
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
    base_action_url = function_url.rstrip("/") + f"?token={html.escape(action_token)}"

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
            '<label class="select-all-label">'
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
        ".subheader{display:flex;align-items:center;padding:10px 16px;"
        "font-size:13px;color:var(--text-2);border-bottom:1px solid var(--border);"
        "background:var(--bg-s0);max-width:700px;margin:0 auto;}"
        ".select-all-label{display:flex;align-items:center;gap:6px;cursor:pointer;"
        "font-weight:500;}"
        # Split-pane layout
        f".split-wrap{{display:flex;height:{split_height};overflow:hidden;}}"
        ".left-pane{flex:0 0 45%;overflow-y:auto;}"
        "#viewer-pane{display:flex;flex-direction:column;flex:1 1 55%;"
        "border-left:1px solid var(--border);background:var(--bg-s1);position:relative;}"
        "#viewer-frame{flex:1;border:none;width:100%;display:none;}"
        "#detail-content{flex:1;overflow-y:auto;padding:24px;display:none;}"
        ".close-btn{position:absolute;top:10px;right:14px;z-index:10;"
        "background:var(--border);border:none;font-size:22px;cursor:pointer;"
        "width:36px;height:36px;border-radius:50%;display:flex;"
        "align-items:center;justify-content:center;color:var(--text-2);}"
        ".close-btn:hover{background:var(--border-h);}"
        # Task list
        ".task-list{max-width:700px;margin:0 auto;padding:12px 16px;}"
        ".task-card{background:var(--bg-s1);border-radius:8px;"
        "border:1px solid var(--border);padding:14px 16px;"
        "margin-bottom:10px;transition:opacity .15s ease-out,transform .15s ease-out,border-color .15s ease-out,background .15s ease-out;cursor:pointer;}"  # noqa: E501
        ".task-card:hover{border-color:var(--border-h);background:var(--bg-s2);}"
        ".task-card.active-card{background:var(--accent-hbg);border-color:var(--accent-b);}"
        ".task-card.removing{opacity:0;transform:translateX(60px);"
        "margin-bottom:0;padding-top:0;padding-bottom:0;max-height:0;"
        "overflow:hidden;}"
        ".card-row{display:flex;align-items:flex-start;gap:10px;}"
        ".card-content{flex:1;min-width:0;}"
        ".select-cb{width:18px;height:18px;margin-top:2px;cursor:pointer;flex-shrink:0;}"
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
        ".complete-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-b);cursor:pointer;"
        "transition:background .15s ease-out;}"
        ".complete-btn:hover{background:var(--ok-b);}"
        ".complete-btn:disabled{background:rgba(34,197,94,0.05);color:rgba(34,197,94,0.4);border-color:var(--ok-bg);cursor:default;}"  # noqa: E501
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
        ".task-card.undo-state .card-row{display:none;}"
        ".undo-bar{display:flex;align-items:center;justify-content:center;"
        "gap:10px;padding:12px 0;font-size:13px;color:var(--text-2);}"
        ".undo-bar a{color:var(--accent-l);font-weight:600;cursor:pointer;"
        "text-decoration:none;}"
        ".undo-bar a:hover{text-decoration:underline;}"
        # Bulk toolbar
        "#bulk-toolbar{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);"
        "background:rgba(22,22,24,0.95);backdrop-filter:blur(12px);border:1px solid var(--border);color:var(--text-1);padding:10px 18px;border-radius:12px;"  # noqa: E501
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
        "@media(max-width:768px){"
        ".task-actions{gap:6px;}"
        ".action-select,.complete-btn{font-size:11px;padding:4px 6px;}"
        ".left-pane{flex:1 1 100%!important;}"
        "#viewer-pane{display:none;position:fixed;top:0;left:0;right:0;bottom:0;z-index:200;"
        "border-left:none;}"
        ".close-btn{top:12px;right:12px;background:var(--border-h);color:var(--text-1);}"
        "#bulk-toolbar{left:10px;right:10px;transform:none;flex-wrap:wrap;"
        "justify-content:center;}"
        "}"
        "::-webkit-scrollbar{width:6px;}"
        "::-webkit-scrollbar-track{background:transparent;}"
        "::-webkit-scrollbar-thumb{background:var(--scrollbar);border-radius:3px;}"
        "</style>"
        "</head><body>" + header_html + '<div class="split-wrap" id="split-wrap">'
        # Left pane — task list
        + '<div class="left-pane">'
        + subheader_html
        + '<div class="task-list">'
        + cards_html
        + "</div></div>"
        # Right pane — task detail / email viewer
        + '<div id="viewer-pane">'
        '<button class="close-btn" onclick="closeViewer()" title="Close">&times;</button>'
        '<div id="viewer-placeholder" style="'
        "flex:1;display:flex;flex-direction:column;align-items:center;"
        'justify-content:center;color:var(--text-3);font-size:15px;gap:12px;">'
        '<span style="font-size:40px;">&#9776;</span>'
        "<span>Select a task to view details</span>"
        "</div>"
        '<div id="detail-content"></div>'
        '<iframe id="viewer-frame" src="about:blank"></iframe>'
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
        # JavaScript
        + "<script>"
        "var _cs=getComputedStyle(document.documentElement);function cv(n){return _cs.getPropertyValue(n).trim();}"
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
        f'fetch("{base_action_url}&action=move&task_id="+taskId+"&project_id="+projectId)'
        ".then(function(r){if(r.ok){"
        "showUndo(taskId,'Moved to '+projName+'.',function(){"
        f'fetch("{base_action_url}&action=move&task_id="+taskId+"&project_id="+origProjectId)'
        ".then(function(r2){if(r2.ok){sel.disabled=false;sel.selectedIndex=0;"
        "restoreCard(taskId);}else{removeCard(taskId);}})"
        ".catch(function(){removeCard(taskId);});});"
        '}else{sel.disabled=false;alert("Move failed");}})'
        '.catch(function(){sel.disabled=false;alert("Move failed");});'
        "}"
        # Priority action
        "function doSetPriority(taskId,priority,sel){"
        "sel.disabled=true;"
        f'fetch("{base_action_url}&action=priority&task_id="+taskId+"&priority="+priority)'
        ".then(function(r){if(r.ok){"
        "sel.disabled=false;"
        "}else{"
        'sel.disabled=false;alert("Priority update failed");}})'
        '.catch(function(){sel.disabled=false;alert("Priority update failed");});'
        "}"
        # Due date action
        "function doSetDueDate(taskId,dateValue,input){"
        "input.disabled=true;"
        f'fetch("{base_action_url}&action=due_date&task_id="+taskId+"&date="+encodeURIComponent(dateValue))'
        ".then(function(r){if(r.ok){"
        "input.disabled=false;"
        "input.style.borderColor='rgba(34,197,94,0.5)';"
        "setTimeout(function(){input.style.borderColor='';},1500);"
        "}else{"
        'input.disabled=false;alert("Due date update failed");}})'
        '.catch(function(){input.disabled=false;alert("Due date update failed");});'
        "}"
        # Complete action
        "function doComplete(taskId,btn){"
        "btn.disabled=true;btn.textContent='...';"
        f'fetch("{base_action_url}&action=complete&task_id="+taskId)'
        ".then(function(r){if(r.ok){"
        "showUndo(taskId,'Completed.',function(){"
        f'fetch("{base_action_url}&action=reopen&task_id="+taskId)'
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
        f'fetch("{base_action_url}&action=commit_label&task_id="+taskId)'
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
        "if(dbc){dbc.textContent='Best Case';dbc.style.background=cv('--purple-bg');dbc.style.color=cv('--purple');dbc.disabled=false;}"  # noqa: E501
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
        f'fetch("{base_action_url}&action=bestcase_label&task_id="+taskId)'
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
        "if(dcb){dcb.textContent='Commit';dcb.style.background=cv('--warn-bg');dcb.style.color=cv('--warn');dcb.disabled=false;}"  # noqa: E501
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
        f'fetch("{base_action_url}&action=remove_bestcase&task_id="+taskId)'
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
        f'fetch("{base_action_url}&action=remove_commit&task_id="+taskId)'
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "btn.textContent='Commit';"
        "btn.classList.remove('remove','committed');"
        "btn.style.background=cv('--warn-bg');btn.style.color=cv('--warn');"
        "btn.disabled=false;"
        "btn.onclick=function(e){e.stopPropagation();doCommit(taskId,btn);};"
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
        "function linkify(t){"
        "t=t.replace(/\\[([^\\]]+)\\]\\(((?:https?|obsidian):\\/\\/[^)]+)\\)/g,"
        '\'<a href="$2" target="_blank" rel="noopener" style="color:\'+cv(\'--accent-l\')+\';text-decoration:underline;">$1</a>\');'  # noqa: E501
        't=t.replace(/(?<!href=")(?<!">)((?:https?|obsidian):\\/\\/[^\\s<)]+)/g,'
        '\'<a href="$1" target="_blank" rel="noopener" style="color:\'+cv(\'--accent-l\')+\';text-decoration:underline;">$1</a>\');'  # noqa: E501
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
        "h+='<div class=\"detail-title\">'+linkify(esc(title))+'</div>';"
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
        "if(description){"
        "h+='<div class=\"detail-section-label\">Description</div>';"
        "var desc=linkify(esc(description)).replace(/\\*\\*([^*]+)\\*\\*/g,'<strong>$1</strong>');"
        "h+='<div class=\"detail-description\">'+desc+'</div>';}"
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
        'style="background:rgba(34,197,94,0.10);color:#22c55e;border:1px solid rgba(34,197,94,0.20);cursor:default;" disabled>\\u2713 Committed</button>\';'  # noqa: E501
        "}else{"
        'h+=\'<button class="detail-action-btn detail-commit-btn commit" '
        'style="background:rgba(234,179,8,0.10);color:#eab308;border:1px solid rgba(234,179,8,0.20);">Commit</button>\';'
        "}"
        "if(isBestCase){"
        'h+=\'<button class="detail-action-btn detail-commit-btn bestcase" '
        'style="background:rgba(34,197,94,0.10);color:#22c55e;border:1px solid rgba(34,197,94,0.20);">\\u2713 Best Case \\u2715</button>\';'  # noqa: E501
        "}else{"
        'h+=\'<button class="detail-action-btn detail-commit-btn bestcase" '
        'style="background:rgba(167,139,250,0.10);color:#a78bfa;border:1px solid rgba(167,139,250,0.20);">Best Case</button>\';'  # noqa: E501
        "}"
        "if(openUrl)h+='<button class=\"detail-action-btn view-email-btn\">View Email</button>';"
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
        "dc.style.display='block';"
        "var vf=document.getElementById('viewer-frame');"
        "vf.src='about:blank';vf.style.display='none';"
        "document.getElementById('viewer-placeholder').style.display='none';"
        "if(window.innerWidth<=768){"
        "document.getElementById('viewer-pane').style.display='flex';"
        "}"
        "}"
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
        f'fetch("{base_action_url}&action=move&task_id="+taskId+"&project_id="+projectId)'
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
        f'fetch("{base_action_url}&action=complete&task_id="+taskId)'
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
        f'fetch("{base_action_url}&action=due_date&task_id="+taskId+"&date="+encodeURIComponent(dateValue))'
        ".then(function(r){if(r.ok&&input){"
        "input.value=dateValue;"
        "input.style.borderColor='rgba(34,197,94,0.5)';"
        "setTimeout(function(){input.style.borderColor='';},1500);"
        "}});"
        "});"
        "document.querySelectorAll('.select-cb:checked').forEach(function(cb){cb.checked=false;});"
        "updateSelection();"
        "}"
        "</script>"
        "</body></html>"
    )
