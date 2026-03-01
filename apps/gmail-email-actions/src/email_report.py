"""Compose and send the daily Email Actions HTML digest via SES."""

import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List

import boto3

logger = logging.getLogger(__name__)

_ses = boto3.client("ses", region_name="us-east-1")

GMAIL_DEEP_LINK = "https://mail.google.com/mail/u/0/#inbox/{thread_id}"


def _days_ago(date_str: str) -> str:
    """Return a compact age string like '3d' or 'today' from an RFC 2822 date string."""
    try:
        dt = parsedate_to_datetime(date_str)
        delta = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
        days = delta.days
        return f"{days}d" if days > 0 else "today"
    except Exception:
        return "?"


def _days_ago_int(date_str: str) -> int:
    """Return integer days since date_str, or -1 on failure."""
    try:
        dt = parsedate_to_datetime(date_str)
        delta = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
        return delta.days
    except Exception:
        return -1


def _sort_by_most_recent(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort tasks by received date, most recent first."""

    def _sort_key(task):
        description = task.get("description", "")
        date_received = _extract_field(description, "\U0001f4c5")
        if date_received:
            try:
                return parsedate_to_datetime(date_received).timestamp()
            except Exception:
                pass
        return 0

    return sorted(tasks, key=_sort_key, reverse=True)


def _age_style(days: int) -> str:
    """Return inline CSS color for the age badge based on days old."""
    if days > 14:
        return "color:#d93025;font-weight:600;"
    elif days > 7:
        return "color:#e37400;font-weight:600;"
    return "color:#5f6368;"


def _strip_from_suffix(subject: str) -> str:
    """Remove ' — from SenderName' suffix from task content."""
    idx = subject.find(" \u2014 from ")
    if idx > 0:
        return subject[:idx]
    return subject


def _extract_msg_id_from_link(gmail_link: str) -> str:
    """Extract the Gmail message ID from a deep link like .../mail/u/0/#inbox/<id>."""
    if "#inbox/" in gmail_link:
        return gmail_link.split("#inbox/")[-1].rstrip("/")
    return gmail_link.rstrip("/").split("/")[-1]


def _extract_msg_id_field(description: str) -> str:
    """Extract the Gmail message ID from the 🆔 Msg ID field in the task description."""
    match = re.search(r"🆔 \*\*Msg ID:\*\*\s*(\S+)", description)
    if match:
        return match.group(1).strip()
    return ""


def _extract_gmail_link(description: str) -> str:
    """Pull the Gmail deep link out of the task description markdown."""
    match = re.search(
        r"\[Open in Gmail\]\((https://mail\.google\.com[^\)]+)\)", description
    )
    if match:
        return match.group(1)
    return ""


def _extract_field(description: str, emoji: str) -> str:
    """Extract a field value from the task description by emoji prefix."""
    pattern = rf"{re.escape(emoji)} \*\*[^*]+\*\*[:\s]+(.+)"
    match = re.search(pattern, description)
    if match:
        return match.group(1).strip()
    return ""


def _build_html(
    tasks: List[Dict[str, Any]], function_url: str = "", action_token: str = ""
) -> str:
    """Build the HTML body for the digest email."""
    tasks = _sort_by_most_recent(tasks)
    count = len(tasks)
    today = datetime.now().strftime("%B %d, %Y")
    plural = "s" if count != 1 else ""

    # Compute urgency count (items older than 7 days)
    urgency_count = 0
    for task in tasks:
        description = task.get("description", "")
        date_received = _extract_field(description, "\U0001f4c5")
        if date_received and _days_ago_int(date_received) > 7:
            urgency_count += 1

    rows = ""
    for idx, task in enumerate(tasks):
        description = task.get("description", "")
        gmail_link = _extract_gmail_link(description)
        from_addr = _extract_field(description, "\U0001f4e7")
        date_received = _extract_field(description, "\U0001f4c5")
        age = _days_ago(date_received) if date_received else "?"
        days_int = _days_ago_int(date_received) if date_received else -1
        content = _strip_from_suffix(task.get("content", ""))
        if content.startswith("[Action] "):
            content = content[len("[Action] ") :]

        open_url = ""
        unstar_link = ""
        open_link = ""

        if gmail_link:
            msg_id = _extract_msg_id_field(description) or _extract_msg_id_from_link(
                gmail_link
            )

            # Route through Lambda (bypasses Gmail deep-link issues on iOS)
            if function_url and action_token:
                _thread_id = (
                    gmail_link.split("#inbox/")[-1] if "#inbox/" in gmail_link else ""
                )
                if _thread_id:
                    open_url = (
                        function_url.rstrip("/")
                        + "?action=open&msg_id="
                        + msg_id
                        + "&thread_id="
                        + _thread_id
                        + "&token="
                        + action_token
                    )
                else:
                    open_url = gmail_link
            else:
                open_url = gmail_link

            if function_url and action_token:
                unstar_url = (
                    function_url.rstrip("/")
                    + "?action=unstar&msg_id="
                    + msg_id
                    + "&token="
                    + action_token
                )
                unstar_link = (
                    '<a href="' + unstar_url + '" '
                    'style="color:#d93025;background:#fce8e6;'
                    "text-decoration:none;font-weight:600;font-size:12px;"
                    'padding:5px 12px;border-radius:14px;display:inline-block;">'
                    "&#10005; Unstar</a>"
                )

            open_link = (
                '<a href="' + open_url + '" '
                'style="color:#1a73e8;background:#e8f0fe;'
                "text-decoration:none;font-weight:600;font-size:12px;"
                'padding:5px 12px;border-radius:14px;display:inline-block;">'
                "Open &#8594;</a>"
            )

        # Subject line (always plain text — "Open →" pill provides the link)
        subject_html = (
            '<div style="font-size:15px;font-weight:600;color:#202124;line-height:1.4;">'
            + content
            + "</div>"
        )

        age_css = _age_style(days_int)

        # Info line: age · sender
        meta_parts = []
        meta_parts.append('<span style="' + age_css + '">' + age + "</span>")
        if from_addr:
            meta_parts.append(from_addr.replace("@", "&#64;"))
        info_html = " &middot; ".join(meta_parts)

        # Action line: unstar · open (separate row for tap targets)
        action_parts = []
        if unstar_link:
            action_parts.append(unstar_link)
        if open_link:
            action_parts.append(open_link)
        action_html = (
            (
                '<div style="margin-top:8px;line-height:1;">'
                + " &nbsp; ".join(action_parts)
                + "</div>"
            )
            if action_parts
            else ""
        )

        border = "border-bottom:1px solid #dadce0;" if idx < count - 1 else ""

        rows += (
            '<div style="padding:16px 0;'
            + border
            + '">'
            + subject_html
            + '<div style="margin-top:6px;font-size:12px;color:#5f6368;line-height:1.4;">'
            + info_html
            + "</div>"
            + action_html
            + "</div>"
        )

    if count == 0:
        table_section = "<p style='color:#5f6368;font-size:15px;'>No outstanding email actions. Inbox zero!</p>"
    else:
        table_section = rows

    # Build header refresh link
    if function_url and action_token:
        rerun_url = function_url.rstrip("/") + "?action=rerun&token=" + action_token
        refresh_link = (
            '<a href="' + rerun_url + '" '
            'style="color:#1a73e8;text-decoration:none;font-size:13px;font-weight:600;'
            'float:right;line-height:1;">'
            "&#8635; Refresh</a>"
        )
    else:
        refresh_link = ""

    # Build subtitle with stats merged in
    subtitle_parts = [str(count) + " item" + plural, today.split(",")[0].strip()]
    if urgency_count > 0:
        subtitle_parts.append("&#9888; " + str(urgency_count) + " overdue")
    subtitle = " &middot; ".join(subtitle_parts)

    # Footer
    footer_content = (
        '<span style="font-size:11px;color:#b0b0b0;">'
        "Sent by Gmail Email Actions</span>"
    )

    # "Manage on Web" link
    web_link = ""
    if function_url and action_token:
        web_url = function_url.rstrip("/") + "?action=web&token=" + action_token
        web_link = (
            '<a href="' + web_url + '" '
            'style="color:#1a73e8;background:#e8f0fe;'
            "text-decoration:none;font-weight:600;font-size:12px;"
            "padding:5px 14px;border-radius:14px;display:inline-block;"
            'margin-top:10px;">Manage on Web &#8594;</a>'
        )

    # Text-only header — no blue banner, matches minimal list rows
    header_row = (
        '<tr><td style="padding:20px 20px 16px;">'
        + refresh_link
        + '<div style="font-size:18px;font-weight:700;color:#202124;line-height:1.3;">'
        "Starred Emails</div>"
        '<div style="margin-top:6px;font-size:13px;color:#5f6368;">'
        + subtitle
        + "</div>"
        + web_link
        + '<div style="margin-top:14px;border-bottom:2px solid #1a73e8;"></div>'
        "</td></tr>"
    )

    return (
        "<!DOCTYPE html>"
        "<html>"
        '<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>'
        "<body style=\"margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',"
        'Roboto,Helvetica,Arial,sans-serif;">'
        '<table width="100%" cellpadding="0" cellspacing="0" style="padding:20px 0;">'
        '<tr><td align="center">'
        '<table cellpadding="0" cellspacing="0" '
        'style="max-width:600px;width:100%;overflow:hidden;">'
        # Header
        + header_row
        # Content
        + '<tr><td style="padding:8px 20px 16px;">' + table_section + "</td></tr>"
        # Footer
        '<tr><td style="padding:12px 20px;text-align:center;">'
        + footer_content
        + "</td></tr>"
        "</table>"
        "</td></tr></table>"
        "</body></html>"
    )


def build_web_html(
    tasks: List[Dict[str, Any]],
    function_url: str = "",
    action_token: str = "",
    embed: bool = False,
    projects: List[Dict[str, Any]] = None,
) -> str:
    """Build an interactive web page listing starred emails with one-click unstar.

    Args:
        projects: Optional list of Todoist project dicts for "Move to Todoist" dropdown.
    """
    tasks = _sort_by_most_recent(tasks)
    count = len(tasks)
    today = datetime.now().strftime("%B %d, %Y")
    plural = "s" if count != 1 else ""
    projects = projects or []

    _FONT = "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif"

    # Build project options HTML for move-to-todoist dropdowns
    project_options_html = (
        '<option value="" disabled selected>Move to Todoist...</option>'
    )
    for proj in sorted(projects, key=lambda p: p.get("name", "").lower()):
        pid = proj.get("id", "")
        pname = proj.get("name", "")
        project_options_html += '<option value="' + pid + '">' + pname + "</option>"

    cards = ""
    for task in tasks:
        task_id = task.get("id", "")
        description = task.get("description", "")
        gmail_link = _extract_gmail_link(description)
        from_addr = _extract_field(description, "\U0001f4e7")
        date_received = _extract_field(description, "\U0001f4c5")
        age = _days_ago(date_received) if date_received else "?"
        days_int = _days_ago_int(date_received) if date_received else -1
        content = _strip_from_suffix(task.get("content", ""))
        if content.startswith("[Action] "):
            content = content[len("[Action] ") :]

        msg_id = ""
        open_url = ""
        unstar_btn = ""

        if gmail_link:
            msg_id = _extract_msg_id_field(description) or _extract_msg_id_from_link(
                gmail_link
            )

            if function_url and action_token:
                _thread_id = (
                    gmail_link.split("#inbox/")[-1] if "#inbox/" in gmail_link else ""
                )
                if _thread_id:
                    open_url = (
                        function_url.rstrip("/")
                        + "?action=open&msg_id="
                        + msg_id
                        + "&thread_id="
                        + _thread_id
                        + "&token="
                        + action_token
                    )
                else:
                    open_url = gmail_link
            else:
                open_url = gmail_link

            if function_url and action_token and msg_id:
                unstar_btn = (
                    "<button onclick=\"event.stopPropagation();doUnstar(this,'"
                    + msg_id
                    + "')\" "
                    'class="action-pill" style="color:var(--err);background:var(--err-bg);border:1px solid var(--err-b);">'
                    "&#10005; Unstar</button>"
                )

        age_css = _age_style(days_int)

        meta_parts = []
        meta_parts.append('<span style="' + age_css + '">' + age + "</span>")
        if from_addr:
            meta_parts.append(from_addr.replace("@", "&#64;"))
        info_html = " &middot; ".join(meta_parts)

        # Action row: unstar + date picker + priority + move to todoist dropdown
        action_parts = []
        if unstar_btn:
            action_parts.append(unstar_btn)
        if task_id:
            # Date picker (updates task directly)
            date_input = (
                '<input type="date" class="action-pill due-date-picker"'
                ' style="color:var(--accent-l);background:var(--accent-bg);font-size:12px;'
                'padding:4px 8px;border:1px solid var(--accent-b);border-radius:6px;cursor:pointer;"'
                ' onclick="event.stopPropagation()"'
                ' onchange="event.stopPropagation();'
                "doSetDueDate('" + task_id + "',this.value,this)\">"
            )
            action_parts.append(date_input)
            # Priority dropdown (updates task directly)
            priority_select = (
                '<select class="action-pill priority-picker"'
                ' style="color:var(--warn);background:var(--warn-bg);font-size:12px;'
                'padding:4px 8px;border:1px solid var(--warn-b);border-radius:6px;cursor:pointer;"'
                ' onclick="event.stopPropagation()"'
                ' onchange="event.stopPropagation();'
                "doSetPriority('" + task_id + "',this.value,this)\">"
                '<option value="" disabled selected>Priority</option>'
                '<option value="4">P1</option>'
                '<option value="3">P2</option>'
                '<option value="2">P3</option>'
                '<option value="1">P4</option>'
                "</select>"
            )
            action_parts.append(priority_select)
        if task_id:
            # Best Case button
            bestcase_btn = (
                "<button onclick=\"event.stopPropagation();doBestCase('"
                + task_id
                + "',this)\" "
                'class="action-pill bestcase-btn" style="color:var(--purple);background:var(--purple-bg);border:1px solid var(--purple-b);'  # noqa: E501
                'font-weight:600;">Best Case</button>'
            )
            action_parts.append(bestcase_btn)
        if projects and task_id:
            move_select = (
                '<select class="action-pill" style="color:var(--accent-l);background:var(--accent-bg);border:1px solid var(--accent-b);"'  # noqa: E501
                ' onclick="event.stopPropagation()"'
                ' onchange="event.stopPropagation();'
                "doMoveTodoist(this,'"
                + msg_id
                + "','"
                + task_id
                + "',this.value)\">"
                + project_options_html
                + "</select>"
            )
            action_parts.append(move_select)
        action_html = (
            (
                '<div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">'
                + "".join(action_parts)
                + "</div>"
            )
            if action_parts
            else ""
        )

        data_attr = ' data-msg-id="' + msg_id + '"' if msg_id else ""
        data_open = ' data-open-url="' + open_url + '"' if open_url else ""
        data_task_id = ' data-task-id="' + task_id + '"' if task_id else ""

        # Checkbox for multi-select
        checkbox = (
            '<input type="checkbox" class="select-cb" '
            'onclick="event.stopPropagation();updateSelection()" '
            'style="width:18px;height:18px;margin-right:10px;cursor:pointer;flex-shrink:0;">'
        )

        cards += (
            '<div class="email-card"'
            + data_attr
            + data_open
            + data_task_id
            + ' onclick="openEmail(this)"'
            + ' style="background:var(--bg-s1);border-radius:8px;border:1px solid var(--border);padding:14px 16px;margin-bottom:10px;cursor:pointer;'  # noqa: E501
            'transition:opacity .3s,max-height .3s,padding .3s;display:flex;align-items:flex-start;">'
            + checkbox
            + '<div style="flex:1;min-width:0;">'
            '<div style="font-size:15px;font-weight:600;color:var(--text-1);line-height:1.4;">'
            + content
            + "</div>"
            '<div style="margin-top:6px;font-size:12px;color:var(--text-2);line-height:1.4;">'
            + info_html
            + "</div>"
            + action_html
            + "</div></div>"
        )

    if count == 0:
        content_section = (
            '<div id="all-clear" style="text-align:center;padding:40px 0;color:var(--text-2);font-size:15px;">'
            "No outstanding email actions. Inbox zero!</div>"
        )
    else:
        content_section = '<div id="card-list">' + cards + "</div>"

    # JavaScript for inline unstar + split-pane viewer + move to todoist + multi-select
    js = (
        "<script>"
        "var _cs=getComputedStyle(document.documentElement);function cv(n){return _cs.getPropertyValue(n).trim();}"
        # openEmail: load email in right pane iframe
        "function openEmail(card){"
        "if(document.activeElement&&document.activeElement.classList.contains('select-cb'))return;"
        "var url=card.getAttribute('data-open-url');"
        "if(!url)return;"
        "document.querySelectorAll('.email-card').forEach(function(c){"
        "c.style.background='';c.classList.remove('active-email');});"
        "card.style.background=cv('--accent-hbg');card.classList.add('active-email');"
        "var frame=document.getElementById('viewer-frame');"
        "frame.src=url+'&embed=1';"
        "document.getElementById('viewer-placeholder').style.display='none';"
        "frame.style.display='block';"
        "if(window.innerWidth<=768){"
        "document.getElementById('viewer-pane').style.display='flex';"
        "document.querySelector('.left-pane').style.flex='0 0 45%';"
        "}"
        "}"
        # closeViewer: show placeholder, hide iframe; on mobile also hide pane
        "function closeViewer(){"
        "var frame=document.getElementById('viewer-frame');"
        "frame.src='';"
        "frame.style.display='none';"
        "document.getElementById('viewer-placeholder').style.display='flex';"
        "document.querySelectorAll('.email-card').forEach(function(c){"
        "c.style.background='';c.classList.remove('active-email');});"
        "if(window.innerWidth<=768){"
        "document.getElementById('viewer-pane').style.display='none';"
        "document.querySelector('.left-pane').style.flex='1 1 100%';"
        "}"
        "}"
        # removeCard: animate out + update count
        "function removeCard(msgId){"
        "var card=document.querySelector('.email-card[data-msg-id=\"'+msgId+'\"]');"
        "if(!card)return;"
        "card.style.opacity='0';"
        "setTimeout(function(){"
        "card.style.maxHeight='0';card.style.padding='0';card.style.overflow='hidden';"
        "setTimeout(function(){card.remove();updateCount();updateSelection();},300);"
        "},300);"
        "}"
        # doUnstar (from list button)
        "function doUnstar(btn,msgId){"
        "btn.disabled=true;"
        "btn.style.background=cv('--border');"
        "btn.style.color=cv('--text-3');"
        "btn.innerHTML='Unstarring\\u2026';"
        "var card=btn.closest('.email-card');"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=unstar&msg_id='+msgId"
        "+'&token=" + (action_token or "") + "';"
        "fetch(url).then(function(r){"
        "if(r.ok){"
        "var activeCard=document.querySelector('.email-card.active-email');"
        "if(activeCard&&activeCard===card){closeViewer();}"
        "removeCard(msgId);"
        "}else{"
        "btn.disabled=false;"
        "btn.style.background=cv('--err-bg');"
        "btn.style.color=cv('--err');"
        "btn.innerHTML='Failed \\u2013 Retry';"
        "}"
        "}).catch(function(){"
        "btn.disabled=false;"
        "btn.style.background=cv('--err-bg');"
        "btn.style.color=cv('--err');"
        "btn.innerHTML='Failed \\u2013 Retry';"
        "});"
        "}"
        # doMoveTodoist: move existing task to a different project, then unstar
        "function doMoveTodoist(sel,msgId,taskId,projectId){"
        "if(!projectId)return;"
        "sel.disabled=true;"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=move_to_project&msg_id='+msgId+'&task_id='+taskId+'&project_id='+projectId"
        "+'&token=" + (action_token or "") + "';"
        "fetch(url).then(function(r){"
        "if(r.ok){"
        "var card=sel.closest('.email-card');"
        "var activeCard=document.querySelector('.email-card.active-email');"
        "if(activeCard&&activeCard===card){closeViewer();}"
        "removeCard(msgId);"
        "}else{sel.disabled=false;sel.selectedIndex=0;alert('Move failed');}"
        "}).catch(function(){sel.disabled=false;sel.selectedIndex=0;alert('Move failed');});"
        "}"
        # doSetDueDate: update task due date directly
        "function doSetDueDate(taskId,dateValue,input){"
        "input.disabled=true;"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=set_due_date&task_id='+taskId+'&date='+encodeURIComponent(dateValue)"
        "+'&token=" + (action_token or "") + "';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "input.disabled=false;"
        "if(d.ok){"
        "input.style.background=cv('--ok-bg');input.style.color=cv('--ok');"
        "setTimeout(function(){input.style.background=cv('--accent-bg');input.style.color=cv('--accent-l');},1500);"
        "}else{input.style.background=cv('--err-bg');input.style.color=cv('--err');}"
        "}).catch(function(){input.disabled=false;input.style.background=cv('--err-bg');input.style.color=cv('--err');});"
        "}"
        # doSetPriority: update task priority directly
        "function doSetPriority(taskId,priority,sel){"
        "sel.disabled=true;"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=set_priority&task_id='+taskId+'&priority='+priority"
        "+'&token=" + (action_token or "") + "';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "sel.disabled=false;"
        "if(d.ok){"
        "sel.style.background=cv('--ok-bg');sel.style.color=cv('--ok');"
        "setTimeout(function(){sel.style.background=cv('--warn-bg');sel.style.color=cv('--warn');},1500);"
        "}else{sel.style.background=cv('--err-bg');sel.style.color=cv('--err');}"
        "}).catch(function(){sel.disabled=false;sel.style.background=cv('--err-bg');sel.style.color=cv('--err');});"
        "}"
        # doBestCase: add Best Case label, remove Commit if present, move to Personal
        "function doBestCase(taskId,btn){"
        "btn.disabled=true;"
        "btn.style.background=cv('--border');btn.style.color=cv('--text-3');"
        "btn.innerHTML='Setting\\u2026';"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=bestcase_label&task_id='+taskId"
        "+'&token=" + (action_token or "") + "';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){"
        "btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        "btn.innerHTML='\\u2713 Best Case';"
        "btn.style.cursor='default';"
        "}else{"
        "btn.disabled=false;"
        "btn.style.background=cv('--purple-bg');btn.style.color=cv('--purple');"
        "btn.innerHTML='Failed \\u2013 Retry';"
        "}"
        "}).catch(function(){"
        "btn.disabled=false;"
        "btn.style.background=cv('--purple-bg');btn.style.color=cv('--purple');"
        "btn.innerHTML='Failed \\u2013 Retry';"
        "});"
        "}"
        # Listen for postMessage from embedded viewer (unstar success)
        "window.addEventListener('message',function(e){"
        "if(e.data&&e.data.type==='unstar'&&e.data.msgId){"
        "closeViewer();"
        "removeCard(e.data.msgId);"
        "}"
        "});"
        "function updateCount(){"
        "var remaining=document.querySelectorAll('.email-card').length;"
        "var el=document.getElementById('item-count');"
        "if(el){el.textContent=remaining+' item'+(remaining===1?'':'s');}"
        "try{window.parent.postMessage({type:'count',source:'starred',count:remaining},'*');}catch(e){}"
        "if(remaining===0){"
        "var list=document.getElementById('card-list');"
        "if(list){list.innerHTML="
        '\'<div style="text-align:center;padding:40px 0;color:var(--ok);font-size:16px;font-weight:600;">'
        "\\u2713 All clear!</div>';}"
        "}"
        "}"
        # Multi-select functions
        "function getSelectedCards(){"
        "var cards=[];"
        "document.querySelectorAll('.select-cb:checked').forEach(function(cb){"
        "var card=cb.closest('.email-card');"
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
        # Bulk unstar
        "function bulkUnstar(){"
        "var cards=getSelectedCards();"
        "cards.forEach(function(card){"
        "var msgId=card.getAttribute('data-msg-id');"
        "if(!msgId)return;"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=unstar&msg_id='+msgId"
        "+'&token=" + (action_token or "") + "';"
        "fetch(url).then(function(r){if(r.ok){removeCard(msgId);}});"
        "});"
        "}"
        # Bulk move to todoist
        "function bulkMoveTodoist(projectId){"
        "if(!projectId)return;"
        "var cards=getSelectedCards();"
        "cards.forEach(function(card){"
        "var msgId=card.getAttribute('data-msg-id');"
        "var taskId=card.getAttribute('data-task-id');"
        "if(!taskId)return;"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=move_to_project&msg_id='+msgId+'&task_id='+taskId+'&project_id='+projectId"
        "+'&token=" + (action_token or "") + "';"
        "fetch(url).then(function(r){if(r.ok){removeCard(msgId);}});"
        "});"
        "}"
        # Bulk set due date
        "function bulkSetDueDate(dateValue){"
        "if(!dateValue)return;"
        "var cards=getSelectedCards();"
        "cards.forEach(function(card){"
        "var taskId=card.getAttribute('data-task-id');"
        "if(!taskId)return;"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=set_due_date&task_id='+taskId+'&date='+encodeURIComponent(dateValue)"
        "+'&token=" + (action_token or "") + "';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){"
        "var inp=card.querySelector('.due-date-picker');"
        "if(inp){inp.value=dateValue;inp.style.background=cv('--ok-bg');inp.style.color=cv('--ok');"
        "setTimeout(function(){inp.style.background=cv('--accent-bg');inp.style.color=cv('--accent-l');},1500);}"
        "}"
        "});"
        "});"
        "}"
        # Bulk set priority
        "function bulkSetPriority(priority){"
        "if(!priority)return;"
        "var cards=getSelectedCards();"
        "cards.forEach(function(card){"
        "var taskId=card.getAttribute('data-task-id');"
        "if(!taskId)return;"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=set_priority&task_id='+taskId+'&priority='+priority"
        "+'&token=" + (action_token or "") + "';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){"
        "var sel=card.querySelector('.priority-picker');"
        "if(sel){sel.value=priority;sel.style.background=cv('--ok-bg');sel.style.color=cv('--ok');"
        "setTimeout(function(){sel.style.background=cv('--warn-bg');sel.style.color=cv('--warn');},1500);}"
        "}"
        "});"
        "});"
        "}"
        # Bulk best case
        "function bulkBestCase(){"
        "var cards=getSelectedCards();"
        "cards.forEach(function(card){"
        "var taskId=card.getAttribute('data-task-id');"
        "if(!taskId)return;"
        "var btn=card.querySelector('.bestcase-btn');"
        "if(btn){btn.disabled=true;btn.style.background=cv('--border');btn.innerHTML='Setting\\u2026';}"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=bestcase_label&task_id='+taskId"
        "+'&token=" + (action_token or "") + "';"
        "fetch(url).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok&&btn){"
        "btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
        "btn.innerHTML='\\u2713 Best Case';btn.style.cursor='default';}"
        "});"
        "});"
        "}"
        "</script>"
    )

    # Embed mode: hide header, full-height split, post count to parent on load
    embed_css = ""
    embed_onload = ""
    split_height = "calc(100vh - 56px)"
    if embed:
        embed_css = ".top-bar{display:none;}"
        split_height = "100vh"
        embed_onload = (
            "<script>"
            "window.addEventListener('load',function(){"
            "var c=document.querySelectorAll('.email-card').length;"
            "try{window.parent.postMessage({type:'count',source:'starred',count:c},'*');}catch(e){}"
            "});"
            "</script>"
        )

    # Bulk toolbar HTML
    bulk_toolbar = (
        '<div id="bulk-toolbar" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);'
        "background:rgba(22,22,24,0.95);backdrop-filter:blur(12px);border:1px solid var(--border);color:var(--text-1);padding:10px 18px;border-radius:12px;"  # noqa: E501
        "box-shadow:0 4px 16px rgba(0,0,0,.25);display:none;align-items:center;gap:10px;"
        'z-index:500;font-size:13px;font-weight:500;">'
        '<span id="bulk-count">0 selected</span>'
        # Bulk date picker
        '<input type="date" style="font-size:12px;padding:5px 8px;border-radius:6px;'
        'border:1px solid var(--border-h);background:var(--bg-s2);color:var(--text-1);" '
        'onchange="bulkSetDueDate(this.value)">'
        # Bulk priority
        '<select style="font-size:12px;padding:5px 8px;border-radius:6px;border:1px solid var(--border-h);'
        'background:var(--bg-s2);color:var(--text-1);" '
        'onchange="bulkSetPriority(this.value);this.selectedIndex=0;">'
        '<option value="" disabled selected>Priority</option>'
        '<option value="4">P1</option>'
        '<option value="3">P2</option>'
        '<option value="2">P3</option>'
        '<option value="1">P4</option>'
        "</select>"
    )
    if projects:
        bulk_toolbar += (
            '<select style="font-size:12px;padding:5px 8px;border-radius:6px;border:1px solid var(--border-h);'
            'background:var(--bg-s2);color:var(--text-1);" '
            'onchange="bulkMoveTodoist(this.value);this.selectedIndex=0;">'
            + project_options_html
            + "</select>"
        )
    bulk_toolbar += (
        '<button onclick="bulkBestCase()" style="font-size:12px;font-weight:600;padding:6px 14px;'
        'border:none;border-radius:6px;cursor:pointer;background:var(--purple-bg);color:var(--purple);border:1px solid var(--purple-b);">Best Case</button>'  # noqa: E501
        '<button onclick="bulkUnstar()" style="font-size:12px;font-weight:600;padding:6px 14px;'
        'border:none;border-radius:6px;cursor:pointer;background:var(--err-bg);color:var(--err);border:1px solid var(--err-b);">Unstar</button>'  # noqa: E501
        "</div>"
    )

    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Cache-Control" content="no-cache,no-store,must-revalidate">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
        "<title>Starred Emails</title>"
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
        "body{font-family:"
        + _FONT
        + ";background:var(--bg-base);color:var(--text-1);margin:0;padding:0;"
        "-webkit-font-smoothing:antialiased;}"
        ".top-bar{background:var(--bg-s0);border-bottom:1px solid var(--border);padding:18px 20px;display:flex;align-items:center;gap:12px;}"  # noqa: E501
        + embed_css
        + ".split-wrap{display:flex;height:"
        + split_height
        + ";overflow:hidden;}"
        ".left-pane{flex:0 0 45%;min-width:0;overflow-y:auto;background:var(--bg-s0);}"
        "#viewer-pane{display:flex;flex-direction:column;flex:1 1 55%;"
        "border-left:1px solid var(--border);background:var(--bg-s1);position:relative;overflow:hidden;}"
        "#viewer-frame{width:100%;height:100%;border:none;display:none;}"
        ".close-btn{position:absolute;top:10px;right:14px;z-index:11;"
        "background:var(--border);border:none;cursor:pointer;font-size:20px;"
        "color:var(--text-2);width:36px;height:36px;border-radius:50%;display:flex;"
        "align-items:center;justify-content:center;}"
        ".close-btn:hover{background:var(--border-h);}"
        ".action-pill{border:none;cursor:pointer;font-weight:600;font-size:12px;"
        "padding:5px 14px;border-radius:6px;font-family:inherit;}"
        ".select-all-row{display:flex;align-items:center;padding:10px 24px 0;"
        "font-size:13px;color:var(--text-2);}"
        ".select-all-row label{display:flex;align-items:center;gap:6px;cursor:pointer;font-weight:500;}"
        "@media(max-width:768px){"
        ".left-pane{flex:1 1 100%!important;}"
        "#viewer-pane{display:none;position:fixed;top:0;right:0;bottom:0;width:100%;z-index:10;"
        "border-left:none;}"
        ".close-btn{top:12px;left:12px;right:auto;"
        "background:var(--border-h);color:var(--text-1);}"
        "#bulk-toolbar{left:10px!important;right:10px;transform:none!important;"
        "flex-wrap:wrap;justify-content:center;}"
        "}"
        "::-webkit-scrollbar{width:6px;}"
        "::-webkit-scrollbar-track{background:transparent;}"
        "::-webkit-scrollbar-thumb{background:var(--scrollbar);border-radius:3px;}"
        "</style>" + embed_onload + "</head>"
        '<body style="font-family:'
        + _FONT
        + ";background:var(--bg-base);color:var(--text-1);margin:0;padding:0;"
        '-webkit-font-smoothing:antialiased;">'
        # Top header bar
        '<div class="top-bar">'
        '<span style="color:var(--text-1);font-size:17px;font-weight:600;letter-spacing:-0.2px;">'
        "&#9993; Starred Emails</span>"
        '<button onclick="location.reload()" '
        'style="margin-left:auto;background:var(--border);border:1px solid var(--border);color:var(--text-1);'
        'font-size:13px;font-weight:600;padding:6px 14px;border-radius:6px;cursor:pointer;">'
        "&#8635; Refresh</button>"
        "</div>"
        # Split-pane wrapper
        '<div class="split-wrap">'
        # Left pane — email list
        '<div class="left-pane">'
        '<div style="max-width:700px;margin:0 auto;min-height:100%;">'
        '<div style="padding:20px 24px 0;">'
        '<div style="font-size:13px;color:var(--text-2);">'
        '<span id="item-count">' + str(count) + " item" + plural + "</span>"
        " &middot; " + today + "</div>"
        '<div style="margin-top:14px;border-bottom:2px solid var(--accent);"></div>'
        "</div>"
        # Select all row
        + (
            '<div class="select-all-row">'
            '<label><input type="checkbox" id="select-all-cb" onclick="toggleSelectAll()"> Select All</label>'
            "</div>"
            if count > 0
            else ""
        )
        + '<div style="padding:0 24px 24px;">'
        + content_section
        + "</div></div></div>"
        # Right pane — email viewer
        '<div id="viewer-pane">'
        '<button class="close-btn" onclick="closeViewer()" title="Close">&times;</button>'
        '<div id="viewer-placeholder" style="'
        "flex:1;display:flex;flex-direction:column;align-items:center;"
        'justify-content:center;color:var(--text-3);font-size:15px;gap:12px;">'
        '<span style="font-size:40px;">&#9993;</span>'
        "<span>Select an email to read it</span>"
        "</div>"
        '<iframe id="viewer-frame"></iframe>'
        "</div>"
        "</div>" + bulk_toolbar + js + "</body></html>"  # end split-wrap
    )


def send_daily_digest(
    open_tasks: List[Dict[str, Any]],
    recipient: str,
    ses_sender: str,
    function_url: str = "",
    action_token: str = "",
) -> None:
    """Compose and send the HTML daily digest via SES.

    Args:
        open_tasks: List of Todoist task dicts from Email Actions project
        recipient: Destination email address
        ses_sender: Verified SES sender address
        function_url: Lambda Function URL for action links (optional)
        action_token: Secret token for authenticating action links (optional)
    """
    count = len(open_tasks)
    subject = f"Starred Emails — {count} outstanding item{'s' if count != 1 else ''}"
    html_body = _build_html(
        open_tasks, function_url=function_url, action_token=action_token
    )

    try:
        _ses.send_email(
            Source=ses_sender,
            Destination={"ToAddresses": [recipient]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
        )
        logger.info(f"Daily digest sent to {recipient} ({count} tasks)")
    except Exception as e:
        logger.error(f"Failed to send daily digest: {e}")
        raise
