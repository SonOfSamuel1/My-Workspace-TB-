"""Orchestration for the daily Inbox Digest.

Fetches inbox tasks from Todoist, trashes previous digest emails via Gmail,
and sends a new HTML digest via SES.
"""

import logging
import os

logger = logging.getLogger(__name__)


def run_daily_digest():
    """Run the full daily digest pipeline.

    Reads configuration from environment variables:
      - TODOIST_API_TOKEN
      - REPORT_EMAIL (recipient)
      - SES_SENDER_EMAIL
      - FUNCTION_URL (Lambda Function URL for action links)
      - ACTION_TOKEN (secret token for action links)
      - GMAIL_CREDENTIALS_PATH
      - GMAIL_TOKEN_PATH
    """
    from email_report import send_daily_digest
    from gmail_service import GmailService
    from todoist_service import TodoistService

    todoist_token = os.environ["TODOIST_API_TOKEN"]
    recipient = os.environ["REPORT_EMAIL"]
    ses_sender = os.environ["SES_SENDER_EMAIL"]
    function_url = os.environ.get("FUNCTION_URL", "")
    action_token = os.environ.get("ACTION_TOKEN", "")
    web_dashboard_url = os.environ.get("WEB_DASHBOARD_URL", "")

    # 1. Fetch inbox tasks from Todoist
    logger.info("Fetching inbox tasks from Todoist...")
    service = TodoistService(todoist_token)
    projects = service.get_all_projects()
    tasks = service.get_inbox_tasks(projects=projects)

    # Sort oldest-first by added_at (email_report also sorts, but we log the count here)
    tasks.sort(key=lambda t: t.get("added_at", "") or t.get("created_at", "") or "")
    logger.info(f"Found {len(tasks)} inbox tasks")

    # 2. Trash previous digest emails via Gmail
    logger.info("Trashing previous digest emails...")
    try:
        gmail = GmailService()
        gmail.connect()
        trashed = gmail.trash_previous_digests()
        logger.info(f"Trashed {trashed} previous digest email(s)")
    except Exception as e:
        logger.warning(f"Could not trash previous digests (non-fatal): {e}")

    # 3. Send new digest via SES
    logger.info("Sending inbox digest email...")
    send_daily_digest(
        tasks=tasks,
        projects=projects,
        recipient=recipient,
        ses_sender=ses_sender,
        function_url=function_url,
        action_token=action_token,
        web_dashboard_url=web_dashboard_url,
    )
    logger.info("Daily digest complete")
