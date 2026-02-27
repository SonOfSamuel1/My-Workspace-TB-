"""HTML view builder for Inbox Digest web dashboard.

Renders task cards with inline disposition controls (Move, Priority, Complete,
Due Date, Commit, Best Case) for the inbox view. Includes multi-select with
bulk actions and a task detail pane.
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
    """Return (text, color) for a due date string."""
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
    """Convert URLs and markdown links in html-escaped text into clickable <a> tags."""
    _URL_SCHEMES = r"(?:https?|obsidian)"
    text = re.sub(
        r"\[([^\]]+)\]\((" + _URL_SCHEMES + r"://[^\)]+)\)",
        r'<a href="\2" target="_blank" rel="noopener" '
        r'style="color:#818cf8;text-decoration:underline;">\1</a>',
        text,
    )

    def _replace_bare_url(m):
        url = m.group(0)
        return (
            f'<a href="{url}" target="_blank" rel="noopener" '
            f'style="color:#818cf8;text-decoration:underline;">{url}</a>'
        )

    text = re.sub(
        r'(?<!href=")(?<!">)(' + _URL_SCHEMES + r"://[^\s<\)]+)",
        _replace_bare_url,
        text,
    )
    return text


def _build_task_card(task, projects_by_id, function_url, action_token):
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

    p_label, p_color = PRIORITY_MAP.get(priority, ("P4", "#56565e"))
    project_name = html.escape(projects_by_id.get(project_id, "Unknown"))
    age = _relative_age(added_at)

    # Due date
    due_obj = task.get("due")
    due_date = (due_obj.get("date", "") or "")[:10] if due_obj else ""
    due_text, due_color = _due_date_display(due_date)

    # Meta line
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
        meta_parts.append(f'<span style="color:#a78bfa;">@{html.escape(lbl)}</span>')
    meta_line = " &middot; ".join(meta_parts)

    # Move dropdown
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
        f"onchange=\"event.stopPropagation();doSetPriority('{task_id}',this.value,this)\">"
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

    # Commit button
    is_committed = "Commit" in labels
    if is_committed:
        commit_btn = (
            '<button class="commit-btn committed" disabled>' "\u2713 Committed</button>"
        )
    else:
        commit_btn = (
            f'<button class="commit-btn" '
            f"onclick=\"event.stopPropagation();doCommit('{task_id}',this)\">"
            "Commit</button>"
        )

    # Best Case button
    is_bestcase = "Best Case" in labels
    if is_bestcase:
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

    # Checkbox
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
        f' onclick="openTaskDetail(this)">'
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


def build_view_html(tasks, projects, function_url, action_token):
    """Build the full HTML page for the inbox digest web dashboard.

    Args:
        tasks: List of task dicts from Todoist API.
        projects: List of project dicts from Todoist API.
        function_url: Base Lambda function URL for action requests.
        action_token: Secret token for authenticating action requests.
    """
    count = len(tasks)
    projects_by_id = {p["id"]: p.get("name", "Unknown") for p in projects}

    # Build project options for bulk move
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
            )
    else:
        cards_html = (
            '<div style="text-align:center;padding:60px 20px;color:#8b8b93;">'
            '<div style="font-size:36px;margin-bottom:12px;">&#10003;</div>'
            '<div style="font-size:16px;">No inbox items</div>'
            "</div>"
        )

    base_action_url = function_url.rstrip("/") + f"?token={html.escape(action_token)}"

    # Header
    header_html = (
        '<div class="top-bar">'
        '<span class="top-bar-title">Inbox Digest</span>'
        f'<span class="top-bar-count">{count} tasks</span>'
        '<button class="refresh-btn" onclick="location.reload()">&#8635; Refresh</button>'
        "</div>"
    )

    # Subheader
    subheader_html = ""
    if tasks:
        subheader_html = (
            '<div class="subheader">'
            '<label class="select-all-label">'
            '<input type="checkbox" id="select-all-cb" onclick="toggleSelectAll()">'
            " Select All</label>"
            f'<span id="task-count-display" style="margin-left:auto;font-size:12px;color:#8b8b93;">'
            f"{count} tasks</span>"
            "</div>"
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
        "<title>Inbox Digest</title>"
        "<style>"
        "*{box-sizing:border-box;margin:0;padding:0;}"
        f"body{{font-family:{_FONT};background:#0e0e10;color:#ececef;color-scheme:dark;"
        "-webkit-font-smoothing:antialiased;}"
        ".top-bar{background:#161618;border-bottom:1px solid rgba(255,255,255,0.06);padding:14px 20px;display:flex;"
        "align-items:center;gap:12px;position:sticky;top:0;z-index:100;}"
        ".top-bar-title{color:#ececef;font-size:17px;font-weight:600;letter-spacing:-0.2px;}"
        ".top-bar-count{color:#8b8b93;font-size:13px;}"
        ".refresh-btn{margin-left:auto;background:rgba(255,255,255,0.06);"
        "border:1px solid rgba(255,255,255,0.06);color:#ececef;font-size:13px;font-weight:600;"
        "padding:6px 14px;border-radius:6px;cursor:pointer;}"
        ".refresh-btn:hover{background:rgba(255,255,255,0.10);}"
        ".subheader{display:flex;align-items:center;padding:10px 16px;"
        "font-size:13px;color:#8b8b93;border-bottom:1px solid rgba(255,255,255,0.06);"
        "background:#161618;max-width:700px;margin:0 auto;}"
        ".select-all-label{display:flex;align-items:center;gap:6px;cursor:pointer;font-weight:500;}"
        # Split-pane layout
        ".split-wrap{display:flex;height:calc(100vh - 56px);overflow:hidden;}"
        ".left-pane{flex:0 0 45%;overflow-y:auto;}"
        "#viewer-pane{display:flex;flex-direction:column;flex:1 1 55%;"
        "border-left:1px solid rgba(255,255,255,0.06);background:#1c1c1f;position:relative;}"
        "#detail-content{flex:1;overflow-y:auto;padding:24px;display:none;}"
        ".close-btn{position:absolute;top:10px;right:14px;z-index:10;"
        "background:rgba(255,255,255,0.06);border:none;font-size:22px;cursor:pointer;"
        "width:36px;height:36px;border-radius:50%;display:flex;"
        "align-items:center;justify-content:center;color:#8b8b93;}"
        ".close-btn:hover{background:rgba(255,255,255,0.10);}"
        # Task cards
        ".task-list{max-width:700px;margin:0 auto;padding:12px 16px;}"
        ".task-card{background:#1c1c1f;border-radius:8px;"
        "border:1px solid rgba(255,255,255,0.06);padding:14px 16px;"
        "margin-bottom:10px;transition:opacity .15s ease-out,transform .15s ease-out,"
        "border-color .15s ease-out,background .15s ease-out;cursor:pointer;}"
        ".task-card:hover{border-color:rgba(255,255,255,0.10);background:#222225;}"
        ".task-card.active-card{background:rgba(99,102,241,0.08);border-color:rgba(99,102,241,0.2);}"
        ".task-card.removing{opacity:0;transform:translateX(60px);"
        "margin-bottom:0;padding-top:0;padding-bottom:0;max-height:0;overflow:hidden;}"
        ".card-row{display:flex;align-items:flex-start;gap:10px;}"
        ".card-content{flex:1;min-width:0;}"
        ".select-cb{width:18px;height:18px;margin-top:2px;cursor:pointer;flex-shrink:0;}"
        ".task-title{font-size:15px;font-weight:600;color:#ececef;line-height:1.4;"
        "margin-bottom:4px;word-break:break-word;}"
        ".task-title a{font-weight:500;}"
        ".task-meta{font-size:12px;color:#8b8b93;margin-bottom:10px;line-height:1.5;}"
        ".task-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center;}"
        ".action-select{font-family:inherit;font-size:12px;padding:5px 8px;"
        "border:1px solid rgba(255,255,255,0.06);border-radius:6px;background:#222225;"
        "color:#ececef;cursor:pointer;}"
        ".action-select:focus{outline:none;border-color:rgba(99,102,241,0.5);"
        "box-shadow:0 0 0 2px rgba(99,102,241,0.15);}"
        ".complete-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:rgba(34,197,94,0.10);color:#22c55e;border:1px solid rgba(34,197,94,0.20);cursor:pointer;"
        "transition:background .15s ease-out;}"
        ".complete-btn:hover{background:rgba(34,197,94,0.20);}"
        ".complete-btn:disabled{background:rgba(34,197,94,0.05);color:rgba(34,197,94,0.4);"
        "border-color:rgba(34,197,94,0.10);cursor:default;}"
        ".commit-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:rgba(234,179,8,0.10);color:#eab308;border:1px solid rgba(234,179,8,0.20);cursor:pointer;"
        "transition:background .15s ease-out;}"
        ".commit-btn:hover{background:rgba(234,179,8,0.20);}"
        ".commit-btn.committed{background:rgba(34,197,94,0.10);color:#22c55e;border-color:rgba(34,197,94,0.20);cursor:default;}"  # noqa: E501
        ".bestcase-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:5px 14px;border-radius:6px;"
        "background:rgba(167,139,250,0.10);color:#a78bfa;border:1px solid rgba(167,139,250,0.20);cursor:pointer;"
        "transition:background .15s ease-out;}"
        ".bestcase-btn:hover{background:rgba(167,139,250,0.20);}"
        ".bestcase-btn.remove{background:rgba(34,197,94,0.10);color:#22c55e;border-color:rgba(34,197,94,0.20);}"
        ".bestcase-btn.remove:hover{background:rgba(239,68,68,0.10);color:#ef4444;border-color:rgba(239,68,68,0.20);}"
        ".task-card.undo-state .card-row{display:none;}"
        ".undo-bar{display:flex;align-items:center;justify-content:center;"
        "gap:10px;padding:12px 0;font-size:13px;color:#8b8b93;}"
        ".undo-bar a{color:#818cf8;font-weight:600;cursor:pointer;text-decoration:none;}"
        ".undo-bar a:hover{text-decoration:underline;}"
        # Bulk toolbar
        "#bulk-toolbar{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);"
        "background:rgba(22,22,24,0.95);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,0.06);"
        "color:#ececef;padding:10px 18px;border-radius:12px;"
        "box-shadow:0 4px 16px rgba(0,0,0,.25);display:none;align-items:center;gap:10px;"
        "z-index:500;font-size:13px;font-weight:500;}"
        "#bulk-toolbar select{font-size:12px;padding:5px 8px;border-radius:6px;"
        "border:1px solid rgba(255,255,255,0.10);background:#222225;color:#ececef;}"
        "#bulk-toolbar button{font-size:12px;font-weight:600;padding:6px 14px;"
        "border:none;border-radius:6px;cursor:pointer;}"
        ".bulk-complete-btn{background:rgba(34,197,94,0.10);color:#22c55e;border:1px solid rgba(34,197,94,0.20);}"
        ".bulk-complete-btn:hover{background:rgba(34,197,94,0.20);}"
        ".bulk-date-input{font-size:12px;padding:5px 8px;border-radius:6px;"
        "border:1px solid rgba(255,255,255,0.10);background:#222225;color:#ececef;}"
        # Detail pane
        ".detail-title{font-size:20px;font-weight:700;color:#ececef;line-height:1.4;margin-bottom:16px;}"
        ".detail-meta{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;}"
        ".detail-meta-tag{display:inline-block;padding:4px 10px;border-radius:6px;"
        "font-size:12px;font-weight:600;background:rgba(255,255,255,0.06);color:#8b8b93;}"
        ".detail-description{font-size:14px;line-height:1.7;color:#8b8b93;"
        "white-space:pre-wrap;margin-bottom:20px;padding:16px;background:#222225;"
        "border-radius:8px;border:1px solid rgba(255,255,255,0.06);}"
        # Responsive
        "@media(max-width:768px){"
        ".task-actions{gap:6px;}"
        ".action-select,.complete-btn{font-size:11px;padding:4px 6px;}"
        ".left-pane{flex:1 1 100%!important;}"
        "#viewer-pane{display:none;position:fixed;top:0;left:0;right:0;bottom:0;z-index:200;"
        "border-left:none;}"
        ".close-btn{top:12px;right:12px;background:rgba(255,255,255,0.10);color:#ececef;}"
        "#bulk-toolbar{left:10px;right:10px;transform:none;flex-wrap:wrap;justify-content:center;}"
        "}"
        "::-webkit-scrollbar{width:6px;}"
        "::-webkit-scrollbar-track{background:transparent;}"
        "::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.10);border-radius:3px;}"
        "</style>"
        "</head><body>" + header_html + '<div class="split-wrap" id="split-wrap">'
        # Left pane
        + '<div class="left-pane">'
        + subheader_html
        + '<div class="task-list">'
        + cards_html
        + "</div></div>"
        # Right pane — task detail
        + '<div id="viewer-pane">'
        '<button class="close-btn" onclick="closeViewer()" title="Close">&times;</button>'
        '<div id="viewer-placeholder" style="'
        "flex:1;display:flex;flex-direction:column;align-items:center;"
        'justify-content:center;color:#56565e;font-size:15px;gap:12px;">'
        '<span style="font-size:40px;">&#9776;</span>'
        "<span>Select a task to view details</span>"
        "</div>"
        '<div id="detail-content"></div>'
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
        "var taskCount=" + str(count) + ";"
        "function updateCount(){"
        "taskCount--;"
        "if(taskCount<0)taskCount=0;"
        "var el=document.getElementById('task-count-display');"
        "if(el){el.textContent=taskCount+' tasks';}"
        "var hc=document.querySelector('.top-bar-count');"
        "if(hc){hc.textContent=taskCount+' tasks';}"
        "}"
        "function undoCount(){"
        "taskCount++;"
        "var el=document.getElementById('task-count-display');"
        "if(el){el.textContent=taskCount+' tasks';}"
        "var hc=document.querySelector('.top-bar-count');"
        "if(hc){hc.textContent=taskCount+' tasks';}"
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
        "btn.style.background='rgba(34,197,94,0.10)';btn.style.color='#22c55e';"
        "var card=btn.closest('.task-card');"
        "if(card){var bc=card.querySelector('.bestcase-btn');"
        "if(bc){bc.textContent='Best Case';bc.classList.remove('remove');"
        "bc.style.background='rgba(167,139,250,0.10)';bc.style.color='#a78bfa';bc.disabled=false;}}"
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
        "btn.textContent='\\u2713 Best Case \\u2715';"
        "btn.classList.add('remove');"
        "btn.style.background='rgba(34,197,94,0.10)';btn.style.color='#22c55e';"
        "btn.onclick=function(e){e.stopPropagation();doRemoveBestCase(taskId,btn);};"
        "var card=btn.closest('.task-card');"
        "if(card){var cb=card.querySelector('.commit-btn');"
        "if(cb){cb.textContent='Commit';cb.classList.remove('committed');"
        "cb.style.background='rgba(234,179,8,0.10)';cb.style.color='#eab308';cb.disabled=false;}}"
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
        "btn.classList.remove('remove');"
        "btn.style.background='rgba(167,139,250,0.10)';btn.style.color='#a78bfa';"
        "btn.disabled=false;"
        "btn.onclick=function(e){e.stopPropagation();doBestCase(taskId,btn);};"
        "}else{"
        "btn.disabled=false;btn.textContent='\\u2713 Best Case \\u2715';"
        'alert("Remove failed");}'
        "})"
        '.catch(function(){btn.disabled=false;btn.textContent="\\u2713 Best Case \\u2715";'
        'alert("Remove failed");});'
        "}"
        # Task detail pane
        "function esc(s){var d=document.createElement('div');"
        "d.appendChild(document.createTextNode(String(s)));return d.innerHTML;}"
        "function linkify(t){"
        "t=t.replace(/\\[([^\\]]+)\\]\\(((?:https?|obsidian):\\/\\/[^)]+)\\)/g,"
        '\'<a href="$2" target="_blank" rel="noopener" style="color:#818cf8;text-decoration:underline;">$1</a>\');'
        't=t.replace(/(?<!href=")(?<!">)((?:https?|obsidian):\\/\\/[^\\s<)]+)/g,'
        '\'<a href="$1" target="_blank" rel="noopener" style="color:#818cf8;text-decoration:underline;">$1</a>\');'
        "return t;}"
        "function openTaskDetail(card){"
        "if(event&&event.target&&event.target.closest('a'))return;"
        "var cbs=card.querySelector('.select-cb');"
        "if(cbs&&document.activeElement===cbs)return;"
        "var taskId=card.getAttribute('data-task-id')||'';"
        "var title=card.getAttribute('data-content')||'(no title)';"
        "var description=card.getAttribute('data-description')||'';"
        "var projectName=card.getAttribute('data-project-name')||'';"
        "var pLabel=card.getAttribute('data-priority-label')||'P4';"
        "var pColor=card.getAttribute('data-priority-color')||'#56565e';"
        "var labels=card.getAttribute('data-labels')||'';"
        "var dueText=card.getAttribute('data-due-text')||'';"
        "var dueColor=card.getAttribute('data-due-color')||'#56565e';"
        "document.querySelectorAll('.task-card').forEach(function(c){"
        "c.classList.remove('active-card');});"
        "card.classList.add('active-card');"
        "var h='';"
        "h+='<div class=\"detail-title\">'+linkify(esc(title))+'</div>';"
        "h+='<div class=\"detail-meta\">';"
        "h+='<span class=\"detail-meta-tag\" style=\"background:'+esc(pColor)+'26;color:'+esc(pColor)+';\">'+esc(pLabel)+'</span>';"  # noqa: E501
        "if(projectName)h+='<span class=\"detail-meta-tag\">'+esc(projectName)+'</span>';"
        "if(dueText)h+='<span class=\"detail-meta-tag\" style=\"color:'+esc(dueColor)+';\">'+esc(dueText)+'</span>';"
        "if(labels){labels.split(',').forEach(function(lbl){"
        "lbl=lbl.trim();if(lbl)h+='<span class=\"detail-meta-tag\" style=\"color:#a78bfa;\">@'+esc(lbl)+'</span>';});}"  # noqa: E501
        "h+='</div>';"
        "if(description){"
        "h+='<div class=\"detail-description\">'+linkify(esc(description))+'</div>';}"
        "h+='<div style=\"margin-top:12px;\">';"
        'h+=\'<a href="https://todoist.com/app/task/\'+taskId+\'" target="_blank" rel="noopener" '
        'style="color:#818cf8;font-size:13px;font-weight:600;text-decoration:none;">'
        "Open in Todoist \\u2192</a></div>';"
        "var det=document.getElementById('detail-content');"
        "det.innerHTML=h;det.style.display='block';"
        "document.getElementById('viewer-placeholder').style.display='none';"
        "if(window.innerWidth<=768){"
        "document.getElementById('viewer-pane').style.display='flex';}"
        "}"
        "function closeViewer(){"
        "document.getElementById('detail-content').style.display='none';"
        "document.getElementById('detail-content').innerHTML='';"
        "document.getElementById('viewer-placeholder').style.display='flex';"
        "document.querySelectorAll('.task-card').forEach(function(c){"
        "c.classList.remove('active-card');});"
        "if(window.innerWidth<=768){"
        "document.getElementById('viewer-pane').style.display='none';}"
        "}"
        # Multi-select
        "function getSelectedCards(){"
        "var cards=[];"
        "document.querySelectorAll('.select-cb:checked').forEach(function(cb){"
        "var card=cb.closest('.task-card');if(card)cards.push(card);});"
        "return cards;}"
        "function updateSelection(){"
        "var sel=getSelectedCards();"
        "var toolbar=document.getElementById('bulk-toolbar');"
        "var countEl=document.getElementById('bulk-count');"
        "if(sel.length>0){"
        "toolbar.style.display='flex';countEl.textContent=sel.length+' selected';"
        "}else{toolbar.style.display='none';}"
        "var allCbs=document.querySelectorAll('.select-cb');"
        "var allChecked=allCbs.length>0;"
        "allCbs.forEach(function(cb){if(!cb.checked)allChecked=false;});"
        "var sa=document.getElementById('select-all-cb');"
        "if(sa)sa.checked=allChecked;}"
        "function toggleSelectAll(){"
        "var sa=document.getElementById('select-all-cb');"
        "var checked=sa?sa.checked:false;"
        "document.querySelectorAll('.select-cb').forEach(function(cb){cb.checked=checked;});"
        "updateSelection();}"
        # Bulk actions
        "function bulkMove(projectId){"
        "if(!projectId)return;"
        "getSelectedCards().forEach(function(card){"
        "var taskId=card.getAttribute('data-task-id');"
        "if(!taskId)return;"
        f'fetch("{base_action_url}&action=move&task_id="+taskId+"&project_id="+projectId)'
        ".then(function(r){if(r.ok){card.classList.add('removing');"
        "setTimeout(function(){card.remove();taskCount--;var el=document.getElementById('task-count-display');"
        "if(el)el.textContent=taskCount+' tasks';updateSelection();},350);}"
        "});});}"
        "function bulkSetDueDate(dateValue){"
        "if(!dateValue)return;"
        "getSelectedCards().forEach(function(card){"
        "var taskId=card.getAttribute('data-task-id');"
        "if(!taskId)return;"
        f'fetch("{base_action_url}&action=due_date&task_id="+taskId+"&date="+encodeURIComponent(dateValue))'
        ".then(function(r){if(r.ok){"
        "var inp=card.querySelector('input[type=date]');"
        "if(inp){inp.value=dateValue;inp.style.borderColor='rgba(34,197,94,0.5)';"
        "setTimeout(function(){inp.style.borderColor='';},1500);}"
        "}});});}"
        "function bulkComplete(){"
        "getSelectedCards().forEach(function(card){"
        "var taskId=card.getAttribute('data-task-id');"
        "if(!taskId)return;"
        "var btn=card.querySelector('.complete-btn');"
        "if(btn){btn.disabled=true;btn.textContent='...';}"
        f'fetch("{base_action_url}&action=complete&task_id="+taskId)'
        ".then(function(r){if(r.ok){card.classList.add('removing');"
        "setTimeout(function(){card.remove();taskCount--;var el=document.getElementById('task-count-display');"
        "if(el)el.textContent=taskCount+' tasks';updateSelection();},350);}"
        "});});}"
        "</script>"
        "</body></html>"
    )
