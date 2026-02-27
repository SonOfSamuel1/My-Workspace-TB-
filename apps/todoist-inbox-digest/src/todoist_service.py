"""Todoist API service for the inbox digest.

Wraps Todoist API v1 calls needed to fetch and manage tasks
across Inbox, Inbox 2, and Inbox Two projects.

API v1 notes:
- Base URL: https://api.todoist.com/api/v1
- Responses are paginated: {"results": [...], "next_cursor": "..."}
- Inbox field: inbox_project (not is_inbox_project)
- Move tasks: POST /tasks/{id}/move with {"project_id": ...}
- Priority mapping: API 4=P1(Red), 3=P2(Orange), 2=P3(Blue), 1=P4(Gray)
"""

import logging
import time
import uuid

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.todoist.com/api/v1"
PAGE_LIMIT = 200

# Module-level TTL caches (shared across requests within the same Lambda container)
_projects_cache: dict = {"data": None, "ts": 0}
_PROJECTS_TTL = 120  # seconds

_inbox_ids_cache: dict = {"data": None, "ts": 0}
_INBOX_IDS_TTL = 300  # seconds


class TodoistService:
    """Service for interacting with Todoist API v1."""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_all_pages(self, endpoint, params=None, max_pages=0):
        """Fetch all pages from a paginated endpoint and return combined results.

        Args:
            max_pages: If > 0, stop after this many pages (0 = unlimited).
        """
        all_results = []
        cursor = None
        base_params = dict(params or {})
        base_params["limit"] = PAGE_LIMIT
        page_count = 0

        while True:
            page_params = dict(base_params)
            if cursor:
                page_params["cursor"] = cursor

            try:
                response = requests.get(
                    f"{API_BASE}/{endpoint}",
                    headers=self.headers,
                    params=page_params,
                )
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch {endpoint}: {e}")
                raise

            results = data.get("results", [])
            all_results.extend(results)
            page_count += 1
            cursor = data.get("next_cursor")
            if not cursor:
                break
            if max_pages and page_count >= max_pages:
                break

        return all_results

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def get_all_projects(self):
        """Return all projects for the authenticated user (TTL-cached)."""
        now = time.time()
        if (
            _projects_cache["data"] is not None
            and (now - _projects_cache["ts"]) < _PROJECTS_TTL
        ):
            logger.info(
                f"Using cached projects ({len(_projects_cache['data'])} projects)"
            )
            return _projects_cache["data"]
        projects = self._get_all_pages("projects")
        _projects_cache["data"] = projects
        _projects_cache["ts"] = now
        logger.info(f"Fetched {len(projects)} projects (cached)")
        return projects

    def get_inbox_project_ids(self, projects=None):
        """Return inbox project IDs (TTL-cached). Almost never change."""
        now = time.time()
        if (
            _inbox_ids_cache["data"] is not None
            and (now - _inbox_ids_cache["ts"]) < _INBOX_IDS_TTL
        ):
            logger.info(f"Using cached inbox IDs: {_inbox_ids_cache['data']}")
            return _inbox_ids_cache["data"]
        if projects is None:
            projects = self.get_all_projects()
        inbox_ids = []
        for p in projects:
            if p.get("inbox_project"):
                inbox_ids.append(p["id"])
            elif p.get("name", "").lower() in ("inbox 2", "inbox two"):
                inbox_ids.append(p["id"])
        _inbox_ids_cache["data"] = inbox_ids
        _inbox_ids_cache["ts"] = now
        logger.info(f"Cached inbox project IDs: {inbox_ids}")
        return inbox_ids

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def get_inbox_tasks(self, projects=None):
        """Get tasks from Inbox and Inbox 2/Inbox Two projects combined.

        Args:
            projects: Optional pre-fetched projects list to avoid redundant API call.
        """
        inbox_ids = self.get_inbox_project_ids(projects)

        all_tasks = []
        for pid in inbox_ids:
            tasks = self._get_all_pages("tasks", {"project_id": pid})
            all_tasks.extend(tasks)
            logger.info(f"Fetched {len(tasks)} tasks from project {pid}")

        return all_tasks

    def get_tasks_by_label(self, label):
        """Get all tasks with a specific label across all projects."""
        tasks = self._get_all_pages("tasks", {"label": label})
        logger.info(f"Fetched {len(tasks)} tasks with label '{label}'")
        return tasks

    def get_tasks_by_priority(self, priority):
        """Get all tasks with a specific priority level.

        Priority mapping: 4=P1(Urgent/Red), 3=P2(High/Orange), 2=P3(Medium/Blue), 1=P4(Normal/Gray)
        The v1 API doesn't support priority filtering, so we paginate all tasks and filter.
        """
        all_tasks = self._get_all_pages("tasks", max_pages=5)
        filtered = [t for t in all_tasks if t.get("priority") == priority]
        logger.info(
            f"Fetched {len(filtered)} tasks with priority {priority} "
            f"(from {len(all_tasks)} total, max 5 pages)"
        )
        return filtered

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def move_task(self, task_id, project_id):
        """Move a task to a different project. Returns True on success."""
        try:
            response = requests.post(
                f"{API_BASE}/tasks/{task_id}/move",
                headers=self.headers,
                json={"project_id": project_id},
            )
            response.raise_for_status()
            logger.info(f"Moved task {task_id} to project {project_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to move task {task_id}: {e}")
            return False

    def update_priority(self, task_id, priority):
        """Update the priority of a task via the Sync API.

        Priority values: 4=P1(Urgent), 3=P2(High), 2=P3(Medium), 1=P4(Normal)
        """
        command = {
            "type": "item_update",
            "uuid": str(uuid.uuid4()),
            "args": {
                "id": task_id,
                "priority": int(priority),
            },
        }
        try:
            response = requests.post(
                f"{API_BASE}/sync",
                headers=self.headers,
                json={"commands": [command]},
            )
            response.raise_for_status()
            result = response.json()
            sync_status = result.get("sync_status", {})
            if sync_status.get(command["uuid"]) == "ok":
                logger.info(f"Updated priority for task {task_id} to {priority}")
                return True
            else:
                logger.error(f"Sync update failed for task {task_id}: {sync_status}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update priority for task {task_id}: {e}")
            return False

    def close_task(self, task_id):
        """Complete/close a task. Returns True on success."""
        try:
            response = requests.post(
                f"{API_BASE}/tasks/{task_id}/close",
                headers=self.headers,
            )
            response.raise_for_status()
            logger.info(f"Closed task {task_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to close task {task_id}: {e}")
            return False

    def reopen_task(self, task_id):
        """Reopen a completed task. Returns True on success."""
        try:
            response = requests.post(
                f"{API_BASE}/tasks/{task_id}/reopen",
                headers=self.headers,
            )
            response.raise_for_status()
            logger.info(f"Reopened task {task_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to reopen task {task_id}: {e}")
            return False

    def _find_project_by_name(self, name):
        """Find a project by exact name. Returns project dict or None."""
        projects = self.get_all_projects()
        for p in projects:
            if p.get("name") == name:
                return p
        return None

    def _count_project_tasks(self, project_id):
        """Count active tasks in a project."""
        tasks = self._get_all_pages("tasks", {"project_id": project_id})
        return len(tasks)

    def _get_commit_target_project(self):
        """Return the project ID for commit: 'Personal', or 'Personal 2' if Personal has 250+ tasks."""
        personal = self._find_project_by_name("Personal")
        if not personal:
            logger.warning("Project 'Personal' not found")
            return None
        count = self._count_project_tasks(personal["id"])
        logger.info(f"Personal project has {count} tasks")
        if count < 250:
            return personal["id"]
        personal2 = self._find_project_by_name("Personal 2")
        if personal2:
            logger.info("Personal full (250+), using Personal 2")
            return personal2["id"]
        logger.warning("Project 'Personal 2' not found, using Personal anyway")
        return personal["id"]

    def _update_labels(self, task_id, labels):
        """Update a task's labels. Returns True on success."""
        response = requests.post(
            f"{API_BASE}/tasks/{task_id}",
            headers=self.headers,
            json={"labels": labels},
        )
        response.raise_for_status()
        return True

    def commit_task(self, task_id):
        """Add 'Commit' label, remove 'Best Case' if present, move to Personal. Returns True on success."""
        try:
            response = requests.get(
                f"{API_BASE}/tasks/{task_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            task = response.json()
            labels = task.get("labels", [])

            changed = False
            if "Commit" not in labels:
                labels.append("Commit")
                changed = True
            if "Best Case" in labels:
                labels.remove("Best Case")
                changed = True
            if changed:
                self._update_labels(task_id, labels)
                logger.info(
                    f"Commit label set on task {task_id} (Best Case removed if present)"
                )

            # Move to Personal / Personal 2
            target_project_id = self._get_commit_target_project()
            if target_project_id and task.get("project_id") != target_project_id:
                self.move_task(task_id, target_project_id)

            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to commit task {task_id}: {e}")
            return False

    def bestcase_task(self, task_id):
        """Add 'Best Case' label, remove 'Commit' if present, move to Personal. Returns True on success."""
        try:
            response = requests.get(
                f"{API_BASE}/tasks/{task_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            task = response.json()
            labels = task.get("labels", [])

            changed = False
            if "Best Case" not in labels:
                labels.append("Best Case")
                changed = True
            if "Commit" in labels:
                labels.remove("Commit")
                changed = True
            if changed:
                self._update_labels(task_id, labels)
                logger.info(
                    f"Best Case label set on task {task_id} (Commit removed if present)"
                )

            # Move to Personal / Personal 2
            target_project_id = self._get_commit_target_project()
            if target_project_id and task.get("project_id") != target_project_id:
                self.move_task(task_id, target_project_id)

            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to bestcase task {task_id}: {e}")
            return False

    def remove_commit_label(self, task_id):
        """Remove the 'Commit' label from a task. Returns True on success."""
        try:
            response = requests.get(
                f"{API_BASE}/tasks/{task_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            task = response.json()
            labels = task.get("labels", [])
            if "Commit" not in labels:
                logger.info(f"Task {task_id} doesn't have Commit label")
                return True
            labels.remove("Commit")
            self._update_labels(task_id, labels)
            logger.info(f"Removed Commit label from task {task_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to remove Commit from task {task_id}: {e}")
            return False

    def remove_bestcase_label(self, task_id):
        """Remove the 'Best Case' label from a task. Returns True on success."""
        try:
            response = requests.get(
                f"{API_BASE}/tasks/{task_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            task = response.json()
            labels = task.get("labels", [])
            if "Best Case" not in labels:
                logger.info(f"Task {task_id} doesn't have Best Case label")
                return True
            labels.remove("Best Case")
            self._update_labels(task_id, labels)
            logger.info(f"Removed Best Case label from task {task_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to remove Best Case from task {task_id}: {e}")
            return False

    def update_due_date(self, task_id, date_string):
        """Update the due date of a task. Pass empty string to clear.

        Args:
            task_id: Todoist task ID.
            date_string: 'YYYY-MM-DD' to set, or '' to clear.

        Returns True on success.
        """
        if date_string:
            payload = {"due_date": date_string}
        else:
            payload = {"due_string": "no date"}
        try:
            response = requests.post(
                f"{API_BASE}/tasks/{task_id}",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            logger.info(f"Updated due date for task {task_id} to '{date_string}'")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update due date for task {task_id}: {e}")
            return False
