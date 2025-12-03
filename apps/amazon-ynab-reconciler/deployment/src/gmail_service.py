"""
Gmail service authentication and connection manager.
Handles OAuth2 authentication for Gmail API access.
"""

import os
import pickle
import logging
from pathlib import Path
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Gmail API scopes needed for email reading
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailService:
    """Manages Gmail API authentication and service creation."""

    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """
        Initialize the Gmail service manager.

        Args:
            credentials_path: Path to credentials.json file
            token_path: Path to store token.pickle file
        """
        # Set default paths if not provided
        base_dir = Path(__file__).parent.parent
        self.credentials_path = credentials_path or str(base_dir / 'credentials' / 'gmail_credentials.json')
        self.token_path = token_path or str(base_dir / 'credentials' / 'gmail_token.pickle')

        # Ensure credentials directory exists
        Path(self.token_path).parent.mkdir(parents=True, exist_ok=True)

        self.service = None
        self.creds = None

    def authenticate(self) -> Credentials:
        """
        Authenticate with Gmail API using OAuth2.

        Returns:
            Authenticated credentials object
        """
        creds = None

        # Load existing token if it exists
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
                logger.info("Loaded existing Gmail authentication token")
            except Exception as e:
                logger.warning(f"Could not load token: {e}")
                creds = None

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired Gmail token")
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found at {self.credentials_path}\n"
                        "Please download credentials.json from Google Cloud Console:\n"
                        "1. Go to https://console.cloud.google.com/\n"
                        "2. Enable Gmail API\n"
                        "3. Create OAuth 2.0 credentials\n"
                        "4. Download as 'gmail_credentials.json' and place in credentials/"
                    )

                logger.info("Starting Gmail OAuth2 flow")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Gmail authentication successful")

            # Save the credentials for the next run
            try:
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info("Saved Gmail authentication token")
            except Exception as e:
                logger.error(f"Could not save token: {e}")

        self.creds = creds
        return creds

    def get_service(self):
        """
        Get authenticated Gmail service object.

        Returns:
            Gmail service object for API calls
        """
        if not self.service:
            if not self.creds:
                self.authenticate()

            try:
                self.service = build('gmail', 'v1', credentials=self.creds)
                logger.info("Gmail service created successfully")
            except Exception as e:
                logger.error(f"Failed to create Gmail service: {e}")
                raise

        return self.service

    def test_connection(self) -> bool:
        """
        Test Gmail API connection.

        Returns:
            True if connection successful
        """
        try:
            service = self.get_service()
            # Try to get user profile
            result = service.users().getProfile(userId='me').execute()
            logger.info(f"Gmail connected: {result.get('emailAddress')}")
            return True
        except HttpError as error:
            logger.error(f"Gmail connection test failed: {error}")
            return False

    def get_user_email(self) -> Optional[str]:
        """
        Get the authenticated user's email address.

        Returns:
            Email address string or None
        """
        try:
            service = self.get_service()
            result = service.users().getProfile(userId='me').execute()
            return result.get('emailAddress')
        except Exception as e:
            logger.error(f"Could not get user email: {e}")
            return None

    @staticmethod
    def setup_credentials():
        """
        Interactive setup helper for Gmail credentials.
        """
        print("\n=== Gmail API Setup ===")
        print("\nTo use Gmail API, you need to:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing")
        print("3. Enable Gmail API")
        print("4. Create credentials (OAuth 2.0 Client ID)")
        print("5. Download credentials as JSON")
        print("6. Save as 'credentials/gmail_credentials.json'")
        print("\nAuthorized redirect URIs should include:")
        print("- http://localhost")
        print("\nOnce you have the credentials file, run this script again.")

        credentials_dir = Path(__file__).parent.parent / 'credentials'
        credentials_dir.mkdir(parents=True, exist_ok=True)
        print(f"\nPlace credentials.json in: {credentials_dir}/")


def get_gmail_service():
    """
    Convenience function to get Gmail service.

    Returns:
        Authenticated Gmail service object
    """
    gmail = GmailService()
    return gmail.get_service()


if __name__ == "__main__":
    # Test Gmail authentication
    print("Testing Gmail authentication...")

    try:
        gmail = GmailService()
        service = gmail.get_service()

        if gmail.test_connection():
            email = gmail.get_user_email()
            print(f"✓ Successfully authenticated as: {email}")
        else:
            print("✗ Authentication failed")
    except FileNotFoundError:
        GmailService.setup_credentials()
    except Exception as e:
        print(f"✗ Error: {e}")