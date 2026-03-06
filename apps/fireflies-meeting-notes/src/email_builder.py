"""Build and send HTML meeting summary emails via SES."""

import logging
import re
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List

import boto3
from fireflies_service import TranscriptData

logger = logging.getLogger(__name__)

_ses = boto3.client("ses", region_name="us-east-1")


def _build_followup_template(transcript: TranscriptData) -> str:
    participants = transcript.participants or []
    if len(participants) > 1:
        greeting = "Hi all,"
    elif len(participants) == 1:
        greeting = f"Hi {_escape(participants[0])},"
    else:
        greeting = "Hi all,"

    action_lines = ""
    if transcript.action_items:
        for item in transcript.action_items:
            action_lines += "- " + _escape(item) + "<br>"
    else:
        action_lines = "- [No action items identified]<br>"

    summary_lines = ""
    bullets = transcript.summary_bullets[:3] if transcript.summary_bullets else []
    for bullet in bullets:
        summary_lines += "- " + _escape(bullet) + "<br>"

    subject_suggestion = _escape(transcript.title)

    template_html = (
        f"<strong>Subject:</strong> Follow-Up: {subject_suggestion}<br><br>"
        f"{greeting}<br><br>"
        "Thanks for the meeting today. Here's a quick recap of what we covered "
        "and the next steps:<br><br>"
    )
    if summary_lines:
        template_html += "<strong>Key Points:</strong><br>" + summary_lines + "<br>"
    template_html += (
        "<strong>Action Items:</strong><br>" + action_lines + "<br>"
        "Please let me know if I missed anything or if you have questions.<br><br>"
        "Best,<br>"
        "Terrance"
    )

    return (
        '<div style="background:#f8f9fa;border:1px solid #dadce0;border-radius:6px;'
        "padding:16px;font-size:13px;color:#3c4043;line-height:1.7;"
        'font-family:monospace,monospace;white-space:pre-wrap;">'
        + template_html
        + "</div>"
    )


def _build_html(
    transcript: TranscriptData,
    obsidian_button_url: str,
    tasks_created: int,
    recordings_url: str = "",
    include_followup_template: bool = False,
) -> str:
    duration_display = f"{transcript.duration_minutes} min"
    action_count = len(transcript.action_items) if transcript.action_items else 0
    participant_count = len(transcript.participants) if transcript.participants else 0

    subtitle_parts = [
        _escape(transcript.date),
        duration_display,
        str(participant_count)
        + " participant"
        + ("s" if participant_count != 1 else ""),
        str(action_count) + " action" + ("s" if action_count != 1 else ""),
    ]
    if tasks_created > 0:
        plural = "s" if tasks_created != 1 else ""
        subtitle_parts.append(
            "&#10003; " + str(tasks_created) + " task" + plural + " created"
        )
    subtitle = " &middot; ".join(subtitle_parts)

    header_row = (
        '<tr><td style="padding:20px 20px 16px;">'
        '<div style="font-size:18px;font-weight:700;color:#202124;line-height:1.3;">'
        + _escape(transcript.title)
        + "</div>"
        '<div style="margin-top:6px;font-size:13px;color:#5f6368;">'
        + subtitle
        + "</div>"
        '<div style="margin-top:14px;border-bottom:2px solid #1a73e8;"></div>'
        "</td></tr>"
    )

    sections = []

    if transcript.summary_overview:
        summary_html = (
            '<div style="color:#202124;font-size:15px;line-height:1.7;">'
            + _md_to_html(transcript.summary_overview)
            + "</div>"
        )
        sections.append(_section_block("Summary Overview", summary_html, first=True))

    if transcript.summary_bullets:
        bullet_rows = ""
        for bullet in transcript.summary_bullets:
            bullet_html = _escape(bullet)
            bullet_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", bullet_html)
            bullet_rows += (
                "<tr>"
                '<td width="16" style="color:#1a73e8;font-size:15px;'
                'vertical-align:top;padding:5px 0;">&#8226;</td>'
                '<td style="padding:5px 0 5px 6px;color:#202124;'
                'font-size:15px;line-height:1.6;">' + bullet_html + "</td></tr>"
            )
        bullets_content = (
            '<table width="100%" cellpadding="0" cellspacing="0" '
            'role="presentation">' + bullet_rows + "</table>"
        )
        sections.append(
            _section_block("Key Points", bullets_content, first=not sections)
        )

    if transcript.action_items:
        action_rows = ""
        for idx, item in enumerate(transcript.action_items, 1):
            border = (
                "border-bottom:1px solid #dadce0;"
                if idx < len(transcript.action_items)
                else ""
            )
            action_rows += (
                '<div style="padding:10px 0;' + border + '">'
                '<span style="color:#1a73e8;font-weight:700;font-size:15px;">'
                + str(idx)
                + ".</span>"
                '<span style="color:#202124;font-size:15px;line-height:1.5;"> '
                + _escape(item)
                + "</span></div>"
            )
        sections.append(_section_block("Action Items", action_rows, first=not sections))

    if transcript.keywords:
        pills = ""
        for kw in transcript.keywords:
            pills += (
                '<span style="display:inline-block;background:#e8f0fe;color:#1a73e8;'
                "border-radius:14px;padding:4px 12px;font-size:12px;font-weight:500;"
                'margin:3px 4px 3px 0;">' + _escape(kw) + "</span>"
            )
        sections.append(_section_block("Keywords", pills, first=not sections))

    if include_followup_template:
        followup_html = _build_followup_template(transcript)
        sections.append(
            _section_block(
                "Follow-Up Email Template",
                followup_html,
                first=not sections,
            )
        )

    buttons_html = ""
    btn_parts = []
    if transcript.audio_url:
        btn_parts.append(
            '<a href="'
            + transcript.audio_url
            + '" style="display:inline-block;color:#1a73e8;background:#e8f0fe;'
            "text-decoration:none;font-weight:600;font-size:12px;"
            'padding:5px 12px;border-radius:14px;">'
            "&#9654; Listen to Recording</a>"
        )
    if obsidian_button_url:
        btn_parts.append(
            '<a href="'
            + obsidian_button_url
            + '" style="display:inline-block;color:#202124;background:#f1f3f4;'
            "text-decoration:none;font-weight:600;font-size:12px;"
            'padding:5px 12px;border-radius:14px;">'
            "&#10003; Save to Obsidian</a>"
        )
    if recordings_url:
        btn_parts.append(
            '<a href="'
            + recordings_url
            + '" style="display:inline-block;color:#1a73e8;background:#e8f0fe;'
            "text-decoration:none;font-weight:600;font-size:12px;"
            'padding:5px 12px;border-radius:14px;">'
            "&#9776; All Recordings</a>"
        )
    if btn_parts:
        buttons_html = (
            '<div style="padding-top:16px;border-top:1px solid #dadce0;">'
            + " &nbsp; ".join(btn_parts)
            + "</div>"
        )

    content_inner = "".join(sections) + buttons_html

    return (
        "<!DOCTYPE html>"
        "<html>"
        '<head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "</head>"
        '<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'
        "'Segoe UI',Roboto,Helvetica,Arial,sans-serif;\">"
        '<table width="100%" cellpadding="0" cellspacing="0" '
        'style="padding:20px 0;" role="presentation">'
        '<tr><td align="center">'
        '<table cellpadding="0" cellspacing="0" '
        'style="max-width:600px;width:100%;overflow:hidden;" role="presentation">'
        + header_row
        + '<tr><td style="padding:8px 20px 16px;">' + content_inner + "</td></tr>"
        + '<tr><td style="padding:12px 20px;text-align:center;">'
        '<span style="font-size:11px;color:#b0b0b0;">'
        "Sent by Fireflies Meeting Notes Processor"
        "</span></td></tr>"
        "</table>"
        "</td></tr></table>"
        "</body></html>"
    )


def _section_block(title: str, content: str, first: bool = False) -> str:
    border = "" if first else "border-top:1px solid #dadce0;"
    return (
        '<div style="padding-top:16px;' + border + '">'
        '<div style="font-size:15px;font-weight:700;color:#202124;'
        'padding-bottom:10px;">' + title + "</div>" + content + "</div>"
    )


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _md_to_html(text: str) -> str:
    escaped = _escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)

    lines = escaped.split("\n")
    has_bullets = any(l.strip().startswith("- ") for l in lines)

    if not has_bullets:
        return "<br>".join(lines)

    rows = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            content = stripped[2:]
            rows += (
                "<tr>"
                '<td width="16" style="color:#1a73e8;font-size:15px;'
                'vertical-align:top;padding:5px 0;">'
                "&#8226;</td>"
                '<td style="padding:5px 0 5px 6px;color:#202124;'
                'font-size:15px;line-height:1.6;">' + content + "</td></tr>"
            )
        elif stripped:
            rows += (
                '<tr><td colspan="2" style="padding:4px 0;color:#202124;'
                'font-size:15px;line-height:1.7;">' + stripped + "</td></tr>"
            )
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" '
        'role="presentation">' + rows + "</table>"
    )


def send_meeting_email(
    transcript: TranscriptData,
    recipient: str,
    ses_sender: str,
    obsidian_button_url: str = "",
    tasks_created: int = 0,
    descriptive_title: str = "",
    recordings_url: str = "",
    include_followup_template: bool = False,
) -> None:
    title_for_subject = descriptive_title or transcript.title
    subject = f"Meeting Notes: {title_for_subject}"
    html_body = _build_html(
        transcript,
        obsidian_button_url,
        tasks_created,
        recordings_url,
        include_followup_template=include_followup_template,
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
        logger.info(f"Meeting summary email sent to {recipient}")
    except Exception as e:
        logger.error(f"Failed to send meeting email: {e}")
        raise


def build_recordings_html(
    recordings: List[Dict[str, Any]],
    function_url: str,
    action_token: str,
) -> str:
    """Build an interactive web page listing all saved recordings with search filter."""
    _FONT = "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif"

    count = len(recordings)
    plural = "s" if count != 1 else ""
    today = datetime.now().strftime("%B %d, %Y")

    cards = ""
    for rec in recordings:
        title = _escape(rec.get("title") or rec.get("original_title", "Untitled"))
        rec_date = _escape(rec.get("date", ""))
        duration = rec.get("duration_minutes", 0)
        duration_str = f"{int(duration)} min" if duration else ""
        participants = rec.get("participants", [])
        p_count = len(participants)
        p_str = str(p_count) + " participant" + ("s" if p_count != 1 else "")
        audio_url = rec.get("audio_url", "")
        transcript_id = rec.get("transcript_id", "")

        meta_parts = []
        if rec_date:
            meta_parts.append(rec_date)
        if duration_str:
            meta_parts.append(duration_str)
        meta_parts.append(p_str)
        meta_html = " &middot; ".join(meta_parts)

        btn_parts = []
        if audio_url:
            btn_parts.append(
                '<a href="' + audio_url + '" '
                'style="color:#1a73e8;background:#e8f0fe;'
                "text-decoration:none;font-weight:600;font-size:12px;"
                'padding:5px 12px;border-radius:14px;display:inline-block;">'
                "&#9654; Listen</a>"
            )
        if transcript_id and function_url and action_token:
            title_encoded = urllib.parse.quote(
                rec.get("title") or rec.get("original_title", ""), safe=""
            )
            obsidian_url = (
                function_url.rstrip("/")
                + "?action=save_obsidian&transcript_id="
                + transcript_id
                + "&title="
                + title_encoded
                + "&token="
                + action_token
            )
            btn_parts.append(
                '<a href="' + obsidian_url + '" '
                'style="color:#202124;background:#f1f3f4;'
                "text-decoration:none;font-weight:600;font-size:12px;"
                'padding:5px 12px;border-radius:14px;display:inline-block;">'
                "&#10003; Save to Obsidian</a>"
            )

        action_html = ""
        if btn_parts:
            action_html = (
                '<div style="margin-top:8px;line-height:1;">'
                + " &nbsp; ".join(btn_parts)
                + "</div>"
            )

        # Store raw title and date as data attributes for JS filtering
        raw_title = (rec.get("title") or rec.get("original_title", "")).lower()
        raw_date = rec.get("date", "").lower()

        cards += (
            '<div class="rec-card" '
            'data-title="' + raw_title.replace('"', '') + '" '
            'data-date="' + raw_date.replace('"', '') + '" '
            'style="padding:16px 0;border-bottom:1px solid #dadce0;">'
            '<div style="font-size:15px;font-weight:600;color:#202124;line-height:1.4;">'
            + title
            + "</div>"
            '<div style="margin-top:6px;font-size:12px;color:#5f6368;line-height:1.4;">'
            + meta_html
            + "</div>"
            + action_html
            + "</div>"
        )

    if count == 0:
        content_section = (
            '<div id="empty-state" style="text-align:center;padding:40px 0;'
            'color:#5f6368;font-size:15px;">No recordings found.</div>'
        )
    else:
        content_section = (
            '<div id="no-results" style="display:none;text-align:center;'
            'padding:40px 0;color:#5f6368;font-size:15px;">No recordings match your search.</div>'
            + cards
        )

    refresh_url = function_url.rstrip("/") + "?action=recordings&token=" + action_token

    search_box = (
        '<div style="padding:16px 24px 0;">'
        '<input id="rec-search" type="search" placeholder="Filter by title or date..." '
        'style="width:100%;box-sizing:border-box;padding:8px 12px;font-size:14px;'
        "border:1px solid #dadce0;border-radius:6px;outline:none;"
        'font-family:inherit;color:#202124;" />'
        "</div>"
    )

    filter_js = (
        "<script>"
        "document.getElementById('rec-search').addEventListener('input',function(){"
        "var q=this.value.toLowerCase().trim();"
        "var cards=document.querySelectorAll('.rec-card');"
        "var shown=0;"
        "cards.forEach(function(c){"
        "var match=!q||c.dataset.title.includes(q)||c.dataset.date.includes(q);"
        "c.style.display=match?'':'none';"
        "if(match)shown++;"
        "});"
        "var noRes=document.getElementById('no-results');"
        "if(noRes)noRes.style.display=(shown===0&&q)?'block':'none';"
        "});"
        "</script>"
    )

    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Cache-Control" content="no-cache,no-store,must-revalidate">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
        "<title>Meeting Recordings</title>"
        "</head>"
        '<body style="font-family:' + _FONT + ";background:#f0f2f5;margin:0;padding:0;"
        '-webkit-font-smoothing:antialiased;">'
        '<div style="background:#1a73e8;padding:18px 20px;">'
        '<span style="color:#fff;font-size:17px;font-weight:600;letter-spacing:-0.2px;">'
        "&#127908; Meeting Recordings</span>"
        '<a href="' + refresh_url + '" '
        'style="float:right;background:rgba(255,255,255,.2);border:none;color:#fff;'
        "font-size:13px;font-weight:600;padding:6px 14px;border-radius:6px;"
        'cursor:pointer;text-decoration:none;">'
        "&#8635; Refresh</a>"
        "</div>"
        '<div style="max-width:600px;margin:0 auto;background:#fff;'
        'box-shadow:0 2px 8px rgba(0,0,0,.10);min-height:60vh;">'
        '<div style="padding:20px 24px 0;">'
        '<div style="font-size:13px;color:#5f6368;">'
        + str(count)
        + " recording"
        + plural
        + " &middot; "
        + today
        + "</div>"
        '<div style="margin-top:14px;border-bottom:2px solid #1a73e8;"></div>'
        "</div>"
        + search_box
        + '<div style="padding:0 24px 24px;">' + content_section + "</div></div>"
        '<div style="text-align:center;padding:16px;font-size:11px;color:#b0b0b0;">'
        "Fireflies Meeting Notes Processor</div>"
        + filter_js
        + "</body></html>"
    )
