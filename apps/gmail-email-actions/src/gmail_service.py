"""Gmail API service for fetching starred emails."""

import base64
import logging
import os
import pickle
from typing import Any, Dict, List, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic",
]

GMAIL_DEEP_LINK = "https://mail.google.com/mail/u/0/#inbox/{thread_id}"


class GmailService:
    """Gmail API wrapper for fetching starred emails."""

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
    ):
        self.credentials_path = credentials_path or os.environ.get(
            "GMAIL_CREDENTIALS_PATH",
            os.path.join(
                os.path.dirname(__file__), "..", "credentials", "gmail_credentials.json"
            ),
        )
        self.token_path = token_path or os.environ.get(
            "GMAIL_TOKEN_PATH",
            os.path.join(
                os.path.dirname(__file__), "..", "credentials", "gmail_token.pickle"
            ),
        )
        self.service = None

    def authenticate(self) -> Credentials:
        """Authenticate with Gmail API using OAuth2."""
        creds = None

        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, "rb") as f:
                    creds = pickle.load(f)
                logger.info("Loaded existing Gmail token")
            except Exception as e:
                logger.warning(f"Could not load token: {e}")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired Gmail token")
                creds.refresh(Request())
                # Save refreshed token
                with open(self.token_path, "wb") as f:
                    pickle.dump(creds, f)
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials not found at {self.credentials_path}"
                    )
                logger.info("Starting Gmail OAuth2 flow (interactive)")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
                with open(self.token_path, "wb") as f:
                    pickle.dump(creds, f)
                logger.info(f"Token saved to {self.token_path}")

        return creds

    def connect(self):
        """Build the Gmail API service."""
        creds = self.authenticate()
        self.service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail API service connected")

    def _get_message_headers(self, message: Dict) -> Dict[str, str]:
        """Extract subject, from, date from message headers."""
        headers = {
            h["name"]: h["value"] for h in message.get("payload", {}).get("headers", [])
        }
        return {
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From", ""),
            "date": headers.get("Date", ""),
        }

    def _extract_body(self, payload: Dict) -> Tuple[str, str]:
        """Walk MIME parts tree and extract HTML and plain-text body.

        Returns:
            (body_html, body_text) — either may be empty string.
        """
        body_html = ""
        body_text = ""

        def _decode_data(data: str) -> str:
            """Base64url-decode body data from the Gmail API."""
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        def _walk(part: Dict) -> None:
            nonlocal body_html, body_text
            mime = part.get("mimeType", "")
            data = part.get("body", {}).get("data", "")

            if mime == "text/html" and data and not body_html:
                body_html = _decode_data(data)
            elif mime == "text/plain" and data and not body_text:
                body_text = _decode_data(data)

            for sub in part.get("parts", []):
                _walk(sub)

        _walk(payload)
        return body_html, body_text

    def get_message_content(self, message_id: str) -> Dict[str, Any]:
        """Fetch full message content including body for rendering.

        Returns:
            Dict with: id, threadId, subject, from, date, body_html, body_text
        """
        if not self.service:
            self.connect()

        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            headers = self._get_message_headers(message)
            body_html, body_text = self._extract_body(message.get("payload", {}))
            return {
                "id": message_id,
                "threadId": message.get("threadId", ""),
                "subject": headers["subject"],
                "from": headers["from"],
                "date": headers["date"],
                "body_html": body_html,
                "body_text": body_text,
            }
        except HttpError as e:
            logger.error(f"Gmail API error fetching message content {message_id}: {e}")
            raise

    def get_starred_emails(self) -> List[Dict[str, Any]]:
        """Fetch all starred emails from Gmail.

        Returns:
            List of dicts with keys: id, threadId, subject, from, date, gmail_link
        """
        if not self.service:
            self.connect()

        results = []
        page_token = None

        try:
            while True:
                kwargs: Dict[str, Any] = {
                    "userId": "me",
                    "q": "is:starred",
                    "maxResults": 100,
                }
                if page_token:
                    kwargs["pageToken"] = page_token

                response = self.service.users().messages().list(**kwargs).execute()
                messages = response.get("messages", [])

                for msg in messages:
                    detail = self.get_message_detail(msg["id"])
                    results.append(detail)

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            logger.info(f"Found {len(results)} starred emails")
            return results

        except HttpError as e:
            logger.error(f"Gmail API error fetching starred emails: {e}")
            raise

    def unstar_email(self, message_id: str) -> None:
        """Remove the STARRED label from a Gmail message."""
        if not self.service:
            self.connect()
        self.service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["STARRED"]},
        ).execute()
        logger.info(f"Unstarred Gmail message {message_id}")

    def trash_previous_digests(self) -> int:
        """Trash previous 'Starred Emails' digest messages so only the newest remains.

        Returns:
            Number of messages trashed.
        """
        if not self.service:
            self.connect()

        query = 'subject:"Starred Emails" subject:"outstanding"'
        trashed = 0

        try:
            page_token = None
            while True:
                kwargs: Dict[str, Any] = {"userId": "me", "q": query}
                if page_token:
                    kwargs["pageToken"] = page_token

                response = self.service.users().messages().list(**kwargs).execute()
                messages = response.get("messages", [])
                logger.info(
                    f"Digest search found {len(messages)} message(s) on this page"
                )

                for msg in messages:
                    self.service.users().messages().trash(
                        userId="me", id=msg["id"]
                    ).execute()
                    logger.info(f"Trashed previous digest message {msg['id']}")
                    trashed += 1

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

        except HttpError as e:
            logger.error(f"Gmail API error trashing previous digests: {e}")
            raise

        return trashed

    def get_message_detail(self, message_id: str) -> Dict[str, Any]:
        """Fetch subject, sender, date for a given message ID.

        Returns:
            Dict with: id, threadId, subject, from, date, gmail_link
        """
        if not self.service:
            self.connect()

        try:
            message = (
                self.service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                )
                .execute()
            )
            headers = self._get_message_headers(message)
            return {
                "id": message_id,
                "threadId": message.get("threadId", ""),
                "subject": headers["subject"],
                "from": headers["from"],
                "date": headers["date"],
                "gmail_link": GMAIL_DEEP_LINK.format(
                    thread_id=message.get("threadId", message_id)
                ),
            }
        except HttpError as e:
            logger.error(f"Gmail API error fetching message {message_id}: {e}")
            raise

    def create_skip_inbox_filter(self, from_email: str) -> dict:
        """Create a Gmail filter to skip the inbox for emails from this sender."""
        if not self.service:
            self.connect()
        return (
            self.service.users()
            .settings()
            .filters()
            .create(
                userId="me",
                body={
                    "criteria": {"from": from_email},
                    "action": {"removeLabelIds": ["INBOX"]},
                },
            )
            .execute()
        )
