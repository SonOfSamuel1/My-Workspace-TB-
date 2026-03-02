"""Compose and send the daily Unread Emails HTML digest via SES."""

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List

import boto3

logger = logging.getLogger(__name__)

_ses = boto3.client("ses", region_name="us-east-1")

GMAIL_DEEP_LINK = "https://mail.google.com/mail/u/0/#inbox/{thread_id}"

# ---------------------------------------------------------------------------
# Inline SVG icons (replace platform-dependent emoji with crisp vector art)
# ---------------------------------------------------------------------------
_SVG_ENVELOPE = (
    '<svg style="display:inline-block;vertical-align:middle" width="16" height="16" '
    'viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="1.5" y="3" width="13" height="10" rx="1.5"/>'
    '<path d="M1.5 4.5L8 9l6.5-4.5"/></svg>'
)
_SVG_ENVELOPE_LG = (
    '<svg style="display:inline-block;vertical-align:middle" width="40" height="40" '
    'viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="1.5" y="3" width="13" height="10" rx="1.5"/>'
    '<path d="M1.5 4.5L8 9l6.5-4.5"/></svg>'
)
_SVG_BLOCK = (
    '<svg style="display:inline-block;vertical-align:middle" width="14" height="14" '
    'viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">'
    '<circle cx="8" cy="8" r="6"/>'
    '<line x1="3.8" y1="3.8" x2="12.2" y2="12.2"/></svg>'
)
_SVG_CALENDAR = (
    '<svg style="display:inline-block;vertical-align:middle" width="14" height="14" '
    'viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round">'
    '<rect x="2" y="3.5" width="12" height="10.5" rx="1.5"/>'
    '<path d="M2 7h12"/><path d="M5.5 1.5v3"/><path d="M10.5 1.5v3"/></svg>'
)
_SVG_TASK = (
    '<svg style="display:inline-block;vertical-align:middle" width="14" height="14" '
    'viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="2" y="2" width="12" height="12" rx="2"/>'
    '<path d="M5 8l2 2 4-4"/></svg>'
)
_SVG_RECORD = (
    '<svg style="display:inline-block;vertical-align:middle" width="10" height="10" '
    'viewBox="0 0 10 10"><circle cx="5" cy="5" r="4" fill="currentColor"/></svg>'
)
_CC_LABEL = "Claude"


def _days_ago(date_str: str) -> str:
    """Return a compact age string like '3d' or 'today' from an RFC 2822 date string."""
    try:
        from zoneinfo import ZoneInfo

        eastern = ZoneInfo("America/New_York")
        dt = parsedate_to_datetime(date_str).astimezone(eastern)
        now = datetime.now(eastern)
        days = (now.date() - dt.date()).days
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


def _sort_by_most_recent(emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort emails by received date, most recent first."""

    def _sort_key(email):
        date_str = email.get("date", "")
        if date_str:
            try:
                return parsedate_to_datetime(date_str).timestamp()
            except Exception:
                pass
        return 0

    return sorted(emails, key=_sort_key, reverse=True)


def _age_style(days: int) -> str:
    """Return inline CSS color for the age badge based on days old."""
    if days > 14:
        return "color:#d93025;font-weight:600;"
    elif days > 7:
        return "color:#e37400;font-weight:600;"
    return "color:#5f6368;"


def _extract_msg_id_from_link(gmail_link: str) -> str:
    """Extract the Gmail message ID from a deep link like .../mail/u/0/#inbox/<id>."""
    if "#inbox/" in gmail_link:
        return gmail_link.split("#inbox/")[-1].rstrip("/")
    return gmail_link.rstrip("/").split("/")[-1]


def _build_html(
    emails: List[Dict[str, Any]], function_url: str = "", action_token: str = ""
) -> str:
    """Build the HTML body for the digest email.

    Args:
        emails: List of email dicts with keys: id, subject, from, date, gmail_link
    """
    emails = _sort_by_most_recent(emails)
    count = len(emails)
    today = datetime.now().strftime("%B %d, %Y")
    plural = "s" if count != 1 else ""

    # Compute urgency count (items older than 7 days)
    urgency_count = 0
    for email in emails:
        date_received = email.get("date", "")
        if date_received and _days_ago_int(date_received) > 7:
            urgency_count += 1

    rows = ""
    for idx, email in enumerate(emails):
        gmail_link = email.get("gmail_link", "")
        from_addr = email.get("from", "")
        date_received = email.get("date", "")
        age = _days_ago(date_received) if date_received else "?"
        days_int = _days_ago_int(date_received) if date_received else -1
        subject = email.get("subject", "(no subject)")
        msg_id = email.get("id", "")

        open_url = ""
        markread_link = ""
        open_link = ""

        if gmail_link:
            if not msg_id:
                msg_id = _extract_msg_id_from_link(gmail_link)

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
                markread_url = (
                    function_url.rstrip("/")
                    + "?action=markread&msg_id="
                    + msg_id
                    + "&token="
                    + action_token
                )
                markread_link = (
                    '<a href="' + markread_url + '" '
                    'style="color:#188038;background:#e6f4ea;'
                    "text-decoration:none;font-weight:600;font-size:12px;"
                    'padding:5px 12px;border-radius:14px;display:inline-block;">'
                    "&#10003; Mark Read</a>"
                )

            open_link = (
                '<a href="' + open_url + '" '
                'style="color:#1a73e8;background:#e8f0fe;'
                "text-decoration:none;font-weight:600;font-size:12px;"
                'padding:5px 12px;border-radius:14px;display:inline-block;">'
                "Open &#8594;</a>"
            )

        # Subject line (always plain text — "Open ->" pill provides the link)
        subject_html = (
            '<div style="font-size:15px;font-weight:600;color:#202124;line-height:1.4;">'
            + subject
            + "</div>"
        )

        age_css = _age_style(days_int)

        # Info line: age . sender
        meta_parts = []
        meta_parts.append('<span style="' + age_css + '">' + age + "</span>")
        if from_addr:
            meta_parts.append(from_addr.replace("@", "&#64;"))
        info_html = " &middot; ".join(meta_parts)

        # Action line: mark read . open (separate row for tap targets)
        action_parts = []
        if markread_link:
            action_parts.append(markread_link)
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
        table_section = (
            "<p style='color:#5f6368;font-size:15px;'>No unread emails. Inbox zero!</p>"
        )
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
        subtitle_parts.append(str(urgency_count) + " overdue")
    subtitle = " &middot; ".join(subtitle_parts)

    # Footer
    footer_content = (
        '<span style="font-size:11px;color:#b0b0b0;">'
        "Sent by Gmail Unread Digest</span>"
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
        "Unread Emails</div>"
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


def build_cards_html(
    emails: List[Dict[str, Any]],
    function_url: str = "",
    action_token: str = "",
    projects: List[Dict[str, Any]] = None,
    toggl_projects: List[Dict[str, Any]] = None,
    view_type: str = "unread",
) -> tuple:
    """Return (cards_html, count) for AJAX refresh.

    cards_html is the ``<div id="card-list">...</div>`` content (or "inbox zero" message).
    count is the number of emails.
    """
    emails = _sort_by_most_recent(emails)
    count = len(emails)
    projects = projects or []
    toggl_projects = toggl_projects or []

    # Build project options HTML for move-to-todoist dropdowns
    project_options_html = (
        '<option value="" disabled selected>Move to Todoist...</option>'
    )
    for proj in sorted(projects, key=lambda p: p.get("name", "").lower()):
        pid = proj.get("id", "")
        pname = proj.get("name", "")
        project_options_html += '<option value="' + pid + '">' + pname + "</option>"

    # Build project options HTML for start-toggl-timer dropdowns
    toggl_project_options_html = ""
    if toggl_projects:
        toggl_project_options_html = (
            '<option value="" disabled selected>\u25b6 Toggl\u2026</option>'
        )
        for tp in sorted(toggl_projects, key=lambda p: p.get("name", "").lower()):
            toggl_project_options_html += (
                '<option value="' + str(tp.get("id", "")) + '"'
                ' data-workspace-id="'
                + str(tp.get("workspace_id", ""))
                + '">'
                + tp.get("name", "")
                + "</option>"
            )

    cards = ""
    for email_item in emails:
        gmail_link = email_item.get("gmail_link", "")
        from_addr = email_item.get("from", "")
        date_received = email_item.get("date", "")
        age = _days_ago(date_received) if date_received else "?"
        days_int = _days_ago_int(date_received) if date_received else -1
        subject = email_item.get("subject", "(no subject)")
        msg_id = email_item.get("id", "")

        open_url = ""
        markread_btn = ""
        skip_inbox_btn = ""

        if gmail_link:
            if not msg_id:
                msg_id = _extract_msg_id_from_link(gmail_link)

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
                markread_btn = (
                    "<button onclick=\"event.stopPropagation();doMarkRead(this,'"
                    + msg_id
                    + "')\" "
                    'class="action-pill" style="color:var(--ok);background:var(--ok-bg);border:1px solid var(--ok-b);">'
                    "&#10003; Mark Read</button>"
                )

        # Skip Inbox button — extract raw email address for filter
        if function_url and action_token and from_addr:
            import re as _re
            import urllib.parse as _urlparse

            _email_match = _re.search(r"<([^>]+)>", from_addr)
            _sender_email = _email_match.group(1) if _email_match else from_addr.strip()
            if _sender_email:
                _filter_url = (
                    function_url.rstrip("/")
                    + "?action=create_filter"
                    + "&from_email="
                    + _urlparse.quote(_sender_email)
                    + "&token="
                    + action_token
                )
                skip_inbox_btn = (
                    "<button onclick=\"event.stopPropagation();doSkipInbox(this,'"
                    + _filter_url
                    + "','"
                    + msg_id
                    + "')\" "
                    'class="action-pill" style="color:var(--warn);background:var(--warn-bg);border:1px solid var(--warn-b);">'
                    + _SVG_BLOCK
                    + " Skip Inbox</button>"
                )

        age_css = _age_style(days_int)

        meta_parts = []
        meta_parts.append('<span style="' + age_css + '">' + age + "</span>")
        if from_addr:
            meta_parts.append(from_addr.replace("@", "&#64;"))
        info_html = " &middot; ".join(meta_parts)

        # Assign CC button — copy email info to clipboard for Claude Code
        safe_subject_cc = subject.replace("'", "\\'").replace('"', "&quot;")
        safe_from_cc = from_addr.replace("'", "\\'").replace('"', "&quot;")
        safe_gmail_cc = gmail_link.replace("'", "\\'").replace('"', "&quot;")
        assign_cc_btn = (
            "<button onclick=\"event.stopPropagation();doCopyEmailForClaude(this,'"
            + safe_subject_cc
            + "','"
            + safe_from_cc
            + "','"
            + safe_gmail_cc
            + "')\" "
            'class="action-pill assign-cc-btn" title="Assign CC" '
            'style="display:inline-flex;align-items:center;justify-content:center;'
            "padding:5px 10px;min-height:36px;background:rgba(196,120,64,0.10);"
            "border:1px solid rgba(196,120,64,0.25);border-radius:6px;"
            'cursor:pointer;">' + _CC_LABEL + "</button>"
        )

        # Action row: mark read + skip inbox + assign cc + date picker + priority + move to todoist dropdown
        action_parts = []
        if markread_btn:
            action_parts.append(markread_btn)
        if skip_inbox_btn:
            action_parts.append(skip_inbox_btn)
        action_parts.append(assign_cc_btn)
        # Date picker (calendar icon button wrapping a hidden native date input)
        date_input = (
            '<label class="action-pill due-date-wrap"'
            ' style="color:var(--accent-l);background:var(--accent-bg);font-size:12px;'
            "padding:5px 10px;min-height:36px;border:1px solid var(--accent-b);border-radius:6px;cursor:pointer;"
            'display:inline-flex;align-items:center;gap:4px;position:relative;"'
            ' onclick="event.stopPropagation()">'
            + _SVG_CALENDAR
            + '<span class="due-date-text" style="font-size:12px;"></span>'
            '<input type="date" class="due-date-picker"'
            ' style="position:absolute;inset:0;opacity:0;width:100%;height:100%;'
            'cursor:pointer;font-size:16px;-webkit-appearance:none;appearance:none;"'
            ' onclick="event.stopPropagation()"'
            " onchange=\"this.parentNode.querySelector('.due-date-text').textContent=this.value||'';\">"
            "</label>"
        )
        action_parts.append(date_input)
        if view_type == "starred":
            # Starred view: Inbox, Best Case, Commit buttons
            safe_subject = subject.replace("'", "\\'").replace('"', "&quot;")
            safe_from = from_addr.replace("'", "\\'").replace('"', "&quot;")
            safe_gmail = gmail_link.replace("'", "\\'").replace('"', "&quot;")
            safe_date = date_received.replace("'", "\\'").replace('"', "&quot;")
            for mode, label, color_var, bg_var, border_var in [
                ("inbox", "Inbox", "--accent-l", "--accent-bg", "--accent-b"),
                ("bestcase", "Best Case", "--purple", "--purple-bg", "--purple-b"),
                ("commit", "Commit", "--warn", "--warn-bg", "--warn-b"),
            ]:
                btn = (
                    '<button class="action-pill" '
                    'style="color:var('
                    + color_var
                    + ");background:var("
                    + bg_var
                    + ");"
                    "border:1px solid var(" + border_var + ');" '
                    "onclick=\"event.stopPropagation();doStarredAction(this,'"
                    + mode
                    + "','"
                    + msg_id
                    + "',"
                    "'"
                    + safe_subject
                    + "','"
                    + safe_from
                    + "','"
                    + safe_gmail
                    + "','"
                    + safe_date
                    + "')\">"
                    + label
                    + "</button>"
                )
                action_parts.append(btn)
        else:
            # Unread view: Priority dropdown + Best Case + Move to Todoist
            # Priority dropdown (stored locally on card)
            priority_select = (
                '<select class="action-pill priority-picker"'
                ' style="color:var(--warn);background:var(--warn-bg);font-size:12px;'
                'padding:4px 8px;border:1px solid var(--warn-b);border-radius:6px;cursor:pointer;"'
                ' onclick="event.stopPropagation()">'
                '<option value="" disabled selected>Priority</option>'
                '<option value="4">P1</option>'
                '<option value="3">P2</option>'
                '<option value="2">P3</option>'
                '<option value="1">P4</option>'
                "</select>"
            )
            action_parts.append(priority_select)
            safe_subject = subject.replace("'", "\\'").replace('"', "&quot;")
            safe_from = from_addr.replace("'", "\\'").replace('"', "&quot;")
            safe_gmail = gmail_link.replace("'", "\\'").replace('"', "&quot;")
            safe_date = date_received.replace("'", "\\'").replace('"', "&quot;")
            # Best Case button
            bestcase_btn = (
                '<button class="action-pill" '
                'style="color:var(--purple);background:var(--purple-bg);border:1px solid var(--purple-b);" '
                "onclick=\"event.stopPropagation();doStarredAction(this,'bestcase','"
                + msg_id
                + "','"
                + safe_subject
                + "','"
                + safe_from
                + "','"
                + safe_gmail
                + "','"
                + safe_date
                + "')\">"
                "Best Case</button>"
            )
            action_parts.append(bestcase_btn)
            if projects:
                move_select = (
                    '<select class="action-pill" style="color:var(--accent-l);background:var(--accent-bg);border:1px solid var(--accent-b);"'
                    ' onclick="event.stopPropagation()"'
                    ' data-subject="' + safe_subject + '"'
                    ' data-from="' + safe_from + '"'
                    ' data-gmail-link="' + safe_gmail + '"'
                    ' data-date="' + safe_date + '"'
                    ' onchange="event.stopPropagation();doMoveTodoist(this)">'
                    + project_options_html
                    + "</select>"
                )
                action_parts.append(move_select)
        if toggl_projects:
            safe_subj_t = subject.replace("'", "\\'").replace('"', "&quot;")
            toggl_select = (
                '<select class="action-pill toggl-timer-select"'
                ' style="color:var(--ok);background:var(--ok-bg);border:1px solid var(--ok-b);"'
                ' onclick="event.stopPropagation()"'
                ' data-subject="' + safe_subj_t + '"'
                ' onchange="event.stopPropagation();doTogglStart(this)">'
                + toggl_project_options_html
                + "</select>"
            )
            action_parts.append(toggl_select)
        action_html = (
            (
                '<div class="card-actions-inline" style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">'
                + "".join(action_parts)
                + "</div>"
            )
            if action_parts
            else ""
        )

        data_attr = ' data-msg-id="' + msg_id + '"' if msg_id else ""
        data_open_attr = ' data-open-url="' + open_url + '"' if open_url else ""
        data_subject = ' data-subject="' + subject.replace('"', "&quot;") + '"'
        data_from = ' data-from="' + from_addr.replace('"', "&quot;") + '"'
        data_gmail = ' data-gmail-link="' + gmail_link.replace('"', "&quot;") + '"'
        data_date_attr = ' data-date="' + date_received.replace('"', "&quot;") + '"'

        # Checkbox for multi-select
        checkbox = (
            '<input type="checkbox" class="select-cb" '
            'onclick="event.stopPropagation();updateSelection()" '
            'style="display:none;width:18px;height:18px;margin-right:10px;cursor:pointer;flex-shrink:0;">'
        )

        # Build menu button HTML (mobile only - hidden on desktop via CSS)
        menu_btn_html = (
            (
                '<button class="card-action-menu-btn" '
                'onclick="event.stopPropagation();openActionSheet(this)" '
                'style="display:none;flex-shrink:0;align-self:flex-start;margin-left:8px;'
                "background:none;border:1px solid var(--border-h);border-radius:6px;"
                "color:var(--text-2);font-size:18px;line-height:1;cursor:pointer;"
                'width:36px;height:36px;align-items:center;justify-content:center;">'
                "&#8942;</button>"
            )
            if action_parts
            else ""
        )

        cards += (
            '<div class="email-card"'
            + data_attr
            + data_open_attr
            + data_subject
            + data_from
            + data_gmail
            + data_date_attr
            + ' onclick="openEmail(this)"'
            + ' style="background:var(--bg-s1);border-radius:8px;border:1px solid var(--border);padding:14px 16px;margin-bottom:10px;'
            "transition:opacity .3s,max-height .3s,padding .3s;cursor:pointer;"
            'display:flex;align-items:flex-start;">'
            + checkbox
            + '<div style="flex:1;min-width:0;">'
            '<div style="font-size:15px;font-weight:600;color:var(--text-1);line-height:1.4;">'
            + subject
            + "</div>"
            '<div style="margin-top:6px;font-size:12px;color:var(--text-2);line-height:1.4;">'
            + info_html
            + "</div>"
            + action_html
            + "</div>"
            + menu_btn_html
            + "</div>"
        )

    if count == 0:
        content_section = (
            '<div id="all-clear" style="text-align:center;padding:40px 0;color:var(--text-2);font-size:15px;">'
            "No unread emails. Inbox zero!</div>"
        )
    else:
        content_section = '<div id="card-list">' + cards + "</div>"

    return content_section, count, project_options_html


def build_web_html(
    emails: List[Dict[str, Any]],
    function_url: str = "",
    action_token: str = "",
    embed: bool = False,
    projects: List[Dict[str, Any]] = None,
    toggl_projects: List[Dict[str, Any]] = None,
    view_type: str = "unread",
) -> str:
    """Build an interactive web page listing unread emails with one-click mark read.

    Args:
        emails: List of email dicts with keys: id, subject, from, date, gmail_link
        embed: If True, hide header bar and post count to parent via postMessage
        projects: Optional list of Todoist project dicts for "Move to Todoist" dropdown.
        toggl_projects: Optional list of Toggl project dicts for "Start Toggl Timer" dropdown.
    """
    projects = projects or []
    toggl_projects = toggl_projects or []

    content_section, count, project_options_html = build_cards_html(
        emails,
        function_url,
        action_token,
        projects,
        toggl_projects,
        view_type=view_type,
    )
    today = datetime.now().strftime("%B %d, %Y")
    plural = "s" if count != 1 else ""

    _FONT = "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif"

    # JavaScript
    js = (
        "<script>"
        "(function(){"
        "var pane=null,ind=null,startY=0,pullY=0,pulling=false,threshold=60;"
        "function init(){pane=document.querySelector('.left-pane');ind=document.getElementById('ptr-indicator');"
        "if(!pane||!ind||window.innerWidth>768)return;"
        "pane.addEventListener('touchstart',onStart,{passive:true});"
        "pane.addEventListener('touchmove',onMove,{passive:false});"
        "pane.addEventListener('touchend',onEnd,{passive:true});}"
        "function onStart(e){if(pane.scrollTop===0){startY=e.touches[0].clientY;pulling=true;}}"
        "function onMove(e){if(!pulling)return;pullY=e.touches[0].clientY-startY;"
        "if(pullY<0){pullY=0;return;}"
        "if(pane.scrollTop>0){pulling=false;pullY=0;ind.className='';ind.style.height='0';return;}"
        "e.preventDefault();"
        "var h=Math.min(pullY*0.5,80);"
        "ind.className='pulling';ind.style.height=h+'px';"
        "ind.style.opacity=Math.min(h/40,1);}"
        "function onEnd(){if(!pulling){return;}"
        "if(pullY*0.5>=threshold){ind.className='refreshing';ind.style.height='50px';ind.style.opacity='1';"
        "doRefresh(function(){ind.className='';ind.style.height='0';ind.style.opacity='0';});}"
        "else{ind.className='';ind.style.height='0';ind.style.opacity='0';}"
        "pulling=false;pullY=0;}"
        "if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',init);}else{init();}"
        "})();"
        "var BASE_URL='" + (function_url.rstrip("/") if function_url else "") + "';"
        "var TOKEN='" + (action_token or "") + "';"
        "var VIEW_TYPE='" + view_type + "';"
        "function doRefresh(cb){"
        "var url=BASE_URL+'?action=refresh_cards&view='+VIEW_TYPE+'&token='+TOKEN;"
        "fetch(url).then(function(r){return r.json();}).then(function(data){"
        "var old=document.getElementById('card-list')||document.getElementById('all-clear');"
        "if(old){var tmp=document.createElement('div');tmp.innerHTML=data.html;"
        "old.parentNode.replaceChild(tmp.firstChild,old);}"
        "var el=document.getElementById('item-count');"
        "if(el){el.textContent=data.count+' item'+(data.count!==1?'s':'');}"
        "if(window.parent!==window){"
        "try{window.parent.postMessage({type:'count',source:'unread',count:data.count},'*');}catch(e){}}"
        "if(cb)cb();"
        "}).catch(function(){location.reload();});}"
        'var _IC_BLOCK=\'<svg style="display:inline-block;vertical-align:middle" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="8" cy="8" r="6"/><line x1="3.8" y1="3.8" x2="12.2" y2="12.2"/></svg>\';'
        'var _IC_CAL=\'<svg style="display:inline-block;vertical-align:middle" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><rect x="2" y="3.5" width="12" height="10.5" rx="1.5"/><path d="M2 7h12"/><path d="M5.5 1.5v3"/><path d="M10.5 1.5v3"/></svg>\';'
        'var _IC_TASK=\'<svg style="display:inline-block;vertical-align:middle" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="12" height="12" rx="2"/><path d="M5 8l2 2 4-4"/></svg>\';'
        'var _IC_REC=\'<svg style="display:inline-block;vertical-align:middle" width="10" height="10" viewBox="0 0 10 10"><circle cx="5" cy="5" r="4" fill="currentColor"/></svg>\';'
        'var _IC_PLAY=\'<svg style="display:inline-block;vertical-align:middle" width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><polygon points="2,1 9,5 2,9"/></svg>\';'
        "var _cs=getComputedStyle(document.documentElement);function cv(n){return _cs.getPropertyValue(n).trim();}"
        "var _activeCard=null;"
        "function openEmail(card){"
        "if(document.activeElement&&document.activeElement.classList.contains('select-cb'))return;"
        "var url=card.getAttribute('data-open-url');"
        "if(!url)return;"
        "_activeCard=card;"
        "var all=document.querySelectorAll('.email-card');"
        "for(var i=0;i<all.length;i++){all[i].style.background='var(--bg-s1)';all[i].classList.remove('active-email');}"
        "card.style.background=cv('--accent-hbg');card.classList.add('active-email');"
        "var pane=document.getElementById('viewer-pane');"
        "var frame=document.getElementById('viewer-frame');"
        "frame.src=url+'&embed=1';"
        "document.getElementById('viewer-placeholder').style.display='none';"
        "frame.style.display='block';"
        # Set up viewer header buttons from card data
        # Hide header buttons if the card already has inline action buttons below the title
        "var vmr=document.getElementById('viewer-markread-btn');"
        "var vsk=document.getElementById('viewer-skip-btn');"
        "var hasInline=!!card.querySelector('.card-actions-inline');"
        "var msgId=card.getAttribute('data-msg-id')||'';"
        "var markBtn=card.querySelector('button[onclick*=\"doMarkRead\"]');"
        "if(!hasInline&&markBtn&&msgId){vmr.style.display='';vmr.disabled=false;vmr.textContent='Mark Read';}else{vmr.style.display='none';}"
        "var skipBtn=card.querySelector('button[onclick*=\"doSkipInbox\"]');"
        "if(!hasInline&&skipBtn){vsk.style.display='';vsk.disabled=false;vsk.textContent='Skip Inbox';}else{vsk.style.display='none';}"
        # Wire up viewer CC buttons with card data
        "var vccs=document.querySelectorAll('.viewer-cc-btn');"
        "var vccSubj=card.getAttribute('data-subject')||'';"
        "var vccFrom=card.getAttribute('data-from')||'';"
        "var vccGmail=card.getAttribute('data-gmail-link')||'';"
        "for(var j=0;j<vccs.length;j++){vccs[j].setAttribute('data-subject',vccSubj);vccs[j].setAttribute('data-from',vccFrom);vccs[j].setAttribute('data-gmail',vccGmail);vccs[j].style.display='';}"
        "if(window.innerWidth<=768){"
        "pane.style.display='flex';"
        "document.body.classList.add('viewer-open');"
        "try{window.parent.postMessage({type:'viewer-open'},'*');}catch(e){}"
        "}"
        "}"
        "function viewerMarkRead(){"
        "if(!_activeCard)return;"
        "var msgId=_activeCard.getAttribute('data-msg-id')||'';"
        "var markBtn=_activeCard.querySelector('button[onclick*=\"doMarkRead\"]');"
        "if(markBtn&&msgId){doMarkRead(markBtn,msgId);}"
        "var btn=document.getElementById('viewer-markread-btn');"
        "btn.disabled=true;btn.textContent='\\u2713 Done';"
        "}"
        "function viewerSkipInbox(){"
        "if(!_activeCard)return;"
        "var skipBtn=_activeCard.querySelector('button[onclick*=\"doSkipInbox\"]');"
        "if(!skipBtn)return;"
        "var onclick=skipBtn.getAttribute('onclick')||'';"
        "var m=onclick.match(/doSkipInbox\\(this,'([^']+)','([^']+)'\\)/);"
        "if(m){doSkipInbox(skipBtn,m[1],m[2]);}"
        "var btn=document.getElementById('viewer-skip-btn');"
        "btn.disabled=true;btn.textContent='\\u2713 Done';"
        "}"
        "function closeViewer(){"
        "var frame=document.getElementById('viewer-frame');"
        "frame.src='about:blank';"
        "frame.style.display='none';"
        "document.getElementById('viewer-placeholder').style.display='flex';"
        "var all=document.querySelectorAll('.email-card');"
        "for(var i=0;i<all.length;i++){all[i].style.background='var(--bg-s1)';all[i].classList.remove('active-email');}"
        "if(window.innerWidth<=768){"
        "document.getElementById('viewer-pane').style.display='none';"
        "document.body.classList.remove('viewer-open');"
        "try{window.parent.postMessage({type:'viewer-close'},'*');}catch(e){}"
        "}"
        "}"
        "function removeCard(msgId){"
        "var card=document.querySelector('.email-card[data-msg-id=\"'+msgId+'\"]');"
        "if(!card)return;"
        "card.style.opacity='0';"
        "setTimeout(function(){"
        "card.style.maxHeight='0';card.style.padding='0';card.style.overflow='hidden';"
        "setTimeout(function(){card.remove();updateCount();updateSelection();},300);"
        "},300);"
        "}"
        "function doCopyEmailForClaude(btn,subject,fromAddr,gmailLink){"
        "var orig=btn.innerHTML;"
        "var msg='Please handle this email in my inbox:\\n\\nSubject: '+subject+'\\nFrom: '+fromAddr+(gmailLink?'\\nGmail: '+gmailLink:'');"
        "navigator.clipboard.writeText(msg).then(function(){"
        "btn.textContent='\\u2713';setTimeout(function(){btn.innerHTML=orig;},1500);"
        "}).catch(function(){btn.textContent='!';setTimeout(function(){btn.innerHTML=orig;},1500);});}"
        "function viewerCopyCC(btn){"
        "var subject=btn.getAttribute('data-subject')||'';"
        "var fromAddr=btn.getAttribute('data-from')||'';"
        "var gmailLink=btn.getAttribute('data-gmail')||'';"
        "doCopyEmailForClaude(btn,subject,fromAddr,gmailLink);}"
        "function doMarkRead(btn,msgId){"
        "btn.disabled=true;"
        "btn.style.background=cv('--border');"
        "btn.style.color=cv('--text-3');"
        "btn.innerHTML='Marking read\\u2026';"
        "var card=btn.closest('.email-card');"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=markread&msg_id='+msgId"
        "+'&token=" + (action_token or "") + "';"
        "fetch(url).then(function(r){"
        "if(r.ok){"
        "var isActive=card&&card.classList.contains('active-email');"
        "if(isActive){closeViewer();}"
        "removeCard(msgId);"
        "}else{"
        "btn.disabled=false;"
        "btn.style.background=cv('--ok-bg');"
        "btn.style.color=cv('--ok');"
        "btn.innerHTML='Failed \\u2013 Retry';"
        "}"
        "}).catch(function(){"
        "btn.disabled=false;"
        "btn.style.background=cv('--ok-bg');"
        "btn.style.color=cv('--ok');"
        "btn.innerHTML='Failed \\u2013 Retry';"
        "});"
        "}"
        # doSkipInbox: create Gmail filter to skip inbox, then mark email as read
        "function doSkipInbox(btn,filterUrl,msgId){"
        "btn.disabled=true;"
        "btn.style.background=cv('--border');"
        "btn.style.color=cv('--text-3');"
        "btn.innerHTML='Creating\u2026';"
        "fetch(filterUrl).then(function(r){return r.json();}).then(function(d){"
        "if(d.ok){"
        "btn.style.background=cv('--ok-bg');"
        "btn.style.color=cv('--ok');"
        "btn.innerHTML='\u2713 Filter set';"
        "if(msgId){"
        "var markUrl='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=markread&msg_id='+msgId"
        "+'&token=" + (action_token or "") + "';"
        "fetch(markUrl).then(function(){"
        "var card=btn.closest('.email-card');"
        "var isActive=card&&card.classList.contains('active-email');"
        "if(isActive){closeViewer();}"
        "removeCard(msgId);"
        "});}"
        "}else{"
        "btn.disabled=false;"
        "btn.style.background=cv('--warn-bg');"
        "btn.style.color=cv('--warn');"
        "btn.innerHTML='Failed \u2013 Retry';"
        "}"
        "}).catch(function(){"
        "btn.disabled=false;"
        "btn.style.background=cv('--warn-bg');"
        "btn.style.color=cv('--warn');"
        "btn.innerHTML='Failed \u2013 Retry';"
        "});"
        "}"
        # doMoveTodoist: create new Todoist task + mark read (uses POST)
        "function doMoveTodoist(sel){"
        "var projectId=sel.value;"
        "if(!projectId)return;"
        "sel.disabled=true;"
        "var card=sel.closest('.email-card');"
        "var msgId=card?card.getAttribute('data-msg-id'):'';"
        "var dueDateInput=card?card.querySelector('.due-date-picker'):null;"
        "var prioritySelect=card?card.querySelector('.priority-picker'):null;"
        "var payload={"
        "msg_id:msgId,"
        "subject:card?card.getAttribute('data-subject'):'',"
        "from_addr:card?card.getAttribute('data-from'):'',"
        "gmail_link:card?card.getAttribute('data-gmail-link'):'',"
        "date:card?card.getAttribute('data-date'):'',"
        "project_id:projectId,"
        "due_date:dueDateInput?dueDateInput.value:'',"
        "priority:prioritySelect?prioritySelect.value:''"
        "};"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=create_todoist&token=" + (action_token or "") + "';"
        "fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})"
        ".then(function(r){"
        "if(r.ok){"
        "var isActive=card&&card.classList.contains('active-email');"
        "if(isActive){closeViewer();}"
        "removeCard(msgId);"
        "}else{sel.disabled=false;sel.selectedIndex=0;alert('Move failed');}"
        "}).catch(function(){sel.disabled=false;sel.selectedIndex=0;alert('Move failed');});"
        "}"
        # doTogglStart: start a Toggl timer with the email subject as description
        "function doTogglStart(sel){"
        "var opt=sel.options[sel.selectedIndex];"
        "var projectId=sel.value;"
        "if(!projectId)return;"
        "var workspaceId=opt?opt.getAttribute('data-workspace-id'):'';"
        "var subject=sel.getAttribute('data-subject')||'';"
        "sel.disabled=true;"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=toggl_start&token=" + (action_token or "") + "';"
        "fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({subject:subject,project_id:projectId,workspace_id:workspaceId})})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "var ind=document.createElement('span');"
        "ind.className='action-pill';"
        "ind.style.cssText='color:var(--ok);background:var(--ok-bg);border:1px solid var(--ok-b);'"
        "+'display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:600;'"
        "+'padding:5px 14px;border-radius:6px;';"
        "ind.innerHTML=_IC_REC+' Running';"
        "sel.parentNode.replaceChild(ind,sel);"
        "}else{"
        "sel.disabled=false;sel.selectedIndex=0;"
        "}"
        "}).catch(function(){sel.disabled=false;sel.selectedIndex=0;});"
        "}"
        "function doStarredAction(btn,mode,msgId,subject,fromAddr,gmailLink,dateRecv){"
        "btn.disabled=true;btn.style.opacity='.5';var origText=btn.textContent;btn.textContent='Adding\u2026';"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=starred_to_todoist&token=" + (action_token or "") + "';"
        "fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({mode:mode,msg_id:msgId,subject:subject,from_addr:fromAddr,gmail_link:gmailLink,date:dateRecv})})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "var card=btn.closest('.email-card');"
        "var isActive=card&&card.classList.contains('active-email');"
        "if(isActive){closeViewer();}"
        "removeCard(msgId);"
        "}else{"
        "btn.disabled=false;btn.style.opacity='1';btn.textContent=origText;"
        "}"
        "}).catch(function(){"
        "btn.disabled=false;btn.style.opacity='1';btn.textContent=origText;"
        "});"
        "}"
        # postMessage listener
        "window.addEventListener('message',function(e){"
        "if(e.data&&e.data.type==='markread'&&e.data.msgId){"
        "closeViewer();"
        "removeCard(e.data.msgId);"
        "}"
        "});"
        "function updateCount(){"
        "var remaining=document.querySelectorAll('.email-card').length;"
        "var el=document.getElementById('item-count');"
        "if(el){el.textContent=remaining;}"
        "try{window.parent.postMessage({type:'count',source:VIEW_TYPE,count:remaining},'*');}catch(e){}"
        "if(remaining===0){"
        "var list=document.getElementById('card-list');"
        "if(list){list.innerHTML="
        "'<div style=\"text-align:center;padding:40px 0;color:'+cv('--ok')+';font-size:16px;font-weight:600;\">"
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
        "function bulkMarkRead(){"
        "var cards=getSelectedCards();"
        "cards.forEach(function(card){"
        "var msgId=card.getAttribute('data-msg-id');"
        "if(!msgId)return;"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=markread&msg_id='+msgId"
        "+'&token=" + (action_token or "") + "';"
        "fetch(url).then(function(r){if(r.ok){removeCard(msgId);}});"
        "});"
        "}"
        # Bulk set due date: update per-card date pickers
        "function bulkSetDueDate(dateValue){"
        "if(!dateValue)return;"
        "var cards=getSelectedCards();"
        "cards.forEach(function(card){"
        "var inp=card.querySelector('.due-date-picker');"
        "if(inp){inp.value=dateValue;inp.style.background=cv('--ok-bg');inp.style.color=cv('--ok');"
        "setTimeout(function(){inp.style.background=cv('--accent-bg');inp.style.color=cv('--accent-l');},1500);}"
        "});"
        "}"
        # Bulk set priority: update per-card priority selects
        "function bulkSetPriority(priority){"
        "if(!priority)return;"
        "var cards=getSelectedCards();"
        "cards.forEach(function(card){"
        "var sel=card.querySelector('.priority-picker');"
        "if(sel){sel.value=priority;sel.style.background=cv('--ok-bg');sel.style.color=cv('--ok');"
        "setTimeout(function(){sel.style.background=cv('--warn-bg');sel.style.color=cv('--warn');},1500);}"
        "});"
        "}"
        "function bulkMoveTodoist(projectId){"
        "if(!projectId)return;"
        "var cards=getSelectedCards();"
        "cards.forEach(function(card){"
        "var msgId=card.getAttribute('data-msg-id');"
        "var dueDateInput=card.querySelector('.due-date-picker');"
        "var prioritySelect=card.querySelector('.priority-picker');"
        "var payload={"
        "msg_id:msgId,"
        "subject:card.getAttribute('data-subject')||'',"
        "from_addr:card.getAttribute('data-from')||'',"
        "gmail_link:card.getAttribute('data-gmail-link')||'',"
        "date:card.getAttribute('data-date')||'',"
        "project_id:projectId,"
        "due_date:dueDateInput?dueDateInput.value:'',"
        "priority:prioritySelect?prioritySelect.value:''"
        "};"
        "var url='" + (function_url.rstrip("/") if function_url else "") + "'"
        "+'?action=create_todoist&token=" + (action_token or "") + "';"
        "fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})"
        ".then(function(r){if(r.ok){removeCard(msgId);}});"
        "});"
        "}"
        # Mobile action sheet open/close
        "var _sheetCard=null;"
        "function openActionSheet(btn){"
        "var card=btn.closest('.email-card');"
        "_sheetCard=card;"
        "var body=document.getElementById('action-sheet-body');"
        "body.innerHTML='';"
        # Mark Read row
        "var markBtn=card.querySelector('button[onclick*=\"doMarkRead\"]');"
        "if(markBtn){"
        "var msgId=card.getAttribute('data-msg-id')||'';"
        "var row=document.createElement('button');"
        "row.className='sheet-action';"
        "row.innerHTML='<span class=\"sheet-action-icon\">\u2713</span>Mark Read';"
        "row.setAttribute('touch-action','manipulation');"
        "row.onclick=function(){"
        "closeActionSheet();"
        "doMarkRead(markBtn,msgId);"
        "};"
        "body.appendChild(row);"
        "}"
        # Skip Inbox row
        "var skipBtn=card.querySelector('button[onclick*=\"doSkipInbox\"]');"
        "if(skipBtn){"
        "var skipOnclick=skipBtn.getAttribute('onclick')||'';"
        "var skipMatch=skipOnclick.match(/doSkipInbox\\(this,'([^']+)','([^']+)'\\)/);"
        "if(skipMatch){"
        "var skipUrl=skipMatch[1];var skipMsgId=skipMatch[2];"
        "var skipRow=document.createElement('button');"
        "skipRow.className='sheet-action';"
        "skipRow.innerHTML='<span class=\"sheet-action-icon\">'+_IC_BLOCK+'</span>Skip Inbox';"
        "skipRow.style.color='var(--warn)';"
        "skipRow.setAttribute('touch-action','manipulation');"
        "skipRow.onclick=function(){"
        "closeActionSheet();"
        "doSkipInbox(skipBtn,skipUrl,skipMsgId);"
        "};"
        "body.appendChild(skipRow);"
        "}}"
        # Date picker row
        "var dateInput=card.querySelector('.due-date-picker');"
        "if(dateInput){"
        "var dateRow=document.createElement('div');"
        "dateRow.className='sheet-input-row';"
        "var dateLabel=document.createElement('label');"
        "dateLabel.className='sheet-input-label';"
        "dateLabel.innerHTML='<span class=\"sheet-input-label-icon\">'+_IC_CAL+'</span>Due Date';"
        "var sheetDateInput=document.createElement('input');"
        "sheetDateInput.type='date';"
        "sheetDateInput.className='sheet-input-ctrl';"
        "sheetDateInput.value=dateInput.value||'';"
        "sheetDateInput.onchange=function(){dateInput.value=this.value;};"
        "dateRow.appendChild(dateLabel);"
        "dateRow.appendChild(sheetDateInput);"
        "body.appendChild(dateRow);"
        "}"
        # Priority row
        "var prioSelect=card.querySelector('.priority-picker');"
        "if(prioSelect){"
        "var prioRow=document.createElement('div');"
        "prioRow.className='sheet-input-row';"
        "var prioLabel=document.createElement('label');"
        "prioLabel.className='sheet-input-label';"
        "prioLabel.innerHTML='<span class=\"sheet-input-label-icon\">\u2691</span>Priority';"
        "var sheetPrioSel=document.createElement('select');"
        "sheetPrioSel.className='sheet-input-ctrl';"
        "sheetPrioSel.innerHTML=prioSelect.innerHTML;"
        "sheetPrioSel.value=prioSelect.value;"
        "sheetPrioSel.onchange=function(){prioSelect.value=this.value;};"
        "prioRow.appendChild(prioLabel);"
        "prioRow.appendChild(sheetPrioSel);"
        "body.appendChild(prioRow);"
        "}"
        # Move to Todoist row
        "var moveSelect=card.querySelector('.action-pill[onchange*=\"doMoveTodoist\"]');"
        "if(moveSelect){"
        "var moveRow=document.createElement('div');"
        "moveRow.className='sheet-input-row';"
        "var moveLabel=document.createElement('label');"
        "moveLabel.className='sheet-input-label';"
        "moveLabel.innerHTML='<span class=\"sheet-input-label-icon\">'+_IC_TASK+'</span>Move to Todoist';"
        "var sheetMoveSel=document.createElement('select');"
        "sheetMoveSel.className='sheet-input-ctrl';"
        "sheetMoveSel.innerHTML=moveSelect.innerHTML;"
        "sheetMoveSel.value=moveSelect.value;"
        "sheetMoveSel.onchange=function(){"
        "moveSelect.value=this.value;"
        "closeActionSheet();"
        "doMoveTodoist(moveSelect);"
        "};"
        "moveRow.appendChild(moveLabel);"
        "moveRow.appendChild(sheetMoveSel);"
        "body.appendChild(moveRow);"
        "}"
        # Toggl timer row
        "var togglSelect=card.querySelector('.toggl-timer-select');"
        "if(togglSelect){"
        "var togglRow=document.createElement('div');"
        "togglRow.className='sheet-input-row';"
        "var togglLabel=document.createElement('label');"
        "togglLabel.className='sheet-input-label';"
        "togglLabel.innerHTML='<span class=\"sheet-input-label-icon\">'+_IC_PLAY+'</span>Start Toggl Timer';"
        "var sheetTogglSel=document.createElement('select');"
        "sheetTogglSel.className='sheet-input-ctrl';"
        "sheetTogglSel.innerHTML=togglSelect.innerHTML;"
        "sheetTogglSel.value=togglSelect.value;"
        "sheetTogglSel.onchange=function(){"
        "togglSelect.value=this.value;"
        "closeActionSheet();"
        "doTogglStart(togglSelect);"
        "};"
        "togglRow.appendChild(togglLabel);"
        "togglRow.appendChild(sheetTogglSel);"
        "body.appendChild(togglRow);"
        "}"
        # Cancel row
        "var cancelRow=document.createElement('button');"
        "cancelRow.className='sheet-action sheet-action-cancel';"
        "cancelRow.innerHTML='<span class=\"sheet-action-icon\">\u2715</span>Cancel';"
        "cancelRow.setAttribute('touch-action','manipulation');"
        "cancelRow.onclick=closeActionSheet;"
        "body.appendChild(cancelRow);"
        "var overlay=document.getElementById('action-sheet-overlay');"
        "overlay.style.display='flex';"
        "}"
        "function closeActionSheet(){"
        "var overlay=document.getElementById('action-sheet-overlay');"
        "if(overlay)overlay.style.display='none';"
        "var body=document.getElementById('action-sheet-body');"
        "if(body)body.innerHTML='';"
        "_sheetCard=null;"
        "}"
        "</script>"
    )

    # Embed mode
    embed_css = ""
    embed_onload = ""
    split_height = "calc(100vh - 56px)"
    viewer_top = "56px"
    if embed:
        embed_css = ".top-bar-unread{display:none;}"
        split_height = "100vh"
        viewer_top = "0"
        embed_onload = (
            "<script>"
            "window.addEventListener('load',function(){"
            "var c=document.querySelectorAll('.email-card').length;"
            "var _viewType='" + view_type + "';"
            "try{window.parent.postMessage({type:'count',source:_viewType,count:c},'*');}catch(e){}"
            "});"
            "</script>"
        )

    # Bulk toolbar HTML
    bulk_toolbar = (
        '<div id="bulk-toolbar" style="position:fixed;bottom:20px;left:50%;transform:translateX(-50%);'
        "background:#16161af2;border:1px solid var(--border);color:var(--text-1);padding:10px 18px;border-radius:12px;"
        "box-shadow:0 4px 16px rgba(0,0,0,.25);display:none;align-items:center;gap:10px;"
        'z-index:500;font-size:13px;font-weight:500;">'
        '<span id="bulk-count">0 selected</span>'
        # Bulk date picker (sets value on per-card pickers for when Move to Todoist is used)
        '<input type="date" style="font-size:12px;padding:5px 8px;border-radius:6px;'
        'border:1px solid var(--border-h);background:var(--bg-s2);color:var(--text-1);" '
        'onchange="bulkSetDueDate(this.value)">'
        # Bulk priority (sets value on per-card pickers)
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
        '<button onclick="bulkMarkRead()" style="font-size:12px;font-weight:600;padding:6px 14px;'
        'border:1px solid var(--ok-b);border-radius:6px;cursor:pointer;background:var(--ok-bg);color:var(--ok);">Mark Read</button>'
        "</div>"
    )

    # CSS
    css = (
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
        "*{box-sizing:border-box;}"
        + embed_css
        + ".section-hdr{display:flex;align-items:center;gap:8px;padding:16px 0 8px;"
        "font-size:11px;font-weight:600;text-transform:uppercase;"
        "letter-spacing:0.6px;border-bottom:1px solid var(--border);margin-bottom:10px;"
        "position:sticky;top:0;z-index:10;background:var(--bg-base);}"
        ".section-badge{background:var(--border);color:var(--text-2);font-size:11px;"
        "font-weight:700;padding:2px 7px;border-radius:8px;}"
        ".split-wrap{display:flex;height:" + split_height + ";overflow:hidden;}"
        ".left-pane{flex:0 0 45%;min-width:0;overflow-y:auto;}"
        "#viewer-pane{display:flex;flex-direction:column;flex:1 1 55%;"
        "border-left:1px solid var(--border);background:var(--bg-base);position:relative;overflow:hidden;}"
        "#viewer-frame{width:100%;height:100%;border:none;display:none;}"
        ".close-btn{position:absolute;top:10px;right:14px;z-index:11;"
        "background:var(--border);border:none;cursor:pointer;font-size:20px;"
        "color:var(--text-2);width:36px;height:36px;border-radius:50%;display:flex;"
        "align-items:center;justify-content:center;}"
        ".close-btn:hover{background:var(--border-h);}"
        ".action-pill{border:none;cursor:pointer;font-weight:600;font-size:12px;"
        "padding:5px 14px;border-radius:6px;font-family:inherit;}"
        ".select-all-row{display:none;}"
        ".select-all-row label{display:none;}"
        ".select-cb{display:none;}"
        ".viewer-mobile-header{display:none;}"
        "@media(max-width:768px){"
        ".left-pane{flex:1 1 100%!important;}"
        "#viewer-pane{display:none;position:fixed;top:0;right:0;bottom:0;width:100%;z-index:10;"
        "border-left:none;flex-direction:column;}"
        ".close-btn{display:none!important;}"
        ".viewer-mobile-header{display:flex;align-items:center;background:transparent;"
        "padding:0 12px;height:52px;flex-shrink:0;z-index:12;}"
        ".viewer-back-btn{display:flex;align-items:center;gap:6px;background:none;border:none;"
        "color:var(--accent-l);font-family:inherit;font-size:15px;font-weight:600;"
        "cursor:pointer;padding:8px 4px;touch-action:manipulation;}"
        ".viewer-header-actions{display:flex;gap:8px;margin-left:auto;}"
        ".viewer-action-btn{font-family:inherit;font-size:12px;font-weight:600;"
        "padding:6px 12px;border-radius:6px;border:none;cursor:pointer;touch-action:manipulation;}"
        ".viewer-markread{background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-b);}"
        ".viewer-skip{background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn-b);}"
        "#bulk-toolbar{left:10px!important;right:10px;transform:none!important;"
        "flex-wrap:wrap;justify-content:center;}"
        ".card-actions-inline{display:flex!important;gap:6px!important;margin-top:10px!important;max-width:100%;}"
        ".card-actions-inline .action-pill{font-size:13px!important;padding:8px 12px!important;min-height:36px!important;touch-action:manipulation;min-width:0;max-width:100%;}"
        ".card-actions-inline select.action-pill{overflow:hidden;text-overflow:ellipsis;}"
        ".card-action-menu-btn{display:none!important;}"
        ".top-bar-unread button{display:none!important;}"
        "}"
        "#ptr-indicator{display:none;align-items:center;justify-content:center;padding:0;height:0;"
        "overflow:hidden;transition:height .2s ease,opacity .2s ease;opacity:0;}"
        "#ptr-indicator.pulling{display:flex;opacity:1;}"
        "#ptr-indicator.refreshing{display:flex;opacity:1;}"
        "#ptr-spinner{width:24px;height:24px;border:3px solid var(--border);border-top-color:var(--accent-l);"
        "border-radius:50%;animation:ptr-spin .6s linear infinite;}"
        "@keyframes ptr-spin{to{transform:rotate(360deg)}}"
        "#action-sheet-overlay{display:none;position:fixed;inset:0;z-index:600;"
        "background:rgba(0,0,0,0.5);align-items:flex-end;justify-content:center;"
        "animation:fadeOverlay .15s ease;}"
        "@keyframes fadeOverlay{from{opacity:0}to{opacity:1}}"
        "#action-sheet{width:100%;max-width:600px;background:var(--bg-s1);"
        "border-radius:16px 16px 0 0;border:1px solid var(--border-h);"
        "padding:0 0 env(safe-area-inset-bottom,12px);overflow:hidden;"
        "animation:slideSheet .2s ease;}"
        "@keyframes slideSheet{from{transform:translateY(100%)}to{transform:translateY(0)}}"
        ".sheet-handle{width:40px;height:4px;border-radius:2px;background:var(--border-h);"
        "margin:12px auto 8px;}"
        ".sheet-title{text-align:center;font-size:13px;font-weight:600;color:var(--text-2);"
        "padding:4px 16px 12px;border-bottom:1px solid var(--border);letter-spacing:.5px;text-transform:uppercase;}"
        ".sheet-action{display:flex;align-items:center;width:100%;min-height:52px;"
        "padding:12px 20px;border:none;border-bottom:1px solid var(--border);"
        "background:none;color:var(--text-1);font-family:inherit;font-size:15px;"
        "font-weight:500;cursor:pointer;text-align:left;touch-action:manipulation;}"
        ".sheet-action:active{background:var(--bg-s2);}"
        ".sheet-action-icon{font-size:18px;margin-right:14px;flex-shrink:0;}"
        ".sheet-action-cancel{color:var(--err);font-weight:600;border-bottom:none;}"
        ".sheet-input-row{display:flex;align-items:center;width:100%;min-height:52px;"
        "padding:10px 20px;border-bottom:1px solid var(--border);gap:12px;}"
        ".sheet-input-label{font-size:15px;font-weight:500;color:var(--text-1);flex:1;}"
        ".sheet-input-label-icon{font-size:18px;margin-right:14px;flex-shrink:0;}"
        ".sheet-input-ctrl{font-size:15px;padding:6px 10px;border-radius:8px;"
        "border:1px solid var(--border-h);background:var(--bg-s2);color:var(--text-1);"
        "font-family:inherit;cursor:pointer;}"
        "::-webkit-scrollbar{width:6px;}"
        "::-webkit-scrollbar-track{background:transparent;}"
        "::-webkit-scrollbar-thumb{background:var(--scrollbar);border-radius:3px;}"
        "</style>"
    )

    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Cache-Control" content="no-cache,no-store,must-revalidate">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
        "<title>Unread Emails</title>" + css + embed_onload + "</head>"
        '<body style="font-family:'
        + _FONT
        + ";background:var(--bg-base);color:var(--text-1);margin:0;padding:0;"
        '-webkit-font-smoothing:antialiased;">'
        # Top header bar
        '<div class="top-bar-unread" style="background:var(--bg-s0);border-bottom:1px solid var(--border);padding:18px 20px;position:sticky;top:0;z-index:20;">'
        '<span style="color:var(--text-1);font-size:17px;font-weight:600;letter-spacing:-0.2px;">'
        + _SVG_ENVELOPE
        + " Unread Emails</span>"
        '<button onclick="doRefresh()" '
        'style="float:right;background:var(--border);border:1px solid var(--border);color:var(--text-1);'
        'font-size:13px;font-weight:600;padding:6px 14px;border-radius:6px;cursor:pointer;">'
        "&#8635; Refresh</button>"
        "</div>"
        # Split-pane wrapper
        '<div class="split-wrap">'
        # Left pane: email list
        '<div class="left-pane">'
        '<div id="ptr-indicator"><div id="ptr-spinner"></div></div>'
        '<div style="max-width:700px;margin:0 auto;min-height:100%;">'
        '<div style="padding:0 16px;">'
        '<div class="section-hdr" style="color:var(--text-2);">'
        "<span>" + today.upper() + "</span>"
        '<span class="section-badge" id="item-count">' + str(count) + "</span>"
        "</div>"
        "</div>"
        # Select all row
        + (
            '<div class="select-all-row" style="display:none">'
            '<label><input type="checkbox" id="select-all-cb" onclick="toggleSelectAll()"> Select All</label>'
            "</div>"
            if count > 0
            else ""
        )
        + '<div style="padding:0 16px 16px;">'
        + content_section
        + "</div></div></div>"
        # Right pane: email viewer iframe
        '<div id="viewer-pane">'
        # Desktop CC button (shown beside close-btn; hidden until email is opened)
        + (
            '<button class="viewer-cc-btn assign-cc-btn" title="Assign CC" '
            'style="display:none;position:absolute;top:10px;right:58px;z-index:11;'
            "padding:5px 10px;background:rgba(196,120,64,0.10);"
            "border:1px solid rgba(196,120,64,0.25);border-radius:6px;"
            'cursor:pointer;color:#c47840;font-size:13px;font-weight:600;align-items:center;justify-content:center;" '
            'onclick="viewerCopyCC(this)">' + _CC_LABEL + "</button>"
        )
        + '<button class="close-btn" onclick="closeViewer()" title="Close">&times;</button>'
        # Mobile-only back header (replaces small × button on phones)
        '<div class="viewer-mobile-header">'
        '<button class="viewer-back-btn" onclick="closeViewer()">&#8592; Back</button>'
        '<div class="viewer-header-actions">'
        '<button id="viewer-markread-btn" class="viewer-action-btn viewer-markread" style="display:none;" onclick="viewerMarkRead()">Mark Read</button>'
        '<button id="viewer-skip-btn" class="viewer-action-btn viewer-skip" style="display:none;" onclick="viewerSkipInbox()">Skip Inbox</button>'
        + (
            '<button class="viewer-cc-btn viewer-action-btn assign-cc-btn" title="Assign CC" '
            'style="display:none;background:rgba(196,120,64,0.10);'
            "border:1px solid rgba(196,120,64,0.25);"
            'align-items:center;justify-content:center;" '
            'onclick="viewerCopyCC(this)">' + _CC_LABEL + "</button>"
        )
        + "</div>"
        "</div>"
        '<div id="viewer-placeholder" style="'
        "flex:1;display:flex;flex-direction:column;align-items:center;"
        'justify-content:center;color:var(--text-3);font-size:15px;gap:12px;">'
        + _SVG_ENVELOPE_LG
        + "<span>Select an email to read it</span>"
        "</div>"
        '<iframe id="viewer-frame" src="about:blank"></iframe>'
        "</div>"
        "</div>" + bulk_toolbar
        # Bottom action sheet (hidden on desktop, shown on mobile via CSS)
        + '<div id="action-sheet-overlay" onclick="closeActionSheet()">'
        '<div id="action-sheet" onclick="event.stopPropagation()">'
        '<div class="sheet-handle"></div>'
        '<div class="sheet-title">Actions</div>'
        '<div id="action-sheet-body"></div>'
        "</div></div>" + js + "</body></html>"
    )


def send_daily_digest(
    emails: List[Dict[str, Any]],
    recipient: str,
    ses_sender: str,
    function_url: str = "",
    action_token: str = "",
) -> None:
    """Compose and send the HTML daily digest via SES.

    Args:
        emails: List of email dicts with keys: id, subject, from, date, gmail_link
        recipient: Destination email address
        ses_sender: Verified SES sender address
        function_url: Lambda Function URL for action links (optional)
        action_token: Secret token for authenticating action links (optional)
    """
    count = len(emails)
    subject = f"Unread Emails — {count} outstanding item{'s' if count != 1 else ''}"
    html_body = _build_html(
        emails, function_url=function_url, action_token=action_token
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
        logger.info(f"Daily digest sent to {recipient} ({count} emails)")
    except Exception as e:
        logger.error(f"Failed to send daily digest: {e}")
        raise
