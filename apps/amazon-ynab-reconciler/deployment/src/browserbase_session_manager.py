"""
Browserbase session manager for persistent Amazon sessions.

Handles session storage, validation, and lifecycle management.
Uses local file storage for development and AWS Parameter Store for Lambda.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class BrowserbaseSessionManager:
    """Manage Browserbase sessions for Amazon automation."""

    PARAMETER_STORE_KEY = '/amazon-reconciler/browserbase-session-id'
    LOCAL_SESSION_FILE = 'browserbase_session.json'

    def __init__(self, config: Dict = None):
        """
        Initialize the session manager.

        Args:
            config: Optional configuration dict with session settings
        """
        self.config = config or {}
        self.data_dir = Path(__file__).parent.parent / 'data'
        self.data_dir.mkdir(exist_ok=True)
        self.session_file = self.data_dir / self.LOCAL_SESSION_FILE

        # Determine storage mode (Lambda uses Parameter Store, local uses file)
        self.use_parameter_store = bool(os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))

        # Session validity settings
        self.session_max_age_days = self.config.get('session_max_age_days', 7)

    def get_session_id(self) -> Optional[str]:
        """
        Get stored session ID.

        Returns:
            Session ID string or None if not found
        """
        if self.use_parameter_store:
            return self._get_from_parameter_store()
        else:
            return self._get_from_local_file()

    def save_session_id(self, session_id: str, metadata: Dict = None) -> bool:
        """
        Save session ID with metadata.

        Args:
            session_id: Browserbase session ID to store
            metadata: Optional metadata dict (amazon_logged_in, created_via, etc.)

        Returns:
            True if save was successful
        """
        if self.use_parameter_store:
            return self._save_to_parameter_store(session_id, metadata)
        else:
            return self._save_to_local_file(session_id, metadata)

    def clear_session(self) -> bool:
        """
        Clear stored session (force re-authentication).

        Returns:
            True if clear was successful
        """
        if self.use_parameter_store:
            return self._clear_parameter_store()
        else:
            return self._clear_local_file()

    def get_session_metadata(self) -> Optional[Dict]:
        """
        Get session metadata (last login, expiry, etc.).

        Returns:
            Metadata dict or None if no session
        """
        if self.use_parameter_store:
            return self._get_metadata_from_parameter_store()
        else:
            return self._get_metadata_from_local_file()

    def is_session_likely_valid(self) -> Tuple[bool, str]:
        """
        Quick check if session is likely valid based on metadata.

        This is a heuristic check - actual validation requires
        navigating to Amazon and checking login state.

        Returns:
            Tuple of (is_likely_valid, reason_string)
        """
        session_id = self.get_session_id()
        if not session_id:
            return False, "No session ID found"

        metadata = self.get_session_metadata()
        if not metadata:
            return False, "No session metadata found"

        last_used = metadata.get('last_used')
        if not last_used:
            return False, "No last_used timestamp in metadata"

        try:
            last_used_dt = datetime.fromisoformat(last_used)
            session_max_age = timedelta(days=self.session_max_age_days)

            age = datetime.now() - last_used_dt
            if age > session_max_age:
                return False, f"Session is {age.days} days old (max: {self.session_max_age_days})"

            return True, f"Session is {age.days} days old, within valid range"

        except Exception as e:
            return False, f"Error checking session age: {e}"

    def update_last_used(self) -> bool:
        """
        Update the last_used timestamp for current session.

        Call this after successful use of the session.

        Returns:
            True if update was successful
        """
        metadata = self.get_session_metadata() or {}
        metadata['last_used'] = datetime.now().isoformat()
        metadata['use_count'] = metadata.get('use_count', 0) + 1

        session_id = self.get_session_id()
        if session_id:
            return self.save_session_id(session_id, metadata)
        return False

    # --- Parameter Store Methods ---

    def _get_from_parameter_store(self) -> Optional[str]:
        """Get session ID from AWS Parameter Store."""
        try:
            import boto3
            ssm = boto3.client('ssm', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
            response = ssm.get_parameter(
                Name=self.PARAMETER_STORE_KEY,
                WithDecryption=True
            )
            data = json.loads(response['Parameter']['Value'])
            return data.get('session_id')
        except Exception as e:
            logger.debug(f"No session in Parameter Store: {e}")
            return None

    def _save_to_parameter_store(self, session_id: str, metadata: Dict = None) -> bool:
        """Save session ID to AWS Parameter Store."""
        try:
            import boto3
            ssm = boto3.client('ssm', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

            data = {
                'session_id': session_id,
                'created_at': datetime.now().isoformat(),
                'last_used': datetime.now().isoformat(),
                **(metadata or {})
            }

            ssm.put_parameter(
                Name=self.PARAMETER_STORE_KEY,
                Value=json.dumps(data),
                Type='SecureString',
                Overwrite=True
            )
            logger.info("Session ID saved to Parameter Store")
            return True
        except Exception as e:
            logger.error(f"Failed to save to Parameter Store: {e}")
            return False

    def _get_metadata_from_parameter_store(self) -> Optional[Dict]:
        """Get full session data from Parameter Store."""
        try:
            import boto3
            ssm = boto3.client('ssm', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
            response = ssm.get_parameter(
                Name=self.PARAMETER_STORE_KEY,
                WithDecryption=True
            )
            return json.loads(response['Parameter']['Value'])
        except Exception as e:
            logger.debug(f"No metadata in Parameter Store: {e}")
            return None

    def _clear_parameter_store(self) -> bool:
        """Delete session from Parameter Store."""
        try:
            import boto3
            ssm = boto3.client('ssm', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
            ssm.delete_parameter(Name=self.PARAMETER_STORE_KEY)
            logger.info("Session cleared from Parameter Store")
            return True
        except Exception as e:
            logger.warning(f"Failed to clear Parameter Store: {e}")
            return False

    # --- Local File Methods ---

    def _get_from_local_file(self) -> Optional[str]:
        """Get session ID from local file."""
        if not self.session_file.exists():
            return None
        try:
            with open(self.session_file, 'r') as f:
                data = json.load(f)
            return data.get('session_id')
        except Exception as e:
            logger.debug(f"Error reading session file: {e}")
            return None

    def _save_to_local_file(self, session_id: str, metadata: Dict = None) -> bool:
        """Save session ID to local file."""
        try:
            # Preserve existing metadata
            existing = self._get_metadata_from_local_file() or {}

            data = {
                **existing,
                'session_id': session_id,
                'last_used': datetime.now().isoformat(),
                **(metadata or {})
            }

            # Set created_at only if not already set
            if 'created_at' not in data:
                data['created_at'] = datetime.now().isoformat()

            with open(self.session_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Session ID saved to {self.session_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save session file: {e}")
            return False

    def _get_metadata_from_local_file(self) -> Optional[Dict]:
        """Get full session data from local file."""
        if not self.session_file.exists():
            return None
        try:
            with open(self.session_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Error reading session metadata: {e}")
            return None

    def _clear_local_file(self) -> bool:
        """Delete local session file."""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
            logger.info("Local session file cleared")
            return True
        except Exception as e:
            logger.warning(f"Failed to clear session file: {e}")
            return False
