"""
Gmail email client implementing the EmailClientBase interface.
Uses OAuth2 for authentication via Google APIs.
"""

import os
import pickle
import base64
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from email_client_base import (
    EmailClientBase,
    EmailAccountConfig,
    EmailMessage,
    AuthenticationError,
    EmailClientError
)

logger = logging.getLogger(__name__)

# Gmail API scopes needed for email reading
# Note: gmail.modify includes read access and is compatible with existing gmail-mcp tokens
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.settings.basic'
]


class GmailEmailClient(EmailClientBase):
    """
    Gmail email client using OAuth2 authentication.

    Implements the EmailClientBase interface for Gmail accounts,
    supporting OAuth2 authentication flow and Gmail API operations.
    """

    def __init__(self, config: EmailAccountConfig):
        """
        Initialize the Gmail client.

        Args:
            config: EmailAccountConfig with Gmail-specific settings
        """
        super().__init__(config)

        # Set default paths if not provided
        base_dir = Path(__file__).parent.parent
        self.credentials_path = os.path.expanduser(config.credentials_path) if config.credentials_path else str(
            base_dir / 'credentials' / 'gmail_credentials.json'
        )
        self.token_path = os.path.expanduser(config.token_path) if config.token_path else str(
            base_dir / 'credentials' / 'gmail_token.pickle'
        )

        # Ensure credentials directory exists
        Path(self.token_path).parent.mkdir(parents=True, exist_ok=True)

        self._service = None
        self._creds = None
        self._client_id = None
        self._client_secret = None

    def _get_client_id(self) -> Optional[str]:
        """Get client_id from credentials file."""
        if self._client_id:
            return self._client_id
        creds_data = self._load_credentials_file()
        if creds_data:
            installed = creds_data.get('installed', creds_data.get('web', {}))
            self._client_id = installed.get('client_id')
            return self._client_id
        return None

    def _get_client_secret(self) -> Optional[str]:
        """Get client_secret from credentials file."""
        if self._client_secret:
            return self._client_secret
        creds_data = self._load_credentials_file()
        if creds_data:
            installed = creds_data.get('installed', creds_data.get('web', {}))
            self._client_secret = installed.get('client_secret')
            return self._client_secret
        return None

    def _load_credentials_file(self) -> Optional[Dict]:
        """Load the OAuth credentials file."""
        try:
            import json
            with open(self.credentials_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth2.

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            creds = None

            # Load existing token if it exists
            if os.path.exists(self.token_path):
                try:
                    # First try pickle format
                    if self.token_path.endswith('.pickle'):
                        with open(self.token_path, 'rb') as token:
                            creds = pickle.load(token)
                    else:
                        # Try JSON format (from gmail-mcp or other sources)
                        import json
                        with open(self.token_path, 'r') as token:
                            token_data = json.load(token)
                            # Handle gmail-mcp format
                            if 'access_token' in token_data and 'refresh_token' in token_data:
                                creds = Credentials(
                                    token=token_data.get('access_token'),
                                    refresh_token=token_data.get('refresh_token'),
                                    token_uri='https://oauth2.googleapis.com/token',
                                    client_id=self._get_client_id(),
                                    client_secret=self._get_client_secret(),
                                    scopes=SCOPES
                                )
                            # Handle standard Google OAuth format
                            elif 'token' in token_data:
                                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
                    logger.info(f"[{self.name}] Loaded existing Gmail authentication token")
                except Exception as e:
                    logger.warning(f"[{self.name}] Could not load token: {e}")
                    creds = None

            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info(f"[{self.name}] Refreshing expired Gmail token")
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        raise AuthenticationError(
                            f"Gmail credentials file not found at {self.credentials_path}\n"
                            "Please download credentials.json from Google Cloud Console.",
                            provider="gmail"
                        )

                    logger.info(f"[{self.name}] Starting Gmail OAuth2 flow")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info(f"[{self.name}] Gmail authentication successful")

                # Save the credentials for the next run
                try:
                    with open(self.token_path, 'wb') as token:
                        pickle.dump(creds, token)
                    logger.info(f"[{self.name}] Saved Gmail authentication token")
                except Exception as e:
                    logger.error(f"[{self.name}] Could not save token: {e}")

            self._creds = creds
            self._service = build('gmail', 'v1', credentials=creds)
            self.is_authenticated = True
            self._user_email = self.get_user_email()

            return True

        except Exception as e:
            logger.error(f"[{self.name}] Gmail authentication failed: {e}")
            raise AuthenticationError(str(e), provider="gmail")

    def _ensure_authenticated(self):
        """Ensure the client is authenticated before making API calls."""
        if not self.is_authenticated or not self._service:
            self.authenticate()

    def search_messages(
        self,
        senders: Optional[List[str]] = None,
        days_back: int = 7,
        subject_contains: Optional[str] = None,
        max_results: int = 100
    ) -> List[EmailMessage]:
        """
        Search for email messages in Gmail.

        Args:
            senders: List of sender email addresses to search for
            days_back: Number of days to look back
            subject_contains: Optional subject filter
            max_results: Maximum number of messages to return

        Returns:
            List of EmailMessage objects
        """
        self._ensure_authenticated()

        try:
            # Build query
            query_parts = []

            # Add sender filter
            if senders:
                sender_query = ' OR '.join([f'from:{sender}' for sender in senders])
                query_parts.append(f'({sender_query})')

            # Add date filter
            after_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
            query_parts.append(f'after:{after_date}')

            # Add subject filter
            if subject_contains:
                query_parts.append(f'subject:{subject_contains}')

            query = ' '.join(query_parts)
            logger.info(f"[{self.name}] Searching Gmail with query: {query}")

            # Execute search
            results = self._service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            message_refs = results.get('messages', [])
            logger.info(f"[{self.name}] Found {len(message_refs)} messages")

            # Fetch full message content
            messages = []
            for msg_ref in message_refs:
                try:
                    message = self.get_message(msg_ref['id'])
                    if message:
                        messages.append(message)
                except Exception as e:
                    logger.error(f"[{self.name}] Error fetching message {msg_ref['id']}: {e}")
                    continue

            return messages

        except HttpError as e:
            logger.error(f"[{self.name}] Gmail API error: {e}")
            raise EmailClientError(f"Gmail API error: {e}", provider="gmail")

    def get_message(self, message_id: str) -> Optional[EmailMessage]:
        """
        Retrieve a specific email message by ID.

        Args:
            message_id: Gmail message ID

        Returns:
            EmailMessage if found, None otherwise
        """
        self._ensure_authenticated()

        try:
            full_msg = self._service.users().messages().get(
                userId='me',
                id=message_id
            ).execute()

            return self._parse_gmail_message(full_msg)

        except HttpError as e:
            logger.error(f"[{self.name}] Error fetching message {message_id}: {e}")
            return None

    def _parse_gmail_message(self, gmail_message: Dict[str, Any]) -> EmailMessage:
        """
        Parse a Gmail API message into an EmailMessage.

        Args:
            gmail_message: Raw Gmail API message object

        Returns:
            EmailMessage object
        """
        # Extract headers
        headers = {}
        payload_headers = gmail_message.get('payload', {}).get('headers', [])
        for header in payload_headers:
            headers[header['name'].lower()] = header['value']

        # Extract body
        body_text = None
        body_html = None

        payload = gmail_message.get('payload', {})
        body_html = self._extract_body_html(payload)
        body_text = self._extract_body_text(payload)

        # Parse date
        date_str = headers.get('date', '')
        try:
            from email.utils import parsedate_to_datetime
            message_date = parsedate_to_datetime(date_str).replace(tzinfo=None)
        except Exception:
            message_date = datetime.now()

        return EmailMessage(
            id=gmail_message['id'],
            subject=headers.get('subject', '(No Subject)'),
            sender=headers.get('from', ''),
            date=message_date,
            body_text=body_text,
            body_html=body_html,
            headers=headers,
            raw_message=gmail_message
        )

    def _extract_body_html(self, payload: Dict[str, Any]) -> Optional[str]:
        """Extract HTML body from Gmail message payload."""
        try:
            # Handle multipart messages
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/html':
                        data = part.get('body', {}).get('data', '')
                        if data:
                            return base64.urlsafe_b64decode(data).decode('utf-8')
                    elif 'parts' in part:  # Nested parts
                        for subpart in part['parts']:
                            if subpart.get('mimeType') == 'text/html':
                                data = subpart.get('body', {}).get('data', '')
                                if data:
                                    return base64.urlsafe_b64decode(data).decode('utf-8')

            # Handle simple messages
            elif payload.get('body', {}).get('data'):
                if payload.get('mimeType') == 'text/html':
                    return base64.urlsafe_b64decode(
                        payload['body']['data']
                    ).decode('utf-8')

        except Exception as e:
            logger.debug(f"Error extracting HTML body: {e}")

        return None

    def _extract_body_text(self, payload: Dict[str, Any]) -> Optional[str]:
        """Extract plain text body from Gmail message payload."""
        try:
            # Handle multipart messages
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        data = part.get('body', {}).get('data', '')
                        if data:
                            return base64.urlsafe_b64decode(data).decode('utf-8')

            # Handle simple messages
            elif payload.get('body', {}).get('data'):
                if payload.get('mimeType') == 'text/plain':
                    return base64.urlsafe_b64decode(
                        payload['body']['data']
                    ).decode('utf-8')

        except Exception as e:
            logger.debug(f"Error extracting text body: {e}")

        return None

    def get_user_email(self) -> Optional[str]:
        """
        Get the authenticated user's email address.

        Returns:
            Email address string or None
        """
        if self._user_email:
            return self._user_email

        self._ensure_authenticated()

        try:
            result = self._service.users().getProfile(userId='me').execute()
            self._user_email = result.get('emailAddress')
            return self._user_email
        except Exception as e:
            logger.error(f"[{self.name}] Could not get user email: {e}")
            return None

    def test_connection(self) -> bool:
        """
        Test the Gmail API connection.

        Returns:
            True if connection is working
        """
        try:
            self._ensure_authenticated()
            result = self._service.users().getProfile(userId='me').execute()
            email = result.get('emailAddress')
            logger.info(f"[{self.name}] Gmail connected: {email}")
            return True
        except Exception as e:
            logger.error(f"[{self.name}] Gmail connection test failed: {e}")
            return False


# Factory function for creating Gmail clients
def create_gmail_client(
    name: str = "Gmail",
    credentials_path: Optional[str] = None,
    token_path: Optional[str] = None
) -> GmailEmailClient:
    """
    Create a Gmail email client with the given configuration.

    Args:
        name: Display name for the account
        credentials_path: Path to OAuth2 credentials JSON
        token_path: Path to store/load token pickle

    Returns:
        Configured GmailEmailClient instance
    """
    config = EmailAccountConfig(
        name=name,
        account_type='gmail',
        credentials_path=credentials_path,
        token_path=token_path
    )
    return GmailEmailClient(config)


if __name__ == "__main__":
    # Test Gmail client
    logging.basicConfig(level=logging.INFO)
    print("Testing Gmail Email Client...")

    try:
        client = create_gmail_client("Test Gmail")
        if client.test_connection():
            email = client.get_user_email()
            print(f"Successfully authenticated as: {email}")

            # Test Amazon email search
            print("\nSearching for Amazon emails...")
            messages = client.search_amazon_emails(days_back=7)
            print(f"Found {len(messages)} Amazon emails")

            for msg in messages[:3]:
                print(f"  - {msg.subject[:60]}... from {msg.sender}")
        else:
            print("Connection test failed")
    except Exception as e:
        print(f"Error: {e}")
