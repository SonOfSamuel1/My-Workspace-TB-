"""Orchestration for Gmail Email Actions sync and daily digest modes."""

import logging
import os
from typing import Any, Dict

from email_report import send_daily_digest
from gmail_service import GmailService
from state_manager import load_state, save_state
from todoist_service import EmailActionsTodoistService

logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("STATE_BUCKET", "gmail-email-actions")
EMAIL_ACTIONS_PROJECT = "Email Actions"


def run_sync(dry_run: bool = False) -> Dict[str, Any]:
    """Poll Gmail for starred emails and create Todoist tasks for new ones.

    Args:
        dry_run: If True, log actions without creating tasks or updating state.

    Returns:
        Summary dict with counts.
    """
    logger.info(f"Starting sync (dry_run={dry_run})")

    todoist_token = os.environ["TODOIST_API_TOKEN"]
    gmail = GmailService()
    todoist = EmailActionsTodoistService(todoist_token)

    # Load existing state
    state = load_state(S3_BUCKET)
    already_processed = set(state["emails"].keys())
    cached_project_id = state.get("project_id")

    # Fetch all starred emails
    starred = gmail.get_starred_emails()
    logger.info(f"Found {len(starred)} starred emails total")

    # Get or create project (using cached ID as fast path)
    project_id = todoist.get_or_create_project(
        EMAIL_ACTIONS_PROJECT, cached_id=cached_project_id
    )

    # Auto-cleanup: remove Todoist tasks for emails no longer starred in Gmail
    current_starred_ids = {e["id"] for e in starred}
    removed_ids = set(state["emails"].keys()) - current_starred_ids
    for msg_id in removed_ids:
        task_id = state["emails"].pop(msg_id)
        if not dry_run:
            try:
                todoist.delete_task(task_id)
            except Exception as e:
                logger.warning(
                    f"Could not delete task {task_id} for removed email {msg_id}: {e}"
                )
        logger.info(f"Removed unstarred email {msg_id}, deleted task {task_id}")

    new_count = 0
    skipped_count = 0

    for email in starred:
        msg_id = email["id"]

        if msg_id in already_processed:
            logger.debug(f"Skipping already-processed email {msg_id}")
            skipped_count += 1
            continue

        logger.info(
            f"New starred email: '{email['subject']}' from {email['from']} ({msg_id})"
        )

        if not dry_run:
            task = todoist.create_task(
                project_id=project_id,
                subject=email["subject"],
                from_addr=email["from"],
                date=email["date"],
                gmail_link=email["gmail_link"],
                msg_id=email["id"],
            )
            state["emails"][msg_id] = task["id"]
            new_count += 1
        else:
            logger.info(f"[DRY RUN] Would create task for: {email['subject']}")
            new_count += 1

    if not dry_run:
        state["project_id"] = project_id
        if new_count > 0 or removed_ids or cached_project_id != project_id:
            save_state(S3_BUCKET, state)

    result = {
        "mode": "sync",
        "removed_tasks": len(removed_ids),
        "starred_total": len(starred),
        "new_tasks_created": new_count,
        "skipped_already_processed": skipped_count,
        "dry_run": dry_run,
    }
    logger.info(f"Sync complete: {result}")
    return result


def run_daily_digest(
    dry_run: bool = False, function_url: str = "", action_token: str = ""
) -> Dict[str, Any]:
    """Fetch open Email Actions tasks and send the HTML digest email.

    Args:
        dry_run: If True, log actions without sending email.
        function_url: Lambda Function URL for action links in the digest.
        action_token: Secret token for authenticating action links.

    Returns:
        Summary dict with counts.
    """
    logger.info(f"Starting daily_digest (dry_run={dry_run})")

    todoist_token = os.environ["TODOIST_API_TOKEN"]
    recipient = os.environ["REPORT_EMAIL"]
    ses_sender = os.environ["SES_SENDER_EMAIL"]

    todoist = EmailActionsTodoistService(todoist_token)

    # Use cached project ID from state if available
    state = load_state(S3_BUCKET)
    cached_project_id = state.get("project_id")

    project_id = todoist.get_or_create_project(
        EMAIL_ACTIONS_PROJECT, cached_id=cached_project_id
    )

    # Update state if project ID changed
    if project_id != cached_project_id and not dry_run:
        state["project_id"] = project_id
        save_state(S3_BUCKET, state)

    open_tasks = todoist.get_open_tasks(project_id)
    logger.info(f"Found {len(open_tasks)} open Email Actions tasks")

    trashed_count = 0
    if not dry_run:
        gmail = GmailService()
        trashed_count = gmail.trash_previous_digests()
        logger.info(f"Trashed {trashed_count} previous digest(s)")

        send_daily_digest(
            open_tasks,
            recipient=recipient,
            ses_sender=ses_sender,
            function_url=function_url,
            action_token=action_token,
        )
    else:
        logger.info(
            f"[DRY RUN] Would send digest to {recipient} with {len(open_tasks)} tasks"
        )

    result = {
        "mode": "daily_digest",
        "open_tasks": len(open_tasks),
        "recipient": recipient,
        "previous_digests_trashed": trashed_count,
        "dry_run": dry_run,
    }
    logger.info(f"Daily digest complete: {result}")
    return result


def get_open_tasks_for_web():
    """Fetch open Email Actions tasks for the web digest page."""
    todoist_token = os.environ["TODOIST_API_TOKEN"]
    todoist = EmailActionsTodoistService(todoist_token)
    state = load_state(S3_BUCKET)
    cached_project_id = state.get("project_id")
    project_id = todoist.get_or_create_project(
        EMAIL_ACTIONS_PROJECT, cached_id=cached_project_id
    )
    return todoist.get_open_tasks(project_id)


def run_unstar(msg_id: str) -> Dict[str, Any]:
    """Unstar a Gmail message and delete its corresponding Todoist task.

    Args:
        msg_id: Gmail message ID to unstar.

    Returns:
        Summary dict.
    """
    logger.info(f"Starting unstar for message {msg_id}")

    todoist_token = os.environ["TODOIST_API_TOKEN"]
    gmail = GmailService()
    todoist = EmailActionsTodoistService(todoist_token)

    state = load_state(S3_BUCKET)
    task_id = state["emails"].get(msg_id)

    gmail.unstar_email(msg_id)
    logger.info(f"Unstarred Gmail message {msg_id}")

    if task_id:
        try:
            todoist.delete_task(task_id)
        except Exception as e:
            logger.warning(f"Could not delete Todoist task {task_id}: {e}")
        del state["emails"][msg_id]
        save_state(S3_BUCKET, state)
        logger.info(f"Deleted Todoist task {task_id} and removed from state")
    else:
        logger.warning(f"No Todoist task found in state for message {msg_id}")

    return {"mode": "unstar", "msg_id": msg_id, "task_id": task_id}


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

    parser = argparse.ArgumentParser(description="Gmail Email Actions automation")
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
