"""Compose and send the daily Code Task Digest HTML email via SES."""

import logging
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import quote

import boto3

logger = logging.getLogger(__name__)

# Todoist API priority -> display label
PRIORITY_LABELS = {4: "P1", 3: "P2", 2: "P3", 1: "P4"}
PRIORITY_COLORS = {4: "#d1453b", 3: "#eb8909", 2: "#246fe0", 1: "#808080"}

# Value label colors
VALUE_COLORS = {"High": "#d1453b", "Medium": "#eb8909", "Low": "#808080"}

SESSION_PURPLE = "#6C3FA5"


def _age_style(age_days: int) -> str:
    """Return inline CSS for the age badge based on days old."""
    if age_days > 14:
        return "color:#d93025;font-weight:600;"
    elif age_days > 7:
        return "color:#e37400;font-weight:600;"
    return "color:#5f6368;"


def _build_sessions_html(sessions: Dict[str, Any], function_url: str = "") -> str:
    """Build the 'Open Sessions' HTML section for the digest email.

    Args:
        sessions: Dict mapping app_name -> SessionSummary-like dict with keys:
            session_id, cwd, first_user_message, last_timestamp,
            user_message_count, assistant_message_count.
        function_url: Lambda Function URL for "Open →" action buttons.

    Returns:
        HTML string for the sessions section, or empty string if no sessions.
    """
    if not sessions:
        return ""

    count = len(sessions)
    plural = "s" if count != 1 else ""

    # Section header
    html = (
        '<tr><td style="padding:20px 20px 8px;">'
        '<div style="font-size:18px;font-weight:700;color:#202124;line-height:1.3;">'
        "Open Sessions</div>"
        '<div style="margin-top:6px;font-size:13px;color:#5f6368;">'
        f"{count} active project{plural}</div>"
        '<div style="margin-top:14px;border-bottom:2px solid '
        + SESSION_PURPLE
        + ';"></div>'
        "</td></tr>"
    )

    # Session cards
    cards = ""
    sorted_apps = sorted(sessions.keys())
    for idx, app_name in enumerate(sorted_apps):
        session = sessions[app_name]

        # Description — truncated first_user_message
        desc = session.get("first_user_message", "")
        if len(desc) > 120:
            desc = desc[:120].rsplit(" ", 1)[0] + "..."

        # Format timestamp
        raw_ts = session.get("last_timestamp", "")
        try:
            dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            ts_display = dt.strftime("%b %d, %-I:%M %p")
        except (ValueError, AttributeError):
            ts_display = raw_ts[:16] if raw_ts else "unknown"

        msg_count = session.get("user_message_count", 0) + session.get(
            "assistant_message_count", 0
        )

        session_id = session.get("session_id", "")
        cwd = session.get("cwd", "")
        # Truncate session ID for display
        id_display = session_id[:13] + "..." if len(session_id) > 16 else session_id

        # Build action link
        if function_url and cwd:
            action_url = (
                function_url.rstrip("/")
                + "?action=open"
                + "&path="
                + quote(cwd, safe="")
                + "&session_id="
                + quote(session_id, safe="")
            )
            action_html = (
                '<a href="' + action_url + '" '
                'style="color:#6C3FA5;background:#f3e8ff;'
                "text-decoration:none;font-weight:600;font-size:12px;"
                'padding:5px 12px;border-radius:14px;display:inline-block;">'
                "Open &#8594;</a>"
            )
        else:
            action_html = (
                '<code style="color:' + SESSION_PURPLE + ";background:#f3e8ff;"
                "font-size:12px;padding:5px 12px;border-radius:14px;"
                'display:inline-block;font-family:monospace;">'
                "claude -r " + id_display + "</code>"
            )

        border = "border-bottom:1px solid #dadce0;" if idx < count - 1 else ""

        cards += (
            '<div style="padding:16px 0;' + border + '">'
            # App name
            '<div style="font-size:14px;font-weight:700;color:'
            + SESSION_PURPLE
            + ';line-height:1.4;">'
            + app_name
            + "</div>"
            # Description
            '<div style="margin-top:4px;font-size:13px;color:#202124;line-height:1.4;">'
            + desc
            + "</div>"
            # Meta line
            '<div style="margin-top:4px;font-size:12px;color:#5f6368;line-height:1.4;">'
            "Last active: "
            + ts_display
            + " &middot; "
            + str(msg_count)
            + " messages</div>"
            # Action button or resume pill
            '<div style="margin-top:8px;line-height:1;">' + action_html + "</div>"
            "</div>"
        )

    html += '<tr><td style="padding:8px 20px 16px;">' + cards + "</td></tr>"
    return html


def _build_html(
    tasks: List[Dict[str, Any]],
    function_url: str = "",
    repo_mappings: Dict[str, str] = None,
    sessions: Dict[str, Any] = None,
) -> str:
    """Build the HTML body for the coding digest email."""
    count = len(tasks)
    today = datetime.now().strftime("%b %d")
    plural = "s" if count != 1 else ""
    repo_mappings = repo_mappings or {}
    default_repo = repo_mappings.get("default", "")

    high_count = sum(
        1 for t in tasks if t.get("scoring", {}).get("value_label") == "High"
    )

    # Build subtitle with stats merged in
    subtitle_parts = [str(count) + " task" + plural, today]
    if high_count > 0:
        subtitle_parts.append(str(high_count) + " high value")
    subtitle = " &middot; ".join(subtitle_parts)

    # Build task rows as div-based cards
    rows = ""
    for idx, task in enumerate(tasks):
        scoring = task.get("scoring", {})
        content = task.get("content", "")
        api_priority = task.get("priority", 1)
        priority_label = PRIORITY_LABELS.get(api_priority, "P4")
        priority_color = PRIORITY_COLORS.get(api_priority, "#808080")
        value_label = scoring.get("value_label", "Low")
        value_color = VALUE_COLORS.get(value_label, "#808080")
        explicit_val = scoring.get("explicit_value", "")
        value_display = explicit_val if explicit_val else value_label
        age_days = scoring.get("age_days", 0)
        age_display = f"{age_days}d" if age_days > 0 else "new"
        age_css = _age_style(age_days)

        # Resolve repo path from task labels
        repo_path = default_repo
        for label in task.get("labels", []):
            if label in repo_mappings:
                repo_path = repo_mappings[label]
                break

        # Build action link
        if function_url and repo_path:
            action_url = (
                function_url.rstrip("/")
                + "?action=open"
                + "&path="
                + quote(repo_path, safe="")
                + "&task="
                + quote(content, safe="")
            )
            action_link = (
                '<a href="' + action_url + '" '
                'style="color:#6C3FA5;background:#f3e8ff;'
                "text-decoration:none;font-weight:600;font-size:12px;"
                'padding:5px 12px;border-radius:14px;display:inline-block;">'
                "Open &#8594;</a>"
            )
        else:
            task_id = task.get("id", "")
            todoist_url = (
                f"https://todoist.com/app/task/{task_id}"
                if task_id
                else "https://todoist.com"
            )
            action_link = (
                '<a href="' + todoist_url + '" '
                'style="color:#6C3FA5;background:#f3e8ff;'
                "text-decoration:none;font-weight:600;font-size:12px;"
                'padding:5px 12px;border-radius:14px;display:inline-block;">'
                "Open &#8594;</a>"
            )

        # Meta line: value pill · priority · age
        meta_parts = [
            '<span style="color:'
            + value_color
            + ';font-weight:600;">'
            + value_display
            + "</span>",
            '<span style="color:'
            + priority_color
            + ';font-weight:600;">'
            + priority_label
            + "</span>",
            '<span style="' + age_css + '">' + age_display + "</span>",
        ]
        meta_html = " &middot; ".join(meta_parts)

        border = "border-bottom:1px solid #dadce0;" if idx < count - 1 else ""

        rows += (
            '<div style="padding:16px 0;' + border + '">'
            '<div style="font-size:15px;font-weight:600;color:#202124;line-height:1.4;">'
            + content
            + "</div>"
            '<div style="margin-top:6px;font-size:12px;color:#5f6368;line-height:1.4;">'
            + meta_html
            + "</div>"
            '<div style="margin-top:8px;line-height:1;">' + action_link + "</div>"
            "</div>"
        )

    if count == 0:
        content_section = (
            "<p style='color:#5f6368;font-size:15px;text-align:center;'>"
            "No outstanding coding tasks. Nice work!</p>"
        )
    else:
        content_section = rows

    sessions_html = _build_sessions_html(sessions or {}, function_url=function_url)

    return (
        "<!DOCTYPE html>"
        "<html>"
        '<head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
        '<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'
        '&#39;Segoe UI&#39;,Roboto,Helvetica,Arial,sans-serif;">'
        '<table width="100%" cellpadding="0" cellspacing="0" style="padding:20px 0;">'
        '<tr><td align="center">'
        '<table cellpadding="0" cellspacing="0" '
        'style="max-width:600px;width:100%;overflow:hidden;">'
        # Header
        '<tr><td style="padding:20px 20px 16px;">'
        '<div style="font-size:18px;font-weight:700;color:#202124;line-height:1.3;">'
        "Code Task Digest</div>"
        '<div style="margin-top:6px;font-size:13px;color:#5f6368;">'
        + subtitle
        + "</div>"
        '<div style="margin-top:14px;border-bottom:2px solid #6C3FA5;"></div>'
        "</td></tr>"
        # Content
        '<tr><td style="padding:8px 20px 16px;">' + content_section + "</td></tr>"
        # Sessions (omitted if empty)
        + sessions_html  # Footer
        + '<tr><td style="padding:12px 20px;text-align:center;">'
        '<span style="font-size:11px;color:#b0b0b0;">'
        "Sent by Todoist Coding Digest</span>"
        "</td></tr>"
        "</table>"
        "</td></tr></table>"
        "</body></html>"
    )


def send_digest(
    tasks: List[Dict[str, Any]],
    recipient: str,
    ses_sender: str,
    ses_region: str = "us-east-1",
    function_url: str = "",
    repo_mappings: Dict[str, str] = None,
    sessions: Dict[str, Any] = None,
) -> str:
    """Compose and send the HTML coding digest via SES.

    Returns the generated HTML (useful for dry-run saving).
    """
    count = len(tasks)
    today = datetime.now().strftime("%B %d, %Y")
    subject = f"Code Digest - {count} task{'s' if count != 1 else ''} ({today})"

    html_body = _build_html(
        tasks,
        function_url=function_url,
        repo_mappings=repo_mappings,
        sessions=sessions,
    )

    ses = boto3.client("ses", region_name=ses_region)
    try:
        ses.send_email(
            Source=ses_sender,
            Destination={"ToAddresses": [recipient]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
        )
        logger.info(f"Coding digest sent to {recipient} ({count} tasks)")
    except Exception as e:
        logger.error(f"Failed to send coding digest: {e}")
        raise

    return html_body


def build_html_only(
    tasks: List[Dict[str, Any]],
    function_url: str = "",
    repo_mappings: Dict[str, str] = None,
    sessions: Dict[str, Any] = None,
) -> str:
    """Build HTML without sending (for dry-run mode)."""
    return _build_html(
        tasks,
        function_url=function_url,
        repo_mappings=repo_mappings,
        sessions=sessions,
    )
