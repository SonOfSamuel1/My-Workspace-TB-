"""Orchestration for Gmail Unread Digest sync and daily digest modes."""

import json
import logging
import os
from typing import Any, Dict, List

from email_report import send_daily_digest
from gmail_service import GmailService
from state_manager import load_state, save_state

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("STATE_BUCKET", "gmail-unread-digest")


def run_sync(dry_run: bool = False) -> Dict[str, Any]:
    """Poll Gmail for unread primary emails and store metadata in S3 state.

    Args:
        dry_run: If True, log actions without updating state.

    Returns:
        Summary dict with counts.
    """
    logger.info(f"Starting sync (dry_run={dry_run})")

    gmail = GmailService()

    # Load existing state
    state = load_state(S3_BUCKET)
    already_processed = set(state["emails"].keys())

    # Fetch all unread primary emails
    unread = gmail.get_unread_emails()
    logger.info(f"Found {len(unread)} unread emails total")

    # Auto-cleanup: remove emails no longer unread in Gmail
    current_unread_ids = {e["id"] for e in unread}
    removed_ids = set(state["emails"].keys()) - current_unread_ids
    for msg_id in removed_ids:
        del state["emails"][msg_id]
        logger.info(f"Removed read email {msg_id} from state")

    new_count = 0
    skipped_count = 0

    for email in unread:
        msg_id = email["id"]

        if msg_id in already_processed:
            logger.debug(f"Skipping already-processed email {msg_id}")
            skipped_count += 1
            continue

        logger.info(
            f"New unread email: '{email['subject']}' from {email['from']} ({msg_id})"
        )

        if not dry_run:
            state["emails"][msg_id] = {
                "subject": email["subject"],
                "from": email["from"],
                "date": email["date"],
                "gmail_link": email["gmail_link"],
            }
            new_count += 1
        else:
            logger.info(f"[DRY RUN] Would store metadata for: {email['subject']}")
            new_count += 1

    if not dry_run:
        if new_count > 0 or removed_ids:
            save_state(S3_BUCKET, state)

    result = {
        "mode": "sync",
        "removed": len(removed_ids),
        "unread_total": len(unread),
        "new_stored": new_count,
        "skipped_already_processed": skipped_count,
        "dry_run": dry_run,
    }
    logger.info(f"Sync complete: {result}")
    return result


def run_followup_sync(dry_run: bool = False) -> Dict[str, Any]:
    """Poll Gmail for sent threads awaiting follow-up and cache metadata in S3.

    Args:
        dry_run: If True, log actions without updating state.

    Returns:
        Summary dict with counts.
    """
    logger.info(f"Starting followup_sync (dry_run={dry_run})")

    gmail = GmailService()
    emails = gmail.get_awaiting_followup_emails(days=30)
    logger.info(f"Found {len(emails)} threads awaiting follow-up")

    bucket = os.environ.get("STATE_BUCKET", "gmail-unread-digest")
    key = "actionos/followup_state.json"

    # Load existing state
    try:
        import boto3

        s3 = boto3.client("s3", region_name="us-east-1")
        obj = s3.get_object(Bucket=bucket, Key=key)
        state = json.loads(obj["Body"].read())
    except Exception:
        state = {"emails": {}, "reviews": {}, "resolved": {}}

    # Ensure all state keys exist
    state.setdefault("emails", {})
    state.setdefault("reviews", {})
    state.setdefault("resolved", {})

    import datetime as _dt

    synced_at = _dt.datetime.now(_dt.timezone.utc).isoformat()

    # Update emails: skip resolved threads, add/update current ones
    resolved = state["resolved"]
    new_emails: dict = {}
    for email in emails:
        tid = email["threadId"]
        if tid in resolved:
            continue
        new_emails[tid] = {
            "id": email["id"],
            "subject": email["subject"],
            "to": email["to"],
            "date": email["date"],
            "gmail_link": email["gmail_link"],
            "thread_message_count": email["thread_message_count"],
            "synced_at": synced_at,
        }

    state["emails"] = new_emails

    # Clean up reviews for threads no longer present
    state["reviews"] = {
        tid: ts for tid, ts in state["reviews"].items() if tid in new_emails
    }

    if not dry_run:
        import json as _json

        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=_json.dumps(state),
            ContentType="application/json",
        )
    else:
        logger.info(
            f"[DRY RUN] Would write followup state with {len(new_emails)} threads"
        )

    result = {
        "mode": "followup_sync",
        "threads_found": len(emails),
        "threads_stored": len(new_emails),
        "dry_run": dry_run,
    }
    logger.info(f"Followup sync complete: {result}")
    return result


def run_daily_digest(
    dry_run: bool = False, function_url: str = "", action_token: str = ""
) -> Dict[str, Any]:
    """Read email metadata from S3 state and send the HTML digest email.

    Args:
        dry_run: If True, log actions without sending email.
        function_url: Lambda Function URL for action links in the digest.
        action_token: Secret token for authenticating action links.

    Returns:
        Summary dict with counts.
    """
    logger.info(f"Starting daily_digest (dry_run={dry_run})")

    recipient = os.environ["REPORT_EMAIL"]
    ses_sender = os.environ["SES_SENDER_EMAIL"]

    state = load_state(S3_BUCKET)
    emails = _state_to_email_list(state)
    logger.info(f"Found {len(emails)} unread emails in state")

    trashed_count = 0
    if not dry_run:
        gmail = GmailService()
        trashed_count = gmail.trash_previous_digests()
        logger.info(f"Trashed {trashed_count} previous digest(s)")

        send_daily_digest(
            emails,
            recipient=recipient,
            ses_sender=ses_sender,
            function_url=function_url,
            action_token=action_token,
        )
    else:
        logger.info(
            f"[DRY RUN] Would send digest to {recipient} with {len(emails)} emails"
        )

    result = {
        "mode": "daily_digest",
        "unread_emails": len(emails),
        "recipient": recipient,
        "previous_digests_trashed": trashed_count,
        "dry_run": dry_run,
    }
    logger.info(f"Daily digest complete: {result}")
    return result


def get_unread_emails_for_web() -> List[Dict[str, Any]]:
    """Fetch unread emails live from Gmail for the web digest page."""
    gmail = GmailService()
    return gmail.get_unread_emails()


def _state_to_email_list(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert state dict to a list of email dicts with 'id' key included."""
    emails = []
    for msg_id, meta in state.get("emails", {}).items():
        email = dict(meta)
        email["id"] = msg_id
        emails.append(email)
    return emails


def run_mark_read(msg_id: str) -> Dict[str, Any]:
    """Mark a Gmail message as read and remove it from S3 state.

    Args:
        msg_id: Gmail message ID to mark as read.

    Returns:
        Summary dict.
    """
    logger.info(f"Starting mark_read for message {msg_id}")

    gmail = GmailService()

    state = load_state(S3_BUCKET)

    gmail.mark_read(msg_id)
    logger.info(f"Marked Gmail message {msg_id} as read")

    if msg_id in state["emails"]:
        del state["emails"][msg_id]
        save_state(S3_BUCKET, state)
        logger.info(f"Removed message {msg_id} from state")
    else:
        logger.warning(f"Message {msg_id} not found in state")

    return {"mode": "markread", "msg_id": msg_id}


def run_rerun_digest() -> Dict[str, Any]:
    """Immediately send a fresh digest email.

    Returns:
        Summary dict from run_daily_digest.
    """
    logger.info("Starting rerun digest")
    function_url = os.environ.get("FUNCTION_URL", "")
    action_token = os.environ.get("ACTION_TOKEN", "")
    return run_daily_digest(
        dry_run=False, function_url=function_url, action_token=action_token
    )


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    parser = argparse.ArgumentParser(description="Gmail Unread Digest automation")
    parser.add_argument(
        "--mode",
        choices=["sync", "daily_digest"],
        default="sync",
        help="Execution mode",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Log actions without side effects"
    )
    args = parser.parse_args()

    if args.mode == "sync":
        run_sync(dry_run=args.dry_run)
    else:
        run_daily_digest(dry_run=args.dry_run)
