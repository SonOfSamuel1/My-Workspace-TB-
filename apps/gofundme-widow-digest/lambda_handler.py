"""AWS Lambda handler for GoFundMe Widow Digest.

Triggered weekly by EventBridge to search GoFundMe for widow campaigns
and create a digest task in Todoist.
"""

import json
import os
from datetime import datetime, timedelta

import boto3
import yaml

from gofundme_search import search_campaigns
from todoist_task_creator import create_digest_task
from email_digest import send_digest_email


def load_credentials():
    """Load secrets from AWS Parameter Store."""
    ssm = boto3.client("ssm", region_name="us-east-1")
    prefix = "/gofundme-widow-digest"

    params = {
        "TODOIST_API_TOKEN": f"{prefix}/todoist-api-token",
        "DIGEST_RECIPIENT_EMAIL": f"{prefix}/recipient-email",
    }
    for env_key, param_name in params.items():
        resp = ssm.get_parameter(Name=param_name, WithDecryption=True)
        os.environ[env_key] = resp["Parameter"]["Value"]


def load_config():
    """Load config.yaml from the Lambda package."""
    config_paths = ["config.yaml", "/var/task/config.yaml"]
    for path in config_paths:
        if os.path.exists(path):
            with open(path) as f:
                return yaml.safe_load(f)["gofundme_widow_digest"]
    raise FileNotFoundError("config.yaml not found")


def get_week_label():
    """Return a human-readable label for the current week."""
    today = datetime.utcnow()
    week_ago = today - timedelta(days=7)
    return f"{week_ago.strftime('%b %-d')} - {today.strftime('%b %-d, %Y')}"


def lambda_handler(event, context):
    """Main Lambda entry point."""
    print(f"Event: {json.dumps(event)}")

    load_credentials()
    config = load_config()

    print("Searching GoFundMe for widow campaigns...")
    campaigns = search_campaigns(config)
    print(f"Found {len(campaigns)} campaigns matching criteria")

    if not campaigns:
        print("No campaigns found this week. Skipping Todoist task creation.")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "No campaigns found", "count": 0}),
        }

    # Limit to max campaigns
    max_campaigns = config.get("max_campaigns_per_digest", 15)
    campaigns = campaigns[:max_campaigns]

    week_label = get_week_label()
    todoist_token = os.environ["TODOIST_API_TOKEN"]

    print(f"Creating Todoist digest task with {len(campaigns)} campaigns...")
    task = create_digest_task(
        campaigns=campaigns,
        todoist_token=todoist_token,
        config=config["todoist"],
        week_label=week_label,
    )

    print(f"Created Todoist task: {task.get('id')} - {task.get('content')}")

    print("Sending digest email...")
    email_sent = send_digest_email(campaigns, week_label)
    print(f"Email sent: {email_sent}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Digest created",
            "count": len(campaigns),
            "task_id": task.get("id"),
            "email_sent": email_sent,
        }),
    }
