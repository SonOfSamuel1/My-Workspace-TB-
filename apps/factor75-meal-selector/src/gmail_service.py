#!/usr/bin/env python3
"""
Gmail Service for Factor 75 Meal Selector

Handles Gmail API authentication and email reply polling.
Extended from base gmail service with reply-specific functionality.
"""

import base64
import logging
import os
import pickle
import re
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, Optional, Tuple

import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Gmail API scopes - need readonly for checking replies, send for sending
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailService:
    """Manages Gmail API authentication and email operations."""

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
    ):
        """
        Initialize the Gmail service.

        Args:
            credentials_path: Path to credentials.json file
            token_path: Path to store token.pickle file
        """
        base_dir = Path(__file__).parent.parent
        self.credentials_path = credentials_path or os.getenv(
            "GMAIL_CREDENTIALS_PATH", str(base_dir / "credentials" / "credentials.json")
        )
        self.token_path = token_path or os.getenv(
            "GMAIL_TOKEN_PATH", str(base_dir / "credentials" / "token.pickle")
        )

        Path(self.token_path).parent.mkdir(parents=True, exist_ok=True)

        self.service = None
        self.creds = None
        self.timezone = pytz.timezone("America/New_York")

    def authenticate(self) -> Credentials:
        """
        Authenticate with Gmail API using OAuth2.

        Returns:
            Authenticated credentials object
        """
        creds = None

        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, "rb") as token:
                    creds = pickle.load(token)
                logger.info("Loaded existing Gmail authentication token")
            except Exception as e:
                logger.warning(f"Could not load token: {e}")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired Gmail token")
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found at {self.credentials_path}\n"
                        "Please download credentials.json from Google Cloud Console."
                    )

                logger.info("Starting Gmail OAuth2 flow")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Gmail authentication successful")

            try:
                with open(self.token_path, "wb") as token:
                    pickle.dump(creds, token)
                logger.info("Saved Gmail authentication token")
            except Exception as e:
                logger.error(f"Could not save token: {e}")

        self.creds = creds
        return creds

    def get_service(self):
        """Get authenticated Gmail service object."""
        if not self.service:
            if not self.creds:
                self.authenticate()

            try:
                self.service = build("gmail", "v1", credentials=self.creds)
                logger.info("Gmail service created successfully")
            except Exception as e:
                logger.error(f"Failed to create Gmail service: {e}")
                raise

        return self.service

    def test_connection(self) -> bool:
        """Test Gmail API connection."""
        try:
            service = self.get_service()
            result = service.users().getProfile(userId="me").execute()
            logger.info(f"Gmail connected: {result.get('emailAddress')}")
            return True
        except HttpError as error:
            logger.error(f"Gmail connection test failed: {error}")
            return False

    def get_user_email(self) -> Optional[str]:
        """Get the authenticated user's email address."""
        try:
            service = self.get_service()
            result = service.users().getProfile(userId="me").execute()
            return result.get("emailAddress")
        except Exception as e:
            logger.error(f"Could not get user email: {e}")
            return None

    def find_reply_to_message(
        self,
        original_message_id: str,
        subject_pattern: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> Optional[Dict]:
        """
        Find a reply to a specific message.

        Args:
            original_message_id: Message ID of the original email
            subject_pattern: Optional subject pattern to match (regex)
            since: Only consider messages after this datetime

        Returns:
            Reply message dict or None if not found
        """
        service = self.get_service()

        # Build search query
        query_parts = ["in:inbox"]

        # Search by subject if provided
        if subject_pattern:
            # Gmail search uses subject: prefix
            query_parts.append('subject:"Re: Factor 75"')

        # Search by date if provided
        if since:
            date_str = since.strftime("%Y/%m/%d")
            query_parts.append(f"after:{date_str}")

        query = " ".join(query_parts)
        logger.info(f"Searching for replies with query: {query}")

        try:
            results = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=20,
                )
                .execute()
            )

            messages = results.get("messages", [])
            logger.info(f"Found {len(messages)} potential reply messages")

            for msg_ref in messages:
                msg = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=msg_ref["id"],
                        format="full",
                    )
                    .execute()
                )

                # Check if this is a reply to our original message
                headers = {
                    h["name"].lower(): h["value"]
                    for h in msg.get("payload", {}).get("headers", [])
                }

                # Check In-Reply-To or References headers
                in_reply_to = headers.get("in-reply-to", "")
                references = headers.get("references", "")

                if (
                    original_message_id in in_reply_to
                    or original_message_id in references
                ):
                    logger.info(f"Found reply message: {msg_ref['id']}")
                    return self._parse_message(msg)

                # Also check subject line
                subject = headers.get("subject", "")
                if "Re: Factor 75" in subject or "RE: Factor 75" in subject:
                    logger.info(f"Found reply by subject: {msg_ref['id']}")
                    return self._parse_message(msg)

            logger.info("No reply found")
            return None

        except HttpError as e:
            logger.error(f"Error searching for replies: {e}")
            return None

    def check_for_selection_reply(
        self,
        original_message_id: str,
        since: Optional[datetime] = None,
    ) -> Optional[Dict]:
        """
        Check for a reply to the meal selection email.

        Convenience method specifically for Factor 75 selection replies.

        Args:
            original_message_id: Message ID of the selection email
            since: Only consider messages after this datetime

        Returns:
            Reply dict with 'body', 'from', 'date', 'message_id' or None
        """
        return self.find_reply_to_message(
            original_message_id=original_message_id,
            subject_pattern=r"Re:.*Factor 75.*Meal Selection",
            since=since,
        )

    def _parse_message(self, msg: Dict) -> Dict:
        """
        Parse a Gmail message into a simpler dict.

        Args:
            msg: Raw Gmail API message

        Returns:
            Dict with body, from, date, subject, message_id
        """
        headers = {
            h["name"].lower(): h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }

        # Extract body
        body = self._extract_body(msg.get("payload", {}))

        # Parse date
        date_str = headers.get("date", "")
        try:
            from email.utils import parsedate_to_datetime

            date = parsedate_to_datetime(date_str)
        except Exception:
            date = datetime.now(self.timezone)

        return {
            "message_id": msg.get("id"),
            "thread_id": msg.get("threadId"),
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "subject": headers.get("subject", ""),
            "date": date,
            "body": body,
            "snippet": msg.get("snippet", ""),
        }

    def _extract_body(self, payload: Dict) -> str:
        """
        Extract text body from message payload.

        Args:
            payload: Gmail message payload

        Returns:
            Decoded body text
        """
        body = ""

        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        elif "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                if mime_type == "text/plain":
                    if part.get("body", {}).get("data"):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                            "utf-8"
                        )
                        break
                elif mime_type == "text/html":
                    if part.get("body", {}).get("data") and not body:
                        html = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                            "utf-8"
                        )
                        body = self._html_to_text(html)
                elif mime_type.startswith("multipart/"):
                    body = self._extract_body(part)
                    if body:
                        break

        return body

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        text = re.sub(
            r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE
        )
        text = re.sub(
            r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE
        )
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)

        import html as html_lib

        text = html_lib.unescape(text)
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = re.sub(r" +", " ", text)

        return text.strip()

    def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Send an email via Gmail API.

        Args:
            to: Recipient email
            subject: Email subject
            body_html: HTML body content
            body_text: Optional plain text body

        Returns:
            Tuple of (success, message_id)
        """
        service = self.get_service()

        if body_text is None:
            body_text = self._html_to_text(body_html)

        msg = MIMEMultipart("alternative")
        msg["To"] = to
        msg["Subject"] = subject

        part1 = MIMEText(body_text, "plain")
        part2 = MIMEText(body_html, "html")
        msg.attach(part1)
        msg.attach(part2)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

        try:
            result = (
                service.users()
                .messages()
                .send(
                    userId="me",
                    body={"raw": raw},
                )
                .execute()
            )

            message_id = result.get("id")
            logger.info(f"Email sent successfully, message ID: {message_id}")
            return True, message_id

        except HttpError as e:
            logger.error(f"Failed to send email: {e}")
            return False, None

    def get_sent_message_id(
        self, subject_pattern: str, since: datetime
    ) -> Optional[str]:
        """
        Find a sent message by subject and date.

        Args:
            subject_pattern: Subject line pattern to match
            since: Only consider messages after this datetime

        Returns:
            Message ID or None
        """
        service = self.get_service()

        date_str = since.strftime("%Y/%m/%d")
        query = f'in:sent subject:"{subject_pattern}" after:{date_str}'

        try:
            results = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=1,
                )
                .execute()
            )

            messages = results.get("messages", [])
            if messages:
                return messages[0]["id"]
            return None

        except HttpError as e:
            logger.error(f"Error finding sent message: {e}")
            return None


def get_gmail_service() -> GmailService:
    """Convenience function to get authenticated Gmail service."""
    gmail = GmailService()
    gmail.get_service()
    return gmail


if __name__ == "__main__":
    print("Testing Gmail authentication for Factor 75...")

    try:
        gmail = GmailService()
        service = gmail.get_service()

        if gmail.test_connection():
            email = gmail.get_user_email()
            print(f"Successfully authenticated as: {email}")
        else:
            print("Authentication failed")
    except FileNotFoundError as e:
        print(f"Setup needed: {e}")
    except Exception as e:
        print(f"Error: {e}")
