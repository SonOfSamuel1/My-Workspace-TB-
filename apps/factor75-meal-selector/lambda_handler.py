#!/usr/bin/env python3
"""
AWS Lambda Handler for Factor 75 Meal Selector

Handles scheduled events from EventBridge:
- scrape_and_email: Weekly trigger to scrape meals and send selection email
- check_replies: Periodic trigger to check for email replies
- submit_selections: Triggered when valid reply found

Environment variables required in Lambda:
- FACTOR75_EMAIL
- FACTOR75_PASSWORD
- USER_EMAIL
- SES_SENDER_EMAIL
- AWS_REGION (set automatically by Lambda)

For Gmail credentials, store in Parameter Store:
- /factor75-selector/gmail-credentials (base64 JSON)
- /factor75-selector/gmail-token (base64 pickle)
"""

import base64
import json
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import boto3  # noqa: E402

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_parameter(name: str, decrypt: bool = True) -> str:
    """Get parameter from AWS Parameter Store."""
    ssm = boto3.client("ssm")
    response = ssm.get_parameter(
        Name=name,
        WithDecryption=decrypt,
    )
    return response["Parameter"]["Value"]


def setup_credentials():
    """
    Set up credentials from Parameter Store for Lambda execution.

    In Lambda, we can't use OAuth flow interactively, so credentials
    must be pre-stored in Parameter Store.
    """
    prefix = os.getenv("AWS_PARAMETER_PREFIX", "/factor75-selector")

    # Set Factor 75 credentials from Parameter Store
    try:
        if not os.getenv("FACTOR75_EMAIL"):
            os.environ["FACTOR75_EMAIL"] = get_parameter(f"{prefix}/factor75-email")
        if not os.getenv("FACTOR75_PASSWORD"):
            os.environ["FACTOR75_PASSWORD"] = get_parameter(
                f"{prefix}/factor75-password"
            )
        if not os.getenv("USER_EMAIL"):
            os.environ["USER_EMAIL"] = get_parameter(f"{prefix}/user-email")
        if not os.getenv("SES_SENDER_EMAIL"):
            os.environ["SES_SENDER_EMAIL"] = get_parameter(f"{prefix}/ses-sender-email")
    except Exception as e:
        logger.warning(f"Could not load some parameters from SSM: {e}")

    # Set up Gmail credentials
    try:
        gmail_creds = get_parameter(f"{prefix}/gmail-credentials")
        gmail_token = get_parameter(f"{prefix}/gmail-token")

        # Write credentials to /tmp (Lambda's writable directory)
        creds_path = "/tmp/gmail_credentials.json"
        token_path = "/tmp/gmail_token.pickle"

        with open(creds_path, "w") as f:
            f.write(base64.b64decode(gmail_creds).decode("utf-8"))

        with open(token_path, "wb") as f:
            f.write(base64.b64decode(gmail_token))

        os.environ["GMAIL_CREDENTIALS_PATH"] = creds_path
        os.environ["GMAIL_TOKEN_PATH"] = token_path

        logger.info("Gmail credentials loaded from Parameter Store")
    except Exception as e:
        logger.warning(f"Could not load Gmail credentials: {e}")


def handle_scrape_and_email(event: dict, context) -> dict:
    """
    Handle scrape_and_email action.

    This would normally use Playwright to scrape Factor 75.
    For Lambda deployment, consider using:
    - Browserbase API for cloud browser
    - Or running Playwright in Lambda container

    For now, sends test email with mock data.
    """
    from factor75_main import Factor75MealSelector

    logger.info("Starting scrape_and_email action")

    selector = Factor75MealSelector()
    success = selector.scrape_and_send_email(
        no_email=event.get("no_email", False),
        use_mock_data=event.get("use_mock_data", True),  # Default to mock for Lambda
    )

    return {
        "statusCode": 200 if success else 500,
        "body": json.dumps(
            {
                "action": "scrape_and_email",
                "success": success,
            }
        ),
    }


def handle_check_replies(event: dict, context) -> dict:
    """
    Handle check_replies action.

    Checks Gmail for replies to the selection email.
    """
    from factor75_main import Factor75MealSelector

    logger.info("Starting check_replies action")

    selector = Factor75MealSelector()
    result = selector.check_replies(dry_run=event.get("dry_run", False))

    if result and result.is_valid:
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "action": "check_replies",
                    "found_valid_reply": True,
                    "meal_numbers": result.meal_numbers,
                    "total_count": result.total_count,
                }
            ),
        }
    else:
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "action": "check_replies",
                    "found_valid_reply": False,
                }
            ),
        }


def handle_submit_selections(event: dict, context) -> dict:
    """
    Handle submit_selections action.

    Submits pending selections to Factor 75.
    Note: In Lambda, this generates instructions but actual submission
    requires browser automation (Browserbase or similar).
    """
    from factor75_main import Factor75MealSelector

    logger.info("Starting submit_selections action")

    selector = Factor75MealSelector()
    success = selector.submit_selections(dry_run=event.get("dry_run", False))

    return {
        "statusCode": 200 if success else 500,
        "body": json.dumps(
            {
                "action": "submit_selections",
                "success": success,
            }
        ),
    }


def lambda_handler(event: dict, context):
    """
    Main Lambda handler.

    Event format:
    {
        "action": "scrape_and_email" | "check_replies" | "submit_selections",
        "no_email": false,     # Optional, for testing
        "dry_run": false,      # Optional, for testing
        "use_mock_data": true  # Optional, use mock data instead of scraping
    }

    EventBridge scheduled events will include:
    {
        "action": "scrape_and_email"
    }
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Handle EventBridge scheduled events
    if "source" in event and event["source"] == "aws.events":
        # Extract action from rule name or detail
        detail = event.get("detail", {})
        action = detail.get("action", "scrape_and_email")
        event = {"action": action}

    # Set up credentials from Parameter Store
    setup_credentials()

    action = event.get("action", "scrape_and_email")

    handlers = {
        "scrape_and_email": handle_scrape_and_email,
        "check_replies": handle_check_replies,
        "submit_selections": handle_submit_selections,
    }

    handler = handlers.get(action)
    if not handler:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "error": f"Unknown action: {action}",
                    "valid_actions": list(handlers.keys()),
                }
            ),
        }

    try:
        return handler(event, context)
    except Exception as e:
        logger.error(f"Error handling {action}: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": str(e),
                    "action": action,
                }
            ),
        }


# For local testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Lambda handler locally")
    parser.add_argument(
        "--action",
        default="scrape_and_email",
        choices=["scrape_and_email", "check_replies", "submit_selections"],
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-email", action="store_true")
    parser.add_argument("--mock-data", action="store_true")

    args = parser.parse_args()

    event = {
        "action": args.action,
        "dry_run": args.dry_run,
        "no_email": args.no_email,
        "use_mock_data": args.mock_data,
    }

    result = lambda_handler(event, None)
    print(json.dumps(result, indent=2))
