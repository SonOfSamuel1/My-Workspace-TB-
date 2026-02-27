"""Todoist API service for fetching tasks from the Claude project.

Uses the new Todoist API v1 (https://developer.todoist.com/api/v1/).
Responses are paginated with {"results": [...], "next_cursor": "..."}.
"""

import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.todoist.com/api/v1"


class TodoistService:
    """Service for interacting with the Todoist API v1."""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    def _paginate(self, url: str, params: dict = None) -> List[Dict[str, Any]]:
        """Fetch all pages from a paginated v1 endpoint."""
        params = dict(params or {})
        all_results = []
        while True:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            all_results.extend(data.get("results", []))
            cursor = data.get("next_cursor")
            if not cursor:
                break
            params["cursor"] = cursor
        return all_results

    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects."""
        try:
            projects = self._paginate(f"{API_BASE}/projects")
            logger.info(f"Found {len(projects)} projects")
            return projects
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch projects: {e}")
            raise

    def get_project_id_by_name(self, project_name: str) -> Optional[str]:
        """Find project ID by name (case-insensitive)."""
        projects = self.get_projects()
        for project in projects:
            if project.get("name", "").lower() == project_name.lower():
                project_id = project.get("id")
                logger.info(f"Found project '{project_name}' with ID: {project_id}")
                return project_id
        logger.warning(f"Project '{project_name}' not found")
        return None

    def get_all_tasks_in_project(self, project_id: str) -> List[Dict[str, Any]]:
        """Fetch ALL open tasks in a project (no date filter)."""
        try:
            tasks = self._paginate(
                f"{API_BASE}/tasks", params={"project_id": project_id}
            )
            logger.info(f"Found {len(tasks)} open tasks in project {project_id}")
            return tasks
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch tasks: {e}")
            raise
