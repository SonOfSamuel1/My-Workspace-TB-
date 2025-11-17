"""
Email Sending Service for Relationship Reports

Handles sending HTML email reports via Gmail API.
"""

import os
import logging
import pickle
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class EmailSender:
    """Service for sending emails via Gmail API."""

    def __init__(self, credentials_path: str, token_path: str):
        """
        Initialize Email Sender.

        Args:
            credentials_path: Path to OAuth2 credentials JSON file
            token_path: Path to store/retrieve the token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None

    def authenticate(self) -> None:
        """Authenticate with Gmail API."""
        creds = None

        # Token stores the user's access and refresh tokens
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        try:
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Successfully authenticated with Gmail API")
        except HttpError as error:
            logger.error(f"Failed to build Gmail service: {error}")
            raise

    def send_html_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        from_email: Optional[str] = None
    ) -> bool:
        """
        Send an HTML email via Gmail API.

        Args:
            to: Recipient email address
            subject: Email subject line
            html_content: HTML content of the email
            from_email: Optional sender email (defaults to authenticated user)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.service:
            self.authenticate()

        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['To'] = to
            message['Subject'] = subject

            if from_email:
                message['From'] = from_email

            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            # Send message
            send_message = {
                'raw': raw_message
            }

            result = self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()

            logger.info(f"Email sent successfully to {to}. Message ID: {result.get('id')}")
            return True

        except HttpError as error:
            logger.error(f"Failed to send email: {error}")
            return False

    def send_plain_text_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None
    ) -> bool:
        """
        Send a plain text email via Gmail API.

        Args:
            to: Recipient email address
            subject: Email subject line
            body: Plain text body of the email
            from_email: Optional sender email (defaults to authenticated user)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.service:
            self.authenticate()

        try:
            # Create message
            message = MIMEText(body)
            message['To'] = to
            message['Subject'] = subject

            if from_email:
                message['From'] = from_email

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            # Send message
            send_message = {
                'raw': raw_message
            }

            result = self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()

            logger.info(f"Email sent successfully to {to}. Message ID: {result.get('id')}")
            return True

        except HttpError as error:
            logger.error(f"Failed to send email: {error}")
            return False

    def validate_credentials(self) -> bool:
        """
        Validate Gmail API credentials.

        Returns:
            True if credentials are valid, False otherwise
        """
        if not self.service:
            try:
                self.authenticate()
            except Exception as e:
                logger.error(f"Failed to authenticate: {e}")
                return False

        try:
            # Try to get user profile
            profile = self.service.users().getProfile(userId='me').execute()
            email = profile.get('emailAddress')
            logger.info(f"Successfully validated Gmail access for: {email}")
            return True

        except HttpError as error:
            logger.error(f"Failed to validate credentials: {error}")
            return False
