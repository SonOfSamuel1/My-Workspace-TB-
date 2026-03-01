"""ActionOS — Unified Lambda handler.

Single Lambda serving all ActionOS routes:

Web views (GET, token required):
  ?action=web                          → ActionOS shell (sidebar + iframes)
  ?action=web&view=home&embed=1        → Home (aggregated sections)
  ?action=web&view=starred&embed=1     → Starred email cards
  ?action=web&view=unread&embed=1      → Unread email cards
  ?action=web&view=inbox&embed=1       → Todoist Inbox
  ?action=web&view=commit&embed=1      → Todoist @commit (today)
  ?action=web&view=p1&embed=1          → Todoist P1 (today)
  ?action=web&view=bestcase&embed=1    → Todoist Best Case (today)
  ?action=web&view=calendar&embed=1    → Calendar events

Email actions (GET, token required):
  ?action=open&msg_id=X                → Email viewer page
  ?action=markread&msg_id=X            → Mark unread email as read
  ?action=unstar&msg_id=X              → Unstar starred email
  ?action=create_filter&from_email=X   → Gmail skip-inbox filter

Todoist actions (GET, token required):
  ?action=move&task_id=X&project_id=Y
  ?action=priority&task_id=X&priority=N
  ?action=complete&task_id=X
  ?action=reopen&task_id=X
  ?action=due_date&task_id=X&date=YYYY-MM-DD
  ?action=commit_label&task_id=X
  ?action=bestcase_label&task_id=X
  ?action=remove_commit&task_id=X
  ?action=remove_bestcase&task_id=X

Todoist create/update (POST, token required):
  ?action=create_task                  → Create new Todoist task
  ?action=update_task                  → Update task title/description
  ?action=create_todoist               → Create Todoist task from email

Home actions (GET, token required):
  ?action=home_reviewed&section=X&item_id=Y

Calendar actions (GET/POST, token required):
  ?action=calendar_reviewed&event_id=X
  ?action=calendar_create_todoist      → Add calendar event as Todoist task
  ?action=calendar_commit              → Commit calendar event as Todoist task
  ?action=calendar_save_checklist      → Save checklist content (POST)

Starred email actions (POST, token required):
  ?action=starred_to_todoist           → Create Todoist task from starred email

Search (GET, token required):
  ?action=search&q=X                   → Search tasks + calendar events

Misc (GET, token required):
  ?action=toggl_start                  → Start Toggl timer (POST body)

Scheduled (EventBridge):
  mode=sync        → Poll Gmail unread, update S3 state
  mode=daily_digest → Send daily email digest
"""

import base64
import hmac
import html
import json
import logging
import os
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import boto3

ssm = boto3.client("ssm", region_name="us-east-1")
_s3 = boto3.client("s3", region_name="us-east-1")

CALENDAR_STATE_BUCKET = os.environ.get("STATE_BUCKET", "gmail-unread-digest")
CALENDAR_STATE_KEY = "calendar_reviewed_state.json"
CHECKLIST_STATE_KEY = "actionos/calendar_checklists.json"
FOLLOWUP_STATE_KEY = "actionos/followup_state.json"
HOME_REVIEWED_STATE_KEY = "actionos/home_reviewed_state.json"

_PAGE_STYLE = (
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
    "background:#0e0e10;margin:0;padding:0;color-scheme:dark;"
)

_CARD_STYLE = (
    "max-width:480px;margin:80px auto;background:#1c1c1f;border-radius:8px;"
    "border:1px solid rgba(255,255,255,0.06);padding:40px;text-align:center;"
)


def _error_page(msg: str) -> str:
    """Styled error page that respects dark/light mode (no white flash)."""
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<style>"
        "html,body{margin:0;padding:0;"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
        "background:#1a1a1a;color:#8e8e93;color-scheme:dark;}"
        "@media(prefers-color-scheme:light){"
        "html,body{background:#eeeef0;color:#5f6368;color-scheme:light;}}"
        "p{padding:24px 20px;font-size:14px;}"
        "</style></head><body>"
        f"<p>{html.escape(str(msg))}</p>"
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _confirmation_page(
    icon_html: str, title: str, title_color: str, message: str
) -> str:
    """Build a confirmation page that auto-closes on desktop."""
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
        "style='display:inline-block;background:rgba(99,102,241,0.10);color:#818cf8;padding:12px 28px;"
        "border:1px solid rgba(99,102,241,0.20);border-radius:6px;text-decoration:none;font-size:15px;'>Back to Inbox</a>"
        "</div></body></html>"
    )


def _error_json(message: str) -> dict:
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"ok": False, "error": message}),
    }


def _ok_json(extra: dict = None) -> dict:
    body = {"ok": True}
    if extra:
        body.update(extra)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


# ---------------------------------------------------------------------------
# Session cookie helpers
# ---------------------------------------------------------------------------

_SESSION_COOKIE_NAME = "aos_session"
_SESSION_MAX_AGE = 604800  # 7 days


def _get_request_cookie(event: dict) -> str:
    """Extract aos_session cookie value from Lambda Function URL event headers."""
    headers = event.get("headers") or {}
    cookie_header = headers.get("cookie", "")  # Lambda lowercases header names
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith(_SESSION_COOKIE_NAME + "="):
            return part[len(_SESSION_COOKIE_NAME) + 1 :]
    return ""


def _is_valid_session(cookie_value: str, expected_token: str) -> bool:
    if not cookie_value or not expected_token:
        return False
    return hmac.compare_digest(cookie_value, expected_token)


def _make_session_cookie(token: str) -> str:
    return (
        f"{_SESSION_COOKIE_NAME}={token}; "
        f"HttpOnly; Secure; SameSite=Strict; Max-Age={_SESSION_MAX_AGE}; Path=/"
    )


def _login_page_html(function_url: str, error: str = "") -> str:
    """Minimal dark-theme login page matching ActionOS style."""
    import html as _html

    error_html = (
        f'<p style="color:#f87171;font-size:14px;margin:0 0 16px;">'
        f"{_html.escape(error)}</p>"
        if error
        else ""
    )
    form_action = _html.escape(
        (function_url.rstrip("/") + "?action=login")
        if function_url
        else "?action=login"
    )
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>ActionOS \u2014 Login</title>"
        "<style>"
        "*{box-sizing:border-box;}"
        "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
        "background:#0e0e10;margin:0;padding:0;display:flex;align-items:center;"
        "justify-content:center;min-height:100vh;color-scheme:dark;}"
        ".card{background:#1c1c1f;border:1px solid rgba(255,255,255,0.06);border-radius:8px;"
        "padding:40px;width:100%;max-width:360px;text-align:center;}"
        "h1{color:#f5f5f7;font-size:22px;margin:0 0 8px;}"
        "p.sub{color:#8b8b93;font-size:14px;margin:0 0 24px;}"
        "input[type=password]{width:100%;background:#2a2a2d;border:1px solid rgba(255,255,255,0.12);"
        "border-radius:6px;padding:10px 14px;color:#f5f5f7;font-size:15px;outline:none;"
        "margin-bottom:0;}"
        "input[type=password]:focus{border-color:rgba(99,102,241,0.6);}"
        "button{width:100%;margin-top:12px;background:rgba(99,102,241,0.85);color:#fff;"
        "border:none;border-radius:6px;padding:11px;font-size:15px;cursor:pointer;}"
        "button:hover{background:rgba(99,102,241,1);}"
        "</style>"
        "</head><body>"
        "<div class='card'>"
        "<h1>ActionOS</h1>"
        "<p class='sub'>Enter your access token to continue.</p>"
        + error_html
        + f"<form method='POST' action='{form_action}'>"
        "<input type='password' name='token' placeholder='Access token' autofocus required>"
        "<button type='submit'>Sign in</button>"
        "</form>"
        "</div></body></html>"
    )


def _sanitize_html(raw_html: str) -> str:
    """Strip dangerous tags and attributes from email HTML."""
    for tag in ("script", "style", "iframe", "object", "embed", "form"):
        raw_html = re.sub(
            rf"<{tag}[^>]*>.*?</{tag}>", "", raw_html, flags=re.DOTALL | re.IGNORECASE
        )
        raw_html = re.sub(rf"<{tag}[^>]*/?>", "", raw_html, flags=re.IGNORECASE)
    raw_html = re.sub(
        r"\s+on\w+\s*=\s*[\"'][^\"']*[\"']", "", raw_html, flags=re.IGNORECASE
    )
    raw_html = re.sub(r"\s+on\w+\s*=\s*\S+", "", raw_html, flags=re.IGNORECASE)
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
    import html as _html

    subject = _html.escape(content.get("subject", "(no subject)"))
    from_addr = _html.escape(content.get("from", ""))
    date = _html.escape(content.get("date", ""))
    msg_id = content.get("id", "")
    thread_id = content.get("threadId", "")

    body_html = content.get("body_html", "")
    body_text = content.get("body_text", "")
    if body_html:
        email_body = (
            '<div style="padding:16px;font-size:15px;line-height:1.6;overflow-x:auto;">'
            + _sanitize_html(body_html)
            + "</div>"
        )
    elif body_text:
        email_body = (
            '<pre style="white-space:pre-wrap;word-break:break-word;font-family:inherit;'
            'font-size:15px;line-height:1.6;padding:16px;margin:0;">'
            + _html.escape(body_text)
            + "</pre>"
        )
    else:
        email_body = '<p style="color:var(--text-3);padding:16px 0;">No message body available.</p>'

    # Extract sender email
    reply_email = from_addr
    email_match = re.search(r"<([^>]+)>", content.get("from", ""))
    if email_match:
        reply_email = _html.escape(email_match.group(1))
    reply_subject = _html.escape("Re: " + content.get("subject", ""))
    reply_url = f"mailto:{reply_email}?subject={reply_subject}"

    _FONT = "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif"

    # Build action buttons
    buttons_html = ""
    if function_url and action_token and msg_id:
        markread_url = function_url.rstrip("/") + "?action=markread&msg_id=" + msg_id
        unstar_url = function_url.rstrip("/") + "?action=unstar&msg_id=" + msg_id
        if embed:
            markread_success_js = (
                'btn.style.background=cv("--ok-bg");btn.style.color=cv("--ok");'
                'btn.innerHTML="\\u2713 Read";btn.style.cursor="default";'
                "setTimeout(function(){"
                "window.parent.postMessage({type:'markread',msgId:'"
                + msg_id
                + "'},'*');"
                "},800);"
            )
            unstar_success_js = (
                'btn.style.background=cv("--ok-bg");btn.style.color=cv("--ok");'
                'btn.innerHTML="\\u2713 Unstarred";btn.style.cursor="default";'
                "window.parent.postMessage({type:'unstar',msgId:'" + msg_id + "'},'*');"
            )
        else:
            markread_success_js = (
                'btn.style.background=cv("--ok-bg");btn.style.color=cv("--ok");'
                'btn.innerHTML="\\u2713 Read";btn.style.cursor="default";'
                "setTimeout(function(){window.location.href='"
                + function_url.rstrip("/")
                + "?action=web"
                + "';},800);"
            )
            unstar_success_js = (
                'btn.style.background=cv("--ok-bg");btn.style.color=cv("--ok");'
                'btn.innerHTML="\\u2713 Unstarred";btn.style.cursor="default";'
                "setTimeout(function(){window.location.href='"
                + function_url.rstrip("/")
                + "?action=web"
                + "';},800);"
            )

        buttons_html += (
            '<a id="markread-btn" href="#" onclick="doMarkRead(event)" '
            'style="display:inline-block;background:var(--ok-bg);color:var(--ok);'
            "padding:9px 16px;border:1px solid var(--ok-b);border-radius:8px;text-decoration:none;"
            'font-size:14px;font-weight:600;">Mark Read</a>'
            '<a id="unstar-btn" href="#" onclick="doUnstar(event)" '
            'style="display:inline-block;background:var(--err-bg);color:var(--err);'
            "padding:9px 16px;border:1px solid var(--err-b);border-radius:8px;text-decoration:none;"
            'font-size:14px;font-weight:600;">Unstar</a>'
        )

        import urllib.parse as _ul

        if reply_email:
            filter_url = (
                function_url.rstrip("/")
                + "?action=create_filter"
                + "&from_email="
                + _ul.quote(reply_email)
            )
            buttons_html += (
                '<a id="skip-inbox-btn" href="#" onclick="doSkipInbox(event)" '
                'style="display:inline-block;background:var(--warn-bg);color:var(--warn);'
                "padding:9px 16px;border:1px solid var(--warn-b);border-radius:8px;text-decoration:none;"
                'font-size:14px;font-weight:600;">Skip Inbox</a>'
            )

        buttons_html += (
            (
                "<script>"
                "var _cs=getComputedStyle(document.documentElement);function cv(n){return _cs.getPropertyValue(n).trim();}"
                "function doMarkRead(e){"
                "e.preventDefault();"
                "var btn=document.getElementById('markread-btn');"
                "btn.style.background=cv('--border');btn.style.pointerEvents='none';btn.innerHTML='Marking...';"
                "fetch('" + markread_url + "')"
                ".then(function(r){if(r.ok){" + markread_success_js + "}else{"
                "btn.innerHTML='Failed \u2013 retry';btn.style.pointerEvents='auto';"
                "}})"
                ".catch(function(){"
                "btn.innerHTML='Failed \u2013 retry';btn.style.pointerEvents='auto';"
                "});}"
                "function doUnstar(e){"
                "e.preventDefault();"
                "var btn=document.getElementById('unstar-btn');"
                "btn.style.background=cv('--border');btn.style.pointerEvents='none';btn.innerHTML='Unstarring...';"
                "fetch('" + unstar_url + "')"
                ".then(function(r){if(r.ok){" + unstar_success_js + "}else{"
                "btn.innerHTML='Failed \u2013 retry';btn.style.pointerEvents='auto';"
                "}})"
                ".catch(function(){"
                "btn.innerHTML='Failed \u2013 retry';btn.style.pointerEvents='auto';"
                "});}"
            )
            + (
                (
                    "function doSkipInbox(e){"
                    "e.preventDefault();"
                    "var btn=document.getElementById('skip-inbox-btn');"
                    "btn.style.background=cv('--border');btn.style.pointerEvents='none';btn.innerHTML='Creating filter\u2026';"
                    "fetch('" + filter_url + "')"
                    ".then(function(r){return r.json();})"
                    ".then(function(d){"
                    "if(d.ok){"
                    "btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
                    "btn.innerHTML='\u2713 Filter created';btn.style.cursor='default';"
                    "if(" + ("true" if embed else "false") + "){"
                    "window.parent.postMessage({type:'skip-inbox',msgId:'"
                    + msg_id
                    + "'},'*');"
                    "}"
                    "}else{"
                    "btn.style.background=cv('--warn-bg');btn.style.color=cv('--warn');"
                    "btn.innerHTML='Failed \u2013 retry';btn.style.pointerEvents='auto';"
                    "}})"
                    ".catch(function(){"
                    "btn.style.background=cv('--warn-bg');btn.style.color=cv('--warn');"
                    "btn.innerHTML='Failed \u2013 retry';btn.style.pointerEvents='auto';"
                    "});}"
                )
                if reply_email
                else ""
            )
            + "</script>"
        )

    gmail_link = ""
    if thread_id:
        gmail_url = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"
        gmail_link = (
            '<a href="' + gmail_url + '" target="_blank" rel="noopener" '
            'style="color:var(--accent-l);font-size:13px;text-decoration:underline;">View in Gmail</a>'
        )

    header_bar = ""
    if not embed:
        header_bar = (
            '<div style="background:var(--bg-s0);border-bottom:1px solid var(--border);padding:18px 20px;">'
            '<span style="color:var(--text-1);font-size:17px;font-weight:600;">'
            '<svg style="display:inline-block;vertical-align:middle" width="16" height="16" '
            'viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="1.5" y="3" width="13" height="10" rx="1.5"/>'
            '<path d="M1.5 4.5L8 9l6.5-4.5"/></svg>'
            " Email Viewer</span>"
            "</div>"
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
        "</style>"
        "</head>"
        '<body style="font-family:'
        + _FONT
        + ';background:var(--bg-base);margin:0;padding:0;">'
        + header_bar
        + '<div style="max-width:700px;margin:0 auto;padding:8px 10px;">'
        '<div style="background:var(--bg-s1);border-radius:8px;border:1px solid var(--border);">'
        '<div style="padding:16px;border-bottom:1px solid var(--border);">'
        '<h1 style="margin:0 0 12px;font-size:19px;color:var(--text-1);font-weight:600;font-family:'
        + _FONT
        + ';">'
        + subject
        + "</h1>"
        '<div style="font-size:13px;color:var(--text-2);">'
        '<strong style="color:var(--text-1);">From:</strong> ' + from_addr + "<br>"
        '<strong style="color:var(--text-1);">Date:</strong> ' + date + "</div></div>"
        '<div style="padding:12px 16px;border-bottom:1px solid var(--border);'
        'display:flex;gap:10px;flex-wrap:wrap;align-items:center;">'
        '<a href="'
        + reply_url
        + '" style="display:inline-block;background:var(--accent-bg);'
        "color:var(--accent-l);padding:9px 16px;border:1px solid var(--accent-b);border-radius:8px;"
        'text-decoration:none;font-size:14px;font-weight:600;">Reply</a>'
        + buttons_html
        + (
            '<span style="margin-left:auto;">' + gmail_link + "</span>"
            if gmail_link
            else ""
        )
        + "</div>"
        '<div style="padding:0;overflow:hidden;">'
        '<div style="background:#fff;padding:0;color:#202124;font-family:'
        + _FONT
        + ';">'
        "<style>"
        ".email-body{overflow:hidden;word-break:break-word;}"
        ".email-body *{font-family:"
        + _FONT
        + "!important;box-sizing:border-box!important;}"
        ".email-body h1{font-size:20px!important;margin:16px 0 8px!important;}"
        ".email-body h2{font-size:17px!important;margin:14px 0 6px!important;}"
        ".email-body h3{font-size:15px!important;margin:12px 0 4px!important;}"
        ".email-body p,.email-body td,.email-body li{font-size:14px!important;line-height:1.6!important;}"
        ".email-body table{width:100%!important;max-width:100%!important;border-collapse:collapse!important;height:auto!important;}"
        ".email-body td,.email-body th{width:auto!important;max-width:100%!important;}"
        ".email-body img{max-width:100%!important;height:auto!important;}"
        ".email-body [style]{max-width:100%!important;}"
        ".email-body div,.email-body span,.email-body section,.email-body article{max-width:100%!important;}"
        "</style>"
        '<div class="email-body">' + email_body + "</div></div></div>"
        "</div></div>"
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# Parameter Store
# ---------------------------------------------------------------------------


def get_parameter(param_name: str, decrypt: bool = True) -> str:
    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=decrypt)
        return response["Parameter"]["Value"]
    except Exception as e:
        logger.error(f"Failed to get parameter {param_name}: {str(e)}")
        raise


def load_credentials():
    """Load all credentials from /action-dashboard/ Parameter Store path."""
    logger.info("Loading credentials from Parameter Store")

    # Gmail credentials
    try:
        gmail_creds_b64 = get_parameter("/action-dashboard/gmail-credentials")
        gmail_creds = base64.b64decode(gmail_creds_b64).decode("utf-8")
        creds_path = "/tmp/gmail_credentials.json"
        with open(creds_path, "w") as f:
            f.write(gmail_creds)
        os.environ["GMAIL_CREDENTIALS_PATH"] = creds_path
    except Exception as e:
        logger.error(f"Could not load Gmail credentials: {e}")
        raise

    # Gmail token
    try:
        gmail_token_b64 = get_parameter("/action-dashboard/gmail-token")
        gmail_token = base64.b64decode(gmail_token_b64)
        token_path = "/tmp/gmail_token.pickle"
        with open(token_path, "wb") as f:
            f.write(gmail_token)
        os.environ["GMAIL_TOKEN_PATH"] = token_path
    except Exception as e:
        logger.warning(f"Could not load Gmail token: {e}")

    # Report / SES config
    os.environ["REPORT_EMAIL"] = get_parameter(
        "/action-dashboard/report-email", decrypt=False
    )
    os.environ["SES_SENDER_EMAIL"] = get_parameter(
        "/action-dashboard/ses-sender-email", decrypt=False
    )

    # Auth token + function URL
    try:
        os.environ["ACTION_TOKEN"] = get_parameter("/action-dashboard/action-token")
    except Exception as e:
        logger.warning(f"Could not load action-token: {e}")

    try:
        os.environ["FUNCTION_URL"] = get_parameter(
            "/action-dashboard/function-url", decrypt=False
        )
    except Exception as e:
        logger.warning(f"Could not load function-url: {e}")

    # Todoist
    try:
        os.environ["TODOIST_API_TOKEN"] = get_parameter(
            "/action-dashboard/todoist-api-token"
        )
    except Exception as e:
        logger.warning(f"Could not load todoist-api-token: {e}")

    # Toggl
    try:
        os.environ["TOGGL_API_TOKEN"] = get_parameter(
            "/action-dashboard/toggl-api-token"
        )
    except Exception as e:
        logger.warning(f"Could not load toggl-api-token: {e}")

    # Calendar credentials (Node.js JSON format)
    try:
        os.environ["CALENDAR_CREDENTIALS_JSON"] = get_parameter(
            "/action-dashboard/calendar-credentials"
        )
    except Exception as e:
        logger.warning(f"Could not load calendar credentials: {e}")

    try:
        os.environ["CALENDAR_TOKEN_JSON"] = get_parameter(
            "/action-dashboard/calendar-token"
        )
    except Exception as e:
        logger.warning(f"Could not load calendar token: {e}")

    # S3 state bucket
    try:
        os.environ["STATE_BUCKET"] = get_parameter(
            "/action-dashboard/state-bucket", decrypt=False
        )
    except Exception as e:
        logger.warning(f"Could not load state-bucket: {e}")

    logger.info("Credentials loaded successfully")


# ---------------------------------------------------------------------------
# Calendar state helpers
# ---------------------------------------------------------------------------


def _load_calendar_state() -> dict:
    try:
        bucket = os.environ.get("STATE_BUCKET", "gmail-unread-digest")
        obj = _s3.get_object(Bucket=bucket, Key=CALENDAR_STATE_KEY)
        return json.loads(obj["Body"].read())
    except Exception:
        return {"reviews": {}}


def _save_calendar_state(state: dict) -> None:
    bucket = os.environ.get("STATE_BUCKET", "gmail-unread-digest")
    _s3.put_object(
        Bucket=bucket,
        Key=CALENDAR_STATE_KEY,
        Body=json.dumps(state),
        ContentType="application/json",
    )


def _load_checklists() -> dict:
    try:
        bucket = os.environ.get("STATE_BUCKET", "gmail-unread-digest")
        obj = _s3.get_object(Bucket=bucket, Key=CHECKLIST_STATE_KEY)
        return json.loads(obj["Body"].read())
    except Exception:
        return {}


def _save_checklists(data: dict) -> None:
    bucket = os.environ.get("STATE_BUCKET", "gmail-unread-digest")
    _s3.put_object(
        Bucket=bucket,
        Key=CHECKLIST_STATE_KEY,
        Body=json.dumps(data),
        ContentType="application/json",
    )


# ---------------------------------------------------------------------------
# Follow-up state helpers
# ---------------------------------------------------------------------------


def _load_followup_state() -> dict:
    try:
        bucket = os.environ.get("STATE_BUCKET", "gmail-unread-digest")
        obj = _s3.get_object(Bucket=bucket, Key=FOLLOWUP_STATE_KEY)
        return json.loads(obj["Body"].read())
    except Exception:
        return {"emails": {}, "reviews": {}, "resolved": {}}


def _save_followup_state(state: dict) -> None:
    bucket = os.environ.get("STATE_BUCKET", "gmail-unread-digest")
    _s3.put_object(
        Bucket=bucket,
        Key=FOLLOWUP_STATE_KEY,
        Body=json.dumps(state),
        ContentType="application/json",
    )


# ---------------------------------------------------------------------------
# Home reviewed state helpers
# ---------------------------------------------------------------------------


def _load_home_reviewed_state() -> dict:
    """Load home review state from S3, pruning expired entries."""
    try:
        bucket = os.environ.get("STATE_BUCKET", "gmail-unread-digest")
        obj = _s3.get_object(Bucket=bucket, Key=HOME_REVIEWED_STATE_KEY)
        state = json.loads(obj["Body"].read())
    except Exception:
        state = {}

    # Prune expired entries
    now = datetime.now(timezone.utc)
    # Daily sections: expire after 2 days; 7-day sections: expire after 8 days
    daily_sections = {"commit", "bestcase", "starred", "inbox"}
    seven_day_sections = {"p1"}
    pruned = {}
    for section, items in state.items():
        if not isinstance(items, dict):
            continue
        max_age_days = (
            2
            if section in daily_sections
            else (8 if section in seven_day_sections else 2)
        )
        pruned_items = {}
        for item_id, ts in items.items():
            try:
                reviewed_at = datetime.fromisoformat(ts)
                if reviewed_at.tzinfo is None:
                    reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
                if (now - reviewed_at).days < max_age_days:
                    pruned_items[item_id] = ts
            except Exception:
                pass
        if pruned_items:
            pruned[section] = pruned_items
    return pruned


def _save_home_reviewed_state(state: dict) -> None:
    bucket = os.environ.get("STATE_BUCKET", "gmail-unread-digest")
    _s3.put_object(
        Bucket=bucket,
        Key=HOME_REVIEWED_STATE_KEY,
        Body=json.dumps(state),
        ContentType="application/json",
    )


# ---------------------------------------------------------------------------
# Todoist helpers
# ---------------------------------------------------------------------------


def _fetch_todoist_projects(todoist_token: str) -> list:
    try:
        from todoist_service import TodoistService

        return TodoistService(todoist_token).get_all_projects()
    except Exception as e:
        logger.warning(f"Could not fetch Todoist projects: {e}")
        return []


def _fetch_toggl_projects(toggl_token: str) -> list:
    try:
        import base64 as _b64

        import requests as _req

        _auth = _b64.b64encode(f"{toggl_token}:api_token".encode()).decode()
        _th = {"Authorization": f"Basic {_auth}", "Content-Type": "application/json"}
        _mr = _req.get(
            "https://api.track.toggl.com/api/v9/me?with_related_data=true",
            headers=_th,
        )
        _mr.raise_for_status()
        _md = _mr.json()
        _wid = _md.get("default_workspace_id")
        return [
            {"id": p.get("id"), "name": p.get("name", ""), "workspace_id": _wid}
            for p in _md.get("projects", [])
            if p.get("active", True)
        ]
    except Exception as e:
        logger.warning(f"Could not fetch Toggl projects: {e}")
        return []


# ---------------------------------------------------------------------------
# Function URL detection
# ---------------------------------------------------------------------------


def _is_function_url_event(event: dict) -> bool:
    return "requestContext" in event and "http" in event.get("requestContext", {})


# ---------------------------------------------------------------------------
# Main action router
# ---------------------------------------------------------------------------


_SERVICE_WORKER_JS = """\
self.addEventListener('push', function(e) {
  var d = {};
  try { d = e.data.json(); } catch(err) { d = { title: 'ActionOS', body: e.data ? e.data.text() : '' }; }
  e.waitUntil(self.registration.showNotification(d.title || 'ActionOS', {
    body: d.body || '',
    icon: d.icon || '',
    data: { url: d.url || '/' },
    requireInteraction: false,
    vibrate: [100, 50, 100]
  }));
});
self.addEventListener('notificationclick', function(e) {
  e.notification.close();
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(cs) {
      for (var i = 0; i < cs.length; i++) {
        if ('focus' in cs[i]) return cs[i].focus();
      }
      return clients.openWindow(e.notification.data.url || '/');
    })
  );
});
self.addEventListener('install', function() { self.skipWaiting(); });
self.addEventListener('activate', function(e) { e.waitUntil(clients.claim()); });
"""


def handle_action(event: dict) -> dict:
    """Route an HTTP request to the appropriate handler."""
    params = event.get("queryStringParameters") or {}

    # -----------------------------------------------------------------------
    # Service worker — no auth required (static JS, no sensitive data)
    # -----------------------------------------------------------------------
    if params.get("action") == "sw":
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/javascript; charset=utf-8",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Service-Worker-Allowed": "/",
            },
            "body": _SERVICE_WORKER_JS,
        }

    # -----------------------------------------------------------------------
    # Login route — no auth required
    # -----------------------------------------------------------------------
    if params.get("action") == "login":
        _fu = os.environ.get("FUNCTION_URL", "")
        _expected = os.environ.get("ACTION_TOKEN", "")
        _method = (
            (event.get("requestContext") or {})
            .get("http", {})
            .get("method", "GET")
            .upper()
        )
        if _method == "POST":
            _raw_body = event.get("body") or ""
            if event.get("isBase64Encoded"):
                _raw_body = base64.b64decode(_raw_body).decode("utf-8")
            _form = urllib.parse.parse_qs(_raw_body)
            _submitted = _form.get("token", [""])[0]
            if _expected and hmac.compare_digest(_submitted, _expected):
                _redir = _fu.rstrip("/") + "?action=web"
                return {
                    "statusCode": 302,
                    "headers": {
                        "Location": _redir,
                        "Set-Cookie": _make_session_cookie(_expected),
                        "Cache-Control": "no-store",
                    },
                    "body": "",
                }
            else:
                logger.warning("Login attempt failed: invalid token")
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "text/html",
                        "Cache-Control": "no-store",
                    },
                    "body": _login_page_html(
                        _fu, error="Invalid token. Please try again."
                    ),
                }
        else:
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html", "Cache-Control": "no-store"},
                "body": _login_page_html(_fu),
            }

    # -----------------------------------------------------------------------
    # Auth check — cookie or token param
    # -----------------------------------------------------------------------
    expected = os.environ.get("ACTION_TOKEN", "")
    cookie_value = _get_request_cookie(event)
    token_param = params.get("token", "")

    cookie_valid = _is_valid_session(cookie_value, expected)
    token_valid = bool(expected and token_param) and hmac.compare_digest(
        token_param, expected
    )

    if not cookie_valid and not token_valid:
        logger.warning("Action request rejected: no valid session")
        _action_check = params.get("action", "")
        _api_actions = {
            "create_task",
            "update_task",
            "create_todoist",
            "subscribe",
            "notify_test",
            "move",
            "priority",
            "complete",
            "reopen",
            "due_date",
            "commit_label",
            "bestcase_label",
            "remove_commit",
            "remove_bestcase",
            "markread",
            "unstar",
            "create_filter",
            "calendar_reviewed",
            "calendar_save_checklist",
            "calendar_create_todoist",
            "calendar_commit",
            "toggl_start",
            "starred_to_todoist",
            "followup_reviewed",
            "followup_resolved",
            "task_comments",
            "count_all",
            "backlog_label",
            "remove_backlog",
            "search",
        }
        if _action_check in _api_actions:
            return {"statusCode": 403, "body": "Forbidden"}
        _login_url = os.environ.get("FUNCTION_URL", "").rstrip("/") + "?action=login"
        return {
            "statusCode": 302,
            "headers": {"Location": _login_url, "Cache-Control": "no-store"},
            "body": "",
        }

    # Lazy migration: valid token param, no cookie → upgrade GET navigation requests
    if token_valid and not cookie_valid:
        _method = (
            (event.get("requestContext") or {})
            .get("http", {})
            .get("method", "GET")
            .upper()
        )
        _action_nav = params.get("action", "")
        if _method == "GET" and _action_nav in ("web", "open", ""):
            _fu = os.environ.get("FUNCTION_URL", "")
            _new_params = {k: v for k, v in params.items() if k != "token"}
            _qs = "&".join(
                f"{urllib.parse.quote(str(k))}={urllib.parse.quote(str(v))}"
                for k, v in _new_params.items()
            )
            _redir = _fu.rstrip("/") + ("?" + _qs if _qs else "?action=web")
            return {
                "statusCode": 302,
                "headers": {
                    "Location": _redir,
                    "Set-Cookie": _make_session_cookie(expected),
                    "Cache-Control": "no-store",
                },
                "body": "",
            }
        # Non-navigation requests (email digest action links) — allow through as-is

    action = params.get("action", "")
    function_url = os.environ.get("FUNCTION_URL", "")
    todoist_token = os.environ.get("TODOIST_API_TOKEN", "")

    logger.info(
        f"Handling action={action} view={params.get('view', '')} embed={params.get('embed', '')}"
    )

    # -----------------------------------------------------------------------
    # Shell: action=web (no embed) → render ActionOS shell
    # -----------------------------------------------------------------------
    if action == "web" and not params.get("embed"):
        view = params.get("view", "")
        if not view:
            # Top-level shell page
            try:
                from dashboard_shell import build_shell_html
                from gmail_service import GmailService

                projects = _fetch_todoist_projects(todoist_token)
                try:
                    gmail = GmailService()
                    starred = gmail.get_starred_emails()
                    starred_count = len(starred)
                except Exception as _e:
                    logger.warning(f"Could not fetch starred count: {_e}")
                    starred_count = 0

                try:
                    from push_service import get_vapid_public_key

                    vapid_public_key = get_vapid_public_key() or ""
                except Exception as _pe:
                    logger.warning(f"Could not load VAPID key: {_pe}")
                    vapid_public_key = ""

                body = build_shell_html(
                    function_url=function_url,
                    action_token=expected,
                    starred_count=starred_count,
                    projects=projects,
                    vapid_public_key=vapid_public_key,
                )
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "text/html",
                        "Cache-Control": "no-cache",
                    },
                    "body": body,
                }
            except Exception as e:
                logger.error(f"Shell build failed: {e}", exc_info=True)
                body = _confirmation_page(
                    "&#10007;", "Error", "#d93025", f"Could not load ActionOS: {e}"
                )
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "text/html"},
                    "body": body,
                }

    # -----------------------------------------------------------------------
    # Embedded views: action=web&embed=1&view=X
    # -----------------------------------------------------------------------
    if action == "web" and params.get("embed") == "1":
        view = params.get("view", "unread")

        # -- Starred email cards --
        if view == "starred":
            try:
                from email_report import build_web_html
                from gmail_service import GmailService

                gmail = GmailService()
                starred = gmail.get_starred_emails()
                projects = _fetch_todoist_projects(todoist_token)
                toggl_projects = _fetch_toggl_projects(
                    os.environ.get("TOGGL_API_TOKEN", "")
                )
                body = build_web_html(
                    starred,
                    function_url=function_url,
                    action_token=expected,
                    embed=True,
                    projects=projects,
                    toggl_projects=toggl_projects,
                    view_type="starred",
                )
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "text/html",
                        "Cache-Control": "private, max-age=30",
                    },
                    "body": body,
                }
            except Exception as e:
                logger.error(f"Starred view failed: {e}", exc_info=True)
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "text/html"},
                    "body": _error_page(f"Error: {e}"),
                }

        # -- Unread email cards --
        elif view == "unread":
            try:
                from email_report import build_web_html
                from unread_main import get_unread_emails_for_web

                emails = get_unread_emails_for_web()
                projects = _fetch_todoist_projects(todoist_token)
                toggl_projects = _fetch_toggl_projects(
                    os.environ.get("TOGGL_API_TOKEN", "")
                )
                body = build_web_html(
                    emails,
                    function_url=function_url,
                    action_token=expected,
                    embed=True,
                    projects=projects,
                    toggl_projects=toggl_projects,
                )
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "text/html",
                        "Cache-Control": "private, max-age=30",
                    },
                    "body": body,
                }
            except Exception as e:
                logger.error(f"Unread view failed: {e}", exc_info=True)
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "text/html"},
                    "body": _error_page(f"Error: {e}"),
                }

        elif view == "home":
            try:
                from calendar_service import CalendarService
                from gmail_service import GmailService
                from home_views import build_home_html
                from todoist_service import TodoistService

                service = TodoistService(todoist_token)
                cal = CalendarService(
                    os.environ["CALENDAR_CREDENTIALS_JSON"],
                    os.environ["CALENDAR_TOKEN_JSON"],
                )
                gmail = GmailService()
                today_str = datetime.now().strftime("%Y-%m-%d")

                with ThreadPoolExecutor(max_workers=8) as ex:
                    f_projects = ex.submit(service.get_all_projects)
                    f_commit = ex.submit(service.get_tasks_by_label, "Commit")
                    f_bestcase = ex.submit(service.get_tasks_by_label, "Best Case")
                    f_p1 = ex.submit(service.get_tasks_by_priority, 4)
                    f_inbox = ex.submit(service.get_inbox_tasks)
                    f_calendar = ex.submit(cal.get_upcoming_events, 90)
                    f_starred = ex.submit(gmail.get_starred_emails)
                    f_unread = ex.submit(
                        lambda: __import__("unread_main").get_unread_emails_for_web()
                    )

                projects = f_projects.result()

                # Filter Todoist tasks to due <= today
                def _due_today(tasks):
                    return [
                        t
                        for t in tasks
                        if t.get("due") and t["due"].get("date", "")[:10] <= today_str
                    ]

                def _due_today_or_undated(tasks):
                    """Include tasks due today/overdue AND tasks with no date."""
                    return [
                        t
                        for t in tasks
                        if not t.get("due")
                        or t["due"].get("date", "")[:10] <= today_str
                    ]

                commit_tasks = _due_today_or_undated(f_commit.result())
                bestcase_tasks = _due_today(f_bestcase.result())
                p1_tasks = _due_today(f_p1.result())
                inbox_tasks = f_inbox.result()
                calendar_events = f_calendar.result()
                starred_emails = f_starred.result()
                try:
                    unread_emails = f_unread.result()
                except Exception:
                    unread_emails = []

                # Follow-up emails from S3 state
                fu_state = _load_followup_state()
                # Inject threadId from dict key for backwards compat
                followup_emails = []
                for tid, edata in fu_state.get("emails", {}).items():
                    edata.setdefault("threadId", tid)
                    followup_emails.append(edata)

                home_state = _load_home_reviewed_state()
                cal_state = _load_calendar_state()

                body = build_home_html(
                    commit_tasks=commit_tasks,
                    bestcase_tasks=bestcase_tasks,
                    calendar_events=calendar_events,
                    p1_tasks=p1_tasks,
                    starred_emails=starred_emails,
                    unread_emails=unread_emails,
                    followup_emails=followup_emails,
                    inbox_tasks=inbox_tasks,
                    projects=projects,
                    home_state=home_state,
                    cal_state=cal_state,
                    followup_state=fu_state,
                    function_url=function_url,
                    action_token=expected,
                    embed=True,
                )
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "text/html",
                        "Cache-Control": "private, max-age=30",
                    },
                    "body": body,
                }
            except Exception as e:
                logger.error(f"Home view failed: {e}", exc_info=True)
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "text/html"},
                    "body": _error_page(f"Error: {e}"),
                }

        # -- Todoist views (inbox / commit / p1 / bestcase) --
        elif view in ("inbox", "commit", "p1", "p1nodate", "bestcase", "sabbath"):
            try:
                from todoist_service import TodoistService
                from todoist_views import build_view_html

                service = TodoistService(todoist_token)
                today_str = datetime.now().strftime("%Y-%m-%d")

                if view == "inbox":
                    projects = service.get_all_projects()
                    tasks = service.get_inbox_tasks(projects=projects)
                    tasks.sort(
                        key=lambda t: t.get("created_at", "") or t.get("added_at", ""),
                        reverse=True,
                    )
                elif view == "commit":
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        projects_future = executor.submit(service.get_all_projects)
                        tasks_future = executor.submit(
                            service.get_tasks_by_label, "Commit"
                        )
                    projects = projects_future.result()
                    all_commit = tasks_future.result()
                    tasks = [
                        t
                        for t in all_commit
                        if not t.get("due")
                        or t["due"].get("date", "")[:10] <= today_str
                    ]
                elif view == "p1":
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        projects_future = executor.submit(service.get_all_projects)
                        tasks_future = executor.submit(service.get_tasks_by_priority, 4)
                    projects = projects_future.result()
                    all_p1 = tasks_future.result()
                    tasks = [
                        t
                        for t in all_p1
                        if t.get("due") and t["due"].get("date", "")[:10] <= today_str
                    ]
                    tasks.sort(
                        key=lambda t: t.get("created_at", "") or t.get("added_at", ""),
                        reverse=True,
                    )
                elif view == "p1nodate":
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        projects_future = executor.submit(service.get_all_projects)
                        tasks_future = executor.submit(service.get_tasks_by_priority, 4)
                    projects = projects_future.result()
                    all_p1 = tasks_future.result()
                    tasks = [t for t in all_p1 if not t.get("due")]
                    tasks.sort(
                        key=lambda t: t.get("created_at", "") or t.get("added_at", ""),
                        reverse=True,
                    )
                elif view == "bestcase":
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        projects_future = executor.submit(service.get_all_projects)
                        tasks_future = executor.submit(
                            service.get_tasks_by_label, "Best Case"
                        )
                    projects = projects_future.result()
                    all_bestcase = tasks_future.result()
                    tasks = [
                        t
                        for t in all_bestcase
                        if t.get("due") and t["due"].get("date", "")[:10] <= today_str
                    ]
                elif view == "sabbath":
                    tasks, projects = service.get_sabbath_tasks()
                    tasks.sort(
                        key=lambda t: t.get("created_at", "") or t.get("added_at", ""),
                        reverse=True,
                    )

                checklists = (
                    _load_checklists() if view == "commit" else None
                )
                body = build_view_html(
                    tasks,
                    projects,
                    view,
                    function_url,
                    expected,
                    embed=True,
                    checklists=checklists,
                )
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "text/html",
                        "Cache-Control": "private, max-age=30",
                    },
                    "body": body,
                }
            except Exception as e:
                logger.error(f"Todoist view={view} failed: {e}", exc_info=True)
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "text/html"},
                    "body": _error_page(f"Error: {e}"),
                }

        # -- Code Projects view --
        elif view == "code":
            try:
                from code_views import build_code_projects_html
                from todoist_service import TodoistService

                service = TodoistService(todoist_token)
                all_tasks, projects, cc_dev_project_ids = (
                    service.get_code_project_tasks()
                )

                # Split tasks into 4 buckets by label
                in_progress_tasks = []
                planned_tasks = []
                backlog_tasks = []
                issues_tasks = []
                for t in all_tasks:
                    labels = t.get("labels", [])
                    if "In Progress" in labels:
                        in_progress_tasks.append(t)
                    elif "Planned" in labels:
                        planned_tasks.append(t)
                    elif "Backlog" in labels:
                        backlog_tasks.append(t)
                    else:
                        issues_tasks.append(t)

                # Sort labelled sections by priority desc
                _pri_sort = lambda t: (
                    -t.get("priority", 1),
                    t.get("added_at", "") or "",
                )
                in_progress_tasks.sort(key=_pri_sort)
                planned_tasks.sort(key=_pri_sort)
                backlog_tasks.sort(key=_pri_sort)
                # Sort new issues by most recent first
                issues_tasks.sort(
                    key=lambda t: t.get("added_at", "") or "",
                    reverse=True,
                )

                body = build_code_projects_html(
                    issues_tasks,
                    in_progress_tasks,
                    planned_tasks,
                    backlog_tasks,
                    projects,
                    function_url,
                    expected,
                    embed=True,
                )
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "text/html",
                        "Cache-Control": "private, max-age=30",
                    },
                    "body": body,
                }
            except Exception as e:
                logger.error(f"Code projects view failed: {e}", exc_info=True)
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "text/html"},
                    "body": _error_page(f"Error: {e}"),
                }

        # -- Calendar view --
        elif view == "calendar":
            try:
                from calendar_service import CalendarService
                from calendar_views import build_calendar_html
                from todoist_service import TodoistService

                cal = CalendarService(
                    os.environ["CALENDAR_CREDENTIALS_JSON"],
                    os.environ["CALENDAR_TOKEN_JSON"],
                )
                # Auto-sync FFM events to Family calendar
                try:
                    cal.sync_ffm_to_family()
                except Exception as sync_err:
                    logger.warning(f"FFM auto-sync failed: {sync_err}")
                events = cal.get_upcoming_events(days=365)
                state = _load_calendar_state()
                projects = _fetch_todoist_projects(todoist_token)
                checklists = _load_checklists()
                body = build_calendar_html(
                    events,
                    state,
                    function_url,
                    expected,
                    projects,
                    embed=True,
                    checklists=checklists,
                )
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "text/html",
                        "Cache-Control": "private, max-age=30",
                    },
                    "body": body,
                }
            except Exception as e:
                logger.error(f"Calendar view failed: {e}", exc_info=True)
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "text/html"},
                    "body": _error_page(f"Error: {e}"),
                }

        # -- Follow-up view --
        elif view == "followup":
            try:
                from followup_views import build_followup_html

                fu_state = _load_followup_state()
                body = build_followup_html(
                    fu_state.get("emails", {}),
                    fu_state,
                    function_url,
                    expected,
                    embed=True,
                )
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "text/html",
                        "Cache-Control": "private, max-age=30",
                    },
                    "body": body,
                }
            except Exception as e:
                logger.error(f"Follow-up view failed: {e}", exc_info=True)
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "text/html"},
                    "body": _error_page(f"Error: {e}"),
                }

    # -----------------------------------------------------------------------
    # Email viewer
    # -----------------------------------------------------------------------
    elif action == "open":
        msg_id = params.get("msg_id", "") or params.get("thread_id", "")
        embed = params.get("embed", "") == "1"
        if msg_id:
            try:
                from gmail_service import GmailService

                gmail = GmailService()
                content = gmail.get_message_content(msg_id)
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
                logger.error(f"Email open failed: {e}", exc_info=True)
                body = _confirmation_page(
                    "&#10007;", "Error", "#d93025", f"Could not load email: {e}"
                )
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "text/html"},
                    "body": body,
                }
        return {"statusCode": 400, "body": "Bad Request"}

    # -----------------------------------------------------------------------
    # Email actions
    # -----------------------------------------------------------------------
    elif action == "markread":
        msg_id = params.get("msg_id", "")
        if not msg_id:
            return {"statusCode": 400, "body": "Missing msg_id"}
        try:
            from unread_main import run_mark_read

            run_mark_read(msg_id)
            return _ok_json()
        except Exception as e:
            logger.error(f"markread failed: {e}", exc_info=True)
            return _error_json(str(e))

    elif action == "unstar":
        msg_id = params.get("msg_id", "")
        if not msg_id:
            return {"statusCode": 400, "body": "Missing msg_id"}
        try:
            from gmail_service import GmailService

            gmail = GmailService()
            gmail.unstar_email(msg_id)
            return _ok_json()
        except Exception as e:
            logger.error(f"unstar failed: {e}", exc_info=True)
            return _error_json(str(e))

    elif action == "create_filter":
        import urllib.parse as _ul

        from_email = params.get("from_email", "")
        if not from_email:
            return _error_json("Missing from_email")
        try:
            from gmail_service import GmailService

            gmail = GmailService()
            gmail.create_skip_inbox_filter(from_email)
            return _ok_json()
        except Exception as e:
            if "Filter already exists" in str(e):
                return _ok_json()
            logger.error(f"create_filter failed: {e}", exc_info=True)
            return _error_json(str(e))

    # -----------------------------------------------------------------------
    # Todoist task actions
    # -----------------------------------------------------------------------
    elif action in (
        "move",
        "priority",
        "complete",
        "reopen",
        "due_date",
        "commit_label",
        "bestcase_label",
        "remove_commit",
        "remove_bestcase",
        "planned_label",
        "in_progress_label",
        "backlog_label",
        "remove_planned",
        "remove_in_progress",
        "remove_backlog",
    ):
        from todoist_service import TodoistService

        service = TodoistService(todoist_token)
        task_id = params.get("task_id", "")
        if not task_id:
            return _error_json("Missing task_id")

        try:
            if action == "move":
                project_id = params.get("project_id", "")
                ok = service.move_task(task_id, project_id)
            elif action == "priority":
                priority = params.get("priority", "")
                ok = service.update_priority(task_id, int(priority))
            elif action == "complete":
                ok = service.close_task(task_id)
            elif action == "reopen":
                ok = service.reopen_task(task_id)
            elif action == "due_date":
                date = params.get("date", "")
                ok = service.update_due_date(task_id, date)
            elif action == "commit_label":
                ok = service.commit_task(task_id)
            elif action == "bestcase_label":
                ok = service.bestcase_task(task_id)
            elif action == "remove_commit":
                ok = service.remove_commit_label(task_id)
            elif action == "remove_bestcase":
                ok = service.remove_bestcase_label(task_id)
            elif action == "planned_label":
                ok = service.planned_task(task_id)
            elif action == "in_progress_label":
                ok = service.in_progress_task(task_id)
            elif action == "backlog_label":
                ok = service.backlog_task(task_id)
            elif action == "remove_planned":
                ok = service.remove_planned_label(task_id)
            elif action == "remove_in_progress":
                ok = service.remove_in_progress_label(task_id)
            elif action == "remove_backlog":
                ok = service.remove_backlog_label(task_id)
            return _ok_json() if ok else _error_json("Action failed")
        except Exception as e:
            logger.error(f"Todoist action={action} failed: {e}", exc_info=True)
            return _error_json(str(e))

    # -----------------------------------------------------------------------
    # AJAX refresh — returns JSON {count, html} for card list swap
    # -----------------------------------------------------------------------
    elif action == "refresh_cards":
        view = params.get("view", "unread")
        try:
            from email_report import build_cards_html
            from gmail_service import GmailService

            if view == "starred":
                gmail = GmailService()
                emails = gmail.get_starred_emails()
            else:
                from unread_main import get_unread_emails_for_web

                emails = get_unread_emails_for_web()

            projects = _fetch_todoist_projects(todoist_token)
            toggl_projects = _fetch_toggl_projects(
                os.environ.get("TOGGL_API_TOKEN", "")
            )
            cards_html, count, _proj_opts = build_cards_html(
                emails,
                function_url,
                expected,
                projects,
                toggl_projects,
                view_type=view,
            )
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                },
                "body": json.dumps({"count": count, "html": cards_html}),
            }
        except Exception as e:
            logger.error(f"refresh_cards failed: {e}", exc_info=True)
            return _error_json(str(e))

    # -----------------------------------------------------------------------
    # Search — search Todoist tasks and calendar events
    # -----------------------------------------------------------------------
    elif action == "search":
        q = (params.get("q") or "").strip()
        if not q:
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                },
                "body": json.dumps({"tasks": [], "events": []}),
            }
        try:
            from calendar_service import CalendarService
            from todoist_service import TodoistService

            service = TodoistService(todoist_token)
            q_lower = q.lower()

            def _fetch_tasks():
                return service.get_all_tasks()

            def _fetch_events():
                try:
                    cal_service = CalendarService(
                        os.environ["CALENDAR_CREDENTIALS_JSON"],
                        os.environ["CALENDAR_TOKEN_JSON"],
                    )
                    return cal_service.get_upcoming_events_cached(days=90)
                except Exception as cal_err:
                    logger.warning(f"Calendar search failed: {cal_err}")
                    return []

            # Parallel fetch
            with ThreadPoolExecutor(max_workers=2) as pool:
                fut_tasks = pool.submit(_fetch_tasks)
                fut_events = pool.submit(_fetch_events)
                all_tasks = fut_tasks.result()
                all_events = fut_events.result()

            # Build project lookup for task project names
            projects = service.get_all_projects()
            proj_map = {p["id"]: p.get("name", "") for p in projects}

            # Filter tasks
            matched_tasks = []
            for t in all_tasks:
                content = (t.get("content") or "").lower()
                desc = (t.get("description") or "").lower()
                if q_lower in content or q_lower in desc:
                    due = t.get("due") or {}
                    matched_tasks.append(
                        {
                            "id": t.get("id", ""),
                            "content": t.get("content", ""),
                            "description": t.get("description", ""),
                            "priority": t.get("priority", 1),
                            "due_date": due.get("date", ""),
                            "labels": t.get("labels", []),
                            "project_name": proj_map.get(t.get("project_id"), ""),
                            "type": "task",
                        }
                    )
                if len(matched_tasks) >= 25:
                    break

            # Filter events
            matched_events = []
            for ev in all_events:
                title = (ev.get("title") or "").lower()
                loc = (ev.get("location") or "").lower()
                desc = (ev.get("description") or "").lower()
                if q_lower in title or q_lower in loc or q_lower in desc:
                    matched_events.append(
                        {
                            "id": ev.get("id", ""),
                            "title": ev.get("title", ""),
                            "start": ev.get("start", ""),
                            "end": ev.get("end", ""),
                            "location": ev.get("location", ""),
                            "is_all_day": ev.get("is_all_day", False),
                            "calendar_type": ev.get("calendar_type", ""),
                            "type": "event",
                        }
                    )
                if len(matched_events) >= 25:
                    break

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                },
                "body": json.dumps({"tasks": matched_tasks, "events": matched_events}),
            }
        except Exception as e:
            logger.error(f"search failed: {e}", exc_info=True)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"tasks": [], "events": []}),
            }

    # -----------------------------------------------------------------------
    # Badge count_all — returns JSON counts for all sidebar tabs
    # -----------------------------------------------------------------------
    elif action == "count_all":
        try:
            from datetime import date

            from todoist_service import TodoistService

            service = TodoistService(todoist_token)
            today = date.today().isoformat()

            def _count_today_or_overdue(tasks):
                return sum(
                    1
                    for t in tasks
                    if (t.get("due") or {}).get("date", "9999")[:10] <= today
                )

            def _count_today_overdue_or_undated(tasks):
                """Count tasks due today/overdue plus undated tasks."""
                return sum(
                    1
                    for t in tasks
                    if not t.get("due")
                    or t["due"].get("date", "")[:10] <= today
                )

            with ThreadPoolExecutor(max_workers=5) as ex:
                f_inbox = ex.submit(service.get_inbox_tasks)
                f_commit = ex.submit(service.get_tasks_by_label, "Commit")
                f_p1 = ex.submit(service.get_tasks_by_priority, 4)
                f_bc = ex.submit(service.get_tasks_by_label, "Best Case")
                f_code = ex.submit(service.get_code_project_tasks)

            code_tasks, _cp, _cc = f_code.result()
            # Only count untagged new issues for the badge
            _status_labels = {"Planned", "In Progress", "Backlog"}
            code_new_issues = [
                t
                for t in code_tasks
                if not _status_labels.intersection(t.get("labels", []))
            ]
            counts = {
                "inbox": len(f_inbox.result()),
                "commit": _count_today_overdue_or_undated(f_commit.result()),
                "p1": _count_today_or_overdue(f_p1.result()),
                "bestcase": _count_today_or_overdue(f_bc.result()),
                "code": len(code_new_issues),
            }
            # Home count: sum of all trackable sections (excludes inbox)
            counts["home"] = (
                counts.get("commit", 0)
                + counts.get("bestcase", 0)
                + counts.get("p1", 0)
            )

            # Unread count from S3 state
            try:
                import state_manager

                state_bucket = os.environ.get("STATE_BUCKET", "gmail-unread-digest")
                state = state_manager.load_state(state_bucket)
                counts["unread"] = len(state.get("emails", {}))
            except Exception:
                pass

            # Follow-up count from S3 state
            try:
                from datetime import timezone as _tz

                fu_state = _load_followup_state()
                fu_emails = fu_state.get("emails", {})
                fu_reviews = fu_state.get("reviews", {})
                fu_unreviewed = 0
                for tid in fu_emails:
                    ts = fu_reviews.get(tid)
                    if ts:
                        try:
                            reviewed_at = datetime.fromisoformat(ts)
                            if reviewed_at.tzinfo is None:
                                reviewed_at = reviewed_at.replace(tzinfo=_tz.utc)
                            if (datetime.now(_tz.utc) - reviewed_at).days < 7:
                                continue
                        except Exception:
                            pass
                    fu_unreviewed += 1
                counts["followup"] = fu_unreviewed
            except Exception:
                pass

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                },
                "body": json.dumps(counts),
            }
        except Exception as e:
            logger.error(f"count_all failed: {e}", exc_info=True)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": "{}",
            }

    # -----------------------------------------------------------------------
    # Todoist create_task / update_task (POST)
    # -----------------------------------------------------------------------
    elif action == "create_task":
        body_str = event.get("body", "")
        if event.get("isBase64Encoded"):
            body_str = base64.b64decode(body_str).decode("utf-8")
        try:
            post_data = json.loads(body_str) if body_str else {}
        except Exception:
            post_data = {}

        content = post_data.get("content", "")
        if not content:
            return _error_json("Missing content")

        try:
            from todoist_service import TodoistService

            service = TodoistService(todoist_token)
            task = service.create_task(
                content=content,
                project_id=post_data.get("project_id"),
                due_date=post_data.get("due_date"),
                priority=post_data.get("priority"),
                description=post_data.get("description"),
                labels=post_data.get("labels"),
            )
            if task:
                return _ok_json({"task": task})
            return _error_json("Create task failed")
        except Exception as e:
            logger.error(f"create_task failed: {e}", exc_info=True)
            return _error_json(str(e))

    elif action == "update_task":
        body_str = event.get("body", "")
        if event.get("isBase64Encoded"):
            body_str = base64.b64decode(body_str).decode("utf-8")
        try:
            post_data = json.loads(body_str) if body_str else {}
        except Exception:
            post_data = {}

        task_id = post_data.get("task_id", "")
        if not task_id:
            return _error_json("Missing task_id")

        try:
            from todoist_service import TodoistService

            service = TodoistService(todoist_token)
            ok = service.update_task(
                task_id=task_id,
                content=post_data.get("content"),
                description=post_data.get("description"),
            )
            return _ok_json() if ok else _error_json("Update failed")
        except Exception as e:
            logger.error(f"update_task failed: {e}", exc_info=True)
            return _error_json(str(e))

    elif action == "task_comments":
        task_id = params.get("task_id", "")
        if not task_id:
            return _error_json("Missing task_id")
        try:
            from todoist_service import TodoistService

            service = TodoistService(todoist_token)
            comments = service.get_task_comments(task_id)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": True, "comments": comments}),
            }
        except Exception as e:
            logger.error(f"task_comments failed: {e}", exc_info=True)
            return _error_json(str(e))

    # -----------------------------------------------------------------------
    # Create Todoist task from email
    # -----------------------------------------------------------------------
    elif action == "create_todoist":
        body_str = event.get("body", "")
        if event.get("isBase64Encoded"):
            body_str = base64.b64decode(body_str).decode("utf-8")
        try:
            post_data = json.loads(body_str) if body_str else {}
        except Exception:
            post_data = {}

        ct_msg_id = post_data.get("msg_id", params.get("msg_id", ""))
        ct_subject = post_data.get("subject", "")
        ct_from = post_data.get("from_addr", "")
        ct_project_id = post_data.get("project_id", params.get("project_id", ""))
        ct_gmail_link = post_data.get("gmail_link", "")
        ct_date = post_data.get("date", "")
        ct_due_date = post_data.get("due_date", "")
        ct_priority = post_data.get("priority", "")

        if not ct_project_id:
            return _error_json("Missing project_id")

        try:
            import requests as _req

            _headers = {
                "Authorization": f"Bearer {todoist_token}",
                "Content-Type": "application/json",
            }
            title = ct_subject if ct_subject else "Email task"
            if ct_from:
                title += f" \u2014 from {ct_from}"
            desc_parts = []
            if ct_from:
                desc_parts.append(f"**From:** {ct_from}")
            if ct_date:
                desc_parts.append(f"**Received:** {ct_date}")
            if ct_gmail_link:
                desc_parts.append(f"[Open in Gmail]({ct_gmail_link})")
            if ct_msg_id:
                desc_parts.append(f"**Msg ID:** {ct_msg_id}")
            task_json = {
                "content": title,
                "description": "\n".join(desc_parts),
                "project_id": ct_project_id,
                "labels": ["Email"],
            }
            if ct_due_date:
                task_json["due_date"] = ct_due_date
            if ct_priority:
                task_json["priority"] = int(ct_priority)
            _r = _req.post(
                "https://api.todoist.com/api/v1/tasks",
                headers=_headers,
                json=task_json,
            )
            _r.raise_for_status()

            if ct_msg_id:
                try:
                    from unread_main import run_mark_read

                    run_mark_read(ct_msg_id)
                except Exception as _me:
                    logger.warning(f"Mark read after create_todoist failed: {_me}")

            return _ok_json()
        except Exception as e:
            logger.error(f"create_todoist failed: {e}", exc_info=True)
            return _error_json(str(e))

    # -----------------------------------------------------------------------
    # Toggl timer
    # -----------------------------------------------------------------------
    elif action == "toggl_start":
        body_str = event.get("body", "")
        if event.get("isBase64Encoded"):
            body_str = base64.b64decode(body_str).decode("utf-8")
        try:
            post_data = json.loads(body_str) if body_str else {}
        except Exception:
            post_data = {}

        ts_subject = post_data.get("subject", "Email task")
        ts_project_id = post_data.get("project_id")
        ts_workspace_id = post_data.get("workspace_id")
        if not ts_workspace_id:
            return _error_json("Missing workspace_id")

        try:
            import base64 as _b64

            import requests as _req

            toggl_token = os.environ.get("TOGGL_API_TOKEN", "")
            _auth = _b64.b64encode(f"{toggl_token}:api_token".encode()).decode()
            _th = {
                "Authorization": f"Basic {_auth}",
                "Content-Type": "application/json",
            }
            timer_body = {
                "description": ts_subject,
                "workspace_id": int(ts_workspace_id),
                "start": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "duration": -1,
                "created_with": "actionos",
            }
            if ts_project_id:
                timer_body["project_id"] = int(ts_project_id)
            _r = _req.post(
                f"https://api.track.toggl.com/api/v9/workspaces/{ts_workspace_id}/time_entries",
                headers=_th,
                json=timer_body,
            )
            _r.raise_for_status()
            return _ok_json()
        except Exception as e:
            logger.error(f"toggl_start failed: {e}", exc_info=True)
            return _error_json(str(e))

    elif action == "home_reviewed":
        section = params.get("section", "")
        item_id = params.get("item_id", "")
        valid_sections = {"commit", "bestcase", "p1", "starred", "inbox"}
        if not section or section not in valid_sections:
            return _error_json("Invalid section")
        if not item_id:
            return _error_json("Missing item_id")
        try:
            state = _load_home_reviewed_state()
            state.setdefault(section, {})[item_id] = datetime.now(
                timezone.utc
            ).isoformat()
            _save_home_reviewed_state(state)
            return _ok_json()
        except Exception as e:
            logger.error(f"home_reviewed failed: {e}", exc_info=True)
            return _error_json(str(e))

    # -----------------------------------------------------------------------
    # Calendar actions
    # -----------------------------------------------------------------------
    elif action == "calendar_reviewed":
        event_id = params.get("event_id", "")
        if not event_id:
            return _error_json("Missing event_id")
        try:
            state = _load_calendar_state()
            state.setdefault("reviews", {})[event_id] = datetime.now(
                timezone.utc
            ).isoformat()
            _save_calendar_state(state)
            return _ok_json()
        except Exception as e:
            logger.error(f"calendar_reviewed failed: {e}", exc_info=True)
            return _error_json(str(e))

    elif action == "calendar_save_checklist":
        body_str = event.get("body", "")
        if event.get("isBase64Encoded"):
            body_str = base64.b64decode(body_str).decode("utf-8")
        try:
            post_data = json.loads(body_str) if body_str else {}
        except Exception:
            post_data = {}
        section = post_data.get("section", "")
        content = post_data.get("content", "")
        if not section:
            return _error_json("Missing section")
        try:
            checklists = _load_checklists()
            checklists[section] = content
            _save_checklists(checklists)
            return _ok_json()
        except Exception as e:
            logger.error(f"calendar_save_checklist failed: {e}", exc_info=True)
            return _error_json(str(e))

    elif action == "starred_to_todoist":
        body_str = event.get("body", "")
        if event.get("isBase64Encoded"):
            body_str = base64.b64decode(body_str).decode("utf-8")
        try:
            post_data = json.loads(body_str) if body_str else {}
        except Exception:
            post_data = {}

        mode = post_data.get("mode", "")  # inbox, bestcase, commit
        msg_id = post_data.get("msg_id", "")
        subject = post_data.get("subject", "")
        from_addr = post_data.get("from_addr", "")
        gmail_link = post_data.get("gmail_link", "")
        date_received = post_data.get("date", "")

        if not mode:
            return _error_json("Missing mode")

        try:
            import requests as _req
            from todoist_service import TodoistService

            service = TodoistService(todoist_token)

            title = subject if subject else "Email task"
            if from_addr:
                title += f" \u2014 from {from_addr}"
            desc_parts = []
            if from_addr:
                desc_parts.append(f"**From:** {from_addr}")
            if date_received:
                desc_parts.append(f"**Received:** {date_received}")
            if gmail_link:
                desc_parts.append(f"[Open in Gmail]({gmail_link})")

            today_str = datetime.now().strftime("%Y-%m-%d")

            _headers = {
                "Authorization": f"Bearer {todoist_token}",
                "Content-Type": "application/json",
            }

            if mode == "inbox":
                # Create task in Inbox
                inbox_ids = service.get_inbox_project_ids()
                project_id = inbox_ids[0] if inbox_ids else None
                task_json = {
                    "content": title,
                    "description": "\n".join(desc_parts),
                    "labels": ["Email"],
                }
                if project_id:
                    task_json["project_id"] = project_id
                _r = _req.post(
                    "https://api.todoist.com/api/v1/tasks",
                    headers=_headers,
                    json=task_json,
                )
                _r.raise_for_status()

            elif mode == "bestcase":
                # Create task, add Best Case + Email labels, set today due date
                task_json = {
                    "content": title,
                    "description": "\n".join(desc_parts),
                    "due_date": today_str,
                    "labels": ["Email"],
                }
                _r = _req.post(
                    "https://api.todoist.com/api/v1/tasks",
                    headers=_headers,
                    json=task_json,
                )
                _r.raise_for_status()
                created = _r.json()
                task_id = created.get("id", "")
                if task_id:
                    service.bestcase_task(task_id)

            elif mode == "commit":
                # Create task, add Commit + Email labels, set today due date
                task_json = {
                    "content": title,
                    "description": "\n".join(desc_parts),
                    "due_date": today_str,
                    "labels": ["Email"],
                }
                _r = _req.post(
                    "https://api.todoist.com/api/v1/tasks",
                    headers=_headers,
                    json=task_json,
                )
                _r.raise_for_status()
                created = _r.json()
                task_id = created.get("id", "")
                if task_id:
                    service.commit_task(task_id)

            else:
                return _error_json(f"Invalid mode: {mode}")

            # Mark email as read + unstar
            if msg_id:
                try:
                    from gmail_service import GmailService

                    gmail = GmailService()
                    gmail.unstar_email(msg_id)
                except Exception as _me:
                    logger.warning(f"Unstar after starred_to_todoist failed: {_me}")

            return _ok_json()
        except Exception as e:
            logger.error(f"starred_to_todoist failed: {e}", exc_info=True)
            return _error_json(str(e))

    elif action in ("calendar_create_todoist", "calendar_commit"):
        try:
            import requests as _req

            event_title = params.get("event_title", "Calendar Event")
            event_date = params.get("event_date", "")
            event_location = params.get("event_location", "")
            event_id = params.get("event_id", "")
            project_id = params.get("project_id", "")
            due_date = (
                (params.get("due_date", "") or event_date[:10]) if event_date else ""
            )
            priority = params.get("priority", "")

            _headers = {
                "Authorization": f"Bearer {todoist_token}",
                "Content-Type": "application/json",
            }
            desc_parts = []
            if event_date:
                desc_parts.append(f"**Date:** {event_date}")
            if event_location:
                desc_parts.append(f"**Location:** {event_location}")
            task_json = {
                "content": event_title,
                "description": "\n".join(desc_parts),
            }
            if project_id:
                task_json["project_id"] = project_id
            if due_date:
                task_json["due_date"] = due_date
            if priority:
                task_json["priority"] = int(priority)

            _r = _req.post(
                "https://api.todoist.com/api/v1/tasks",
                headers=_headers,
                json=task_json,
            )
            _r.raise_for_status()

            if action == "calendar_commit":
                from todoist_service import TodoistService

                svc = TodoistService(todoist_token)
                created = _r.json()
                svc.commit_task(created.get("id", ""))

                # Also mark event as reviewed
                if event_id:
                    state = _load_calendar_state()
                    state.setdefault("reviews", {})[event_id] = datetime.now(
                        timezone.utc
                    ).isoformat()
                    _save_calendar_state(state)

            return _ok_json()
        except Exception as e:
            logger.error(f"{action} failed: {e}", exc_info=True)
            return _error_json(str(e))

    # -----------------------------------------------------------------------
    # Follow-up actions
    # -----------------------------------------------------------------------
    elif action == "followup_reviewed":
        thread_id = params.get("thread_id", "")
        if not thread_id:
            return _error_json("Missing thread_id")
        try:
            fu_state = _load_followup_state()
            fu_state.setdefault("reviews", {})[thread_id] = datetime.now(
                timezone.utc
            ).isoformat()
            _save_followup_state(fu_state)
            return _ok_json()
        except Exception as e:
            logger.error(f"followup_reviewed failed: {e}", exc_info=True)
            return _error_json(str(e))

    elif action == "followup_resolved":
        thread_id = params.get("thread_id", "")
        if not thread_id:
            return _error_json("Missing thread_id")
        try:
            fu_state = _load_followup_state()
            fu_state.setdefault("resolved", {})[thread_id] = datetime.now(
                timezone.utc
            ).isoformat()
            fu_state.get("emails", {}).pop(thread_id, None)
            fu_state.get("reviews", {}).pop(thread_id, None)
            _save_followup_state(fu_state)
            return _ok_json()
        except Exception as e:
            logger.error(f"followup_resolved failed: {e}", exc_info=True)
            return _error_json(str(e))

    # -----------------------------------------------------------------------
    # Daily digest rerun
    # -----------------------------------------------------------------------
    elif action == "rerun":
        try:
            from unread_main import run_rerun_digest

            result = run_rerun_digest()
            body = _confirmation_page(
                "&#8635;",
                "Digest Sent",
                "#34a853",
                f"A fresh digest with {result.get('unread_emails', '?')} email(s) has been sent.",
            )
        except Exception as e:
            logger.error(f"rerun failed: {e}", exc_info=True)
            body = _confirmation_page(
                "&#10007;", "Error", "#d93025", f"Could not send digest: {e}"
            )
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": body,
        }

    # -----------------------------------------------------------------------
    # Push notifications
    # -----------------------------------------------------------------------
    elif action == "subscribe":
        body_str = event.get("body", "")
        if event.get("isBase64Encoded"):
            body_str = base64.b64decode(body_str).decode("utf-8")
        try:
            sub = json.loads(body_str) if body_str else {}
        except Exception:
            return _error_json("Invalid JSON")
        from push_service import store_subscription

        ok = store_subscription(sub)
        return _ok_json() if ok else _error_json("Failed to store subscription")

    elif action == "notify_test":
        from push_service import send_push

        ok = send_push("ActionOS", "Push notifications are working! 🎉", "/")
        return _ok_json() if ok else _error_json("Push failed — check subscription")

    else:
        return {"statusCode": 400, "body": "Bad Request"}


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------


def lambda_handler(event, context):
    """Main Lambda handler."""
    logger.info("=" * 60)
    logger.info("ACTION-DASHBOARD (ActionOS) - Starting")
    logger.info(f"Event keys: {list(event.keys())}")
    logger.info("=" * 60)

    try:
        load_credentials()

        if _is_function_url_event(event):
            logger.info("Detected Function URL event — routing to handle_action")
            return handle_action(event)

        # EventBridge scheduled invocation
        mode = event.get("mode", "sync")
        dry_run = event.get("dry_run", False)

        from unread_main import run_daily_digest, run_sync

        if mode == "daily_digest":
            logger.info("Running in daily_digest mode")
            result = run_daily_digest(
                dry_run=dry_run,
                function_url=os.environ.get("FUNCTION_URL", ""),
                action_token=os.environ.get("ACTION_TOKEN", ""),
            )
        else:
            logger.info("Running in sync mode")
            result = run_sync(dry_run=dry_run)

            from unread_main import run_followup_sync

            followup_result = run_followup_sync(dry_run=dry_run)
            logger.info(f"Followup sync: {followup_result}")

        logger.info(f"Completed: {result}")
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
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["sync", "daily_digest"], default="sync")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = lambda_handler({"mode": args.mode, "dry_run": args.dry_run}, None)
    print(json.dumps(result, indent=2))
