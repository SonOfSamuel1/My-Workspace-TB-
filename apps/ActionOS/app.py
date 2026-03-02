"""
app.py — Flask entry point for ActionOS on Railway.

Wraps the existing lambda_handler.handle_action() dispatcher so all
?action= routing continues to work unchanged.  APScheduler replaces
EventBridge for periodic jobs.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Path setup — src/ modules must be importable (same as Lambda's sys.path)
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# ---------------------------------------------------------------------------
# AWS credentials must be in env vars before boto3 clients are created at
# module-level inside lambda_handler.  Railway sets these via the dashboard.
# ---------------------------------------------------------------------------
from flask import Flask, make_response, redirect, request
from lambda_handler import (
    _get_home_html,
    _get_shell_data,
    _load_countdowns,
    _save_countdowns,
    handle_action,
    load_credentials,
)

# ---------------------------------------------------------------------------
# Section A: credential loading at startup
# ---------------------------------------------------------------------------

_credentials_loaded = False


def _ensure_credentials() -> None:
    global _credentials_loaded
    if not _credentials_loaded:
        load_credentials()  # fetches from SSM, writes /tmp/ files, sets env vars
        _credentials_loaded = True


_ensure_credentials()  # called at import time, before any route fires

# Warm the shell data cache in the background so the first user request is fast.
import threading as _threading

def _warm_caches():
    try:
        todoist_token = os.environ.get("TODOIST_API_TOKEN", "")
        function_url = os.environ.get("FUNCTION_URL", "")
        action_token = os.environ.get("ACTION_TOKEN", "")
        if not (todoist_token and function_url and action_token):
            return

        def _view_event(view):
            return {
                "queryStringParameters": {"action": "web", "embed": "1", "view": view},
                "body": "",
                "isBase64Encoded": False,
                "headers": {"cookie": f"aos_session={action_token}", "content-type": ""},
                "requestContext": {"http": {"method": "GET"}},
            }

        import logging as _log
        _wlog = _log.getLogger(__name__)

        def _warm(name, fn, *args):
            try:
                fn(*args)
            except Exception as _e:
                _wlog.warning(f"[cache-warm] {name} failed: {_e}")

        from concurrent.futures import ThreadPoolExecutor as _WarmTPE
        with _WarmTPE(max_workers=4) as _ex:
            _ex.submit(_warm, "shell", _get_shell_data, todoist_token)
            _ex.submit(_warm, "home", _get_home_html, function_url, action_token, todoist_token)
            _ex.submit(_warm, "calendar", handle_action, _view_event("calendar"))
            _ex.submit(_warm, "code", handle_action, _view_event("code"))
    except Exception as e:
        import logging as _log
        _log.getLogger(__name__).warning(f"[cache-warm] outer failure: {e}")

_threading.Thread(target=_warm_caches, daemon=True).start()

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Section B: request adapter  (Flask → Lambda event shape)
# ---------------------------------------------------------------------------


def _build_lambda_event() -> dict:
    qs_params = {k: v for k, v in request.args.items()}
    cookie_header = "; ".join(f"{k}={v}" for k, v in request.cookies.items())
    body = request.get_data().decode("utf-8") if request.get_data() else ""
    return {
        "queryStringParameters": qs_params,
        "body": body,
        "isBase64Encoded": False,  # gunicorn always decodes; base64 branch never fires
        "headers": {
            "cookie": cookie_header,
            "content-type": request.content_type or "",
        },
        "requestContext": {"http": {"method": request.method.upper()}},
    }


# ---------------------------------------------------------------------------
# Section C: response adapter  (Lambda result dict → Flask Response)
# ---------------------------------------------------------------------------


def _apply_cookie_header(resp, set_cookie_str: str) -> None:
    """Parse a 'name=val; HttpOnly; Path=/; ...' string and set it on resp."""
    parts = [p.strip() for p in set_cookie_str.split(";")]
    if not parts:
        return
    name, _, value = parts[0].partition("=")
    kwargs = {}
    for part in parts[1:]:
        key, _, val = part.partition("=")
        key = key.strip().lower()
        if key == "httponly":
            kwargs["httponly"] = True
        elif key == "secure":
            kwargs["secure"] = True
        elif key == "samesite":
            kwargs["samesite"] = val.strip()
        elif key == "path":
            kwargs["path"] = val.strip()
        elif key == "domain":
            kwargs["domain"] = val.strip()
        elif key == "max-age":
            try:
                kwargs["max_age"] = int(val.strip())
            except ValueError:
                pass
    resp.set_cookie(name.strip(), value, **kwargs)


def _lambda_to_flask_response(result: dict):
    status = result.get("statusCode", 200)
    body = result.get("body", "")
    headers = dict(result.get("headers", {}))
    set_cookie = headers.pop("Set-Cookie", None)

    if status in (301, 302, 303, 307, 308):
        resp = redirect(headers.get("Location", "/"), code=status)
    else:
        # Encode to bytes first so surrogate characters from calendar event
        # titles / emoji don't trigger Flask's strict UTF-8 encoder.
        if isinstance(body, str):
            body = body.encode("utf-8", errors="replace")
        resp = make_response(body, status)

    for k, v in headers.items():
        resp.headers[k] = v
    if set_cookie:
        _apply_cookie_header(resp, set_cookie)
    return resp


# ---------------------------------------------------------------------------
# Section D: single catch-all route
# ---------------------------------------------------------------------------


@app.route("/", defaults={"path": ""}, methods=["GET", "POST"])
@app.route("/<path:path>", methods=["GET", "POST"])
def catch_all(path):
    event = _build_lambda_event()
    result = handle_action(event)
    return _lambda_to_flask_response(result)


# ---------------------------------------------------------------------------
# Section E: APScheduler — replaces EventBridge scheduled invocations
# ---------------------------------------------------------------------------


def _job_sync() -> None:
    """Every 10 min: sync unread emails and follow-ups."""
    from unread_main import run_followup_sync, run_sync

    run_sync()
    run_followup_sync()


def _job_daily_digest() -> None:
    """7:00 AM Eastern: send the daily email digest."""
    from unread_main import run_daily_digest

    run_daily_digest(
        function_url=os.environ.get("FUNCTION_URL", ""),
        action_token=os.environ.get("ACTION_TOKEN", ""),
    )


def _job_check_countdowns() -> None:
    """Every 5 min: fire push notifications for due countdown timers."""
    from datetime import datetime, timezone

    from push_service import send_push

    countdowns = _load_countdowns()
    if not countdowns:
        return

    now = datetime.now(timezone.utc)
    fired = []
    for eid, entry in list(countdowns.items()):
        notify_at = datetime.fromisoformat(entry["notify_at"])
        if notify_at.tzinfo is None:
            notify_at = notify_at.replace(tzinfo=timezone.utc)
        if notify_at <= now:
            func_url = os.environ.get("FUNCTION_URL", "")
            cal_url = func_url.rstrip("/") + "?action=web&view=calendar&embed=1"
            send_push(entry["title"], "Starting in 5 minutes", cal_url)
            fired.append(eid)

    for eid in fired:
        del countdowns[eid]
    if fired:
        _save_countdowns(countdowns)


def init_scheduler():
    from apscheduler.executors.pool import ThreadPoolExecutor as APSThreadPool
    from apscheduler.schedulers.background import BackgroundScheduler

    sched = BackgroundScheduler(
        executors={"default": APSThreadPool(max_workers=2)},
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 120},
        timezone="America/New_York",
    )
    sched.add_job(_job_sync, "interval", minutes=10, id="sync")
    sched.add_job(_job_daily_digest, "cron", hour=7, minute=0, id="daily_digest")
    sched.add_job(_job_check_countdowns, "interval", minutes=5, id="check_countdowns")
    sched.add_job(_warm_caches, "interval", minutes=4, id="rewarm_caches")
    sched.start()
    return sched


# Guard: don't double-start in Flask's debug reloader
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    _scheduler = init_scheduler()


# ---------------------------------------------------------------------------
# Local dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
