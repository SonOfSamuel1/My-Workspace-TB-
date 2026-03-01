"""Core business logic for Todoist Inbox Manager.

Keeps the official Inbox under INBOX_TASK_LIMIT by moving the oldest
tasks to overflow projects ("Inbox 2", "Inbox 3", …) and maintains a
permanent navigator task inside the Inbox that links to those projects
with live task counts.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytz
from inbox_service import InboxService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INBOX_TASK_LIMIT = 250  # Move tasks out when Inbox reaches this count
OVERFLOW_TASK_LIMIT = 290  # Max tasks per overflow inbox before creating the next
NAVIGATOR_TASK_NAME = "⚡ INBOX MANAGER — Overflow Inboxes"
DEFAULT_TIMEZONE = "America/New_York"
MAX_OVERFLOW_NUM = 10  # Safety cap — never create beyond Inbox 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def _format_timestamp(timezone_str: str = DEFAULT_TIMEZONE) -> str:
    tz = pytz.timezone(timezone_str)
    now = datetime.now(tz)
    return now.strftime("%Y-%m-%d %I:%M %p %Z")


def _build_navigator_description(
    overflow_projects: List[Dict[str, Any]],
    timezone_str: str = DEFAULT_TIMEZONE,
) -> str:
    """Build the description text for the navigator task."""
    timestamp = _format_timestamp(timezone_str)

    if not overflow_projects:
        return (
            "✅ Inbox is within limits. No overflow inboxes needed.\n\n"
            f"Last updated: {timestamp}\n"
            "Auto-managed. Do not delete — it will be recreated automatically."
        )

    lines = [
        "📊 Inbox Overflow Summary",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    for proj in overflow_projects:
        name = proj["name"]
        count = proj["task_count"]
        pid = proj["id"]
        url = f"https://todoist.com/app/project/{pid}"
        lines.append(f"📁 {name}: {count} tasks → {url}")

    lines.append("")
    lines.append(f"Last updated: {timestamp}")
    lines.append("Auto-managed. Do not delete — it will be recreated automatically.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def manage_inbox(
    api_token: str,
    timezone_str: str = DEFAULT_TIMEZONE,
) -> Dict[str, Any]:
    """Run one cycle of inbox management.

    Steps:
    1. Find the real Inbox project.
    2. Count inbox tasks (excluding the navigator task).
    3. If count > INBOX_TASK_LIMIT, move oldest tasks to overflow project(s).
    4. Scan all overflow inboxes for live task counts.
    5. Upsert the navigator task with current overflow info.

    Returns:
        dict with keys: tasks_moved, overflow_projects, errors, inbox_count_before,
        inbox_count_after, navigator_action.
    """
    service = InboxService(api_token)
    results: Dict[str, Any] = {
        "tasks_moved": 0,
        "overflow_projects": [],
        "errors": [],
        "inbox_count_before": 0,
        "inbox_count_after": 0,
        "navigator_action": "none",
    }

    # ------------------------------------------------------------------
    # Step 1 — Find Inbox
    # ------------------------------------------------------------------
    inbox = service.get_inbox_project()
    if inbox is None:
        msg = "Could not locate the Inbox project"
        logger.error(msg)
        results["errors"].append(msg)
        return results

    inbox_id = inbox["id"]
    logger.info(f"Inbox project id: {inbox_id}")

    # ------------------------------------------------------------------
    # Step 2 — Count inbox tasks (excluding navigator)
    # ------------------------------------------------------------------
    all_inbox_tasks = service.get_tasks_in_project(inbox_id)
    real_tasks = [t for t in all_inbox_tasks if t.get("content") != NAVIGATOR_TASK_NAME]
    count = len(real_tasks)
    results["inbox_count_before"] = count
    logger.info(f"Inbox has {count} real tasks (limit: {INBOX_TASK_LIMIT})")

    # ------------------------------------------------------------------
    # Step 3 — Move oldest tasks out if needed
    # ------------------------------------------------------------------
    if count > INBOX_TASK_LIMIT:
        tasks_to_move_count = count - INBOX_TASK_LIMIT
        logger.info(f"Need to move {tasks_to_move_count} tasks out of Inbox")

        # Sort by added_at ascending (oldest first); API v1 uses added_at
        sorted_tasks = sorted(
            real_tasks,
            key=lambda t: t.get("added_at", ""),
        )
        tasks_to_move = sorted_tasks[:tasks_to_move_count]

        current_overflow_num = 2

        # Cache: overflow_num -> project dict
        overflow_cache: Dict[int, Dict[str, Any]] = {}

        def _get_or_create_overflow(num: int) -> Optional[Dict[str, Any]]:
            if num in overflow_cache:
                return overflow_cache[num]
            name = f"Inbox {num}"
            proj = service.get_project_by_name(name)
            if proj is None:
                proj = service.create_project(name)
            overflow_cache[num] = proj
            return proj

        def _task_count_for_overflow(num: int) -> int:
            proj = overflow_cache.get(num)
            if proj is None:
                return 0
            tasks = service.get_tasks_in_project(proj["id"])
            return len(tasks)

        for task in tasks_to_move:
            # Find a project with capacity
            while current_overflow_num <= MAX_OVERFLOW_NUM:
                proj = _get_or_create_overflow(current_overflow_num)
                if proj is None:
                    msg = f"Could not get/create Inbox {current_overflow_num}"
                    logger.error(msg)
                    results["errors"].append(msg)
                    break

                existing_count = _task_count_for_overflow(current_overflow_num)
                if existing_count < OVERFLOW_TASK_LIMIT:
                    break  # This project has capacity
                else:
                    logger.info(
                        f"Inbox {current_overflow_num} is full "
                        f"({existing_count} tasks), moving to next"
                    )
                    current_overflow_num += 1
            else:
                msg = (
                    f"Reached overflow cap (Inbox {MAX_OVERFLOW_NUM}). Stopping moves."
                )
                logger.error(msg)
                results["errors"].append(msg)
                break

            proj = overflow_cache.get(current_overflow_num)
            if proj is None:
                continue

            success = service.move_task_to_project(task["id"], proj["id"])
            if success:
                results["tasks_moved"] += 1
            else:
                results["errors"].append(f"Failed to move task {task['id']}")

    # ------------------------------------------------------------------
    # Step 4 — Scan all overflow inboxes for live counts
    # ------------------------------------------------------------------
    overflow_projects: List[Dict[str, Any]] = []
    num = 2
    while num <= MAX_OVERFLOW_NUM:
        name = f"Inbox {num}"
        proj = service.get_project_by_name(name)
        if proj is None:
            break  # No more overflow inboxes
        tasks = service.get_tasks_in_project(proj["id"])
        overflow_projects.append(
            {
                "name": name,
                "id": proj["id"],
                "task_count": len(tasks),
            }
        )
        num += 1

    results["overflow_projects"] = overflow_projects

    # Recount inbox tasks after moves
    post_inbox_tasks = service.get_tasks_in_project(inbox_id)
    results["inbox_count_after"] = len(
        [t for t in post_inbox_tasks if t.get("content") != NAVIGATOR_TASK_NAME]
    )

    # ------------------------------------------------------------------
    # Step 5 — Upsert navigator task
    # ------------------------------------------------------------------
    description = _build_navigator_description(overflow_projects, timezone_str)

    existing_nav = service.find_navigator_task(inbox_id, NAVIGATOR_TASK_NAME)
    if existing_nav is None:
        service.create_task(
            content=NAVIGATOR_TASK_NAME,
            project_id=inbox_id,
            description=description,
            order=1,
        )
        results["navigator_action"] = "created"
        logger.info("Navigator task created")
    else:
        service.update_task(existing_nav["id"], description)
        results["navigator_action"] = "updated"
        logger.info("Navigator task updated")

    return results
