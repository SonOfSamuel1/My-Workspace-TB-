"""AWS Lambda handler for Gmail Email Actions automation.

Two invocation modes:
- sync (every 5 min via EventBridge): polls Gmail starred emails, creates Todoist tasks
- daily_digest (8 AM ET via EventBridge): sends HTML email digest of open Email Actions tasks
"""

import base64
import html
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import boto3  # noqa: E402

ssm = boto3.client("ssm", region_name="us-east-1")
_s3 = boto3.client("s3", region_name="us-east-1")

CALENDAR_STATE_KEY = "calendar_reviewed_state.json"

_PAGE_STYLE = (
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
    "background:#0e0e10;margin:0;padding:0;color-scheme:dark;"
)

_CARD_STYLE = (
    "max-width:480px;margin:80px auto;background:#1c1c1f;border-radius:8px;"
    "border:1px solid rgba(255,255,255,0.06);padding:40px;text-align:center;"
)


def _confirmation_page(
    icon_html: str, title: str, title_color: str, message: str
) -> str:
    """Build a confirmation page: auto-closes on desktop, shows card on mobile."""
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<script>"
        "try{window.close();}catch(e){}"
        "setTimeout(function(){try{window.close();}catch(e){}},500);"
        "</script></head>"
        "<body style='" + _PAGE_STYLE + "'>"
        "<div style='" + _CARD_STYLE + "'>"
        "<div style='font-size:48px;line-height:1;margin-bottom:16px;'>"
        + icon_html
        + "</div>"
        "<h2 style='margin:0 0 8px;color:"
        + title_color
        + ";font-size:20px;'>"
        + title
        + "</h2>"
        "<p style='color:#8b8b93;font-size:15px;margin:0 0 20px;'>" + message + "</p>"
        "<a href='https://mail.google.com/mail/u/0/#inbox' "
        "style='display:inline-block;background:rgba(99,102,241,0.10);color:#818cf8;border:1px solid rgba(99,102,241,0.20);padding:12px 28px;"  # noqa: E501
        "border-radius:6px;text-decoration:none;font-size:15px;'>Back to Inbox</a>"
        "</div></body></html>"
    )


def _sanitize_html(raw_html: str) -> str:
    """Strip dangerous tags and attributes from email HTML for safe inline rendering."""
    # Remove <script>, <style>, <iframe>, <object>, <embed>, <form> tags and contents
    for tag in ("script", "style", "iframe", "object", "embed", "form"):
        raw_html = re.sub(
            rf"<{tag}[^>]*>.*?</{tag}>", "", raw_html, flags=re.DOTALL | re.IGNORECASE
        )
        # Also remove self-closing variants
        raw_html = re.sub(rf"<{tag}[^>]*/?>", "", raw_html, flags=re.IGNORECASE)
    # Remove on* event handler attributes (onclick, onerror, etc.)
    raw_html = re.sub(
        r"\s+on\w+\s*=\s*[\"'][^\"']*[\"']", "", raw_html, flags=re.IGNORECASE
    )
    raw_html = re.sub(r"\s+on\w+\s*=\s*\S+", "", raw_html, flags=re.IGNORECASE)
    # Remove javascript: URLs in href/src
    raw_html = re.sub(
        r'(href|src)\s*=\s*["\']javascript:[^"\']*["\']',
        "",
        raw_html,
        flags=re.IGNORECASE,
    )
    return raw_html


def _email_viewer_page(
    content: dict, function_url: str = "", action_token: str = "", embed: bool = False
) -> str:
    """Render a mobile-friendly HTML page showing the email content."""
    subject = html.escape(content.get("subject", "(no subject)"))
    from_addr = html.escape(content.get("from", ""))
    date = html.escape(content.get("date", ""))
    msg_id = content.get("id", "")
    thread_id = content.get("threadId", "")

    # Prepare email body: prefer HTML, fall back to plain text
    body_html = content.get("body_html", "")
    body_text = content.get("body_text", "")
    if body_html:
        email_body = (
            '<div style="padding:16px 0;font-size:15px;line-height:1.6;overflow-x:auto;">'
            + _sanitize_html(body_html)
            + "</div>"
        )
    elif body_text:
        email_body = (
            '<pre style="white-space:pre-wrap;word-break:break-word;font-family:inherit;'
            'font-size:15px;line-height:1.6;padding:16px 0;margin:0;">'
            + html.escape(body_text)
            + "</pre>"
        )
    else:
        email_body = '<p style="color:var(--text-3);padding:16px 0;">No message body available.</p>'

    # Build action buttons
    # Reply via mailto (opens Gmail compose on iOS)
    reply_email = from_addr
    # Extract just the email address from "Name <email>" format
    email_match = re.search(r"<([^>]+)>", content.get("from", ""))
    if email_match:
        reply_email = html.escape(email_match.group(1))
    reply_subject = html.escape("Re: " + content.get("subject", ""))
    reply_url = f"mailto:{reply_email}?subject={reply_subject}"

    # Unstar button — uses fetch() with inline animation instead of navigation
    unstar_btn = ""
    if function_url and action_token and msg_id:
        unstar_url = (
            function_url.rstrip("/")
            + "?action=unstar&msg_id="
            + msg_id
            + "&token="
            + action_token
        )
        # After successful unstar: in embed mode, notify parent via postMessage;
        # in standalone mode, redirect back to web digest.
        if embed:
            _unstar_success_js = (
                'btn.style.background=cv("--ok-bg");'
                'btn.style.color=cv("--ok");'
                'btn.innerHTML="\\u2713 Unstarred";'
                'btn.style.cursor="default";'
                'window.parent.postMessage({type:"unstar",msgId:"' + msg_id + '"},"*");'
            )
        else:
            _unstar_success_js = (
                'btn.style.background=cv("--ok-bg");'
                'btn.style.color=cv("--ok");'
                'btn.innerHTML="\\u2713 Unstarred";'
                'btn.style.cursor="default";'
                'setTimeout(function(){window.location.href="'
                + function_url.rstrip("/")
                + "?action=web&token="
                + action_token
                + '";},800);'
            )
        unstar_btn = (
            '<a id="unstar-btn" href="#" onclick="doUnstar(event)" '
            'style="display:inline-block;background:var(--err-bg);'
            "color:var(--err);border:1px solid var(--err-b);padding:11px 24px;border-radius:8px;text-decoration:none;"
            "font-size:14px;font-weight:600;letter-spacing:-0.1px;"
            'transition:all .3s ease;">Unstar</a>'
            "<script>"
            "var _cs=getComputedStyle(document.documentElement);function cv(n){return _cs.getPropertyValue(n).trim();}"
            "function doUnstar(e){"
            "e.preventDefault();"
            'var btn=document.getElementById("unstar-btn");'
            'btn.style.background=cv("--text-2");'
            'btn.style.pointerEvents="none";'
            'btn.innerHTML="Unstarring\\u2026";'
            'fetch("' + unstar_url + '")'
            ".then(function(r){"
            "if(r.ok){" + _unstar_success_js + "}else{"
            'btn.style.background=cv("--err-bg");'
            'btn.style.color=cv("--err");'
            'btn.innerHTML="Failed \\u2013 Tap to retry";'
            'btn.style.pointerEvents="auto";'
            "}"
            "})"
            ".catch(function(){"
            'btn.style.background=cv("--err-bg");'
            'btn.style.color=cv("--err");'
            'btn.innerHTML="Failed \\u2013 Tap to retry";'
            'btn.style.pointerEvents="auto";'
            "});"
            "}"
            "</script>"
        )

    # Skip Inbox filter button
    skip_inbox_btn = ""
    if function_url and action_token and reply_email:
        import urllib.parse

        filter_url = (
            function_url.rstrip("/")
            + "?action=create_filter"
            + "&from_email="
            + urllib.parse.quote(reply_email)
            + "&token="
            + action_token
        )
        skip_inbox_btn = (
            '<a id="skip-inbox-btn" href="#" onclick="doSkipInbox(event)" '
            'style="display:inline-block;background:var(--warn-bg);'
            "color:var(--warn);border:1px solid var(--warn-b);padding:11px 24px;border-radius:8px;text-decoration:none;"
            "font-size:14px;font-weight:600;letter-spacing:-0.1px;"
            'transition:all .3s ease;">Skip Inbox</a>'
            "<script>"
            "var _cs=getComputedStyle(document.documentElement);function cv(n){return _cs.getPropertyValue(n).trim();}"
            "function doSkipInbox(e){"
            "e.preventDefault();"
            'var btn=document.getElementById("skip-inbox-btn");'
            'btn.style.background=cv("--text-2");btn.style.pointerEvents="none";'
            'btn.innerHTML="Creating filter\u2026";'
            'fetch("' + filter_url + '")'
            ".then(function(r){return r.json();})"
            ".then(function(d){"
            "if(d.ok){"
            'btn.style.background=cv("--ok-bg");'
            'btn.style.color=cv("--ok");'
            'btn.innerHTML="\u2713 Filter created";'
            'btn.style.cursor="default";'
            "}else{"
            'btn.style.background=cv("--warn-bg");'
            'btn.style.color=cv("--warn");'
            'btn.innerHTML="Failed \u2013 Tap to retry";'
            'btn.style.pointerEvents="auto";'
            "}"
            "})"
            ".catch(function(){"
            'btn.style.background=cv("--warn-bg");'
            'btn.style.color=cv("--warn");'
            'btn.innerHTML="Failed \u2013 Tap to retry";'
            'btn.style.pointerEvents="auto";'
            "});}"
            "</script>"
        )

    # Gmail web fallback link
    gmail_web_url = ""
    if thread_id:
        gmail_web_url = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"

    gmail_link = ""
    if gmail_web_url:
        gmail_link = (
            '<a href="'
            + gmail_web_url
            + '" style="color:var(--accent-l);font-size:13px;'
            'text-decoration:underline;">View in Gmail</a>'
        )

    _FONT = "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif"
    _VIEWER_STYLE = (
        "font-family:" + _FONT + ";"
        "background:var(--bg-base);margin:0;padding:0;-webkit-font-smoothing:antialiased;"
    )

    # Conditionally show/hide the blue header bar (hidden in embed mode)
    header_bar = ""
    if not embed:
        header_bar = (
            '<div style="background:var(--bg-s0);border-bottom:1px solid var(--border);padding:18px 20px;">'
            '<span style="color:var(--text-1);font-size:17px;font-weight:600;letter-spacing:-0.2px;">'
            "&#9993; Email Viewer</span>"
            "</div>"
        )

    # Action buttons bar (Reply + Unstar + Skip Inbox + View in Gmail) — placed above email body
    action_bar = (
        '<div style="padding:16px 24px;border-bottom:1px solid var(--border);'
        'display:flex;gap:12px;flex-wrap:wrap;align-items:center;">'
        '<a href="'
        + reply_url
        + '" style="display:inline-block;background:var(--accent-bg);'
        "color:var(--accent-l);border:1px solid var(--accent-b);padding:11px 24px;border-radius:8px;text-decoration:none;"
        'font-size:14px;font-weight:600;letter-spacing:-0.1px;">Reply</a>'
        + unstar_btn
        + skip_inbox_btn
        + (
            ' <span style="margin-left:auto;">' + gmail_link + "</span>"
            if gmail_link
            else ""
        )
        + "</div>"
    )

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
        "<title>" + subject + "</title>"
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
        "</style>"
        "</head>"
        '<body style="'
        + _VIEWER_STYLE
        + '">'
        + header_bar
        + '<div style="max-width:700px;margin:0 auto;background:var(--bg-s1);'
        'border:1px solid var(--border);">'
        '<div style="padding:20px 24px;border-bottom:1px solid var(--border);">'
        '<h1 style="margin:0 0 12px;font-size:19px;color:var(--text-1);font-weight:600;'
        'letter-spacing:-0.3px;line-height:1.35;">' + subject + "</h1>"
        '<div style="font-size:13px;color:var(--text-2);line-height:1.6;">'
        '<strong style="color:var(--text-1);">From:</strong> ' + from_addr + "<br>"
        '<strong style="color:var(--text-1);">Date:</strong> '
        + date
        + "</div></div>"
        + action_bar
        + '<div style="padding:16px 24px 20px;"><div style="background:#fff;border-radius:6px;padding:0 16px;">'
        + email_body
        + "</div></div>"  # noqa: E501
        "</div>"
        "</body></html>"
    )


def _build_container_html(
    starred_embed_url: str,
    unread_embed_url: str,
    starred_count: int,
    todoist_web_url: str = "",
    calendar_url: str = "",
) -> str:
    """Build the container page with vertical sidebar and iframes for Starred, Unread, Todoist, and Calendar views."""
    _FONT = (
        "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,"
        "'Segoe UI',Roboto,sans-serif"
    )

    # Build tab definitions: (id, label, url, preload)
    tabs = [
        ("starred", "Starred", starred_embed_url, True),
        ("unread", "Unread", unread_embed_url, True),
    ]
    if todoist_web_url:
        # Todoist tabs preloaded (hidden) so badge counts appear immediately
        base = todoist_web_url.rstrip("&").rstrip("?")
        sep = "&" if "?" in base else "?"
        tabs.append(
            ("inbox", "Inbox", f"{base}{sep}action=web&view=inbox&embed=1", True)
        )
        tabs.append(
            ("commit", "@commit", f"{base}{sep}action=web&view=commit&embed=1", True)
        )
        tabs.append(("p1", "P1", f"{base}{sep}action=web&view=p1&embed=1", True))
        tabs.append(
            (
                "bestcase",
                "Best Case",
                f"{base}{sep}action=web&view=bestcase&embed=1",
                True,
            )
        )
    if calendar_url:
        tabs.append(("calendar", "Calendar", calendar_url, True))

    # Generate sidebar tab HTML
    sidebar_tabs_html = ""
    for i, (tid, label, _url, _preload) in enumerate(tabs):
        active = " active" if i == 0 else ""
        badge_text = str(starred_count) if tid == "starred" else "..."
        sidebar_tabs_html += (
            f'<div class="sidebar-tab{active}" id="tab-{tid}" '
            f'draggable="true" data-tab-id="{tid}" onclick="switchTab(\'{tid}\')">'
            f'<span class="tab-label">{label}</span>'
            f'<span class="badge" id="badge-{tid}">{badge_text}</span>'
            f"</div>"
        )

    # Generate iframe HTML
    iframes_html = ""
    for i, (tid, _label, url, preload) in enumerate(tabs):
        display = "" if i == 0 else "display:none;"
        src = url if preload else "about:blank"
        iframes_html += (
            f'<iframe id="frame-{tid}" src="{src}" style="{display}"'
            f' data-src="{url}"></iframe>'
        )

    # Build tab URLs JSON for lazy loading
    tab_urls_json = "{"
    tab_urls_json += ",".join(f'"{tid}":"{url}"' for tid, _label, url, _preload in tabs)
    tab_urls_json += "}"

    # Build tab IDs array for switching
    tab_ids_json = "[" + ",".join(f'"{tid}"' for tid, *_ in tabs) + "]"

    # Build mobile section picker dropdown items
    first_label = tabs[0][1] if tabs else "Dashboard"
    first_badge = str(starred_count) if tabs and tabs[0][0] == "starred" else "..."
    dropdown_items_html = ""
    for i, (tid, label, _url, _preload) in enumerate(tabs):
        active_cls = " active" if i == 0 else ""
        check = "&#10003;" if i == 0 else "&nbsp;&nbsp;&nbsp;"
        badge_init = str(starred_count) if tid == "starred" else "..."
        dropdown_items_html += (
            f'<div class="section-dropdown-item{active_cls}" data-tab-id="{tid}" '
            f"onclick=\"selectSection('{tid}')\">"
            f'<span class="section-dropdown-check">{check}</span>'
            f'<span class="section-dropdown-label">{label}</span>'
            f'<span class="badge section-dropdown-badge" id="dpbadge-{tid}">{badge_init}</span>'
            f"</div>"
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
        "<title>Dashboard</title>"
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
        "body{font-family:" + _FONT + ";background:var(--bg-base);"
        "-webkit-font-smoothing:antialiased;}"
        ".header{background:var(--bg-s0);border-bottom:1px solid var(--border);padding:14px 20px;display:flex;"
        "align-items:center;justify-content:space-between;}"
        ".header-title{color:var(--text-1);font-size:17px;font-weight:600;letter-spacing:-0.2px;}"
        ".refresh-btn{background:var(--border);border:1px solid var(--border);color:var(--text-1);"
        "font-size:13px;font-weight:600;padding:6px 14px;border-radius:6px;cursor:pointer;}"
        ".refresh-btn:hover{background:var(--border-h);}"
        ".app-body{display:flex;height:calc(100vh - 48px);overflow:hidden;}"
        ".sidebar{width:180px;min-width:180px;background:var(--bg-s0);"
        "border-right:1px solid var(--border);display:flex;flex-direction:column;"
        "overflow-y:auto;user-select:none;}"
        ".sidebar-tab{display:flex;align-items:center;justify-content:space-between;"
        "padding:14px 16px;font-size:14px;font-weight:600;color:var(--text-2);"
        "cursor:pointer;border-left:3px solid transparent;transition:all .15s ease-out;}"
        ".sidebar-tab:hover{background:var(--bg-s2);}"
        ".sidebar-tab.active{color:var(--text-1);background:var(--accent-hbg);border-left-color:var(--accent);}"
        ".badge{display:inline-block;background:var(--border);color:var(--text-2);font-size:11px;"
        "font-weight:700;padding:2px 8px;border-radius:10px;}"
        ".sidebar-tab.active .badge{background:var(--accent-bg);color:var(--accent-l);}"
        ".sidebar-tab.dragging{opacity:0.4;}"
        ".sidebar-tab.drag-over{border-top:2px solid var(--accent);}"
        ".tab-label-input{font:inherit;font-size:14px;font-weight:600;width:80px;"
        "border:1px solid var(--accent);border-radius:3px;padding:1px 4px;outline:none;"
        "background:var(--bg-s2);color:var(--text-1);}"
        ".main-content{flex:1;position:relative;overflow:hidden;}"
        ".main-content iframe{display:block;position:absolute;top:0;left:0;width:100%;height:100%;"
        "border:none;}"
        # Section picker (mobile header button) — hidden on desktop
        ".section-picker{display:none;align-items:center;gap:8px;background:var(--bg-s2);"
        "border:1px solid var(--border-h);border-radius:8px;padding:7px 12px 7px 14px;"
        "cursor:pointer;touch-action:manipulation;}"
        ".section-picker-label{font-size:14px;font-weight:600;color:var(--text-1);}"
        ".section-picker-chevron{font-size:11px;color:var(--text-2);margin-left:2px;}"
        # Dropdown container — anchored below header
        ".section-dropdown{display:none;position:fixed;top:49px;left:0;right:0;z-index:9999;"
        "background:var(--bg-s1);border-bottom:1px solid var(--border-h);"
        "box-shadow:0 8px 32px rgba(0,0,0,.4);"
        "overflow-y:auto;max-height:calc(100dvh - 56px);}"
        ".section-dropdown.open{display:block;animation:ddSlide .15s ease;}"
        "@keyframes ddSlide{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}"
        ".section-dropdown-item{display:flex;align-items:center;gap:12px;padding:15px 20px;"
        "font-size:15px;font-weight:500;color:var(--text-2);cursor:pointer;"
        "border-bottom:1px solid var(--border);touch-action:manipulation;}"
        ".section-dropdown-item:last-child{border-bottom:none;}"
        ".section-dropdown-item.active{color:var(--text-1);background:var(--accent-hbg);}"
        ".section-dropdown-check{width:20px;font-size:14px;color:var(--accent-l);flex-shrink:0;}"
        ".section-dropdown-label{flex:1;}"
        ".section-dropdown-badge{margin-left:auto;}"
        # Backdrop to close dropdown on tap-outside
        ".section-dropdown-backdrop{display:none;position:fixed;inset:0;z-index:9998;}"
        ".section-dropdown-backdrop.open{display:block;}"
        "@media(max-width:768px){"
        ".section-picker{display:flex;}"
        ".sidebar{display:none!important;}"
        ".app-body{flex-direction:column;}"
        ".main-content{flex:1;height:100%;}"
        "}"
        "::-webkit-scrollbar{width:6px;}"
        "::-webkit-scrollbar-track{background:transparent;}"
        "::-webkit-scrollbar-thumb{background:var(--scrollbar);border-radius:3px;}"
        "</style>"
        "</head><body>"
        # Header (contains title + mobile section picker + refresh)
        '<div class="header">'
        '<span class="header-title">Dashboard</span>'
        # Mobile section picker button (hidden on desktop via CSS)
        + f'<button class="section-picker" id="section-picker" onclick="toggleSectionPicker()">'
        f'<span class="section-picker-label" id="section-picker-label">{first_label}</span>'
        f'<span class="badge" id="section-picker-badge">{first_badge}</span>'
        f'<span class="section-picker-chevron">&#9660;</span>'
        f"</button>"
        + '<button class="refresh-btn" onclick="refreshActive()">&#8635; Refresh</button>'
        "</div>"
        # App body: sidebar + main content
        '<div class="app-body">'
        '<div class="sidebar" id="sidebar">' + sidebar_tabs_html + "</div>"
        '<div class="main-content">' + iframes_html + "</div>"
        "</div>"
        # Backdrop and dropdown rendered as direct children of body (avoid iOS stacking issues)
        + '<div class="section-dropdown-backdrop" id="section-dropdown-backdrop" '
        'onclick="closeSectionPicker()"></div>'
        + '<div class="section-dropdown" id="section-dropdown">'
        + dropdown_items_html
        + "</div>"
        # JavaScript
        "<script>"
        "var activeTab='" + tabs[0][0] + "';"
        "var tabIds=" + tab_ids_json + ";"
        "var tabUrls=" + tab_urls_json + ";"
        "function switchTab(tab){"
        "if(tab===activeTab)return;"
        "activeTab=tab;"
        "tabIds.forEach(function(id){"
        "document.getElementById('tab-'+id).className='sidebar-tab'+(id===tab?' active':'');"
        "document.getElementById('frame-'+id).style.display=id===tab?'block':'none';"
        "});"
        "var frame=document.getElementById('frame-'+tab);"
        "if(frame&&frame.src.indexOf('about:blank')!==-1){"
        "frame.src=tabUrls[tab];"
        "}"
        # Sync the mobile section picker label/badge
        "var sidebarTab=document.getElementById('tab-'+tab);"
        "if(sidebarTab){"
        "var lbl=sidebarTab.querySelector('.tab-label');"
        "var bdg=sidebarTab.querySelector('.badge');"
        "var pl=document.getElementById('section-picker-label');"
        "var pb=document.getElementById('section-picker-badge');"
        "if(pl&&lbl)pl.textContent=lbl.textContent;"
        "if(pb&&bdg)pb.textContent=bdg.textContent;"
        "}"
        # Sync active state in dropdown
        "document.querySelectorAll('.section-dropdown-item').forEach(function(item){"
        "var isActive=item.getAttribute('data-tab-id')===tab;"
        "item.classList.toggle('active',isActive);"
        "item.querySelector('.section-dropdown-check').innerHTML=isActive?'&#10003;':'&nbsp;&nbsp;&nbsp;';"
        "});"
        "}"
        # Section picker open/close/select
        "function toggleSectionPicker(){"
        "var dd=document.getElementById('section-dropdown');"
        "var bd=document.getElementById('section-dropdown-backdrop');"
        "var isOpen=dd.classList.contains('open');"
        "dd.classList.toggle('open',!isOpen);"
        "bd.classList.toggle('open',!isOpen);"
        "}"
        "function closeSectionPicker(){"
        "document.getElementById('section-dropdown').classList.remove('open');"
        "document.getElementById('section-dropdown-backdrop').classList.remove('open');"
        "}"
        "function selectSection(tab){"
        "closeSectionPicker();"
        "switchTab(tab);"
        "}"
        "function refreshActive(){"
        "var frame=document.getElementById('frame-'+activeTab);"
        "if(frame){frame.contentWindow.location.reload();}"
        "}"
        "window.addEventListener('message',function(e){"
        "if(e.data&&e.data.type==='count'){"
        "var badge=document.getElementById('badge-'+e.data.source);"
        "if(badge){badge.textContent=e.data.count;}"
        # Also sync the dropdown badge and, if this is the active tab, the picker badge
        "var dpBadge=document.getElementById('dpbadge-'+e.data.source);"
        "if(dpBadge){dpBadge.textContent=e.data.count;}"
        "if(e.data.source===activeTab){"
        "var pb=document.getElementById('section-picker-badge');"
        "if(pb)pb.textContent=e.data.count;"
        "}"
        "}"
        "if(e.data&&e.data.type==='viewer-open'){closeSectionPicker();}"
        "});"
        # Drag-and-drop tab reordering
        "function initDragDrop(){"
        "document.querySelectorAll('.sidebar-tab').forEach(function(tab){"
        "tab.addEventListener('dragstart',function(e){"
        "e.dataTransfer.setData('text/plain',tab.getAttribute('data-tab-id'));"
        "tab.classList.add('dragging');});"
        "tab.addEventListener('dragend',function(){"
        "tab.classList.remove('dragging');"
        "document.querySelectorAll('.sidebar-tab').forEach(function(t){"
        "t.classList.remove('drag-over');});});"
        "tab.addEventListener('dragover',function(e){"
        "e.preventDefault();tab.classList.add('drag-over');});"
        "tab.addEventListener('dragleave',function(){"
        "tab.classList.remove('drag-over');});"
        "tab.addEventListener('drop',function(e){"
        "e.preventDefault();tab.classList.remove('drag-over');"
        "var fromId=e.dataTransfer.getData('text/plain');"
        "reorderTabs(fromId,tab.getAttribute('data-tab-id'));});});"
        "}"
        "function reorderTabs(fromId,beforeId){"
        "if(fromId===beforeId)return;"
        "var sidebar=document.getElementById('sidebar');"
        "var fromTab=document.querySelector('[data-tab-id=\"'+fromId+'\"]');"
        "var beforeTab=document.querySelector('[data-tab-id=\"'+beforeId+'\"]');"
        "if(fromTab&&beforeTab){sidebar.insertBefore(fromTab,beforeTab);saveTabOrder();}"
        "}"
        "function saveTabOrder(){"
        "var order=[];"
        "document.querySelectorAll('.sidebar-tab').forEach(function(tab){"
        "order.push(tab.getAttribute('data-tab-id'));});"
        "localStorage.setItem('dashboard_tab_order',JSON.stringify(order));"
        "}"
        "function restoreTabOrder(){"
        "try{"
        "var saved=localStorage.getItem('dashboard_tab_order');"
        "if(!saved)return;"
        "var order=JSON.parse(saved);"
        "var sidebar=document.getElementById('sidebar');"
        "order.forEach(function(tabId){"
        "var tab=document.querySelector('[data-tab-id=\"'+tabId+'\"]');"
        "if(tab)sidebar.appendChild(tab);});"
        "}catch(e){}}"
        "restoreTabOrder();"
        "initDragDrop();"
        # Double-click to rename tab labels, persisted in localStorage
        "function initRename(){"
        "document.querySelectorAll('.tab-label').forEach(function(lbl){"
        "lbl.addEventListener('dblclick',function(e){"
        "e.stopPropagation();"
        "var tab=lbl.closest('.sidebar-tab');"
        "var tabId=tab.getAttribute('data-tab-id');"
        "var inp=document.createElement('input');"
        "inp.className='tab-label-input';"
        "inp.value=lbl.textContent;"
        "lbl.style.display='none';"
        "lbl.parentNode.insertBefore(inp,lbl);"
        "inp.focus();inp.select();"
        "function commit(){"
        "var val=inp.value.trim();"
        "if(val){lbl.textContent=val;saveTabNames();}"
        "lbl.style.display='';inp.remove();"
        "}"
        "inp.addEventListener('blur',commit);"
        "inp.addEventListener('keydown',function(ke){"
        "if(ke.key==='Enter'){ke.preventDefault();inp.blur();}"
        "if(ke.key==='Escape'){inp.value=lbl.textContent;inp.blur();}"
        "});"
        "});});}"
        "function saveTabNames(){"
        "var names={};"
        "document.querySelectorAll('.sidebar-tab').forEach(function(tab){"
        "var id=tab.getAttribute('data-tab-id');"
        "var lbl=tab.querySelector('.tab-label');"
        "if(lbl)names[id]=lbl.textContent;"
        "});"
        "localStorage.setItem('dashboard_tab_names',JSON.stringify(names));"
        "}"
        "function restoreTabNames(){"
        "try{"
        "var saved=localStorage.getItem('dashboard_tab_names');"
        "if(!saved)return;"
        "var names=JSON.parse(saved);"
        "Object.keys(names).forEach(function(id){"
        "var tab=document.querySelector('[data-tab-id=\"'+id+'\"]');"
        "if(tab){var lbl=tab.querySelector('.tab-label');"
        "if(lbl)lbl.textContent=names[id];}"
        "});"
        "}catch(e){}}"
        "restoreTabNames();"
        "initRename();"
        "</script>"
        "</body></html>"
    )


def get_parameter(param_name: str, decrypt: bool = True) -> str:
    """Get parameter from AWS Parameter Store."""
    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=decrypt)
        return response["Parameter"]["Value"]
    except Exception as e:
        logger.error(f"Failed to get parameter {param_name}: {str(e)}")
        raise


def _load_calendar_reviewed_state() -> dict:
    """Load calendar reviewed state from S3."""
    try:
        obj = _s3.get_object(
            Bucket=os.environ.get("STATE_BUCKET", "gmail-email-actions"),
            Key=CALENDAR_STATE_KEY,
        )
        return json.loads(obj["Body"].read())
    except Exception:
        return {"reviews": {}}


def _save_calendar_reviewed_state(state: dict) -> None:
    """Persist calendar reviewed state to S3."""
    _s3.put_object(
        Bucket=os.environ.get("STATE_BUCKET", "gmail-email-actions"),
        Key=CALENDAR_STATE_KEY,
        Body=json.dumps(state),
        ContentType="application/json",
    )


def _is_event_reviewed(event_id: str, state: dict) -> bool:
    """Return True if the event was reviewed within the last 7 days."""
    ts = state.get("reviews", {}).get(event_id)
    if not ts:
        return False
    try:
        reviewed_at = datetime.fromisoformat(ts)
        if reviewed_at.tzinfo is None:
            reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - reviewed_at).days < 7
    except Exception:
        return False


def _fetch_todoist_projects(todoist_token: str) -> list:
    """Return all Todoist projects as a list of dicts."""
    try:
        from todoist_service import EmailActionsTodoistService

        todoist = EmailActionsTodoistService(todoist_token)
        return todoist.get_all_projects()
    except Exception as e:
        logger.warning(f"Could not fetch Todoist projects: {e}")
        return []


def load_credentials():
    """Load all credentials from Parameter Store and set env vars / write temp files."""
    logger.info("Loading credentials from Parameter Store")

    # Gmail OAuth2 credentials JSON (base64-encoded)
    try:
        gmail_creds_b64 = get_parameter("/gmail-email-actions/gmail-credentials")
        gmail_creds = base64.b64decode(gmail_creds_b64).decode("utf-8")
        creds_path = "/tmp/gmail_credentials.json"
        with open(creds_path, "w") as f:
            f.write(gmail_creds)
        os.environ["GMAIL_CREDENTIALS_PATH"] = creds_path
        logger.info("Gmail credentials written to /tmp/gmail_credentials.json")
    except Exception as e:
        logger.error(f"Could not load Gmail credentials: {e}")
        raise

    # Gmail OAuth2 token (base64-encoded pickle)
    try:
        gmail_token_b64 = get_parameter("/gmail-email-actions/gmail-token")
        gmail_token = base64.b64decode(gmail_token_b64)
        token_path = "/tmp/gmail_token.pickle"
        with open(token_path, "wb") as f:
            f.write(gmail_token)
        os.environ["GMAIL_TOKEN_PATH"] = token_path
        logger.info("Gmail token written to /tmp/gmail_token.pickle")
    except Exception as e:
        logger.warning(f"Could not load Gmail token: {e}")

    # Todoist API token
    todoist_token = get_parameter("/gmail-email-actions/todoist-api-token")
    os.environ["TODOIST_API_TOKEN"] = todoist_token
    logger.info("Todoist API token loaded")

    # Report recipient email
    report_email = get_parameter("/gmail-email-actions/report-email", decrypt=False)
    os.environ["REPORT_EMAIL"] = report_email

    # SES sender email
    ses_sender = get_parameter("/gmail-email-actions/ses-sender-email", decrypt=False)
    os.environ["SES_SENDER_EMAIL"] = ses_sender

    # Action token (secret for authenticating Function URL action links)
    try:
        action_token = get_parameter("/gmail-email-actions/action-token")
        os.environ["ACTION_TOKEN"] = action_token
    except Exception as e:
        logger.warning(f"Could not load action-token: {e}")

    # Lambda Function URL (for embedding action links in digest)
    try:
        function_url = get_parameter("/gmail-email-actions/function-url", decrypt=False)
        os.environ["FUNCTION_URL"] = function_url
    except Exception as e:
        logger.warning(f"Could not load function-url: {e}")

    # Unread digest web URL (for tabbed container page)
    try:
        unread_web_url = get_parameter(
            "/gmail-email-actions/unread-web-url", decrypt=False
        )
        os.environ["UNREAD_WEB_URL"] = unread_web_url
    except Exception as e:
        logger.warning(f"Could not load unread-web-url: {e}")

    # Todoist actions web URL (for Todoist tabs in container page)
    try:
        todoist_web_url = get_parameter(
            "/gmail-email-actions/todoist-web-url", decrypt=False
        )
        os.environ["TODOIST_WEB_URL"] = todoist_web_url
    except Exception as e:
        logger.warning(f"Could not load todoist-web-url: {e}")

    # Calendar OAuth credentials (Node.js JSON format from brandon-family-calendar-reporting)
    try:
        os.environ["CALENDAR_CREDENTIALS_JSON"] = get_parameter(
            "/calendar-report/oauth-credentials"
        )
    except Exception as e:
        logger.warning(f"Could not load calendar credentials: {e}")

    try:
        os.environ["CALENDAR_TOKEN_JSON"] = get_parameter(
            "/calendar-report/oauth-token"
        )
    except Exception as e:
        logger.warning(f"Could not load calendar token: {e}")

    logger.info("All credentials loaded successfully")


def _is_function_url_event(event: dict) -> bool:
    """Detect a Lambda Function URL HTTP invocation."""
    return "requestContext" in event and "http" in event.get("requestContext", {})


def handle_action(event: dict) -> dict:
    """Handle an HTTP action request from a Function URL invocation."""
    params = event.get("queryStringParameters") or {}
    token = params.get("token", "")
    expected = os.environ.get("ACTION_TOKEN", "")

    if not expected or token != expected:
        logger.warning("Action request rejected: invalid token")
        return {"statusCode": 403, "body": "Forbidden"}

    action = params.get("action", "")
    msg_id = params.get("msg_id", "")

    from email_actions_main import run_rerun_digest, run_unstar

    if action == "unstar" and msg_id:
        logger.info(f"Action: unstar message {msg_id}")
        try:
            run_unstar(msg_id)
            body = _confirmation_page(
                "&#10003;",
                "Email Unstarred",
                "#34a853",
                "The email has been unstarred in Gmail and its Todoist task has been deleted.",
            )
        except Exception as e:
            logger.error(f"Unstar failed: {e}", exc_info=True)
            body = _confirmation_page(
                "&#10007;",
                "Error",
                "#d93025",
                f"Could not unstar email: {e}",
            )
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": body,
        }

    elif action == "rerun":
        logger.info("Action: rerun digest")
        try:
            result = run_rerun_digest()
            body = _confirmation_page(
                "&#8635;",
                "Digest Sent",
                "#34a853",
                f"A fresh digest with {result.get('open_tasks', '?')} task(s) has been sent.",
            )
        except Exception as e:
            logger.error(f"Rerun failed: {e}", exc_info=True)
            body = _confirmation_page(
                "&#10007;",
                "Error",
                "#d93025",
                f"Could not send digest: {e}",
            )
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": body,
        }

    elif action == "web":
        embed = params.get("embed", "") == "1"
        logger.info(f"Action: web digest page (embed={embed})")
        try:
            # Fetch Todoist projects for "Move to Todoist" dropdown
            todoist_token = os.environ.get("TODOIST_API_TOKEN", "")
            todoist_projects = _fetch_todoist_projects(todoist_token)

            if embed:
                # Embedded mode: return starred list without header
                from email_actions_main import get_open_tasks_for_web
                from email_report import build_web_html

                tasks = get_open_tasks_for_web()
                function_url = os.environ.get("FUNCTION_URL", "")
                body = build_web_html(
                    tasks,
                    function_url=function_url,
                    action_token=expected,
                    embed=True,
                    projects=todoist_projects,
                )
            else:
                # Container mode: tabbed page with iframes for starred + unread + todoist + calendar
                unread_web_url = os.environ.get("UNREAD_WEB_URL", "")
                if unread_web_url:
                    from email_actions_main import get_open_tasks_for_web

                    tasks = get_open_tasks_for_web()
                    starred_count = len(tasks)
                    function_url = os.environ.get("FUNCTION_URL", "")
                    starred_embed_url = (
                        function_url.rstrip("/")
                        + "?action=web&embed=1&token="
                        + expected
                    )
                    unread_embed_url = unread_web_url + "&embed=1"
                    todoist_web_url = os.environ.get("TODOIST_WEB_URL", "")
                    calendar_url = (
                        function_url.rstrip("/")
                        + "?action=calendar&embed=1&token="
                        + expected
                    )
                    body = _build_container_html(
                        starred_embed_url,
                        unread_embed_url,
                        starred_count,
                        todoist_web_url=todoist_web_url,
                        calendar_url=calendar_url,
                    )
                else:
                    # Fallback: no unread URL configured, show standalone starred page
                    from email_actions_main import get_open_tasks_for_web
                    from email_report import build_web_html

                    tasks = get_open_tasks_for_web()
                    function_url = os.environ.get("FUNCTION_URL", "")
                    body = build_web_html(
                        tasks,
                        function_url=function_url,
                        action_token=expected,
                        projects=todoist_projects,
                    )
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "text/html",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                },
                "body": body,
            }
        except Exception as e:
            logger.error(f"Web digest failed: {e}", exc_info=True)
            body = _confirmation_page(
                "&#10007;",
                "Error",
                "#d93025",
                f"Could not load web digest: {e}",
            )
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": body,
            }

    elif action == "set_due_date":
        task_id = params.get("task_id", "")
        date = params.get("date", "")
        if not task_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": "Missing task_id"}),
            }
        logger.info(f"Action: set_due_date task={task_id} date={date}")
        try:
            from todoist_service import EmailActionsTodoistService

            todoist_token = os.environ.get("TODOIST_API_TOKEN", "")
            todoist = EmailActionsTodoistService(todoist_token)
            ok = todoist.update_due_date(task_id, date)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": ok}),
            }
        except Exception as e:
            logger.error(f"Set due date failed: {e}", exc_info=True)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": str(e)}),
            }

    elif action == "set_priority":
        task_id = params.get("task_id", "")
        priority = params.get("priority", "")
        if not task_id or not priority:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {"ok": False, "error": "Missing task_id or priority"}
                ),
            }
        logger.info(f"Action: set_priority task={task_id} priority={priority}")
        try:
            from todoist_service import EmailActionsTodoistService

            todoist_token = os.environ.get("TODOIST_API_TOKEN", "")
            todoist = EmailActionsTodoistService(todoist_token)
            ok = todoist.update_priority(task_id, int(priority))
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": ok}),
            }
        except Exception as e:
            logger.error(f"Set priority failed: {e}", exc_info=True)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": str(e)}),
            }

    elif action == "move_to_project":
        task_id = params.get("task_id", "")
        project_id = params.get("project_id", "")
        move_msg_id = params.get("msg_id", "")
        if not task_id or not project_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {"ok": False, "error": "Missing task_id or project_id"}
                ),
            }
        logger.info(
            f"Action: move_to_project task={task_id} project={project_id} msg={move_msg_id}"
        )
        try:
            from todoist_service import EmailActionsTodoistService

            todoist_token = os.environ.get("TODOIST_API_TOKEN", "")
            todoist = EmailActionsTodoistService(todoist_token)
            ok = todoist.move_task(task_id, project_id)
            # Also unstar the email in Gmail
            if ok and move_msg_id:
                try:
                    from email_actions_main import run_unstar

                    run_unstar(move_msg_id)
                except Exception as ue:
                    logger.warning(f"Unstar after move failed: {ue}")
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": ok}),
            }
        except Exception as e:
            logger.error(f"Move to project failed: {e}", exc_info=True)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": str(e)}),
            }

    elif action == "create_filter":
        from_email = params.get("from_email", "")
        if not from_email:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": "missing from_email"}),
            }
        logger.info(f"Action: create_filter from={from_email}")
        try:
            from gmail_service import GmailService

            gmail = GmailService()
            gmail.create_skip_inbox_filter(from_email)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": True}),
            }
        except Exception as e:
            logger.error(f"create_filter failed: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": str(e)}),
            }

    elif action == "open":
        thread_id = params.get("thread_id", "")
        open_msg_id = params.get("msg_id", "")
        embed = params.get("embed", "") == "1"
        lookup_id = open_msg_id or thread_id
        if lookup_id:
            try:
                from gmail_service import GmailService

                gmail = GmailService()
                content = gmail.get_message_content(lookup_id)
                function_url = os.environ.get("FUNCTION_URL", "")
                body = _email_viewer_page(
                    content,
                    function_url=function_url,
                    action_token=expected,
                    embed=embed,
                )
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "text/html"},
                    "body": body,
                }
            except Exception as e:
                logger.error(f"Failed to fetch email content: {e}", exc_info=True)
                body = _confirmation_page(
                    "&#10007;",
                    "Error",
                    "#d93025",
                    f"Could not load email: {e}",
                )
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "text/html"},
                    "body": body,
                }
        return {"statusCode": 400, "body": "Bad Request"}

    elif action == "calendar":
        embed = params.get("embed", "") == "1"
        logger.info(f"Action: calendar tab (embed={embed})")
        try:
            from calendar_service import CalendarService
            from calendar_views import build_calendar_html

            service = CalendarService(
                os.environ.get("CALENDAR_CREDENTIALS_JSON", ""),
                os.environ.get("CALENDAR_TOKEN_JSON", ""),
            )
            events = service.get_upcoming_events()
            reviewed_state = _load_calendar_reviewed_state()
            function_url = os.environ.get("FUNCTION_URL", "")
            todoist_token = os.environ.get("TODOIST_API_TOKEN", "")
            projects = _fetch_todoist_projects(todoist_token)
            body = build_calendar_html(
                events, reviewed_state, function_url, expected, projects, embed=embed
            )
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "text/html",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                },
                "body": body,
            }
        except Exception as e:
            logger.error(f"Calendar tab failed: {e}", exc_info=True)
            body = _confirmation_page(
                "&#10007;",
                "Error",
                "#d93025",
                f"Could not load calendar: {e}",
            )
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": body,
            }

    elif action == "calendar_reviewed":
        event_id = params.get("event_id", "")
        if not event_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": "missing event_id"}),
            }
        logger.info(f"Action: calendar_reviewed event_id={event_id}")
        try:
            state = _load_calendar_reviewed_state()
            state.setdefault("reviews", {})[event_id] = datetime.now(
                timezone.utc
            ).isoformat()
            _save_calendar_reviewed_state(state)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": True}),
            }
        except Exception as e:
            logger.error(f"calendar_reviewed failed: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": str(e)}),
            }

    elif action == "calendar_create_todoist":
        event_title = params.get("event_title", "")
        event_date = params.get("event_date", "")
        event_location = params.get("event_location", "")
        event_id = params.get("event_id", "")
        project_id = params.get("project_id", "")
        due_date = params.get("due_date", "")
        priority = params.get("priority", "")

        if not event_title or not project_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {"ok": False, "error": "missing event_title or project_id"}
                ),
            }

        logger.info(
            f"Action: calendar_create_todoist event={event_title} project={project_id}"
        )
        try:
            import requests as _requests

            todoist_token = os.environ.get("TODOIST_API_TOKEN", "")
            task_content = event_title
            description_parts = []
            if event_date:
                description_parts.append(f"\U0001f4c5 Date: {event_date}")
            if event_location:
                description_parts.append(f"\U0001f4cd Location: {event_location}")
            if event_id:
                description_parts.append(f"\U0001f194 Calendar Event ID: {event_id}")

            payload: dict = {
                "content": task_content,
                "project_id": project_id,
            }
            if description_parts:
                payload["description"] = "\n".join(description_parts)
            if due_date:
                payload["due_date"] = due_date
            if priority:
                try:
                    payload["priority"] = int(priority)
                except ValueError:
                    pass

            resp = _requests.post(
                "https://api.todoist.com/api/v1/tasks",
                headers={
                    "Authorization": f"Bearer {todoist_token}",
                    "Content-Type": "application/json",
                    "X-Request-Id": str(__import__("uuid").uuid4()),
                },
                json=payload,
                timeout=10,
            )
            if resp.ok:
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"ok": True}),
                }
            else:
                logger.warning(
                    f"Todoist create task failed: {resp.status_code} {resp.text}"
                )
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"ok": False, "error": resp.text}),
                }
        except Exception as e:
            logger.error(f"calendar_create_todoist failed: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": str(e)}),
            }

    elif action == "calendar_commit":
        event_title = params.get("event_title", "")
        event_date = params.get("event_date", "")
        event_location = params.get("event_location", "")
        event_id = params.get("event_id", "")

        if not event_title:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": "missing event_title"}),
            }

        logger.info(f"Action: calendar_commit event={event_title}")
        try:
            import requests as _requests

            todoist_token = os.environ.get("TODOIST_API_TOKEN", "")
            _headers = {
                "Authorization": f"Bearer {todoist_token}",
                "Content-Type": "application/json",
            }

            # Find or create "Calendar Actions" project
            project_id = None
            proj_resp = _requests.get(
                "https://api.todoist.com/api/v1/projects",
                headers=_headers,
                params={"limit": 200},
                timeout=10,
            )
            if proj_resp.ok:
                for p in proj_resp.json().get("results", []):
                    if p.get("name") == "Calendar Actions":
                        project_id = p["id"]
                        break
            if not project_id:
                create_resp = _requests.post(
                    "https://api.todoist.com/api/v1/projects",
                    headers={
                        **_headers,
                        "X-Request-Id": str(__import__("uuid").uuid4()),
                    },
                    json={"name": "Calendar Actions"},
                    timeout=10,
                )
                if create_resp.ok:
                    project_id = create_resp.json().get("id")
                    logger.info(f"Created 'Calendar Actions' project: {project_id}")
                else:
                    logger.error(f"Failed to create project: {create_resp.text}")

            description_parts = []
            if event_date:
                description_parts.append(f"\U0001f4c5 Date: {event_date}")
            if event_location:
                description_parts.append(f"\U0001f4cd Location: {event_location}")
            if event_id:
                description_parts.append(f"\U0001f194 Calendar Event ID: {event_id}")

            payload: dict = {
                "content": event_title,
                "labels": ["Commit"],
            }
            if project_id:
                payload["project_id"] = project_id
            if description_parts:
                payload["description"] = "\n".join(description_parts)
            # Set due datetime to 1:00 AM on event date
            if event_date:
                payload["due_datetime"] = f"{event_date[:10]}T01:00:00"

            resp = _requests.post(
                "https://api.todoist.com/api/v1/tasks",
                headers={**_headers, "X-Request-Id": str(__import__("uuid").uuid4())},
                json=payload,
                timeout=10,
            )
            if resp.ok:
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"ok": True}),
                }
            else:
                logger.warning(
                    f"Calendar commit task failed: {resp.status_code} {resp.text}"
                )
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"ok": False, "error": resp.text}),
                }
        except Exception as e:
            logger.error(f"calendar_commit failed: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": str(e)}),
            }

    elif action == "bestcase_label":
        task_id = params.get("task_id", "")
        if not task_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": "Missing task_id"}),
            }
        logger.info(f"Action: bestcase_label task={task_id}")
        try:
            from todoist_service import EmailActionsTodoistService

            todoist_token = os.environ.get("TODOIST_API_TOKEN", "")
            todoist = EmailActionsTodoistService(todoist_token)
            ok = todoist.bestcase_task(task_id)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": ok}),
            }
        except Exception as e:
            logger.error(f"bestcase_label failed: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": str(e)}),
            }

    else:
        return {"statusCode": 400, "body": "Bad Request"}


def lambda_handler(event, context):
    """Main Lambda handler.

    Handles:
    - Lambda Function URL HTTP requests (unstar / rerun actions)
    - EventBridge scheduled events with mode: 'sync' or 'daily_digest'
    """
    logger.info("=" * 60)
    logger.info("GMAIL EMAIL ACTIONS LAMBDA - Starting")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 60)

    try:
        load_credentials()

        if _is_function_url_event(event):
            logger.info("Detected Function URL event — routing to handle_action")
            return handle_action(event)

        mode = event.get("mode", "sync")
        dry_run = event.get("dry_run", False)

        from email_actions_main import run_daily_digest, run_sync

        if mode == "daily_digest":
            logger.info("Running in daily_digest mode")
            function_url = os.environ.get("FUNCTION_URL", "")
            action_token = os.environ.get("ACTION_TOKEN", "")
            result = run_daily_digest(
                dry_run=dry_run, function_url=function_url, action_token=action_token
            )
        else:
            logger.info("Running in sync mode")
            result = run_sync(dry_run=dry_run)

        logger.info("=" * 60)
        logger.info(f"Completed successfully: {result}")
        logger.info("=" * 60)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Completed successfully", "result": result}),
        }

    except Exception as e:
        logger.error(f"Lambda failed: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Failed: {str(e)}"}),
        }


if __name__ == "__main__":
    # Local test
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["sync", "daily_digest"], default="sync")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = lambda_handler({"mode": args.mode, "dry_run": args.dry_run}, None)
    print(json.dumps(result, indent=2))
