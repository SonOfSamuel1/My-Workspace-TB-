#!/usr/bin/env python3
"""
Re-authorize Gmail with correct scopes for sending email.

This script will:
1. Delete any existing token
2. Start OAuth flow with gmail.send scope
3. Save the new token
"""

import os
import sys
import pickle
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# Gmail API scope for sending emails
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def main():
    base_dir = Path(__file__).parent.parent
    credentials_path = base_dir / 'credentials' / 'gmail_credentials.json'
    token_path = base_dir / 'credentials' / 'gmail_token.pickle'

    print(f"Credentials file: {credentials_path}")
    print(f"Token file: {token_path}")

    # Check credentials exist
    if not credentials_path.exists():
        print(f"ERROR: Credentials file not found at {credentials_path}")
        sys.exit(1)

    # Delete existing token
    if token_path.exists():
        print("Deleting existing token...")
        token_path.unlink()

    print(f"\nStarting OAuth flow with scope: {SCOPES[0]}")
    print("A browser window will open for authentication...\n")

    # Run OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(
        str(credentials_path), SCOPES
    )
    creds = flow.run_local_server(port=0)

    # Save the token
    with open(token_path, 'wb') as token:
        pickle.dump(creds, token)

    print(f"\nNew token saved to: {token_path}")
    print(f"Scopes: {creds.scopes}")
    print("\nNow upload the new token to S3:")
    print(f'  aws s3 cp "{token_path}" s3://ynab-reviewer-credentials-718881314209/gmail_token.pickle')

if __name__ == '__main__':
    main()
