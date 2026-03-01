"""AWS Lambda handler for Gmail Unread Digest automation.

Two invocation modes:
- sync (every 5 min via EventBridge): polls Gmail unread primary emails, stores metadata in S3
- daily_digest (8 AM ET via EventBridge): sends HTML email digest of unread emails from S3 state
"""

import base64
import html
import json
import logging
import os
import re
import sys

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import boto3  # noqa: E402

ssm = boto3.client("ssm", region_name="us-east-1")

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
        "style='display:inline-block;background:rgba(99,102,241,0.10);color:#818cf8;padding:12px 28px;"
        "border:1px solid rgba(99,102,241,0.20);border-radius:6px;text-decoration:none;font-size:15px;'>Back to Inbox</a>"
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
        email_body = (
            '<p style="color:#888;padding:16px 0;">No message body available.</p>'
        )

    # Build action buttons
    # Reply via mailto (opens Gmail compose on iOS)
    reply_email = from_addr
    # Extract just the email address from "Name <email>" format
    email_match = re.search(r"<([^>]+)>", content.get("from", ""))
    if email_match:
        reply_email = html.escape(email_match.group(1))
    reply_subject = html.escape("Re: " + content.get("subject", ""))
    reply_url = f"mailto:{reply_email}?subject={reply_subject}"

    # Mark Read button — uses fetch() with inline animation instead of navigation
    markread_btn = ""
    if function_url and action_token and msg_id:
        markread_url = (
            function_url.rstrip("/")
            + "?action=markread&msg_id="
            + msg_id
            + "&token="
            + action_token
        )
        # In embed mode, notify parent frame after mark-read instead of navigating
        if embed:
            markread_success_js = (
                "btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
                "btn.innerHTML='\\u2713 Read';"
                "btn.style.cursor='default';"
                "setTimeout(function(){"
                "window.parent.postMessage({type:'markread',msgId:'"
                + msg_id
                + "'},'*');"
                "},800);"
            )
        else:
            markread_success_js = (
                "btn.style.background=cv('--ok-bg');btn.style.color=cv('--ok');"
                "btn.innerHTML='\\u2713 Read';"
                "btn.style.cursor='default';"
                "setTimeout(function(){window.location.href='"
                + function_url.rstrip("/")
                + "?action=web&token="
                + action_token
                + "';},800);"
            )
        markread_btn = (
            '<a id="markread-btn" href="#" onclick="doMarkRead(event)" '
            'style="display:inline-block;background:var(--ok-bg);'
            "color:var(--ok);padding:11px 24px;border:1px solid var(--ok-b);border-radius:8px;text-decoration:none;"
            "font-size:14px;font-weight:600;letter-spacing:-0.1px;"
            'transition:all .3s ease;">Mark Read</a>'
            "<script>"
            "var _cs=getComputedStyle(document.documentElement);function cv(n){return _cs.getPropertyValue(n).trim();}"
            "function doMarkRead(e){"
            "e.preventDefault();"
            'var btn=document.getElementById("markread-btn");'
            'btn.style.background=cv("--border");'
            'btn.style.pointerEvents="none";'
            'btn.innerHTML="Marking read\\u2026";'
            'fetch("' + markread_url + '")'
            ".then(function(r){"
            "if(r.ok){" + markread_success_js + "}else{"
            'btn.style.background=cv("--ok-bg");'
            'btn.innerHTML="Failed \\u2013 Tap to retry";'
            'btn.style.pointerEvents="auto";'
            "}"
            "})"
            ".catch(function(){"
            'btn.style.background=cv("--ok-bg");'
            'btn.innerHTML="Failed \\u2013 Tap to retry";'
            'btn.style.pointerEvents="auto";'
            "});"
            "}"
            "</script>"
        )

    # Gmail web fallback link
    gmail_web_url = ""
    if thread_id:
        gmail_web_url = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"

    gmail_link = ""
    if gmail_web_url:
        gmail_link = (
            '<a href="' + gmail_web_url + '" target="_blank" rel="noopener noreferrer" '
            'style="color:var(--accent-l);font-size:13px;'
            'text-decoration:underline;">View in Gmail</a>'
        )

    _FONT = "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif"
    _VIEWER_STYLE = (
        "font-family:" + _FONT + ";"
        "background:var(--bg-base);margin:0;padding:0;-webkit-font-smoothing:antialiased;"
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
        + (
            '<div style="background:var(--bg-s0);border-bottom:1px solid var(--border);padding:18px 20px;">'
            '<span style="color:var(--text-1);font-size:17px;font-weight:600;letter-spacing:-0.2px;">'
            "&#9993; Email Viewer</span>"
            "</div>"
            if not embed
            else ""
        )
        + '<div style="max-width:700px;margin:0 auto;background:var(--bg-s1);'
        'border:1px solid var(--border);">'
        '<div style="padding:20px 24px;border-bottom:1px solid var(--border);">'
        '<h1 style="margin:0 0 12px;font-size:19px;color:var(--text-1);font-weight:600;'
        'letter-spacing:-0.3px;line-height:1.35;">' + subject + "</h1>"
        '<div style="font-size:13px;color:var(--text-2);line-height:1.6;">'
        '<strong style="color:var(--text-1);">From:</strong> ' + from_addr + "<br>"
        '<strong style="color:var(--text-1);">Date:</strong> ' + date + "</div></div>"
        '<div style="padding:12px 24px;border-bottom:1px solid var(--border);'
        'display:flex;gap:12px;flex-wrap:wrap;align-items:center;">'
        '<a href="'
        + reply_url
        + '" style="display:inline-block;background:var(--accent-bg);'
        "color:var(--accent-l);padding:11px 24px;border:1px solid var(--accent-b);border-radius:8px;text-decoration:none;"
        'font-size:14px;font-weight:600;letter-spacing:-0.1px;">Reply</a>'
        + markread_btn
        + (
            ' <span style="margin-left:auto;">' + gmail_link + "</span>"
            if gmail_link
            else ""
        )
        + "</div>"
        '<div style="padding:0 24px 20px;">' + email_body + "</div>"
        "</div>"
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


def load_credentials():
    """Load all credentials from Parameter Store and set env vars / write temp files."""
    logger.info("Loading credentials from Parameter Store")

    # Gmail OAuth2 credentials JSON (base64-encoded)
    try:
        gmail_creds_b64 = get_parameter("/gmail-unread-digest/gmail-credentials")
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
        gmail_token_b64 = get_parameter("/gmail-unread-digest/gmail-token")
        gmail_token = base64.b64decode(gmail_token_b64)
        token_path = "/tmp/gmail_token.pickle"
        with open(token_path, "wb") as f:
            f.write(gmail_token)
        os.environ["GMAIL_TOKEN_PATH"] = token_path
        logger.info("Gmail token written to /tmp/gmail_token.pickle")
    except Exception as e:
        logger.warning(f"Could not load Gmail token: {e}")

    # Report recipient email
    report_email = get_parameter("/gmail-unread-digest/report-email", decrypt=False)
    os.environ["REPORT_EMAIL"] = report_email

    # SES sender email
    ses_sender = get_parameter("/gmail-unread-digest/ses-sender-email", decrypt=False)
    os.environ["SES_SENDER_EMAIL"] = ses_sender

    # Action token (secret for authenticating Function URL action links)
    try:
        action_token = get_parameter("/gmail-unread-digest/action-token")
        os.environ["ACTION_TOKEN"] = action_token
    except Exception as e:
        logger.warning(f"Could not load action-token: {e}")

    # Lambda Function URL (for embedding action links in digest)
    try:
        function_url = get_parameter("/gmail-unread-digest/function-url", decrypt=False)
        os.environ["FUNCTION_URL"] = function_url
    except Exception as e:
        logger.warning(f"Could not load function-url: {e}")

    # Todoist API token (for "Move to Todoist" feature)
    try:
        todoist_token = get_parameter("/gmail-unread-digest/todoist-api-token")
        os.environ["TODOIST_API_TOKEN"] = todoist_token
    except Exception as e:
        logger.warning(f"Could not load todoist-api-token: {e}")

    # Toggl API token (for "Start Toggl Timer" feature)
    try:
        toggl_token = get_parameter("/gmail-unread-digest/toggl-api-token")
        os.environ["TOGGL_API_TOKEN"] = toggl_token
    except Exception as e:
        logger.warning(f"Could not load toggl-api-token: {e}")

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

    from unread_main import run_mark_read, run_rerun_digest

    if action == "markread" and msg_id:
        logger.info(f"Action: mark read message {msg_id}")
        try:
            run_mark_read(msg_id)
            body = _confirmation_page(
                "&#10003;",
                "Email Marked as Read",
                "#34a853",
                "The email has been marked as read in Gmail.",
            )
        except Exception as e:
            logger.error(f"Mark read failed: {e}", exc_info=True)
            body = _confirmation_page(
                "&#10007;",
                "Error",
                "#d93025",
                f"Could not mark email as read: {e}",
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
                f"A fresh digest with {result.get('unread_emails', '?')} email(s) has been sent.",
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
        logger.info("Action: web digest page")
        try:
            from email_report import build_web_html
            from unread_main import get_unread_emails_for_web

            embed = params.get("embed", "") == "1"
            emails = get_unread_emails_for_web()
            function_url = os.environ.get("FUNCTION_URL", "")

            # Fetch Todoist projects for "Move to Todoist" dropdown
            todoist_projects = []
            todoist_token = os.environ.get("TODOIST_API_TOKEN", "")
            if todoist_token:
                try:
                    import requests as _req

                    _cursor = None
                    while True:
                        _params = {"limit": 50}
                        if _cursor:
                            _params["cursor"] = _cursor
                        _r = _req.get(
                            "https://api.todoist.com/api/v1/projects",
                            headers={
                                "Authorization": f"Bearer {todoist_token}",
                                "Content-Type": "application/json",
                            },
                            params=_params,
                        )
                        _r.raise_for_status()
                        _d = _r.json()
                        todoist_projects.extend(_d.get("results", []))
                        _cursor = _d.get("next_cursor")
                        if not _cursor:
                            break
                except Exception as _e:
                    logger.warning(f"Could not fetch Todoist projects: {_e}")

            # Fetch Toggl projects for "Start Toggl Timer" dropdown
            toggl_projects = []
            toggl_token = os.environ.get("TOGGL_API_TOKEN", "")
            if toggl_token:
                try:
                    import base64 as _b64

                    import requests as _req

                    _auth = _b64.b64encode(f"{toggl_token}:api_token".encode()).decode()
                    _th = {
                        "Authorization": f"Basic {_auth}",
                        "Content-Type": "application/json",
                    }
                    _mr = _req.get(
                        "https://api.track.toggl.com/api/v9/me?with_related_data=true",
                        headers=_th,
                    )
                    _mr.raise_for_status()
                    _md = _mr.json()
                    _wid = _md.get("default_workspace_id")
                    toggl_projects = [
                        {
                            "id": p.get("id"),
                            "name": p.get("name", ""),
                            "workspace_id": _wid,
                        }
                        for p in _md.get("projects", [])
                        if p.get("active", True)
                    ]
                except Exception as _e:
                    logger.warning(f"Could not fetch Toggl projects: {_e}")

            body = build_web_html(
                emails,
                function_url=function_url,
                action_token=expected,
                embed=embed,
                projects=todoist_projects,
                toggl_projects=toggl_projects,
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

    elif action == "create_todoist":
        # POST body contains: msg_id, subject, from, project_id, gmail_link
        body_str = event.get("body", "")
        if event.get("isBase64Encoded"):
            import base64 as _b64

            body_str = _b64.b64decode(body_str).decode("utf-8")
        try:
            import json as _json

            post_data = _json.loads(body_str) if body_str else {}
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
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": "Missing project_id"}),
            }

        logger.info(
            f"Action: create_todoist project={ct_project_id} msg={ct_msg_id} subject={ct_subject}"
        )
        try:
            import requests as _req

            todoist_token = os.environ.get("TODOIST_API_TOKEN", "")
            _headers = {
                "Authorization": f"Bearer {todoist_token}",
                "Content-Type": "application/json",
            }

            # Build task content and description
            title = f"[Action] {ct_subject}" if ct_subject else "[Action] Email task"
            if ct_from:
                title += f" — from {ct_from}"
            desc_parts = []
            if ct_from:
                desc_parts.append(f"\U0001f4e7 **From:** {ct_from}")
            if ct_date:
                desc_parts.append(f"\U0001f4c5 **Received:** {ct_date}")
            if ct_gmail_link:
                desc_parts.append(f"\U0001f517 [Open in Gmail]({ct_gmail_link})")
            if ct_msg_id:
                desc_parts.append(f"\U0001f194 **Msg ID:** {ct_msg_id}")
            description = "\n".join(desc_parts)

            task_json = {
                "content": title,
                "description": description,
                "project_id": ct_project_id,
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

            # Mark email as read in Gmail
            if ct_msg_id:
                try:
                    from unread_main import run_mark_read

                    run_mark_read(ct_msg_id)
                except Exception as mre:
                    logger.warning(f"Mark read after create_todoist failed: {mre}")

            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": True}),
            }
        except Exception as e:
            logger.error(f"Create todoist task failed: {e}", exc_info=True)
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
            # Treat "Filter already exists" as success
            if "Filter already exists" in str(e):
                logger.info(
                    f"Filter already exists for {from_email} — treating as success"
                )
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"ok": True}),
                }
            logger.error(f"create_filter failed: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": str(e)}),
            }

    elif action == "toggl_start":
        body_str = event.get("body", "")
        if event.get("isBase64Encoded"):
            import base64 as _b64

            body_str = _b64.b64decode(body_str).decode("utf-8")
        try:
            post_data = json.loads(body_str) if body_str else {}
        except Exception:
            post_data = {}

        ts_subject = post_data.get("subject", "Email task")
        ts_project_id = post_data.get("project_id")
        ts_workspace_id = post_data.get("workspace_id")

        if not ts_workspace_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": "Missing workspace_id"}),
            }

        try:
            import base64 as _b64
            from datetime import datetime, timezone

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
                "created_with": "action-dashboard",
            }
            if ts_project_id:
                timer_body["project_id"] = int(ts_project_id)
            _r = _req.post(
                f"https://api.track.toggl.com/api/v9/workspaces/{ts_workspace_id}/time_entries",
                headers=_th,
                json=timer_body,
            )
            _r.raise_for_status()
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": True}),
            }
        except Exception as e:
            logger.error(f"toggl_start failed: {e}", exc_info=True)
            return {
                "statusCode": 200,
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

    else:
        return {"statusCode": 400, "body": "Bad Request"}


def lambda_handler(event, context):
    """Main Lambda handler.

    Handles:
    - Lambda Function URL HTTP requests (markread / rerun actions)
    - EventBridge scheduled events with mode: 'sync' or 'daily_digest'
    """
    logger.info("=" * 60)
    logger.info("GMAIL UNREAD DIGEST LAMBDA - Starting")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 60)

    try:
        load_credentials()

        if _is_function_url_event(event):
            logger.info("Detected Function URL event — routing to handle_action")
            return handle_action(event)

        mode = event.get("mode", "sync")
        dry_run = event.get("dry_run", False)

        from unread_main import run_daily_digest, run_sync

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
