"""AWS Lambda handler for Eight Sleep -> Toggl sleep sync."""

import json
import logging
import os
import sys

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm = boto3.client("ssm")


def get_parameter(name: str) -> str:
    resp = ssm.get_parameter(Name=name, WithDecryption=True)
    return resp["Parameter"]["Value"]


def load_credentials():
    """Load credentials from AWS SSM Parameter Store."""
    os.environ["EIGHT_SLEEP_EMAIL"] = get_parameter(
        "/eight-sleep-toggl-sync/eight-sleep-email"
    )
    os.environ["EIGHT_SLEEP_PASSWORD"] = get_parameter(
        "/eight-sleep-toggl-sync/eight-sleep-password"
    )
    os.environ["TOGGL_API_TOKEN"] = get_parameter(
        "/eight-sleep-toggl-sync/toggl-api-token"
    )
    os.environ["TOGGL_WORKSPACE_ID"] = get_parameter(
        "/eight-sleep-toggl-sync/toggl-workspace-id"
    )


def handler(event, context):
    """Lambda entry point. Triggered daily by EventBridge."""
    try:
        load_credentials()

        # Add src to path for imports
        src_dir = os.path.join(os.path.dirname(__file__), "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        from src.main import sync

        result = sync()
        logger.info(f"Sync result: {result}")

        return {
            "statusCode": 200,
            "body": json.dumps(result),
        }

    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
