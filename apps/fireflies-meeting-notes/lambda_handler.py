"""AWS Lambda handler for Fireflies Meeting Notes Processor.

Two invocation modes:
- POST (Fireflies webhook): processes a completed transcript
- GET (email button click): redirects to obsidian:// URI for note saving
"""

import json
import logging
import os
import sys
import urllib.parse
from datetime import date
from typing import Tuple

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import boto3  # noqa: E402

ssm = boto3.client("ssm", region_name="us-east-1")

_PAGE_STYLE = (
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
    "background:#f0f2f5;margin:0;padding:0;"
)

_CARD_STYLE = (
    "max-width:520px;margin:80px auto;background:#fff;border-radius:8px;"
    "box-shadow:0 2px 8px rgba(0,0,0,.10);padding:40px;text-align:center;"
)


def get_parameter(param_name: str, decrypt: bool = True) -> str:
    """Get parameter from AWS Parameter Store."""
    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=decrypt)
        return response["Parameter"]["Value"]
    except Exception as e:
        logger.error(f"Failed to get parameter {param_name}: {str(e)}")
        raise


def load_action_credentials():
    """Load only the credentials needed for GET action requests (4 params).

    Used for email button clicks — avoids loading webhook/email params
    that aren't needed, cutting SSM latency from ~560ms to ~320ms.
    """
    logger.info("Loading action credentials from Parameter Store")

    prefix = "/fireflies-meeting-notes"

    os.environ["FIREFLIES_API_KEY"] = get_parameter(f"{prefix}/fireflies-api-key")
    os.environ["OBSIDIAN_VAULT_NAME"] = get_parameter(
        f"{prefix}/obsidian-vault-name", decrypt=False
    )
    os.environ["ACTION_TOKEN"] = get_parameter(f"{prefix}/action-token")

    try:
        os.environ["S3_BUCKET"] = get_parameter(f"{prefix}/s3-bucket", decrypt=False)
    except Exception:
        logger.info(f"Optional parameter {prefix}/s3-bucket not found, skipping")

    try:
        os.environ["FUNCTION_URL"] = get_parameter(
            f"{prefix}/function-url", decrypt=False
        )
    except Exception:
        logger.info(f"Optional parameter {prefix}/function-url not found, skipping")

    logger.info("Action credentials loaded (5 params)")


def load_all_credentials():
    """Load all credentials from Parameter Store (7 params).

    Used for POST webhook and direct invocation — needs everything.
    """
    logger.info("Loading all credentials from Parameter Store")

    prefix = "/fireflies-meeting-notes"

    os.environ["FIREFLIES_API_KEY"] = get_parameter(f"{prefix}/fireflies-api-key")
    os.environ["TODOIST_API_TOKEN"] = get_parameter(f"{prefix}/todoist-api-token")
    os.environ["SES_SENDER_EMAIL"] = get_parameter(
        f"{prefix}/ses-sender-email", decrypt=False
    )
    os.environ["REPORT_EMAIL"] = get_parameter(f"{prefix}/report-email", decrypt=False)
    os.environ["OBSIDIAN_VAULT_NAME"] = get_parameter(
        f"{prefix}/obsidian-vault-name", decrypt=False
    )
    os.environ["ACTION_TOKEN"] = get_parameter(f"{prefix}/action-token")
    os.environ["FUNCTION_URL"] = get_parameter(f"{prefix}/function-url", decrypt=False)

    try:
        os.environ["S3_BUCKET"] = get_parameter(f"{prefix}/s3-bucket", decrypt=False)
    except Exception:
        logger.info(f"Optional parameter {prefix}/s3-bucket not found, skipping")

    logger.info("All credentials loaded (7 params)")


def _is_http_event(event: dict) -> Tuple[bool, str]:
    """Detect an HTTP invocation (Function URL or API Gateway).

    Returns:
        Tuple of (is_http, http_method).
    """
    rc = event.get("requestContext", {})
    # Lambda Function URL format
    if "http" in rc:
        return True, rc["http"].get("method", "").upper()
    # API Gateway proxy format
    if "httpMethod" in rc:
        return True, rc["httpMethod"].upper()
    return False, ""


def _obsidian_redirect_page(obsidian_uri: str) -> str:
    """Build an HTML page that auto-redirects to an obsidian:// URI.

    No clipboard involved — the content is URL-encoded in the URI itself.
    Works on mobile without user-gesture restrictions.
    """
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Save to Obsidian</title>"
        "</head>"
        "<body style='" + _PAGE_STYLE + "'>"
        "<div style='" + _CARD_STYLE + "'>"
        "<div style='font-size:48px;line-height:1;margin-bottom:16px;'>&#10070;</div>"
        "<h2 id='title' style='margin:0 0 8px;color:#7c3aed;font-size:20px;'>"
        "Opening Obsidian...</h2>"
        "<p id='message' style='color:#555;font-size:15px;margin:0 0 20px;'>"
        "Saving meeting notes to Obsidian.</p>"
        "<a id='manual-btn' href='" + obsidian_uri + "' style='"
        "display:none;background:#7c3aed;color:#fff;"
        "padding:12px 28px;border:none;border-radius:6px;font-size:15px;"
        "cursor:pointer;font-weight:600;text-decoration:none;'"
        ">Open Obsidian</a>"
        "</div>"
        "<script>"
        "setTimeout(function() {"
        "  window.location.href = '" + obsidian_uri.replace("'", "\\'") + "';"
        "}, 300);"
        "setTimeout(function() {"
        "  document.getElementById('manual-btn').style.display = 'inline-block';"
        "  document.getElementById('message').textContent = "
        "    'If Obsidian did not open, tap the button below.';"
        "}, 2000);"
        "</script>"
        "</body></html>"
    )


def handle_action(event: dict) -> dict:
    """Handle GET requests for email button clicks.

    Routes:
    - action=save_obsidian: redirect to obsidian:// URI
    - action=recordings: render All Recordings web page
    """
    params = event.get("queryStringParameters") or {}
    token = params.get("token", "")
    expected = os.environ.get("ACTION_TOKEN", "")

    if not expected or token != expected:
        logger.warning("Action request rejected: invalid token")
        return {"statusCode": 403, "body": "Forbidden"}

    action = params.get("action", "")

    if action == "recordings":
        return _handle_recordings()
    elif action == "save_obsidian":
        return _handle_save_obsidian(params)
    else:
        return {"statusCode": 400, "body": "Bad Request"}


def _handle_save_obsidian(params: dict) -> dict:
    """Handle save_obsidian action — redirect to obsidian:// URI.

    Retrieval order:
    1. S3 (pre-stored at email-send time) — fast (~50-100ms)
    2. Fireflies API fallback (old emails without S3 pre-store) — slow (~2-5s)

    Note naming:
    - New emails: "Meeting - {title}" from URL title param
    - Old emails (no title param): date-based name (backward compat)
    """
    transcript_id = params.get("transcript_id", "")
    if not transcript_id:
        return {"statusCode": 400, "body": "Bad Request: missing transcript_id"}

    title = params.get("title", "")
    logger.info(
        f"Action: save_obsidian for transcript {transcript_id}"
        + (f" title='{title}'" if title else " (no title — old email)")
    )

    try:
        vault_name = os.environ.get("OBSIDIAN_VAULT_NAME", "")
        if not vault_name:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "text/html"},
                "body": "<h1>Configuration error</h1>",
            }

        # --- Try S3 first (fast path) ---
        note_content = None
        s3_bucket = os.environ.get("S3_BUCKET", "")
        if s3_bucket:
            try:
                from obsidian_formatter import retrieve_note

                note_content = retrieve_note(transcript_id, s3_bucket)
                logger.info("Retrieved note from S3 (fast path)")
            except Exception as s3_err:
                logger.warning(
                    f"S3 retrieval failed, falling back to Fireflies: {s3_err}"
                )

        # --- Fireflies API fallback (slow path) ---
        if note_content is None:
            from fireflies_service import FirefliesService
            from obsidian_formatter import build_full_markdown_safe

            fireflies_key = os.environ.get("FIREFLIES_API_KEY", "")
            if not fireflies_key:
                return {
                    "statusCode": 500,
                    "headers": {"Content-Type": "text/html"},
                    "body": "<h1>Configuration error</h1>",
                }

            service = FirefliesService(fireflies_key)
            transcript = service.fetch_transcript(transcript_id)
            note_content = build_full_markdown_safe(transcript)
            # Backfill title from transcript if URL didn't have it
            if not title:
                title = transcript.title
            logger.info("Built note from Fireflies API (fallback)")

        # --- Build Obsidian URI ---
        vault_encoded = urllib.parse.quote(vault_name, safe="")
        content_encoded = urllib.parse.quote(note_content, safe="")

        if title:
            # New flow: separate note named "Meeting - {title}"
            # Strip characters illegal in Obsidian filenames: \ / :
            safe_title = title.replace("\\", "").replace("/", "-").replace(":", "")
            note_name = urllib.parse.quote(f"Meeting - {safe_title}", safe="")
            obsidian_uri = (
                f"obsidian://new?vault={vault_encoded}"
                f"&name={note_name}&content={content_encoded}"
            )
        else:
            # Old email backward compat: append to daily note
            daily_name = urllib.parse.quote(date.today().isoformat(), safe="")
            obsidian_uri = (
                f"obsidian://new?vault={vault_encoded}"
                f"&name={daily_name}&content={content_encoded}&append"
            )

        body = _obsidian_redirect_page(obsidian_uri)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": body,
        }
    except Exception as e:
        logger.error(f"save_obsidian failed: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "text/html"},
            "body": f"<h1>Error</h1><p>{e}</p>",
        }


def _handle_recordings() -> dict:
    """Handle recordings action — render All Recordings web page."""
    try:
        s3_bucket = os.environ.get("S3_BUCKET", "")
        if not s3_bucket:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "text/html"},
                "body": "<h1>Configuration error: S3_BUCKET not set</h1>",
            }

        function_url = os.environ.get("FUNCTION_URL", "")
        action_token = os.environ.get("ACTION_TOKEN", "")

        from email_builder import build_recordings_html
        from obsidian_formatter import list_recordings

        recordings = list_recordings(s3_bucket)
        html = build_recordings_html(recordings, function_url, action_token)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/html",
                "Cache-Control": "no-cache",
            },
            "body": html,
        }
    except Exception as e:
        logger.error(f"recordings page failed: {e}", exc_info=True)
        error_html = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "</head>"
            "<body style='" + _PAGE_STYLE + "'>"
            "<div style='" + _CARD_STYLE + "'>"
            "<h2 style='color:#d93025;'>Error loading recordings</h2>"
            "<p style='color:#555;'>" + str(e) + "</p>"
            "</div></body></html>"
        )
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "text/html"},
            "body": error_html,
        }


def handle_webhook(event: dict) -> dict:
    """Handle POST requests from Fireflies webhook."""
    # Parse webhook body
    body = event.get("body", "")
    if event.get("isBase64Encoded"):
        import base64

        body = base64.b64decode(body).decode("utf-8")

    try:
        payload = json.loads(body) if isinstance(body, str) else body
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook body")
        return {"statusCode": 400, "body": "Invalid JSON"}

    # Extract transcript ID from Fireflies webhook payload
    transcript_id = payload.get("transcriptId") or payload.get("transcript_id", "")

    if not transcript_id:
        # Fireflies may nest it under "data"
        data = payload.get("data", {})
        transcript_id = data.get("transcriptId") or data.get("transcript_id", "")

    if not transcript_id:
        logger.error(f"No transcript ID found in webhook payload: {payload}")
        return {"statusCode": 400, "body": "Missing transcript ID"}

    logger.info(f"Webhook received for transcript: {transcript_id}")

    from fireflies_main import process_meeting

    result = process_meeting(transcript_id)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Processed", "result": result}),
    }


def lambda_handler(event, context):
    """Main Lambda handler.

    Routes:
    - Lambda Function URL GET: email button actions (save_obsidian)
    - Lambda Function URL POST: Fireflies webhook
    - Direct invocation with transcript_id: manual processing
    """
    logger.info("=" * 60)
    logger.info("FIREFLIES MEETING NOTES - Starting")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 60)

    try:
        is_http, method = _is_http_event(event)
        if is_http:
            if method == "GET":
                logger.info("HTTP GET — routing to handle_action")
                load_action_credentials()
                return handle_action(event)
            elif method == "POST":
                logger.info("HTTP POST — routing to handle_webhook")
                load_all_credentials()
                return handle_webhook(event)
            else:
                return {"statusCode": 405, "body": "Method Not Allowed"}

        # Direct invocation (e.g., manual test or EventBridge)
        load_all_credentials()
        transcript_id = event.get("transcript_id", "")
        if not transcript_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing transcript_id"}),
            }

        from fireflies_main import process_meeting

        result = process_meeting(transcript_id)

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
    import argparse

    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(description="Fireflies Meeting Notes Processor")
    parser.add_argument(
        "--transcript-id", required=True, help="Fireflies transcript ID to process"
    )
    args = parser.parse_args()

    # For local runs, skip Parameter Store and use .env
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
    from fireflies_main import process_meeting

    result = process_meeting(args.transcript_id)
    print(json.dumps(result, indent=2))
