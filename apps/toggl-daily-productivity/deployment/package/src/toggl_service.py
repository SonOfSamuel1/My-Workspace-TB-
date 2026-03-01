"""
Toggl Track API Integration Service

This module provides integration with Toggl Track API to fetch time entries
and sync them to Google Calendar.
"""

import os
import logging
import time
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

        # Cache for project names (loaded once, used many times)
        self._project_cache = {}
        self._projects_loaded = False

        # Rate limiting (Toggl free tier allows ~1 request/second)
        self._last_request_time = 0
        self._min_request_interval = 2.0  # 2 seconds between requests to avoid rate limits
        self._max_retries = 5
        self._retry_delay = 30  # 30 seconds to wait before retry (API rate limit is harsh)

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

    def _rate_limit(self):
        """Ensure we don't exceed API rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def get_current_time_entry(self) -> Optional[Dict]:
        """
        Get currently running time entry.

        Returns:
            Dictionary with time entry data or None if no entry is running
        """
        try:
            self._rate_limit()
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
        Get time entries for a date range with retry logic.

        Args:
            start_date: Start date (defaults to today)
            end_date: End date (defaults to today)

        Returns:
            List of time entry dictionaries
        """
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

        # Retry logic for rate limiting
        for attempt in range(self._max_retries):
            try:
                self._rate_limit()
                response = requests.get(url, headers=self.headers, params=params)

                # Handle rate limiting
                if response.status_code == 402 or response.status_code == 429:
                    wait_time = self._retry_delay * (attempt + 1)
                    self.logger.warning(f"Rate limited (attempt {attempt + 1}/{self._max_retries}), waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()

                entries = response.json()
                formatted_entries = [self._format_time_entry(entry) for entry in entries]

                self.logger.info(f"Retrieved {len(formatted_entries)} time entries")
                return formatted_entries

            except requests.exceptions.RequestException as e:
                if attempt < self._max_retries - 1:
                    wait_time = self._retry_delay * (attempt + 1)
                    self.logger.warning(f"Request failed (attempt {attempt + 1}/{self._max_retries}), retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Error fetching time entries after {self._max_retries} attempts: {str(e)}")
                    return []

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
            self._rate_limit()
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

    def _load_project_cache(self):
        """Load all projects into cache once using /me endpoint (works on free tier)."""
        if self._projects_loaded:
            return

        try:
            self._rate_limit()
            # Use /me?with_related_data=true which works on free tier
            url = f"{self.base_url}/me?with_related_data=true"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            projects = data.get('projects', [])
            for project in projects:
                self._project_cache[project.get('id')] = project.get('name', 'Unknown Project')

            self.logger.info(f"Cached {len(projects)} projects")
            self._projects_loaded = True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error loading project cache: {str(e)}")
            self._projects_loaded = True

    def _get_project_name(self, project_id: int) -> Optional[str]:
        """
        Get project name by ID (with caching).

        Args:
            project_id: Toggl project ID

        Returns:
            Project name or None
        """
        # Load all projects once on first call
        if not self._projects_loaded:
            self._load_project_cache()

        return self._project_cache.get(project_id)

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

            self._rate_limit()
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
            self._rate_limit()
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
