"""Main module for Todoist daily reminders automation.

This module creates reminders at 8am, 11am, 4pm, and 7pm for all tasks
that are due today or overdue and have the @commit label.
"""

import logging
import os
import sys
from datetime import date, datetime, time
from typing import List, Tuple

import pytz
from todoist_service import TodoistService

# Configure logging
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_LABEL = "commit"
DEFAULT_TIMEZONE = "America/New_York"
DEFAULT_REMINDER_TIMES = [
    (8, 0),  # 8:00 AM
    (11, 0),  # 11:00 AM
    (16, 0),  # 4:00 PM
    (19, 0),  # 7:00 PM
]


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_reminder_datetimes(
    target_date: date, reminder_hours: List[Tuple[int, int]], timezone_str: str
) -> List[datetime]:
    """Generate reminder datetime objects for the specified times.

    Args:
        target_date: The date for the reminders
        reminder_hours: List of (hour, minute) tuples
        timezone_str: Timezone string (e.g., 'America/New_York')

    Returns:
        List of timezone-aware datetime objects
    """
    tz = pytz.timezone(timezone_str)
    now = datetime.now(tz)

    reminder_datetimes = []
    for hour, minute in reminder_hours:
        reminder_dt = tz.localize(datetime.combine(target_date, time(hour, minute)))
        # Only include reminders that are in the future
        if reminder_dt > now:
            reminder_datetimes.append(reminder_dt)
        else:
            logger.info(f"Skipping {hour:02d}:{minute:02d} reminder - time has passed")

    return reminder_datetimes


def process_tasks_and_create_reminders(
    api_token: str,
    label_name: str = DEFAULT_LABEL,
    timezone_str: str = DEFAULT_TIMEZONE,
    reminder_times: List[Tuple[int, int]] = None,
    clear_existing: bool = True,
) -> dict:
    """Fetch tasks with the specified label and create reminders.

    Args:
        api_token: Todoist API token
        label_name: Label to filter tasks by (without @)
        timezone_str: Timezone for reminders
        reminder_times: List of (hour, minute) tuples for reminder times
        clear_existing: Whether to clear existing reminders before adding new ones

    Returns:
        Dictionary with processing results
    """
    if reminder_times is None:
        reminder_times = DEFAULT_REMINDER_TIMES

    service = TodoistService(api_token)
    today = date.today()
    results = {
        "tasks_found": 0,
        "reminders_created": 0,
        "reminders_deleted": 0,
        "errors": [],
    }

    try:
        # Set today as due date for any @commit tasks with no due date
        logger.info(f"Checking for undated tasks with @{label_name} label...")
        undated_tasks = service.get_undated_tasks_with_label(label_name)
        for task in undated_tasks:
            task_id = task["id"]
            task_content = task.get("content", "Unknown task")[:50]
            logger.info(
                f"Setting due date to today for undated task: {task_content}..."
            )
            service.set_due_date_today(task_id)

        # Get tasks due today or overdue with the @commit label
        logger.info(f"Fetching tasks due today or overdue with @{label_name} label...")
        tasks = service.get_tasks_due_today_with_label(label_name)
        results["tasks_found"] = len(tasks)

        if not tasks:
            logger.info(f"No tasks found due today or overdue with @{label_name} label")
            return results

        # Get reminder times that are still in the future
        reminder_datetimes = get_reminder_datetimes(today, reminder_times, timezone_str)

        if not reminder_datetimes:
            logger.info("All reminder times have passed for today")
            return results

        # Get all existing reminders if we need to clear them
        existing_reminders = []
        if clear_existing:
            logger.info("Fetching existing reminders...")
            existing_reminders = service.get_existing_reminders()

        # Process each task
        for task in tasks:
            task_id = task["id"]
            task_content = task.get("content", "Unknown task")[:50]
            logger.info(f"Processing task: {task_content}...")

            # Clear existing reminders for this task if requested
            if clear_existing:
                task_reminders = service.get_reminders_for_task(
                    task_id, existing_reminders
                )

                for reminder in task_reminders:
                    reminder_id = reminder.get("id")
                    if reminder_id:
                        if service.delete_reminder(reminder_id):
                            results["reminders_deleted"] += 1

            # Create new reminders at each specified time
            for reminder_dt in reminder_datetimes:
                result = service.create_reminder(
                    task_id=task_id, reminder_time=reminder_dt, timezone=timezone_str
                )

                if result:
                    results["reminders_created"] += 1
                else:
                    error_msg = (
                        f"Failed to create reminder for task {task_id} "
                        f"at {reminder_dt.strftime('%I:%M %p')}"
                    )
                    results["errors"].append(error_msg)
                    logger.error(error_msg)

        logger.info("=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Tasks found: {results['tasks_found']}")
        logger.info(f"Reminders created: {results['reminders_created']}")
        logger.info(f"Reminders deleted: {results['reminders_deleted']}")
        if results["errors"]:
            logger.warning(f"Errors: {len(results['errors'])}")
        logger.info("=" * 60)

        return results

    except Exception as e:
        logger.error(f"Error processing tasks: {e}", exc_info=True)
        results["errors"].append(str(e))
        return results


def main():
    """Main entry point for the daily reminders automation."""
    setup_logging()

    logger.info("=" * 60)
    logger.info("TODOIST DAILY REMINDERS - Starting execution")
    logger.info("=" * 60)

    # Get API token from environment
    api_token = os.environ.get("TODOIST_API_TOKEN")
    if not api_token:
        logger.error("TODOIST_API_TOKEN environment variable is required")
        sys.exit(1)

    # Get optional configuration from environment
    label_name = os.environ.get("TODOIST_LABEL", DEFAULT_LABEL)
    timezone_str = os.environ.get("TODOIST_TIMEZONE", DEFAULT_TIMEZONE)

    # Parse custom reminder times if provided
    reminder_times = DEFAULT_REMINDER_TIMES
    custom_times = os.environ.get("TODOIST_REMINDER_TIMES")
    if custom_times:
        try:
            # Expected format: "08:00,11:00,16:00,19:00"
            reminder_times = []
            for time_str in custom_times.split(","):
                hour, minute = map(int, time_str.strip().split(":"))
                reminder_times.append((hour, minute))
            logger.info(f"Using custom reminder times: {reminder_times}")
        except ValueError as e:
            logger.warning(
                f"Invalid TODOIST_REMINDER_TIMES format: {e}. Using defaults."
            )
            reminder_times = DEFAULT_REMINDER_TIMES

    # Process tasks and create reminders
    results = process_tasks_and_create_reminders(
        api_token=api_token,
        label_name=label_name,
        timezone_str=timezone_str,
        reminder_times=reminder_times,
    )

    if results["errors"]:
        logger.warning(f"Completed with {len(results['errors'])} errors")
        sys.exit(1)
    else:
        logger.info("Completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
