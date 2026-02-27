"""Minimal Gmail API service — only trash previous digest emails."""

import logging
import os
import pickle
from typing import Any, Dict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


class GmailService:
    """Gmail API wrapper for trashing previous digest emails."""

    def __init__(
        self,
        credentials_path=None,
        token_path=None,
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
                with open(self.token_path, "wb") as f:
                    pickle.dump(creds, f)
            else:
                raise RuntimeError(
                    "Gmail token is missing or invalid and cannot be refreshed in Lambda. "
                    "Run local auth flow first to generate token."
                )

        return creds

    def connect(self):
        """Build the Gmail API service."""
        creds = self.authenticate()
        self.service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail API service connected")

    def trash_previous_digests(self) -> int:
        """Trash previous 'Inbox Digest' messages so only the newest remains.

        Returns:
            Number of messages trashed.
        """
        if not self.service:
            self.connect()

        query = 'subject:"Inbox Digest" subject:"outstanding"'
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
