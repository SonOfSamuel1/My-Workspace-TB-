"""Toggl Track API client for creating time entries."""

from __future__ import annotations

import requests
from base64 import b64encode
from datetime import datetime


class TogglClient:
    BASE_URL = "https://api.track.toggl.com/api/v9"

    def __init__(self, api_token: str, workspace_id: int):
        self.workspace_id = workspace_id
        auth = b64encode(f"{api_token}:api_token".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
        }

    def create_time_entry(
        self,
        description: str,
        start: str,
        duration_seconds: int,
        project_id: int | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Create a completed time entry.

        Args:
            description: Entry description
            start: ISO 8601 UTC start time (e.g. "2026-03-01T03:50:00Z")
            duration_seconds: Duration in seconds
            project_id: Optional Toggl project ID
            tags: Optional list of tag names
        """
        payload = {
            "created_with": "eight-sleep-toggl-sync",
            "description": description,
            "start": start,
            "duration": duration_seconds,
            "workspace_id": self.workspace_id,
        }
        if project_id:
            payload["project_id"] = project_id
        if tags:
            payload["tags"] = tags

        resp = requests.post(
            f"{self.BASE_URL}/workspaces/{self.workspace_id}/time_entries",
            json=payload,
            headers=self.headers,
        )
        resp.raise_for_status()
        return resp.json()

    def get_time_entries(self, start_date: str, end_date: str) -> list[dict]:
        """Get time entries for a date range (for deduplication)."""
        resp = requests.get(
            f"{self.BASE_URL}/me/time_entries",
            params={"start_date": start_date, "end_date": end_date},
            headers=self.headers,
        )
        resp.raise_for_status()
        return resp.json()
