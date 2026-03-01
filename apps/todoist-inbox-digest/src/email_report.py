"""Compose and send the daily Inbox Digest HTML email via SES."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import boto3

logger = logging.getLogger(__name__)

_ses = boto3.client("ses", region_name="us-east-1")

# Priority display: API value -> (label, bg_color, text_color)
PRIORITY_MAP = {
    4: ("P1", "#fce8e6", "#d93025"),
    3: ("P2", "#fef3c7", "#d97706"),
    2: ("P3", "#e8f0fe", "#1a73e8"),
    1: ("P4", "#f3f4f6", "#6b7280"),
}


def _relative_age(added_at: str) -> str:
    """Return a short relative age string like '14d' or '2h' from an ISO timestamp."""
    if not added_at:
        return "?"
    try:
        created = datetime.fromisoformat(added_at.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - created
        days = delta.days
        if days > 0:
            return f"{days}d"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}h"
        minutes = delta.seconds // 60
        return f"{minutes}m"
    except Exception:
        return "?"


def _age_days(added_at: str) -> int:
    """Return integer days since added_at, or -1 on failure."""
    if not added_at:
        return -1
    try:
        created = datetime.fromisoformat(added_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - created).days
    except Exception:
        return -1


def _age_style(days: int) -> str:
    """Return inline CSS color for the age badge based on days old."""
    if days > 14:
        return "color:#d93025;font-weight:600;"
    elif days > 7:
        return "color:#e37400;font-weight:600;"
    return "color:#5f6368;"


def _due_display(task: Dict) -> tuple:
    """Return (text, color) for a task's due date."""
    due_obj = task.get("due")
    if not due_obj:
        return ("no date", "#6b7280")
    due_date_str = (due_obj.get("date", "") or "")[:10]
    if not due_date_str:
        return ("no date", "#6b7280")
    try:
        due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        diff = (due - today).days
        if diff < 0:
            return ("overdue", "#d93025")
        elif diff == 0:
            return ("due today", "#188038")
        elif diff == 1:
            return ("due tomorrow", "#1a73e8")
        else:
            return ("due " + due.strftime("%b %-d"), "#5f6368")
    except Exception:
        return (due_date_str, "#5f6368")


def _project_name(task: Dict, projects_by_id: Dict) -> str:
    """Return the project name for a task."""
    return projects_by_id.get(task.get("project_id", ""), "Inbox")


def _pill(text: str, href: str, bg: str, color: str) -> str:
    """Build an HTML email-safe action pill link."""
    return (
        '<a href="' + href + '" '
        'style="color:' + color + ";background:" + bg + ";"
        "text-decoration:none;font-weight:600;font-size:12px;"
        'padding:5px 12px;border-radius:14px;display:inline-block;">' + text + "</a>"
    )


def _build_html(
    tasks: List[Dict[str, Any]],
    projects: List[Dict[str, Any]],
    function_url: str = "",
    action_token: str = "",
    web_dashboard_url: str = "",
) -> str:
    """Build the HTML body for the inbox digest email."""
    projects_by_id = {p["id"]: p.get("name", "Unknown") for p in projects}

    # Sort oldest-first by added_at
    tasks.sort(key=lambda t: t.get("added_at", "") or t.get("created_at", "") or "")

    count = len(tasks)
    today = datetime.now().strftime("%B %-d")
    plural = "s" if count != 1 else ""

    # Count overdue
    overdue_count = 0
    for task in tasks:
        due_text, _ = _due_display(task)
        if due_text == "overdue":
            overdue_count += 1

    def _action_url(action, task_id=""):
        base = function_url.rstrip("/") + "?action=" + action
        if task_id:
            base += "&task_id=" + task_id
        base += "&source=email&token=" + action_token
        return base

    # Build task rows
    rows = ""
    for idx, task in enumerate(tasks):
        task_id = task.get("id", "")
        content = task.get("content", "(no title)")
        added_at = task.get("added_at", "") or task.get("created_at", "")
        age = _relative_age(added_at)
        days = _age_days(added_at)
        priority = task.get("priority", 1)
        p_label, p_bg, p_color = PRIORITY_MAP.get(
            priority, ("P4", "#f3f4f6", "#6b7280")
        )
        proj = _project_name(task, projects_by_id)
        due_text, due_color = _due_display(task)
        age_css = _age_style(days)

        # Meta line: age + project + priority + due
        meta_parts = [
            '<span style="' + age_css + '">' + age + "</span>",
            proj,
            '<span style="color:'
            + p_color
            + ';font-weight:600;">'
            + p_label
            + "</span>",
            '<span style="color:'
            + due_color
            + ';font-weight:500;">'
            + due_text
            + "</span>",
        ]
        info_html = " &middot; ".join(meta_parts)

        # Action pills — only Complete and Open
        pills = []

        # Complete (green)
        if function_url and action_token:
            pills.append(
                _pill(
                    "&#10003; Complete",
                    _action_url("complete", task_id),
                    "#e6f4ea",
                    "#188038",
                )
            )

        # Open in Todoist (blue)
        pills.append(
            _pill(
                "Open &#8594;",
                f"https://todoist.com/app/task/{task_id}",
                "#e8f0fe",
                "#1a73e8",
            )
        )

        action_html = (
            (
                '<div style="margin-top:8px;line-height:2;">'
                + " &nbsp; ".join(pills)
                + "</div>"
            )
            if pills
            else ""
        )

        border = "border-bottom:1px solid #dadce0;" if idx < count - 1 else ""

        rows += (
            '<div style="padding:16px 0;' + border + '">'
            '<div style="font-size:15px;font-weight:600;color:#202124;line-height:1.4;">'
            + content
            + "</div>"
            '<div style="margin-top:6px;font-size:12px;color:#5f6368;line-height:1.4;">'
            + info_html
            + "</div>"
            + action_html
            + "</div>"
        )

    if count == 0:
        table_section = "<p style='color:#5f6368;font-size:15px;'>No outstanding inbox tasks. Inbox zero!</p>"
    else:
        table_section = rows

    # Header refresh link
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

    # Subtitle
    subtitle_parts = [str(count) + " item" + plural, today]
    if overdue_count > 0:
        subtitle_parts.append("&#9888; " + str(overdue_count) + " overdue")
    subtitle = " &middot; ".join(subtitle_parts)

    # Manage on Web link — points to the action-dashboard (todoist-actions-web)
    web_link = ""
    if web_dashboard_url:
        web_link = (
            '<a href="' + web_dashboard_url + '" '
            'style="color:#1a73e8;background:#e8f0fe;'
            "text-decoration:none;font-weight:600;font-size:12px;"
            "padding:5px 14px;border-radius:14px;display:inline-block;"
            'margin-top:10px;">Manage on Web &#8594;</a>'
        )

    header_row = (
        '<tr><td style="padding:20px 20px 16px;">'
        + refresh_link
        + '<div style="font-size:18px;font-weight:700;color:#202124;line-height:1.3;">'
        "Inbox Digest</div>"
        '<div style="margin-top:6px;font-size:13px;color:#5f6368;">'
        + subtitle
        + "</div>"
        + web_link
        + '<div style="margin-top:14px;border-bottom:2px solid #1a73e8;"></div>'
        "</td></tr>"
    )

    footer_content = (
        '<span style="font-size:11px;color:#b0b0b0;">'
        "Sent by Todoist Inbox Digest</span>"
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
        + header_row
        + '<tr><td style="padding:8px 20px 16px;">'
        + table_section
        + "</td></tr>"
        '<tr><td style="padding:12px 20px;text-align:center;">'
        + footer_content
        + "</td></tr>"
        "</table>"
        "</td></tr></table>"
        "</body></html>"
    )


def send_daily_digest(
    tasks: List[Dict[str, Any]],
    projects: List[Dict[str, Any]],
    recipient: str,
    ses_sender: str,
    function_url: str = "",
    action_token: str = "",
    web_dashboard_url: str = "",
) -> None:
    """Compose and send the HTML daily digest via SES.

    Args:
        tasks: List of Todoist task dicts from inbox projects.
        projects: List of all Todoist project dicts.
        recipient: Destination email address.
        ses_sender: Verified SES sender address.
        function_url: Lambda Function URL for action links (Complete).
        action_token: Secret token for authenticating action links.
        web_dashboard_url: Full URL to the web dashboard for "Manage on Web".
    """
    count = len(tasks)
    subject = f"Inbox Digest \u2014 {count} outstanding item{'s' if count != 1 else ''}"
    html_body = _build_html(
        tasks,
        projects,
        function_url=function_url,
        action_token=action_token,
        web_dashboard_url=web_dashboard_url,
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
        logger.info(f"Inbox Digest sent to {recipient} ({count} tasks)")
    except Exception as e:
        logger.error(f"Failed to send inbox digest: {e}")
        raise
