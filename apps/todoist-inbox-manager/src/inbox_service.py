"""Todoist API service for inbox management.

Wraps Todoist API v1 calls needed to manage the Inbox project
and its overflow projects.

Key differences from deprecated REST v2:
- Base URL: https://api.todoist.com/api/v1
- Responses are paginated: {"results": [...], "next_cursor": "..."}
- Inbox field: inbox_project (not is_inbox_project)
- Task date field: added_at (not created_at)
- Move tasks: POST /tasks/{id}/move with {"project_id": ...}
- Update task description: POST /api/v1/sync with item_update command
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.todoist.com/api/v1"
PAGE_LIMIT = 200  # max items per page


class InboxService:
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

    def _get_all_pages(
        self, endpoint: str, params: Dict = None
    ) -> List[Dict[str, Any]]:
        """Fetch all pages from a paginated endpoint and return combined results."""
        all_results: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        base_params = dict(params or {})
        base_params["limit"] = PAGE_LIMIT

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
            cursor = data.get("next_cursor")
            if not cursor:
                break

        return all_results

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Return all projects for the authenticated user."""
        projects = self._get_all_pages("projects")
        logger.info(f"Fetched {len(projects)} projects")
        return projects

    def get_inbox_project(self) -> Optional[Dict[str, Any]]:
        """Return the official Inbox project (inbox_project == True)."""
        for project in self.get_all_projects():
            if project.get("inbox_project"):
                logger.info(f"Found Inbox project: id={project['id']}")
                return project
        logger.error("No inbox project found")
        return None

    def get_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Return a project whose name matches exactly (case-insensitive)."""
        for project in self.get_all_projects():
            if project.get("name", "").lower() == name.lower():
                logger.info(f"Found project '{name}': id={project['id']}")
                return project
        logger.info(f"Project '{name}' not found")
        return None

    def create_project(self, name: str) -> Dict[str, Any]:
        """Create a new project with the given name and return it."""
        try:
            response = requests.post(
                f"{API_BASE}/projects",
                headers=self.headers,
                json={"name": name},
            )
            response.raise_for_status()
            project = response.json()
            logger.info(f"Created project '{name}': id={project['id']}")
            return project
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create project '{name}': {e}")
            raise

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def get_tasks_in_project(self, project_id: str) -> List[Dict[str, Any]]:
        """Return all tasks in the given project (handles pagination)."""
        tasks = self._get_all_pages("tasks", {"project_id": project_id})
        logger.info(f"Fetched {len(tasks)} tasks from project {project_id}")
        return tasks

    def move_task_to_project(self, task_id: str, project_id: str) -> bool:
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

    def create_task(
        self,
        content: str,
        project_id: str,
        description: str = "",
        order: int = 1,
    ) -> Dict[str, Any]:
        """Create a new task and return it."""
        payload: Dict[str, Any] = {
            "content": content,
            "project_id": project_id,
            "description": description,
            "order": order,
        }
        try:
            response = requests.post(
                f"{API_BASE}/tasks",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            task = response.json()
            logger.info(f"Created task '{content}': id={task['id']}")
            return task
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create task '{content}': {e}")
            raise

    def update_task(self, task_id: str, description: str) -> bool:
        """Update the description of an existing task via the Sync API.

        The v1 REST API does not expose a direct PATCH/PUT for tasks;
        description updates go through the Sync API.
        Returns True on success.
        """
        command = {
            "type": "item_update",
            "uuid": str(uuid.uuid4()),
            "args": {
                "id": task_id,
                "description": description,
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
                logger.info(f"Updated description for task {task_id}")
                return True
            else:
                logger.error(f"Sync update failed for task {task_id}: {sync_status}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return False

    def find_navigator_task(
        self, project_id: str, navigator_name: str
    ) -> Optional[Dict[str, Any]]:
        """Find the navigator task by exact content match inside a project."""
        tasks = self.get_tasks_in_project(project_id)
        for task in tasks:
            if task.get("content") == navigator_name:
                logger.info(f"Found navigator task: id={task['id']}")
                return task
        logger.info("Navigator task not found")
        return None
