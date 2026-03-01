"""Todoist API service for Email Actions project management."""

import logging
import uuid
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

REST_API_BASE = "https://api.todoist.com/api/v1"

EMAIL_ACTIONS_PROJECT = "Email Actions"


class EmailActionsTodoistService:
    """Manages Email Actions tasks in Todoist."""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    def get_or_create_project(
        self,
        project_name: str = EMAIL_ACTIONS_PROJECT,
        cached_id: Optional[str] = None,
    ) -> str:
        """Find or create a Todoist project by name, paginating the full project list.

        Args:
            project_name: Name to find or create.
            cached_id: If provided, verify this project still exists before searching.

        Returns:
            The project ID
        """
        # Fast path: verify cached project still exists
        if cached_id:
            try:
                r = requests.get(
                    f"{REST_API_BASE}/projects/{cached_id}", headers=self.headers
                )
                if r.status_code == 200:
                    logger.info(
                        f"Using cached project ID {cached_id} for '{project_name}'"
                    )
                    return cached_id
            except Exception:
                pass

        try:
            # Paginate through ALL projects to find by name
            cursor = None
            while True:
                params: Dict[str, Any] = {"limit": 50}
                if cursor:
                    params["cursor"] = cursor
                response = requests.get(
                    f"{REST_API_BASE}/projects", headers=self.headers, params=params
                )
                response.raise_for_status()
                data = response.json()
                projects = data.get("results", [])

                for project in projects:
                    if project.get("name", "").lower() == project_name.lower():
                        project_id = project["id"]
                        logger.info(
                            f"Found existing project '{project_name}' (ID: {project_id})"
                        )
                        return project_id

                cursor = data.get("next_cursor")
                if not cursor:
                    break

            # Not found — create it
            logger.info(f"Creating project '{project_name}'")
            response = requests.post(
                f"{REST_API_BASE}/projects",
                headers=self.headers,
                json={"name": project_name},
            )
            response.raise_for_status()
            project_id = response.json()["id"]
            logger.info(f"Created project '{project_name}' (ID: {project_id})")
            return project_id

        except requests.RequestException as e:
            logger.error(f"Failed to get/create project '{project_name}': {e}")
            raise

    def create_task(
        self,
        project_id: str,
        subject: str,
        from_addr: str,
        date: str,
        gmail_link: str,
        msg_id: str = "",
    ) -> Dict[str, Any]:
        """Create an Email Actions Todoist task.

        Returns:
            The created task dict
        """
        title = f"[Action] {subject} — from {from_addr}"
        description = (
            f"📧 **From:** {from_addr}\n"
            f"📅 **Received:** {date}\n"
            f"🔗 [Open in Gmail]({gmail_link})"
        )
        if msg_id:
            description += f"\n🆔 **Msg ID:** {msg_id}"

        try:
            response = requests.post(
                f"{REST_API_BASE}/tasks",
                headers=self.headers,
                json={
                    "content": title,
                    "description": description,
                    "project_id": project_id,
                },
            )
            response.raise_for_status()
            task = response.json()
            # API v1 may wrap in {"results": [...]}
            if isinstance(task, dict) and "results" in task:
                task = task["results"][0]
            logger.info(f"Created task: {title} (ID: {task['id']})")
            return task

        except requests.RequestException as e:
            logger.error(f"Failed to create task for '{subject}': {e}")
            raise

    def delete_task(self, task_id: str) -> None:
        """Permanently delete a Todoist task by ID."""
        response = requests.delete(
            f"{REST_API_BASE}/tasks/{task_id}", headers=self.headers
        )
        response.raise_for_status()
        logger.info(f"Deleted Todoist task {task_id}")

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Return all projects for the authenticated user."""
        all_projects: List[Dict[str, Any]] = []
        cursor = None
        while True:
            params: Dict[str, Any] = {"limit": 50}
            if cursor:
                params["cursor"] = cursor
            response = requests.get(
                f"{REST_API_BASE}/projects", headers=self.headers, params=params
            )
            response.raise_for_status()
            data = response.json()
            all_projects.extend(data.get("results", []))
            cursor = data.get("next_cursor")
            if not cursor:
                break
        logger.info(f"Fetched {len(all_projects)} projects")
        return all_projects

    def move_task(self, task_id: str, project_id: str) -> bool:
        """Move a task to a different project. Returns True on success."""
        try:
            response = requests.post(
                f"{REST_API_BASE}/tasks/{task_id}/move",
                headers=self.headers,
                json={"project_id": project_id},
            )
            response.raise_for_status()
            logger.info(f"Moved task {task_id} to project {project_id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to move task {task_id}: {e}")
            return False

    def update_due_date(self, task_id: str, date_string: str) -> bool:
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
                f"{REST_API_BASE}/tasks/{task_id}",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            logger.info(f"Updated due date for task {task_id} to '{date_string}'")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to update due date for task {task_id}: {e}")
            return False

    def update_priority(self, task_id: str, priority: int) -> bool:
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
                f"{REST_API_BASE}/sync",
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
        except requests.RequestException as e:
            logger.error(f"Failed to update priority for task {task_id}: {e}")
            return False

    def _find_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a project by exact name. Returns project dict or None."""
        projects = self.get_all_projects()
        for p in projects:
            if p.get("name") == name:
                return p
        return None

    def _count_project_tasks(self, project_id: str) -> int:
        """Count active tasks in a project."""
        all_tasks: List[Dict[str, Any]] = []
        cursor = None
        while True:
            params: Dict[str, Any] = {"project_id": project_id, "limit": 200}
            if cursor:
                params["cursor"] = cursor
            response = requests.get(
                f"{REST_API_BASE}/tasks", headers=self.headers, params=params
            )
            response.raise_for_status()
            data = response.json()
            all_tasks.extend(data.get("results", []))
            cursor = data.get("next_cursor")
            if not cursor:
                break
        return len(all_tasks)

    def _get_commit_target_project(self) -> Optional[str]:
        """Return project ID for commit/bestcase: 'Personal', or 'Personal 2' if Personal has 250+ tasks."""
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

    def _update_labels(self, task_id: str, labels: list) -> bool:
        """Update a task's labels. Returns True on success."""
        response = requests.post(
            f"{REST_API_BASE}/tasks/{task_id}",
            headers=self.headers,
            json={"labels": labels},
        )
        response.raise_for_status()
        return True

    def bestcase_task(self, task_id: str) -> bool:
        """Add 'Best Case' label, remove 'Commit' if present, move to Personal. Returns True on success."""
        try:
            response = requests.get(
                f"{REST_API_BASE}/tasks/{task_id}",
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
        except requests.RequestException as e:
            logger.error(f"Failed to bestcase task {task_id}: {e}")
            return False

    def get_open_tasks(self, project_id: str) -> List[Dict[str, Any]]:
        """Return all non-completed tasks in the Email Actions project, paginating all pages.

        Returns:
            List of task dicts (each includes content, description, id)
        """
        try:
            all_tasks: List[Dict[str, Any]] = []
            cursor = None
            while True:
                params: Dict[str, Any] = {"project_id": project_id, "limit": 50}
                if cursor:
                    params["cursor"] = cursor
                response = requests.get(
                    f"{REST_API_BASE}/tasks",
                    headers=self.headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
                page = data.get("results", []) if isinstance(data, dict) else data
                all_tasks.extend(page)
                cursor = data.get("next_cursor") if isinstance(data, dict) else None
                if not cursor:
                    break

            logger.info(f"Found {len(all_tasks)} open tasks in project {project_id}")
            return all_tasks

        except requests.RequestException as e:
            logger.error(f"Failed to fetch tasks for project {project_id}: {e}")
            raise
