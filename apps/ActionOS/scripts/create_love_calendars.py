#!/usr/bin/env python3
"""One-time script to create Love Brittany and Love Children Google Calendars.

Run once, copy the printed calendar IDs into calendar_service.py, then archive.

Usage:
    python scripts/create_love_calendars.py

Requires:
    - google-api-python-client, google-auth-oauthlib
    - Valid OAuth client credentials (from SSM or local file)
    - Will open browser for OAuth consent with full calendar read/write scope
"""

import json
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main():
    # Load OAuth client credentials (not the token — we need a fresh auth with write scope)
    creds_json = os.environ.get("CALENDAR_CREDENTIALS_JSON", "")

    if not creds_json:
        creds_path = os.path.join(
            os.path.dirname(__file__), "..", "credentials", "calendar_credentials.json"
        )
        if os.path.exists(creds_path):
            with open(creds_path) as f:
                creds_json = f.read()
        else:
            print(
                f"ERROR: No credentials found. Set CALENDAR_CREDENTIALS_JSON env var or place file at {creds_path}"
            )
            sys.exit(1)

    creds_data = json.loads(creds_json)

    # Write client credentials to a temp file for the OAuth flow
    import tempfile

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(creds_data, tmp)
    tmp.close()

    print(
        "Opening browser for Google OAuth consent (full calendar read/write access)..."
    )
    print("Please authorize the app in your browser.\n")

    try:
        flow = InstalledAppFlow.from_client_secrets_file(tmp.name, SCOPES)
        creds = flow.run_local_server(port=0)
    finally:
        os.unlink(tmp.name)

    service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    calendars_to_create = [
        {"summary": "Love Brittany", "description": "Events and plans for Brittany"},
        {"summary": "Love Children", "description": "Events and plans for the kids"},
    ]

    print("Creating Google Calendars...\n")
    for cal_info in calendars_to_create:
        try:
            created = service.calendars().insert(body=cal_info).execute()
            cal_id = created.get("id", "")
            print(f"  Created: {cal_info['summary']}")
            print(f"  Calendar ID: {cal_id}")
            print()
        except Exception as e:
            print(f"  FAILED to create {cal_info['summary']}: {e}")
            print()

    print("Copy the Calendar IDs above into calendar_service.py CALENDAR_IDS dict.")
    print(
        "Replace PLACEHOLDER_LOVE_BRITTANY_CALENDAR_ID and PLACEHOLDER_LOVE_CHILDREN_CALENDAR_ID."
    )


if __name__ == "__main__":
    main()
