"""Core logic for moving prefixed tasks to their respective projects.

Scans Inbox and Inbox 2 for tasks with specific prefixes and moves them to
their corresponding target projects:
- 'cc-' or 'cc ' → Claude Code
- 'event prep:' → Event Prep
- 'cal' → Schedule Calendar Event
- 'Take detailed notes:' → Take Detailed Notes
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from todoist_service import TodoistService

logger = logging.getLogger(__name__)

INBOX_2_NAME = "Inbox 2"

# Mapping of prefix patterns to target project names
# Each prefix is (pattern, project_name, strip_prefix_flag)
PREFIX_TO_PROJECT = [
    ("cc-", "Claude Code", True),
    ("cc ", "Claude Code", True),
    ("event prep:", "Event Prep", True),
    ("cal ", "Schedule Calendar Event", True),
    ("Take detailed notes:", "Take Detailed Notes", True),
]


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def _find_matching_prefix(
    content: str, prefixes: List[Tuple[str, str, bool]]
) -> Optional[Tuple[str, str, bool]]:
    """Find the first matching prefix for a task content.

    Args:
        content: Task content to check
        prefixes: List of (prefix_pattern, project_name, strip_flag) tuples

    Returns:
        Tuple of (matched_prefix, target_project, strip_prefix) or None
    """
    content_lower = content.lower()
    for prefix_pattern, target_project, strip_flag in prefixes:
        if content_lower.startswith(prefix_pattern.lower()):
            return (prefix_pattern, target_project, strip_flag)
    return None


def move_cc_tasks(api_token: str) -> Dict[str, Any]:
    """Find prefixed tasks in Inbox/Inbox 2 and move them to their target projects.

    Handles multiple prefixes with their corresponding projects.

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

    # Cache target projects to avoid repeated lookups
    target_projects_cache = {}
    for prefix_pattern, project_name, _ in PREFIX_TO_PROJECT:
        if project_name not in target_projects_cache:
            project = service.get_project_by_name(project_name)
            if not project:
                error = f"Target project '{project_name}' not found"
                logger.error(error)
                results["errors"].append(error)
            else:
                target_projects_cache[project_name] = project["id"]
                logger.info(f"Target project: '{project_name}' (id={project['id']})")

    if not target_projects_cache:
        error = "No target projects found"
        logger.error(error)
        results["errors"].append(error)
        return results

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

    # Scan each source project for prefixed tasks
    for source_name, source_project in source_projects:
        source_id = source_project["id"]
        tasks = service.get_tasks_in_project(source_id)
        moved_count = 0

        for task in tasks:
            results["tasks_scanned"] += 1
            content = task.get("content", "")

            match = _find_matching_prefix(content, PREFIX_TO_PROJECT)
            if match:
                matched_prefix, target_project_name, strip_flag = match
                target_id = target_projects_cache.get(target_project_name)

                if not target_id:
                    logger.warning(
                        f"Skipping task '{content}' — target project '{target_project_name}' not available"
                    )
                    continue

                task_id = task["id"]
                logger.info(
                    f"Moving task '{content}' (id={task_id}) from {source_name} to '{target_project_name}'"
                )

                if service.move_task_to_project(task_id, target_id):
                    # Strip the prefix from the task name if flagged
                    if strip_flag:
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
