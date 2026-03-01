"""Todoist API v1 service for CC task mover.

Slim wrapper around the Todoist API v1 endpoints needed to find
and move tasks between projects.
"""

import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.todoist.com/api/v1"
PAGE_LIMIT = 200
REQUEST_TIMEOUT = 30


class TodoistService:
    """Service for interacting with Todoist API v1."""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

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
                    timeout=REQUEST_TIMEOUT,
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
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            logger.info(f"Moved task {task_id} to project {project_id}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to move task {task_id}: {e}")
            return False

    def update_task_content(self, task_id: str, content: str) -> bool:
        """Update a task's content. Returns True on success."""
        try:
            response = requests.post(
                f"{API_BASE}/tasks/{task_id}",
                headers=self.headers,
                json={"content": content},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            logger.info(f"Updated task {task_id} content to '{content}'")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update task {task_id} content: {e}")
            return False
