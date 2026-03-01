"""AWS Lambda handler for Todoist Coding Digest.

Two invocation modes:
- EventBridge (mode: "digest"): runs full digest pipeline, sends email
- Function URL (action: "open"): serves redirect page to open Cursor + show Claude command
"""

import json
import logging
import os
import sys
from urllib.parse import unquote

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import boto3  # noqa: E402

ssm = boto3.client("ssm", region_name="us-east-1")


def get_parameter(param_name: str, decrypt: bool = True) -> str:
    """Get parameter from AWS Parameter Store."""
    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=decrypt)
        return response["Parameter"]["Value"]
    except Exception as e:
        logger.error(f"Failed to get parameter {param_name}: {e}")
        raise


def load_credentials():
    """Load credentials from Parameter Store into environment."""
    logger.info("Loading credentials from Parameter Store")

    todoist_token = get_parameter("/coding-digest/todoist-api-token")
    os.environ["TODOIST_API_TOKEN"] = todoist_token

    recipient = get_parameter("/coding-digest/email-recipient", decrypt=False)
    os.environ["EMAIL_RECIPIENT"] = recipient

    ses_sender = get_parameter("/coding-digest/ses-sender-email", decrypt=False)
    os.environ["SES_SENDER_EMAIL"] = ses_sender

    try:
        function_url = get_parameter("/coding-digest/function-url", decrypt=False)
        os.environ["FUNCTION_URL"] = function_url
    except Exception:
        logger.warning("Could not load function-url parameter")

    logger.info("Credentials loaded successfully")


def _is_function_url_event(event: dict) -> bool:
    """Detect a Lambda Function URL HTTP invocation."""
    return "requestContext" in event and "http" in event.get("requestContext", {})


def _html_escape(text: str) -> str:
    """Basic HTML escaping for user-provided strings."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def handle_open_action(params: dict) -> dict:
    """Serve a redirect page that opens Cursor and shows the Claude command."""
    repo_path = unquote(params.get("path", ""))
    task_name = unquote(params.get("task", ""))
    session_id = unquote(params.get("session_id", ""))

    cursor_url = f"cursor://file{repo_path}"
    safe_cursor_url = _html_escape(cursor_url)

    if session_id:
        claude_cmd = f"claude -r {_html_escape(session_id)}"
    else:
        safe_task = _html_escape(task_name)
        claude_cmd = f'claude --plan "{safe_task}"'

    body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Open in Cursor</title></head>
<body style="font-family:Arial,sans-serif;padding:40px;text-align:center;
    background:#f5f5f5;margin:0;">
<div style="max-width:500px;margin:40px auto;background:#fff;border-radius:12px;
    padding:40px;box-shadow:0 2px 8px rgba(0,0,0,.1);">
<h2 style="color:#6C3FA5;margin-top:0;">Opening in Cursor...</h2>
<p style="color:#555;">If Cursor doesn't open automatically:</p>
<a href="{safe_cursor_url}"
   style="display:inline-block;background:#6C3FA5;color:#fff;padding:12px 28px;
   border-radius:6px;text-decoration:none;font-size:16px;margin:10px 0;">
   Open in Cursor</a>
<hr style="margin:30px 0;border:none;border-top:1px solid #e0e0e0;">
<p style="color:#555;">Then run in terminal:</p>
<code style="display:inline-block;background:#f0f0f0;padding:10px 20px;border-radius:6px;
    font-size:14px;color:#333;word-break:break-all;">{claude_cmd}</code>
</div>
<script>window.location.href = "{safe_cursor_url}";</script>
</body></html>"""

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html"},
        "body": body,
    }


def lambda_handler(event, context):
    """Main Lambda handler."""
    logger.info("=" * 60)
    logger.info("TODOIST CODING DIGEST LAMBDA - Starting")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 60)

    try:
        # Function URL requests don't need full credentials for the open action
        if _is_function_url_event(event):
            params = event.get("queryStringParameters") or {}
            action = params.get("action", "")

            if action == "open":
                return handle_open_action(params)
            else:
                return {"statusCode": 400, "body": "Bad Request"}

        # EventBridge / manual invocation - load credentials and run digest
        load_credentials()

        import yaml

        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)

        dry_run = event.get("dry_run", False)

        from digest_main import run_digest

        result = run_digest(config, dry_run=dry_run)

        logger.info(f"Completed successfully: {result}")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Completed successfully", "result": result}),
        }

    except Exception as e:
        logger.error(f"Lambda failed: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Failed: {str(e)}"}),
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["digest", "open"], default="digest")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = lambda_handler({"mode": args.mode, "dry_run": args.dry_run}, None)
    print(json.dumps(result, indent=2))
