"""AWS Lambda handler for Gmail Email Actions automation.

Two invocation modes:
- sync (every 5 min via EventBridge): polls Gmail starred emails, creates Todoist tasks
- daily_digest (8 AM ET via EventBridge): sends HTML email digest of open Email Actions tasks
"""

import base64
import json
import logging
import os
import sys

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
        logger.error(f"Failed to get parameter {param_name}: {str(e)}")
        raise


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

    logger.info("All credentials loaded successfully")


def lambda_handler(event, context):
    """Main Lambda handler.

    Event fields:
        mode: 'sync' (default) or 'daily_digest'
        dry_run: bool (default False)
    """
    logger.info("=" * 60)
    logger.info("GMAIL EMAIL ACTIONS LAMBDA - Starting")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 60)

    try:
        load_credentials()

        mode = event.get("mode", "sync")
        dry_run = event.get("dry_run", False)

        from email_actions_main import run_daily_digest, run_sync

        if mode == "daily_digest":
            logger.info("Running in daily_digest mode")
            result = run_daily_digest(dry_run=dry_run)
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
