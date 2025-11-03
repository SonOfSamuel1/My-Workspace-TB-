"""
Google Calendar API Integration Service

This module provides integration with Google Calendar API to create and manage
calendar events for time tracking entries.
"""

import os
import logging
import pickle
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class CalendarService:
    """Service for interacting with Google Calendar API."""

    # OAuth2 scopes required
    SCOPES = ['https://www.googleapis.com/auth/calendar']

    def __init__(self, env_file: str = '.env'):
        """
        Initialize Calendar service.

        Args:
            env_file: Path to environment file containing configuration
        """
        self.logger = logging.getLogger(__name__)
        self._load_environment(env_file)

        # Configuration
        self.calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        self.credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials/credentials.json')
        self.token_file = os.getenv('GOOGLE_TOKEN_FILE', 'credentials/token.pickle')

        # Calendar service
        self.service = None
        self.authenticate()

        self.logger.info("CalendarService initialized successfully")

    def _load_environment(self, env_file: str):
        """Load environment variables from .env file."""
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()

    def authenticate(self):
        """Authenticate with Google Calendar API using OAuth2."""
        creds = None

        # Load existing token
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)

        # Refresh or create new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                self.logger.info("Refreshing expired credentials")
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_file}\n"
                        "Please download OAuth2 credentials from Google Cloud Console"
                    )

                self.logger.info("Starting OAuth2 flow")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
            self.logger.info("Credentials saved")

        # Build service
        self.service = build('calendar', 'v3', credentials=creds)
        self.logger.info("Successfully authenticated with Google Calendar")

    def create_time_entry_event(self, time_entry: Dict) -> Optional[str]:
        """
        Create a calendar event from a time entry.

        Args:
            time_entry: Time entry dictionary from TogglService

        Returns:
            Event ID if successful, None otherwise
        """
        try:
            # Don't create events for running entries
            if time_entry.get('is_running'):
                self.logger.warning(f"Skipping running time entry: {time_entry.get('description')}")
                return None

            # Prepare event data
            event = self._build_event_from_time_entry(time_entry)

            # Check if event already exists (avoid duplicates)
            existing_event_id = self._find_existing_event(time_entry)
            if existing_event_id:
                self.logger.info(f"Event already exists for time entry {time_entry.get('id')}")
                return existing_event_id

            # Create event
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()

            event_id = created_event.get('id')
            self.logger.info(f"Created calendar event: {event_id} for '{time_entry.get('description')}'")

            return event_id

        except HttpError as e:
            self.logger.error(f"Failed to create calendar event: {str(e)}")
            return None

    def update_time_entry_event(self, time_entry: Dict, event_id: str) -> bool:
        """
        Update an existing calendar event for a time entry.

        Args:
            time_entry: Updated time entry dictionary
            event_id: Google Calendar event ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build updated event
            event = self._build_event_from_time_entry(time_entry)

            # Update event
            self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()

            self.logger.info(f"Updated calendar event: {event_id}")
            return True

        except HttpError as e:
            self.logger.error(f"Failed to update calendar event {event_id}: {str(e)}")
            return False

    def delete_time_entry_event(self, event_id: str) -> bool:
        """
        Delete a calendar event.

        Args:
            event_id: Google Calendar event ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            self.logger.info(f"Deleted calendar event: {event_id}")
            return True

        except HttpError as e:
            self.logger.error(f"Failed to delete calendar event {event_id}: {str(e)}")
            return False

    def _build_event_from_time_entry(self, time_entry: Dict) -> Dict:
        """
        Build Google Calendar event structure from time entry.

        Args:
            time_entry: Time entry dictionary

        Returns:
            Event dictionary for Google Calendar API
        """
        # Event title
        description = time_entry.get('description', 'Time Entry')
        project = time_entry.get('project_name')
        if project:
            summary = f"[Time] {description} - {project}"
        else:
            summary = f"[Time] {description}"

        # Event description (body)
        description_parts = [
            f"**Time Tracking Entry**",
            f"",
            f"Description: {time_entry.get('description', 'No description')}",
            f"Duration: {time_entry.get('duration_display', 'N/A')}",
        ]

        if project:
            description_parts.append(f"Project: {project}")

        if time_entry.get('tags'):
            tags_str = ', '.join(time_entry.get('tags', []))
            description_parts.append(f"Tags: {tags_str}")

        if time_entry.get('billable'):
            description_parts.append(f"💰 Billable")

        description_parts.extend([
            f"",
            f"Toggl Link: {time_entry.get('toggl_url', 'N/A')}",
            f"",
            f"_Synced from Toggl Track_"
        ])

        event_description = '\n'.join(description_parts)

        # Time information
        start_time = time_entry.get('start_time')
        end_time = time_entry.get('end_time')

        # Format times for Google Calendar
        if isinstance(start_time, datetime):
            start_dict = {
                'dateTime': start_time.isoformat(),
                'timeZone': os.getenv('TIMEZONE', 'America/New_York')
            }
        else:
            raise ValueError("Invalid start_time format")

        if isinstance(end_time, datetime):
            end_dict = {
                'dateTime': end_time.isoformat(),
                'timeZone': os.getenv('TIMEZONE', 'America/New_York')
            }
        else:
            raise ValueError("Invalid end_time format")

        # Color coding (optional - can map project colors)
        color_id = self._get_color_for_project(time_entry.get('project_id'))

        # Build event
        event = {
            'summary': summary,
            'description': event_description,
            'start': start_dict,
            'end': end_dict,
            'extendedProperties': {
                'private': {
                    'toggl_entry_id': str(time_entry.get('id')),
                    'source': 'toggl_track',
                    'sync_version': '1.0'
                }
            },
            'reminders': {
                'useDefault': False,
                'overrides': []  # No reminders for time tracking entries
            }
        }

        if color_id:
            event['colorId'] = color_id

        return event

    def _find_existing_event(self, time_entry: Dict) -> Optional[str]:
        """
        Find existing calendar event for a time entry.

        Args:
            time_entry: Time entry dictionary

        Returns:
            Event ID if found, None otherwise
        """
        try:
            # Search for events with matching toggl_entry_id
            toggl_id = str(time_entry.get('id'))
            start_time = time_entry.get('start_time')

            if not start_time:
                return None

            # Search within a time window around the entry
            time_min = (start_time - timedelta(hours=1)).isoformat()
            time_max = (start_time + timedelta(hours=25)).isoformat()

            events = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                privateExtendedProperty=f'toggl_entry_id={toggl_id}',
                singleEvents=True
            ).execute()

            items = events.get('items', [])
            if items:
                return items[0].get('id')

            return None

        except HttpError as e:
            self.logger.warning(f"Error searching for existing event: {str(e)}")
            return None

    def _get_color_for_project(self, project_id: Optional[int]) -> Optional[str]:
        """
        Map Toggl project to Google Calendar color.

        Args:
            project_id: Toggl project ID

        Returns:
            Google Calendar color ID or None
        """
        # Color mapping (customize as needed)
        # Google Calendar color IDs: 1-11
        # 1=Lavender, 2=Sage, 3=Grape, 4=Flamingo, 5=Banana,
        # 6=Tangerine, 7=Peacock, 8=Graphite, 9=Blueberry,
        # 10=Basil, 11=Tomato

        # Default color for time tracking entries
        return '8'  # Graphite - neutral gray

    def get_events_for_date(self, date: datetime) -> List[Dict]:
        """
        Get all calendar events for a specific date.

        Args:
            date: Date to fetch events for

        Returns:
            List of event dictionaries
        """
        try:
            # Set time range for the entire day
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=0)

            time_min = start_of_day.isoformat() + 'Z'
            time_max = end_of_day.isoformat() + 'Z'

            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            self.logger.info(f"Retrieved {len(events)} events for {date.strftime('%Y-%m-%d')}")

            return events

        except HttpError as e:
            self.logger.error(f"Failed to fetch events: {str(e)}")
            return []

    def validate_credentials(self) -> bool:
        """
        Validate Google Calendar API credentials.

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            # Try to fetch calendar metadata
            calendar = self.service.calendars().get(calendarId=self.calendar_id).execute()
            self.logger.info(f"Successfully validated access to calendar: {calendar.get('summary')}")
            return True

        except HttpError as e:
            self.logger.error(f"Failed to validate credentials: {str(e)}")
            return False

    def get_events(
        self,
        start_date: datetime,
        end_date: datetime,
        search_terms: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get calendar events within a date range with optional search filtering.

        Args:
            start_date: Start of date range
            end_date: End of date range
            search_terms: Optional list of search terms to filter events

        Returns:
            List of matching event dictionaries
        """
        try:
            # Ensure timezone awareness
            if start_date.tzinfo is None:
                tz = os.getenv('TIMEZONE', 'America/New_York')
                start_date = start_date.replace(tzinfo=timezone.utc)

            if end_date.tzinfo is None:
                tz = os.getenv('TIMEZONE', 'America/New_York')
                end_date = end_date.replace(tzinfo=timezone.utc)

            time_min = start_date.isoformat()
            time_max = end_date.isoformat()

            # If search terms provided, search for each term
            if search_terms:
                all_events = []
                for term in search_terms:
                    try:
                        events_result = self.service.events().list(
                            calendarId=self.calendar_id,
                            timeMin=time_min,
                            timeMax=time_max,
                            q=term,
                            singleEvents=True,
                            orderBy='startTime'
                        ).execute()

                        events = events_result.get('items', [])
                        all_events.extend(events)

                    except HttpError as e:
                        self.logger.warning(f"Error searching for term '{term}': {str(e)}")
                        continue

                # Remove duplicates based on event ID
                unique_events = {e['id']: e for e in all_events}.values()

                # Convert to list with datetime objects
                result_events = []
                for event in unique_events:
                    event_dict = self._parse_event_to_dict(event)
                    result_events.append(event_dict)

                self.logger.info(
                    f"Found {len(result_events)} events matching search terms "
                    f"between {start_date.date()} and {end_date.date()}"
                )
                return result_events

            else:
                # Get all events in range
                events_result = self.service.events().list(
                    calendarId=self.calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()

                events = events_result.get('items', [])

                result_events = []
                for event in events:
                    event_dict = self._parse_event_to_dict(event)
                    result_events.append(event_dict)

                self.logger.info(
                    f"Found {len(result_events)} events "
                    f"between {start_date.date()} and {end_date.date()}"
                )
                return result_events

        except HttpError as e:
            self.logger.error(f"Failed to fetch events: {str(e)}")
            return []

    def _parse_event_to_dict(self, event: Dict) -> Dict:
        """
        Parse Google Calendar event to a simplified dictionary.

        Args:
            event: Raw event from Google Calendar API

        Returns:
            Simplified event dictionary with datetime objects
        """
        from dateutil import parser

        # Parse start time
        start = event.get('start', {})
        if 'dateTime' in start:
            start_dt = parser.parse(start['dateTime'])
        elif 'date' in start:
            # All-day event
            start_dt = parser.parse(start['date'])
        else:
            start_dt = datetime.now()

        # Parse end time
        end = event.get('end', {})
        if 'dateTime' in end:
            end_dt = parser.parse(end['dateTime'])
        elif 'date' in end:
            end_dt = parser.parse(end['date'])
        else:
            end_dt = start_dt + timedelta(hours=1)

        return {
            'id': event.get('id'),
            'summary': event.get('summary', 'Untitled Event'),
            'description': event.get('description', ''),
            'start': start_dt,
            'end': end_dt,
            'location': event.get('location', ''),
            'attendees': event.get('attendees', []),
            'htmlLink': event.get('htmlLink', '')
        }


if __name__ == "__main__":
    # Setup logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test the service
    try:
        from datetime import timedelta

        cal = CalendarService()

        if cal.validate_credentials():
            print("✓ Calendar credentials validated")

            # Get today's events
            events = cal.get_events_for_date(datetime.now())
            print(f"✓ Found {len(events)} events today")

        else:
            print("✗ Failed to validate credentials")

    except Exception as e:
        print(f"✗ Error: {str(e)}")
