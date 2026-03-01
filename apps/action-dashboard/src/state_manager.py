"""S3-backed state manager for tracking unread Gmail emails."""

import json
import logging
from typing import Any, Dict

import boto3

logger = logging.getLogger(__name__)

STATE_KEY = "state/unread_emails.json"

_s3 = boto3.client("s3")


def load_state(s3_bucket: str) -> Dict[str, Any]:
    """Load state dict from S3.

    Returns:
        Dict with keys:
            emails: {gmail_message_id -> {subject, from, date, gmail_link}}
    """
    try:
        response = _s3.get_object(Bucket=s3_bucket, Key=STATE_KEY)
        state = json.loads(response["Body"].read())
        # Migrate old format (flat dict of email_id -> task_id string)
        if "emails" not in state:
            state = {"emails": {}}
        else:
            # Migrate from old Todoist format: if any value is a plain string
            # (task_id), drop it — will be re-synced with full metadata
            migrated = {}
            for msg_id, val in state["emails"].items():
                if isinstance(val, dict):
                    migrated[msg_id] = val
                # else: old task_id string — skip, will be re-added on next sync
            state["emails"] = migrated
        # Drop legacy project_id field
        state.pop("project_id", None)
        logger.info(
            f"Loaded state from s3://{s3_bucket}/{STATE_KEY} "
            f"({len(state['emails'])} emails)"
        )
        return state
    except _s3.exceptions.NoSuchKey:
        logger.info("No existing state file in S3, starting fresh")
        return {"emails": {}}
    except Exception as e:
        logger.error(f"Error loading state from S3: {e}")
        return {"emails": {}}


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
