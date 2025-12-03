#!/usr/bin/env python3
"""
Generate Gmail token with gmail.send scope.

Run this script locally to authenticate and generate a token with the correct scope.
"""

from google_auth_oauthlib.flow import InstalledAppFlow
import pickle
from pathlib import Path

# Required scope for sending emails
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def main():
    base_dir = Path(__file__).parent.parent
    credentials_path = base_dir / 'credentials' / 'gmail_credentials.json'
    token_path = base_dir / 'credentials' / 'gmail_token.pickle'

    print(f"Using credentials: {credentials_path}")
    print(f"Token will be saved to: {token_path}")
    print(f"Required scope: {SCOPES}")
    print()
    print("A browser window will open. Please authenticate with your Google account.")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(port=8080, open_browser=True)

    with open(token_path, 'wb') as token:
        pickle.dump(creds, token)

    print()
    print(f"Token saved to: {token_path}")
    print(f"Scopes: {creds.scopes}")
    print()
    print("Next steps:")
    print("1. Upload to S3: aws s3 cp credentials/gmail_token.pickle s3://ynab-reviewer-credentials-718881314209/")
    print("2. Test the Lambda function")

if __name__ == '__main__':
    main()
