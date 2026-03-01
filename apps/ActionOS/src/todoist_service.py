"""Todoist API service for the actions web interface.

Wraps Todoist API v1 calls needed to fetch and manage tasks
across Inbox, @commit label, and P1 priority views.

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

_all_tasks_cache: dict = {"data": None, "ts": 0}
_ALL_TASKS_TTL = 60  # seconds


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
            elif p.get("name", "").lower() == "inbox 2":
                inbox_ids.append(p["id"])
        _inbox_ids_cache["data"] = inbox_ids
        _inbox_ids_cache["ts"] = now
        logger.info(f"Cached inbox project IDs: {inbox_ids}")
        return inbox_ids

    def get_all_tasks(self):
        """Return all tasks across all projects (TTL-cached, 60s)."""
        now = time.time()
        if (
            _all_tasks_cache["data"] is not None
            and (now - _all_tasks_cache["ts"]) < _ALL_TASKS_TTL
        ):
            logger.info(
                f"Using cached all-tasks ({len(_all_tasks_cache['data'])} tasks)"
            )
            return _all_tasks_cache["data"]
        tasks = self._get_all_pages("tasks", max_pages=5)
        _all_tasks_cache["data"] = tasks
        _all_tasks_cache["ts"] = now
        logger.info(f"Fetched {len(tasks)} all-tasks (cached for {_ALL_TASKS_TTL}s)")
        return tasks

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def get_inbox_tasks(self, projects=None):
        """Get tasks from Inbox and Inbox 2 projects combined.

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

    # -- Code view status labels: Planned / In Progress / Backlog -----------

    _CODE_STATUS_LABELS = ("Planned", "In Progress", "Backlog")

    def _set_code_status_label(self, task_id, label):
        """Add *label*, remove other code-status labels. Returns True on success."""
        try:
            response = requests.get(
                f"{API_BASE}/tasks/{task_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            task = response.json()
            labels = task.get("labels", [])

            changed = False
            if label not in labels:
                labels.append(label)
                changed = True
            for other in self._CODE_STATUS_LABELS:
                if other != label and other in labels:
                    labels.remove(other)
                    changed = True
            if changed:
                self._update_labels(task_id, labels)
                logger.info(f"Set '{label}' on task {task_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to set '{label}' on task {task_id}: {e}")
            return False

    def _remove_code_status_label(self, task_id, label):
        """Remove a code-status label from a task. Returns True on success."""
        try:
            response = requests.get(
                f"{API_BASE}/tasks/{task_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            task = response.json()
            labels = task.get("labels", [])
            if label not in labels:
                return True
            labels.remove(label)
            self._update_labels(task_id, labels)
            logger.info(f"Removed '{label}' from task {task_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to remove '{label}' from task {task_id}: {e}")
            return False

    def planned_task(self, task_id):
        return self._set_code_status_label(task_id, "Planned")

    def in_progress_task(self, task_id):
        return self._set_code_status_label(task_id, "In Progress")

    def backlog_task(self, task_id):
        return self._set_code_status_label(task_id, "Backlog")

    def remove_planned_label(self, task_id):
        return self._remove_code_status_label(task_id, "Planned")

    def remove_in_progress_label(self, task_id):
        return self._remove_code_status_label(task_id, "In Progress")

    def remove_backlog_label(self, task_id):
        return self._remove_code_status_label(task_id, "Backlog")

    def update_task(self, task_id, content=None, description=None):
        """Update a task's content (title) and/or description. Returns True on success."""
        payload = {}
        if content is not None:
            payload["content"] = content
        if description is not None:
            payload["description"] = description
        if not payload:
            return True
        try:
            response = requests.post(
                f"{API_BASE}/tasks/{task_id}",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            logger.info(f"Updated task {task_id}: {list(payload.keys())}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return False

    def create_task(
        self,
        content,
        project_id=None,
        due_date=None,
        priority=None,
        description=None,
        labels=None,
    ):
        """Create a new task. Returns the created task dict on success."""
        payload = {"content": content}
        if project_id:
            payload["project_id"] = project_id
        if due_date:
            payload["due_date"] = due_date
        if priority is not None:
            payload["priority"] = int(priority)
        if description:
            payload["description"] = description
        if labels:
            payload["labels"] = list(labels)
        try:
            response = requests.post(
                f"{API_BASE}/tasks",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            task = response.json()
            logger.info(f"Created task '{content}' (id={task.get('id')})")
            return task
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create task '{content}': {e}")
            return None

    def get_sabbath_tasks(self):
        """Fetch tasks from the 'Sabbath Actions' project and with 'Sabbath Approved' label.

        Returns combined, deduplicated list of tasks from both sources plus the projects list.
        """
        projects = self.get_all_projects()

        # Find the "Sabbath Actions" project
        sabbath_project = None
        for p in projects:
            if p.get("name") == "Sabbath Actions":
                sabbath_project = p
                break

        # Fetch tasks from both sources
        project_tasks = []
        if sabbath_project:
            project_tasks = self._get_all_pages(
                "tasks", {"project_id": sabbath_project["id"]}
            )

        label_tasks = self._get_all_pages("tasks", {"label": "Sabbath Approved"})

        # Deduplicate
        seen_ids = set()
        combined = []
        for t in project_tasks + label_tasks:
            if t["id"] not in seen_ids:
                combined.append(t)
                seen_ids.add(t["id"])

        logger.info(
            f"Sabbath tasks: {len(project_tasks)} from project, "
            f"{len(label_tasks)} from label, {len(combined)} combined"
        )
        return combined, projects

    def get_code_project_tasks(self):
        """Fetch all tasks from Claude Code-related projects.

        Scans all projects for names containing 'claude code' or 'cc development'.
        Returns:
            (all_tasks, projects, cc_dev_project_ids)
            - all_tasks: combined list of task dicts (deduped)
            - projects: full list of all project dicts
            - cc_dev_project_ids: set of project IDs classed as Active Development
        """
        projects = self.get_all_projects()

        cc_project_ids = []
        cc_dev_project_ids = set()

        for p in projects:
            name_lower = p.get("name", "").lower()
            if (
                "claude code" in name_lower
                or "cc dev" in name_lower
                or name_lower.startswith("cc-")
            ):
                cc_project_ids.append(p["id"])
                # "CC Dev in Progress" (or similar) → Active Development bucket
                if "dev" in name_lower and name_lower != "claude code":
                    cc_dev_project_ids.add(p["id"])

        all_tasks = []
        seen_ids: set = set()
        for pid in cc_project_ids:
            tasks = self._get_all_pages("tasks", {"project_id": pid})
            for t in tasks:
                if t["id"] not in seen_ids:
                    all_tasks.append(t)
                    seen_ids.add(t["id"])

        logger.info(
            f"Code projects: {len(cc_project_ids)} projects, {len(all_tasks)} tasks, "
            f"{len(cc_dev_project_ids)} active-dev project(s)"
        )
        return all_tasks, projects, cc_dev_project_ids

    def get_task_comments(self, task_id):
        """Fetch all comments for a task (includes file attachments).

        Returns list of comment dicts with keys like: id, content, posted_at,
        file_attachment (optional: file_url, file_name, file_type, image, etc).
        """
        try:
            results = self._get_all_pages(
                "/comments", params={"task_id": task_id}, max_pages=5
            )
            return results
        except Exception as e:
            logger.error(f"Failed to fetch comments for task {task_id}: {e}")
            return []

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
                timeout=10,
            )
            if not response.ok:
                logger.error(
                    f"Failed to update due date for task {task_id}: "
                    f"status={response.status_code} body={response.text[:200]}"
                )
                return False
            logger.info(f"Updated due date for task {task_id} to '{date_string}'")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update due date for task {task_id}: {e}")
            return False
