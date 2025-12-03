#!/usr/bin/env python3
"""
Eight Sleep API Service Module

Provides synchronous wrapper for the Eight Sleep API to retrieve
sleep data, health metrics, and bed status information.

Uses the pyeight library for API communication.
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)


class EightSleepService:
    """
    Eight Sleep API service for retrieving sleep and health data.

    Provides a synchronous interface to the Eight Sleep API,
    wrapping the async pyeight library.
    """

    def __init__(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        timezone: str = 'America/New_York'
    ):
        """
        Initialize Eight Sleep service.

        Args:
            email: Eight Sleep account email (or EIGHT_SLEEP_EMAIL env var)
            password: Eight Sleep account password (or EIGHT_SLEEP_PASSWORD env var)
            timezone: Timezone for sleep data (default: America/New_York)
        """
        self.email = email or os.getenv('EIGHT_SLEEP_EMAIL')
        self.password = password or os.getenv('EIGHT_SLEEP_PASSWORD')
        self.timezone = timezone

        self._eight = None
        self._loop = None

        if not self.email or not self.password:
            raise ValueError(
                "Eight Sleep credentials required. Set EIGHT_SLEEP_EMAIL and "
                "EIGHT_SLEEP_PASSWORD environment variables or pass to constructor."
            )

        logger.info(f"Eight Sleep service initialized for {self.email}")

    def _get_event_loop(self):
        """Get or create event loop for async operations."""
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop

    async def _async_connect(self):
        """Async method to connect to Eight Sleep API."""
        try:
            from pyeight.eight import EightSleep
        except ImportError:
            raise ImportError(
                "pyeight library required. Install with: pip install pyeight"
            )

        self._eight = EightSleep(
            self.email,
            self.password,
            self.timezone,
            None  # No client session, library creates its own
        )

        await self._eight.start()
        logger.info("Connected to Eight Sleep API")

    def connect(self) -> bool:
        """
        Connect to Eight Sleep API.

        Returns:
            True if connection successful
        """
        try:
            loop = self._get_event_loop()
            loop.run_until_complete(self._async_connect())
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Eight Sleep: {e}")
            return False

    async def _async_update_data(self):
        """Async method to update device and user data."""
        if not self._eight:
            raise RuntimeError("Not connected. Call connect() first.")

        await self._eight.update_device_data()
        await self._eight.update_user_data()

    def update_data(self) -> bool:
        """
        Update device and user data from Eight Sleep API.

        Returns:
            True if update successful
        """
        try:
            loop = self._get_event_loop()
            loop.run_until_complete(self._async_update_data())
            logger.info("Updated Eight Sleep data")
            return True
        except Exception as e:
            logger.error(f"Failed to update data: {e}")
            return False

    def get_users(self) -> List[Dict[str, Any]]:
        """
        Get list of users associated with the Eight Sleep device.

        Returns:
            List of user dictionaries with id and side info
        """
        if not self._eight:
            return []

        users = []
        for user_id, user in self._eight.users.items():
            users.append({
                'user_id': user_id,
                'side': user.side,
                'name': getattr(user, 'name', user.side)
            })

        return users

    def get_sleep_data(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get sleep data for a user.

        Args:
            user_id: User ID (defaults to first user if not specified)

        Returns:
            Dictionary with sleep metrics
        """
        if not self._eight:
            raise RuntimeError("Not connected. Call connect() first.")

        # Get user
        if user_id:
            user = self._eight.users.get(user_id)
        else:
            # Default to first user
            user = next(iter(self._eight.users.values()), None)

        if not user:
            logger.warning("No user found")
            return {}

        # Extract sleep data from user object
        sleep_data = {
            'user_id': getattr(user, 'userid', 'unknown'),
            'side': getattr(user, 'side', 'unknown'),

            # Sleep metrics
            'sleep_score': self._safe_get(user, 'current_sleep_score'),
            'sleep_fitness_score': self._safe_get(user, 'current_fitness_score'),
            'sleep_routine_score': self._safe_get(user, 'current_routine_score'),

            # Time metrics
            'time_slept': self._safe_get(user, 'current_sleep_duration'),
            'time_to_sleep': self._safe_get(user, 'current_latency'),
            'times_awake': self._safe_get(user, 'current_tosses_and_turns'),

            # Biometrics
            'heart_rate': self._safe_get(user, 'current_heart_rate'),
            'hrv': self._safe_get(user, 'current_hrv'),
            'breath_rate': self._safe_get(user, 'current_breath_rate'),

            # Bed status
            'bed_temp': self._safe_get(user, 'current_bed_temp'),
            'target_temp': self._safe_get(user, 'target_heating_level'),
            'is_in_bed': self._safe_get(user, 'bed_presence'),

            # Sleep stages (if available)
            'sleep_stages': self._safe_get(user, 'current_sleep_stages'),

            # Timestamps
            'last_seen': self._safe_get(user, 'last_seen'),
            'sleep_start': self._safe_get(user, 'current_session_start'),
            'sleep_end': self._safe_get(user, 'current_session_end'),
        }

        return sleep_data

    def get_device_data(self) -> Dict[str, Any]:
        """
        Get Eight Sleep device/mattress data.

        Returns:
            Dictionary with device metrics
        """
        if not self._eight:
            raise RuntimeError("Not connected. Call connect() first.")

        device_data = {
            'device_id': getattr(self._eight, 'device_id', 'unknown'),
            'room_temp': self._safe_get(self._eight, 'room_temp'),
            'is_online': self._safe_get(self._eight, 'is_online'),
            'water_level': self._safe_get(self._eight, 'water_level'),
            'needs_priming': self._safe_get(self._eight, 'needs_priming'),
            'last_prime': self._safe_get(self._eight, 'last_prime'),
        }

        return device_data

    def get_sleep_history(
        self,
        user_id: Optional[str] = None,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get sleep history for a user.

        Note: This requires additional API calls and may not be
        available in all pyeight versions.

        Args:
            user_id: User ID (defaults to first user)
            days: Number of days of history

        Returns:
            List of sleep session dictionaries
        """
        if not self._eight:
            raise RuntimeError("Not connected. Call connect() first.")

        # Get user
        if user_id:
            user = self._eight.users.get(user_id)
        else:
            user = next(iter(self._eight.users.values()), None)

        if not user:
            return []

        # Try to get intervals/sessions if available
        history = []
        intervals = self._safe_get(user, 'intervals') or []

        for interval in intervals[-days:]:
            if isinstance(interval, dict):
                history.append(interval)

        return history

    def get_full_report_data(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive data for daily report.

        Args:
            user_id: User ID (defaults to first user)

        Returns:
            Dictionary with all relevant sleep and device data
        """
        # Ensure data is fresh
        self.update_data()

        report_data = {
            'timestamp': datetime.now().isoformat(),
            'sleep_data': self.get_sleep_data(user_id),
            'device_data': self.get_device_data(),
            'users': self.get_users(),
        }

        # Add sleep quality assessment
        sleep_score = report_data['sleep_data'].get('sleep_score')
        if sleep_score is not None:
            if sleep_score >= 85:
                report_data['quality_assessment'] = 'Excellent'
            elif sleep_score >= 70:
                report_data['quality_assessment'] = 'Good'
            elif sleep_score >= 55:
                report_data['quality_assessment'] = 'Fair'
            else:
                report_data['quality_assessment'] = 'Needs Improvement'
        else:
            report_data['quality_assessment'] = 'Unknown'

        return report_data

    def _safe_get(self, obj: Any, attr: str, default: Any = None) -> Any:
        """Safely get attribute from object."""
        try:
            value = getattr(obj, attr, default)
            # Handle async properties or methods
            if asyncio.iscoroutine(value):
                return default
            return value
        except Exception:
            return default

    def validate_credentials(self) -> bool:
        """
        Validate Eight Sleep credentials.

        Returns:
            True if credentials are valid
        """
        try:
            if self.connect():
                users = self.get_users()
                logger.info(f"Credentials valid. Found {len(users)} user(s).")
                return True
            return False
        except Exception as e:
            logger.error(f"Credential validation failed: {e}")
            return False

    async def _async_stop(self):
        """Async method to stop the Eight Sleep session."""
        if self._eight:
            await self._eight.stop()

    def disconnect(self):
        """Disconnect from Eight Sleep API."""
        try:
            if self._eight and self._loop:
                self._loop.run_until_complete(self._async_stop())
            self._eight = None
            logger.info("Disconnected from Eight Sleep API")
        except Exception as e:
            logger.warning(f"Error during disconnect: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
