"""S3-backed state manager for tracking processed Gmail message IDs."""

import json
import logging
from typing import Any, Dict

import boto3

logger = logging.getLogger(__name__)

STATE_KEY = "state/processed_emails.json"

_s3 = boto3.client("s3")


def load_state(s3_bucket: str) -> Dict[str, Any]:
    """Load state dict from S3.

    Returns:
        Dict with keys:
            emails: {gmail_message_id -> todoist_task_id}
            project_id: cached Todoist Email Actions project ID (str or None)
    """
    try:
        response = _s3.get_object(Bucket=s3_bucket, Key=STATE_KEY)
        state = json.loads(response["Body"].read())
        # Migrate old format (flat dict of email_id -> task_id)
        if "emails" not in state:
            state = {"emails": state, "project_id": None}
        logger.info(
            f"Loaded state from s3://{s3_bucket}/{STATE_KEY} "
            f"({len(state['emails'])} emails, project_id={state.get('project_id')})"
        )
        return state
    except _s3.exceptions.NoSuchKey:
        logger.info("No existing state file in S3, starting fresh")
        return {"emails": {}, "project_id": None}
    except Exception as e:
        logger.error(f"Error loading state from S3: {e}")
        return {"emails": {}, "project_id": None}


def save_state(s3_bucket: str, state: Dict[str, Any]) -> None:
    """Save state dict to S3."""
    try:
        _s3.put_object(
            Bucket=s3_bucket,
            Key=STATE_KEY,
            Body=json.dumps(state, indent=2),
            ContentType="application/json",
        )
        logger.info(
            f"Saved state to s3://{s3_bucket}/{STATE_KEY} "
            f"({len(state.get('emails', {}))} emails)"
        )
    except Exception as e:
        logger.error(f"Error saving state to S3: {e}")
        raise
