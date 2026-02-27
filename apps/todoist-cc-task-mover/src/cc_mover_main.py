"""Core logic for moving cc-prefixed tasks to the Claude Code project.

Scans Inbox and Inbox 2 for tasks starting with 'cc-' or 'cc ' (case-insensitive)
and moves them to the 'Claude Code' project.
"""

import logging
from typing import Any, Dict

from todoist_service import TodoistService

logger = logging.getLogger(__name__)

TARGET_PROJECT_NAME = "Claude Code"
INBOX_2_NAME = "Inbox 2"
CC_PREFIXES = ("cc-", "cc ")


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def move_cc_tasks(api_token: str) -> Dict[str, Any]:
    """Find cc-/cc tasks in Inbox/Inbox 2 and move them to the Claude Code project.

    Returns:
        Dict with tasks_moved, tasks_scanned, source_breakdown, and errors.
    """
    service = TodoistService(api_token)
    results = {
        "tasks_moved": 0,
        "tasks_scanned": 0,
        "source_breakdown": {},
        "errors": [],
    }

    # Find the target project
    target_project = service.get_project_by_name(TARGET_PROJECT_NAME)
    if not target_project:
        error = f"Target project '{TARGET_PROJECT_NAME}' not found"
        logger.error(error)
        results["errors"].append(error)
        return results

    target_id = target_project["id"]
    logger.info(f"Target project: '{TARGET_PROJECT_NAME}' (id={target_id})")

    # Collect source projects
    source_projects = []

    inbox = service.get_inbox_project()
    if inbox:
        source_projects.append(("Inbox", inbox))
    else:
        results["errors"].append("Official Inbox project not found")

    inbox_2 = service.get_project_by_name(INBOX_2_NAME)
    if inbox_2:
        source_projects.append((INBOX_2_NAME, inbox_2))
    else:
        logger.info(f"'{INBOX_2_NAME}' project not found — skipping")

    if not source_projects:
        error = "No source projects found"
        logger.error(error)
        results["errors"].append(error)
        return results

    # Scan each source project for cc- tasks
    for source_name, source_project in source_projects:
        source_id = source_project["id"]
        tasks = service.get_tasks_in_project(source_id)
        moved_count = 0

        for task in tasks:
            results["tasks_scanned"] += 1
            content = task.get("content", "")

            content_lower = content.lower()
            matched_prefix = next(
                (p for p in CC_PREFIXES if content_lower.startswith(p)), None
            )
            if matched_prefix:
                task_id = task["id"]
                logger.info(
                    f"Moving task '{content}' (id={task_id}) from {source_name}"
                )

                if service.move_task_to_project(task_id, target_id):
                    # Strip the cc prefix from the task name
                    new_content = content[len(matched_prefix) :].strip()
                    if new_content:
                        if not service.update_task_content(task_id, new_content):
                            results["errors"].append(
                                f"Moved but failed to rename task '{content}' (id={task_id})"
                            )
                    results["tasks_moved"] += 1
                    moved_count += 1
                else:
                    results["errors"].append(
                        f"Failed to move task '{content}' (id={task_id})"
                    )

        results["source_breakdown"][source_name] = {
            "tasks_scanned": len(tasks),
            "tasks_moved": moved_count,
        }

    return results
