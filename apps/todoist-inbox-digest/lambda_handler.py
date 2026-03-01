"""AWS Lambda handler for Todoist Inbox Digest.

Serves the inbox task dashboard with inline action controls and sends
a daily HTML digest email. Deployed as a Lambda with Function URL.

Trigger modes:
- EventBridge: {"mode": "daily_digest"} -> fetch tasks, trash old digest, send email
- Function URL: ?action=web|complete|reopen|move|priority|due_date|commit_label|bestcase_label|rerun

Routes (all require valid token):
- ?action=web                  - Render inbox dashboard HTML
- ?action=complete&task_id=X   - Complete/close task
- ?action=reopen&task_id=X     - Reopen a completed task
- ?action=move&task_id=X&project_id=Y  - Move task to project
- ?action=priority&task_id=X&priority=N - Update task priority
- ?action=due_date&task_id=X&date=YYYY-MM-DD  - Update due date
- ?action=commit_label&task_id=X  - Add Commit label, move to Personal
- ?action=bestcase_label&task_id=X - Add Best Case label, move to Personal
- ?action=remove_commit&task_id=X  - Remove Commit label
- ?action=remove_bestcase&task_id=X - Remove Best Case label
- ?action=rerun                - Re-run daily digest, show confirmation
"""

import base64
import json
import logging
import os
import sys
import tempfile

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import boto3  # noqa: E402

ssm = boto3.client("ssm", region_name="us-east-1")


def get_parameter(param_name, decrypt=True):
    """Get parameter from AWS Parameter Store."""
    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=decrypt)
        return response["Parameter"]["Value"]
    except Exception as e:
        logger.error(f"Failed to get parameter {param_name}: {str(e)}")
        raise


def load_credentials():
    """Load credentials from Parameter Store and set env vars."""
    logger.info("Loading credentials from Parameter Store")

    todoist_token = get_parameter("/todoist-inbox-digest/todoist-api-token")
    os.environ["TODOIST_API_TOKEN"] = todoist_token

    action_token = get_parameter("/todoist-inbox-digest/action-token")
    os.environ["ACTION_TOKEN"] = action_token

    try:
        function_url = get_parameter(
            "/todoist-inbox-digest/function-url", decrypt=False
        )
        os.environ["FUNCTION_URL"] = function_url
    except Exception as e:
        logger.warning(f"Could not load function-url: {e}")

    try:
        report_email = get_parameter(
            "/todoist-inbox-digest/report-email", decrypt=False
        )
        os.environ["REPORT_EMAIL"] = report_email
    except Exception as e:
        logger.warning(f"Could not load report-email: {e}")

    try:
        ses_sender = get_parameter(
            "/todoist-inbox-digest/ses-sender-email", decrypt=False
        )
        os.environ["SES_SENDER_EMAIL"] = ses_sender
    except Exception as e:
        logger.warning(f"Could not load ses-sender-email: {e}")

    # Web dashboard URL (todoist-actions-web) for "Manage on Web" link in email
    try:
        taw_url = get_parameter("/todoist-actions-web/function-url", decrypt=False)
        taw_token = get_parameter("/todoist-actions-web/action-token")
        os.environ["WEB_DASHBOARD_URL"] = (
            taw_url.rstrip("/") + "?action=web&view=inbox&token=" + taw_token
        )
    except Exception as e:
        logger.warning(f"Could not load web dashboard URL: {e}")

    # Gmail credentials (base64 encoded in Parameter Store)
    try:
        gmail_creds_b64 = get_parameter("/todoist-inbox-digest/gmail-credentials")
        creds_path = os.path.join(tempfile.gettempdir(), "gmail_credentials.json")
        with open(creds_path, "wb") as f:
            f.write(base64.b64decode(gmail_creds_b64))
        os.environ["GMAIL_CREDENTIALS_PATH"] = creds_path
    except Exception as e:
        logger.warning(f"Could not load gmail-credentials: {e}")

    try:
        gmail_token_b64 = get_parameter("/todoist-inbox-digest/gmail-token")
        token_path = os.path.join(tempfile.gettempdir(), "gmail_token.pickle")
        with open(token_path, "wb") as f:
            f.write(base64.b64decode(gmail_token_b64))
        os.environ["GMAIL_TOKEN_PATH"] = token_path
    except Exception as e:
        logger.warning(f"Could not load gmail-token: {e}")

    logger.info("All credentials loaded successfully")


def _error_html(message):
    """Return a simple error page."""
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "</head><body style='font-family:sans-serif;background:#f0f2f5;"
        "margin:0;padding:0;'>"
        "<div style='max-width:480px;margin:80px auto;background:#fff;"
        "border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.10);"
        "padding:40px;text-align:center;'>"
        "<div style='font-size:48px;margin-bottom:16px;'>&#10007;</div>"
        "<h2 style='color:#d93025;font-size:20px;margin:0 0 8px;'>Error</h2>"
        f"<p style='color:#555;font-size:15px;'>{message}</p>"
        "</div></body></html>"
    )


def _confirmation_html(title, message, success=True):
    """Return a confirmation page for email-originated actions."""
    icon = "&#10003;" if success else "&#10007;"
    color = "#188038" if success else "#d93025"
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "</head><body style='font-family:sans-serif;background:#f0f2f5;"
        "margin:0;padding:0;'>"
        "<div style='max-width:480px;margin:80px auto;background:#fff;"
        "border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.10);"
        "padding:40px;text-align:center;'>"
        f"<div style='font-size:48px;margin-bottom:16px;color:{color};'>{icon}</div>"
        f"<h2 style='color:{color};font-size:20px;margin:0 0 8px;'>{title}</h2>"
        f"<p style='color:#555;font-size:15px;'>{message}</p>"
        "</div></body></html>"
    )


def handle_action(event):
    """Handle an HTTP action request from a Function URL invocation."""
    params = event.get("queryStringParameters") or {}
    token = params.get("token", "")
    expected = os.environ.get("ACTION_TOKEN", "")

    if not expected or token != expected:
        logger.warning("Action request rejected: invalid token")
        return {"statusCode": 403, "body": "Forbidden"}

    action = params.get("action", "")
    source = params.get("source", "")  # "email" for email-originated actions
    function_url = os.environ.get("FUNCTION_URL", "")
    todoist_token = os.environ.get("TODOIST_API_TOKEN", "")

    from todoist_service import TodoistService

    service = TodoistService(todoist_token)

    # Helper: return JSON for web, HTML confirmation for email
    def _action_response(ok, action_name="Action"):
        if source == "email":
            if ok:
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "text/html"},
                    "body": _confirmation_html(
                        f"{action_name} Complete",
                        "The action was applied successfully.",
                    ),
                }
            else:
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "text/html"},
                    "body": _confirmation_html(
                        f"{action_name} Failed",
                        "Something went wrong. Please try again.",
                        success=False,
                    ),
                }
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": ok}),
        }

    if action == "web":
        logger.info("Action: web (inbox dashboard)")
        try:
            projects = service.get_all_projects()
            tasks = service.get_inbox_tasks(projects=projects)
            tasks.sort(
                key=lambda t: t.get("created_at", "") or t.get("added_at", ""),
                reverse=True,
            )

            from web_views import build_view_html

            body = build_view_html(tasks, projects, function_url, expected)
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "text/html",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                },
                "body": body,
            }
        except Exception as e:
            logger.error(f"Web view failed: {e}", exc_info=True)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": _error_html(f"Could not load view: {e}"),
            }

    elif action == "move":
        task_id = params.get("task_id", "")
        project_id = params.get("project_id", "")
        if not task_id or not project_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {"ok": False, "error": "Missing task_id or project_id"}
                ),
            }
        logger.info(f"Action: move task={task_id} to project={project_id}")
        ok = service.move_task(task_id, project_id)
        return _action_response(ok, "Move")

    elif action == "priority":
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
        logger.info(f"Action: priority task={task_id} priority={priority}")
        ok = service.update_priority(task_id, int(priority))
        p_names = {4: "P1", 3: "P2", 2: "P3", 1: "P4"}
        return _action_response(
            ok, f"Priority → {p_names.get(int(priority), priority)}"
        )

    elif action == "complete":
        task_id = params.get("task_id", "")
        if not task_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": "Missing task_id"}),
            }
        logger.info(f"Action: complete task={task_id}")
        ok = service.close_task(task_id)
        return _action_response(ok, "Task Completed")

    elif action == "reopen":
        task_id = params.get("task_id", "")
        if not task_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": "Missing task_id"}),
            }
        logger.info(f"Action: reopen task={task_id}")
        ok = service.reopen_task(task_id)
        return _action_response(ok, "Task Reopened")

    elif action == "due_date":
        task_id = params.get("task_id", "")
        date = params.get("date", "")
        if not task_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": "Missing task_id"}),
            }
        logger.info(f"Action: due_date task={task_id} date={date}")
        ok = service.update_due_date(task_id, date)
        return _action_response(ok, f"Due Date → {date or 'cleared'}")

    elif action == "commit_label":
        task_id = params.get("task_id", "")
        if not task_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": "Missing task_id"}),
            }
        logger.info(f"Action: commit_label task={task_id}")
        ok = service.commit_task(task_id)
        return _action_response(ok, "Committed")

    elif action == "bestcase_label":
        task_id = params.get("task_id", "")
        if not task_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": "Missing task_id"}),
            }
        logger.info(f"Action: bestcase_label task={task_id}")
        ok = service.bestcase_task(task_id)
        return _action_response(ok, "Best Case")

    elif action == "remove_bestcase":
        task_id = params.get("task_id", "")
        if not task_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": "Missing task_id"}),
            }
        logger.info(f"Action: remove_bestcase task={task_id}")
        ok = service.remove_bestcase_label(task_id)
        return _action_response(ok, "Best Case Removed")

    elif action == "remove_commit":
        task_id = params.get("task_id", "")
        if not task_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"ok": False, "error": "Missing task_id"}),
            }
        logger.info(f"Action: remove_commit task={task_id}")
        ok = service.remove_commit_label(task_id)
        return _action_response(ok, "Commit Removed")

    elif action == "rerun":
        logger.info("Action: rerun (re-send daily digest)")
        try:
            from inbox_digest_main import run_daily_digest

            run_daily_digest()
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": _confirmation_html(
                    "Digest Sent",
                    "A fresh Inbox Digest email has been sent to your inbox.",
                ),
            }
        except Exception as e:
            logger.error(f"Rerun failed: {e}", exc_info=True)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": _confirmation_html(
                    "Rerun Failed",
                    f"Could not send digest: {e}",
                    success=False,
                ),
            }

    else:
        return {"statusCode": 400, "body": "Bad Request"}


def lambda_handler(event, context):
    """Main Lambda handler for EventBridge and Function URL invocations."""
    logger.info("=" * 60)
    logger.info("TODOIST INBOX DIGEST - Starting")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 60)

    try:
        load_credentials()

        # EventBridge scheduled invocation
        mode = event.get("mode", "")
        if mode == "daily_digest":
            logger.info("Mode: daily_digest (EventBridge trigger)")
            from inbox_digest_main import run_daily_digest

            run_daily_digest()
            return {"statusCode": 200, "body": "Daily digest sent"}

        # Function URL invocation
        if "requestContext" in event and "http" in event.get("requestContext", {}):
            return handle_action(event)

        return {"statusCode": 400, "body": "Unknown invocation type"}

    except Exception as e:
        logger.error(f"Lambda failed: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Failed: {str(e)}"}),
        }
