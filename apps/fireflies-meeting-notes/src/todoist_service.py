"""Todoist REST API v1 service for creating meeting action item tasks."""

import logging
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

REST_API_BASE = "https://api.todoist.com/api/v1"


class MeetingTodoistService:
    """Creates Todoist tasks from meeting action items."""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    def create_action_tasks(
        self,
        action_items: List[str],
        meeting_title: str,
        meeting_date: str,
    ) -> int:
        """Create a Todoist task for each action item in Inbox.

        Args:
            action_items: List of action item strings from the meeting.
            meeting_title: Title of the meeting for context.
            meeting_date: Date string of the meeting.

        Returns:
            Count of tasks successfully created.
        """
        created = 0

        for item in action_items:
            item_text = item.strip()
            if not item_text:
                continue

            payload: Dict[str, Any] = {
                "content": item_text,
                "description": f"From meeting: {meeting_title} ({meeting_date})",
                "labels": ["meeting-action"],
            }

            try:
                response = requests.post(
                    f"{REST_API_BASE}/tasks",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                task = response.json()
                logger.info(f"Created task: {item_text} (ID: {task['id']})")
                created += 1
            except requests.RequestException as e:
                logger.error(f"Failed to create task for '{item_text}': {e}")

        logger.info(
            f"Created {created}/{len(action_items)} tasks "
            f"for meeting '{meeting_title}'"
        )
        return created
