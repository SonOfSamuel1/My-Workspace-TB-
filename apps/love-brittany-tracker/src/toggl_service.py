"""
Toggl Track API Integration Service

This module provides integration with Toggl Track API to fetch time entries
and sync them to Google Calendar.
"""

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import requests
from base64 import b64encode


class TogglService:
    """Service for interacting with Toggl Track API."""

    def __init__(self, env_file: str = '.env'):
        """
        Initialize Toggl service.

        Args:
            env_file: Path to environment file containing API credentials
        """
        self.logger = logging.getLogger(__name__)
        self._load_environment(env_file)

        # Toggl API configuration
        self.api_token = os.getenv('TOGGL_API_TOKEN')
        self.workspace_id = os.getenv('TOGGL_WORKSPACE_ID')
        self.base_url = "https://api.track.toggl.com/api/v9"

        if not self.api_token:
            raise ValueError("TOGGL_API_TOKEN not found in environment")

        # Setup authentication header
        auth_string = f"{self.api_token}:api_token"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = b64encode(auth_bytes).decode('ascii')

        self.headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json'
        }

        self.logger.info("TogglService initialized successfully")

    def _load_environment(self, env_file: str):
        """Load environment variables from .env file."""
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()

    def get_current_time_entry(self) -> Optional[Dict]:
        """
        Get currently running time entry.

        Returns:
            Dictionary with time entry data or None if no entry is running
        """
        try:
            url = f"{self.base_url}/me/time_entries/current"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            entry = response.json()
            if entry:
                self.logger.info(f"Found running time entry: {entry.get('description', 'No description')}")
                return self._format_time_entry(entry)

            return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching current time entry: {str(e)}")
            return None

    def get_time_entries(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get time entries for a date range.

        Args:
            start_date: Start date (defaults to today)
            end_date: End date (defaults to today)

        Returns:
            List of time entry dictionaries
        """
        try:
            # Default to today if no dates provided
            if not start_date:
                start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if not end_date:
                end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)

            # Format dates for Toggl API (ISO 8601)
            start_iso = start_date.isoformat() + 'Z'
            end_iso = end_date.isoformat() + 'Z'

            url = f"{self.base_url}/me/time_entries"
            params = {
                'start_date': start_iso,
                'end_date': end_iso
            }

            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            entries = response.json()
            formatted_entries = [self._format_time_entry(entry) for entry in entries]

            self.logger.info(f"Retrieved {len(formatted_entries)} time entries")
            return formatted_entries

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching time entries: {str(e)}")
            return []

    def get_time_entry_by_id(self, entry_id: int) -> Optional[Dict]:
        """
        Get a specific time entry by ID.

        Args:
            entry_id: Toggl time entry ID

        Returns:
            Dictionary with time entry data or None if not found
        """
        try:
            url = f"{self.base_url}/time_entries/{entry_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            entry = response.json()
            return self._format_time_entry(entry)

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching time entry {entry_id}: {str(e)}")
            return None

    def _format_time_entry(self, entry: Dict) -> Dict:
        """
        Format raw Toggl time entry into standardized format.

        Args:
            entry: Raw time entry from Toggl API

        Returns:
            Formatted time entry dictionary
        """
        # Parse start time
        start_str = entry.get('start', '')
        start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))

        # Calculate end time
        if entry.get('stop'):
            end_str = entry.get('stop', '')
            end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        else:
            # Entry is still running
            end_time = None

        # Calculate duration (in seconds, negative if running)
        duration = entry.get('duration', 0)
        if duration < 0:
            # Running entry - duration is negative start timestamp
            from datetime import timezone as tz
            now_utc = datetime.now(tz.utc)
            duration_seconds = int((now_utc - start_time).total_seconds())
        else:
            duration_seconds = duration

        # Format duration as hours and minutes
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        duration_display = f"{hours}h {minutes}m"

        # Get project info
        project_id = entry.get('project_id')
        project_name = None
        if project_id:
            project_name = self._get_project_name(project_id)

        # Get tags
        tags = entry.get('tags', [])

        return {
            'id': entry.get('id'),
            'description': entry.get('description', 'No description'),
            'start_time': start_time,
            'end_time': end_time,
            'duration_seconds': duration_seconds,
            'duration_display': duration_display,
            'project_id': project_id,
            'project_name': project_name,
            'tags': tags,
            'billable': entry.get('billable', False),
            'is_running': duration < 0,
            'workspace_id': entry.get('workspace_id'),
            'toggl_url': f"https://track.toggl.com/timer/{entry.get('id')}"
        }

    def _get_project_name(self, project_id: int) -> Optional[str]:
        """
        Get project name by ID (with caching).

        Args:
            project_id: Toggl project ID

        Returns:
            Project name or None
        """
        # TODO: Implement caching for project names
        try:
            url = f"{self.base_url}/workspaces/{self.workspace_id}/projects/{project_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            project = response.json()
            return project.get('name', 'Unknown Project')

        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Could not fetch project name for ID {project_id}: {str(e)}")
            return None

    def get_workspace_projects(self) -> List[Dict]:
        """
        Get all projects in the workspace.

        Returns:
            List of project dictionaries
        """
        try:
            if not self.workspace_id:
                self.logger.warning("No workspace ID configured")
                return []

            url = f"{self.base_url}/workspaces/{self.workspace_id}/projects"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            projects = response.json()
            self.logger.info(f"Retrieved {len(projects)} projects")

            return [{
                'id': p.get('id'),
                'name': p.get('name'),
                'color': p.get('color'),
                'active': p.get('active', True),
                'billable': p.get('billable', False)
            } for p in projects]

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching projects: {str(e)}")
            return []

    def validate_credentials(self) -> bool:
        """
        Validate Toggl API credentials.

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            url = f"{self.base_url}/me"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            user = response.json()
            self.logger.info(f"Successfully authenticated as: {user.get('fullname', user.get('email'))}")
            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to validate credentials: {str(e)}")
            return False


if __name__ == "__main__":
    # Setup logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test the service
    try:
        toggl = TogglService()

        # Validate credentials
        if toggl.validate_credentials():
            print("✓ Credentials validated")

            # Get today's entries
            entries = toggl.get_time_entries()
            print(f"\n✓ Found {len(entries)} time entries today:")

            for entry in entries:
                status = "🟢 RUNNING" if entry['is_running'] else "⏹️  STOPPED"
                project = f"[{entry['project_name']}]" if entry['project_name'] else ""
                print(f"  {status} {entry['description']} {project} - {entry['duration_display']}")

            # Get current entry
            current = toggl.get_current_time_entry()
            if current:
                print(f"\n✓ Currently tracking: {current['description']} - {current['duration_display']}")
            else:
                print("\n• No timer currently running")

        else:
            print("✗ Failed to validate credentials")

    except Exception as e:
        print(f"✗ Error: {str(e)}")
