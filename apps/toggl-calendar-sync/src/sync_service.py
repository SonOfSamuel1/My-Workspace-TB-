"""
Time Tracking Sync Service

This module orchestrates the synchronization between Toggl Track and Google Calendar.
"""

import os
import logging
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from toggl_service import TogglService
from calendar_service import CalendarService


class SyncService:
    """Service for syncing Toggl time entries to Google Calendar."""

    def __init__(self, env_file: str = '.env'):
        """
        Initialize Sync service.

        Args:
            env_file: Path to environment file
        """
        self.logger = logging.getLogger(__name__)
        self._load_environment(env_file)

        # Initialize services
        self.toggl = TogglService(env_file)
        self.calendar = CalendarService(env_file)

        # Configuration
        self.sync_enabled = os.getenv('TOGGL_SYNC_ENABLED', 'true').lower() == 'true'
        self.auto_sync = os.getenv('TOGGL_AUTO_SYNC', 'true').lower() == 'true'
        self.sync_running_entries = os.getenv('TOGGL_SYNC_RUNNING', 'false').lower() == 'true'

        # State tracking file
        self.state_file = 'cache/sync_state.json'
        self.state = self._load_state()

        self.logger.info("SyncService initialized successfully")

    def _load_environment(self, env_file: str):
        """Load environment variables from .env file."""
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()

    def _load_state(self) -> Dict:
        """Load sync state from file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load sync state: {str(e)}")

        return {
            'synced_entries': {},  # toggl_id -> calendar_event_id mapping
            'last_sync': None,
            'total_synced': 0
        }

    def _save_state(self):
        """Save sync state to file."""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save sync state: {str(e)}")

    def sync_time_entry(self, time_entry: Dict) -> Optional[str]:
        """
        Sync a single time entry to calendar.

        Args:
            time_entry: Time entry dictionary from TogglService

        Returns:
            Calendar event ID if successful, None otherwise
        """
        if not self.sync_enabled:
            self.logger.info("Sync is disabled")
            return None

        # Skip running entries unless configured to sync them
        if time_entry.get('is_running') and not self.sync_running_entries:
            self.logger.info(f"Skipping running entry: {time_entry.get('description')}")
            return None

        toggl_id = str(time_entry.get('id'))

        # Check if already synced
        if toggl_id in self.state['synced_entries']:
            event_id = self.state['synced_entries'][toggl_id]
            self.logger.info(f"Entry {toggl_id} already synced to event {event_id}")

            # Update existing event
            if self.calendar.update_time_entry_event(time_entry, event_id):
                self.logger.info(f"Updated calendar event {event_id}")
                return event_id
            else:
                # Update failed, try to recreate
                self.logger.warning(f"Update failed, removing from sync state")
                del self.state['synced_entries'][toggl_id]
                self._save_state()

        # Create new calendar event
        event_id = self.calendar.create_time_entry_event(time_entry)

        if event_id:
            # Record sync
            self.state['synced_entries'][toggl_id] = event_id
            self.state['total_synced'] = self.state.get('total_synced', 0) + 1
            self._save_state()

            self.logger.info(f"Successfully synced entry {toggl_id} to event {event_id}")
            return event_id

        return None

    def sync_date_range(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Sync all time entries in a date range.

        Args:
            start_date: Start date (defaults to today)
            end_date: End date (defaults to today)

        Returns:
            Dictionary with sync statistics
        """
        if not self.sync_enabled:
            return {'success': False, 'message': 'Sync is disabled'}

        # Get time entries from Toggl
        entries = self.toggl.get_time_entries(start_date, end_date)

        stats = {
            'total_entries': len(entries),
            'synced': 0,
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'errors': []
        }

        for entry in entries:
            try:
                toggl_id = str(entry.get('id'))

                # Skip running entries unless configured
                if entry.get('is_running') and not self.sync_running_entries:
                    stats['skipped'] += 1
                    continue

                # Check if already synced
                already_synced = toggl_id in self.state['synced_entries']

                # Sync entry
                event_id = self.sync_time_entry(entry)

                if event_id:
                    if already_synced:
                        stats['updated'] += 1
                    else:
                        stats['synced'] += 1
                else:
                    stats['failed'] += 1

            except Exception as e:
                self.logger.error(f"Error syncing entry {entry.get('id')}: {str(e)}")
                stats['failed'] += 1
                stats['errors'].append(str(e))

        # Update last sync time
        self.state['last_sync'] = datetime.now().isoformat()
        self._save_state()

        return stats

    def sync_today(self) -> Dict:
        """
        Sync today's time entries.

        Returns:
            Dictionary with sync statistics
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.sync_date_range(start_date=today)

    def sync_yesterday(self) -> Dict:
        """
        Sync yesterday's time entries.

        Returns:
            Dictionary with sync statistics
        """
        yesterday = datetime.now() - timedelta(days=1)
        yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        return self.sync_date_range(start_date=yesterday, end_date=yesterday)

    def sync_week(self) -> Dict:
        """
        Sync current week's time entries.

        Returns:
            Dictionary with sync statistics
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())
        return self.sync_date_range(start_date=week_start)

    def unsync_entry(self, toggl_id: str) -> bool:
        """
        Remove a time entry from calendar and sync state.

        Args:
            toggl_id: Toggl time entry ID

        Returns:
            True if successful, False otherwise
        """
        toggl_id = str(toggl_id)

        if toggl_id not in self.state['synced_entries']:
            self.logger.warning(f"Entry {toggl_id} not found in sync state")
            return False

        event_id = self.state['synced_entries'][toggl_id]

        # Delete calendar event
        if self.calendar.delete_time_entry_event(event_id):
            # Remove from state
            del self.state['synced_entries'][toggl_id]
            self._save_state()
            self.logger.info(f"Unsynced entry {toggl_id}")
            return True

        return False

    def get_sync_stats(self) -> Dict:
        """
        Get current sync statistics.

        Returns:
            Dictionary with sync statistics
        """
        return {
            'sync_enabled': self.sync_enabled,
            'auto_sync': self.auto_sync,
            'total_synced_entries': len(self.state['synced_entries']),
            'last_sync': self.state.get('last_sync'),
            'total_synced_all_time': self.state.get('total_synced', 0)
        }

    def validate_services(self) -> bool:
        """
        Validate all service connections.

        Returns:
            True if all services are valid, False otherwise
        """
        toggl_valid = self.toggl.validate_credentials()
        calendar_valid = self.calendar.validate_credentials()

        return toggl_valid and calendar_valid


if __name__ == "__main__":
    # Setup logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test the service
    try:
        sync = SyncService()

        print("=== Time Tracking Sync Service Test ===\n")

        # Validate services
        print("Validating services...")
        if sync.validate_services():
            print("✓ All services validated\n")

            # Show stats
            stats = sync.get_sync_stats()
            print("Current Stats:")
            print(f"  Sync enabled: {stats['sync_enabled']}")
            print(f"  Auto-sync: {stats['auto_sync']}")
            print(f"  Total synced entries: {stats['total_synced_entries']}")
            print(f"  Last sync: {stats['last_sync'] or 'Never'}")
            print()

            # Sync today
            print("Syncing today's entries...")
            result = sync.sync_today()
            print(f"✓ Sync complete:")
            print(f"  Total entries: {result['total_entries']}")
            print(f"  Newly synced: {result['synced']}")
            print(f"  Updated: {result['updated']}")
            print(f"  Skipped: {result['skipped']}")
            print(f"  Failed: {result['failed']}")

            if result.get('errors'):
                print(f"\nErrors:")
                for error in result['errors']:
                    print(f"  - {error}")

        else:
            print("✗ Service validation failed")

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
