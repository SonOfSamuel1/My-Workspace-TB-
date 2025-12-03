"""Todoist API service for fetching tasks and managing reminders.

Uses both REST API v2 for fetching tasks and Sync API for reminders.
Note: Reminders require Todoist Premium subscription.
"""

import logging
import requests
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, date

logger = logging.getLogger(__name__)

# API endpoints
REST_API_BASE = "https://api.todoist.com/rest/v2"
SYNC_API_BASE = "https://api.todoist.com/sync/v9"


class TodoistService:
    """Service for interacting with Todoist APIs."""

    def __init__(self, api_token: str):
        """Initialize the Todoist service.

        Args:
            api_token: Todoist API token
        """
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    def get_tasks_due_today_with_label(self, label_name: str) -> List[Dict[str, Any]]:
        """Get all tasks due today that have a specific label.

        Args:
            label_name: The label name to filter by (without @)

        Returns:
            List of task dictionaries matching the criteria
        """
        # Use Todoist filter syntax to get tasks due today with the label
        # The filter combines "today" (due today) with the label
        filter_query = f"today & @{label_name}"

        try:
            response = requests.get(
                f"{REST_API_BASE}/tasks",
                headers=self.headers,
                params={"filter": filter_query}
            )
            response.raise_for_status()
            tasks = response.json()

            logger.info(f"Found {len(tasks)} tasks due today with @{label_name} label")
            return tasks

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch tasks: {e}")
            raise

    def get_existing_reminders(self) -> List[Dict[str, Any]]:
        """Get all existing reminders using the Sync API.

        Returns:
            List of reminder dictionaries
        """
        try:
            response = requests.post(
                f"{SYNC_API_BASE}/sync",
                headers=self.headers,
                json={
                    "sync_token": "*",
                    "resource_types": ["reminders"]
                }
            )
            response.raise_for_status()
            data = response.json()

            reminders = data.get("reminders", [])
            logger.info(f"Found {len(reminders)} existing reminders")
            return reminders

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch reminders: {e}")
            raise

    def create_reminder(
        self,
        task_id: str,
        reminder_time: datetime,
        timezone: str = "America/New_York"
    ) -> Optional[Dict[str, Any]]:
        """Create a reminder for a task at a specific time.

        Args:
            task_id: The ID of the task to add a reminder to
            reminder_time: The datetime for the reminder
            timezone: The timezone for the reminder (default: America/New_York)

        Returns:
            The created reminder dictionary, or None if creation failed
        """
        # Format the datetime for Todoist Sync API
        # Format: YYYY-MM-DDTHH:MM:SS
        due_string = reminder_time.strftime("%Y-%m-%dT%H:%M:%S")

        # Generate a unique temporary ID for the command
        temp_id = str(uuid.uuid4())

        command = {
            "type": "reminder_add",
            "temp_id": temp_id,
            "uuid": str(uuid.uuid4()),
            "args": {
                "item_id": task_id,
                "type": "absolute",
                "due": {
                    "date": due_string,
                    "timezone": timezone,
                    "is_recurring": False,
                    "lang": "en"
                }
            }
        }

        try:
            response = requests.post(
                f"{SYNC_API_BASE}/sync",
                headers=self.headers,
                json={"commands": [command]}
            )
            response.raise_for_status()
            result = response.json()

            # Check if the command was successful
            sync_status = result.get("sync_status", {})
            command_uuid = command["uuid"]

            if sync_status.get(command_uuid) == "ok":
                # Get the real reminder ID from temp_id_mapping
                temp_id_mapping = result.get("temp_id_mapping", {})
                real_id = temp_id_mapping.get(temp_id)

                logger.info(
                    f"Created reminder for task {task_id} at "
                    f"{reminder_time.strftime('%I:%M %p')} (ID: {real_id})"
                )
                return {"id": real_id, "task_id": task_id, "due": due_string}
            else:
                error = sync_status.get(command_uuid, "Unknown error")
                logger.error(f"Failed to create reminder: {error}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create reminder: {e}")
            return None

    def delete_reminder(self, reminder_id: str) -> bool:
        """Delete a reminder by ID.

        Args:
            reminder_id: The ID of the reminder to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        command = {
            "type": "reminder_delete",
            "uuid": str(uuid.uuid4()),
            "args": {
                "id": reminder_id
            }
        }

        try:
            response = requests.post(
                f"{SYNC_API_BASE}/sync",
                headers=self.headers,
                json={"commands": [command]}
            )
            response.raise_for_status()
            result = response.json()

            sync_status = result.get("sync_status", {})
            if sync_status.get(command["uuid"]) == "ok":
                logger.info(f"Deleted reminder {reminder_id}")
                return True
            else:
                logger.error(f"Failed to delete reminder: {sync_status}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete reminder: {e}")
            return False

    def get_reminders_for_task(
        self,
        task_id: str,
        all_reminders: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Get existing reminders for a specific task.

        Args:
            task_id: The task ID to filter by
            all_reminders: Optional list of all reminders (to avoid extra API call)

        Returns:
            List of reminders for the specified task
        """
        if all_reminders is None:
            all_reminders = self.get_existing_reminders()

        # Filter reminders for the specific task
        task_reminders = [
            r for r in all_reminders
            if r.get("item_id") == task_id and not r.get("is_deleted", False)
        ]

        return task_reminders
