"""AWS Lambda handler for Todoist Actions Web interface.

Serves three Todoist task views (Inbox, Commit, P1) with inline
disposition controls. Deployed as a Lambda with Function URL.

Routes (all require valid token):
- ?action=web&view=inbox|commit|p1  - Render task list HTML
- ?action=move&task_id=X&project_id=Y  - Move task to project
- ?action=priority&task_id=X&priority=N  - Update task priority
- ?action=complete&task_id=X  - Complete/close task
- ?action=reopen&task_id=X  - Reopen a completed task
- ?action=due_date&task_id=X&date=YYYY-MM-DD  - Update task due date
"""

import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

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

    todoist_token = get_parameter("/todoist-actions-web/todoist-api-token")
    os.environ["TODOIST_API_TOKEN"] = todoist_token

    action_token = get_parameter("/todoist-actions-web/action-token")
    os.environ["ACTION_TOKEN"] = action_token

    try:
        function_url = get_parameter("/todoist-actions-web/function-url", decrypt=False)
        os.environ["FUNCTION_URL"] = function_url
    except Exception as e:
        logger.warning(f"Could not load function-url: {e}")

    # Email actions Lambda URL + token (for split-pane email viewer)
    try:
        ea_url = get_parameter(
            "/todoist-actions-web/email-actions-function-url", decrypt=False
        )
        os.environ["EMAIL_ACTIONS_FUNCTION_URL"] = ea_url
    except Exception as e:
        logger.warning(f"Could not load email-actions-function-url: {e}")

    try:
        ea_token = get_parameter("/todoist-actions-web/email-actions-action-token")
        os.environ["EMAIL_ACTIONS_ACTION_TOKEN"] = ea_token
    except Exception as e:
        logger.warning(f"Could not load email-actions-action-token: {e}")

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


def handle_action(event):
    """Handle an HTTP action request from a Function URL invocation."""
    params = event.get("queryStringParameters") or {}
    token = params.get("token", "")
    expected = os.environ.get("ACTION_TOKEN", "")

    if not expected or token != expected:
        logger.warning("Action request rejected: invalid token")
        return {"statusCode": 403, "body": "Forbidden"}

    action = params.get("action", "")
    function_url = os.environ.get("FUNCTION_URL", "")
    todoist_token = os.environ.get("TODOIST_API_TOKEN", "")

    from todoist_service import TodoistService

    service = TodoistService(todoist_token)

    if action == "web":
        view = params.get("view", "inbox")
        embed = params.get("embed", "") == "1"
        logger.info(f"Action: web view={view} embed={embed}")

        try:
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
                    tasks_future = executor.submit(service.get_tasks_by_label, "Commit")
                projects = projects_future.result()
                all_commit = tasks_future.result()
                today_str = datetime.now().strftime("%Y-%m-%d")
                tasks = [
                    t
                    for t in all_commit
                    if t.get("due") and t["due"].get("date", "")[:10] <= today_str
                ]
            elif view == "p1":
                with ThreadPoolExecutor(max_workers=2) as executor:
                    projects_future = executor.submit(service.get_all_projects)
                    tasks_future = executor.submit(service.get_tasks_by_priority, 4)
                projects = projects_future.result()
                all_p1 = tasks_future.result()
                today_str = datetime.now().strftime("%Y-%m-%d")
                tasks = [
                    t
                    for t in all_p1
                    if t.get("due") and t["due"].get("date", "")[:10] <= today_str
                ]
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
                today_str = datetime.now().strftime("%Y-%m-%d")
                tasks = [
                    t
                    for t in all_bestcase
                    if t.get("due") and t["due"].get("date", "")[:10] <= today_str
                ]
            else:
                projects = service.get_all_projects()
                tasks = service.get_inbox_tasks(projects=projects)

            email_actions_url = os.environ.get("EMAIL_ACTIONS_FUNCTION_URL", "")
            email_actions_token = os.environ.get("EMAIL_ACTIONS_ACTION_TOKEN", "")

            from web_views import build_view_html

            body = build_view_html(
                tasks,
                projects,
                view,
                function_url,
                expected,
                embed=embed,
                email_actions_url=email_actions_url,
                email_actions_token=email_actions_token,
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
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": ok}),
        }

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
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": ok}),
        }

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
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": ok}),
        }

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
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": ok}),
        }

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
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": ok}),
        }

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
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": ok}),
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
        ok = service.bestcase_task(task_id)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": ok}),
        }

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
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": ok}),
        }

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
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"ok": ok}),
        }

    else:
        return {"statusCode": 400, "body": "Bad Request"}


def lambda_handler(event, context):
    """Main Lambda handler for Function URL invocations."""
    logger.info("=" * 60)
    logger.info("TODOIST ACTIONS WEB - Starting")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 60)

    try:
        load_credentials()

        if "requestContext" in event and "http" in event.get("requestContext", {}):
            return handle_action(event)

        return {"statusCode": 400, "body": "This function only handles HTTP requests"}

    except Exception as e:
        logger.error(f"Lambda failed: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Failed: {str(e)}"}),
        }
