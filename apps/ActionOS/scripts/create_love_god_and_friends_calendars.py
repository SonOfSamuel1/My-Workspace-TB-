#!/usr/bin/env python3
"""Create Love God and Love Friends & Family Google Calendars using SSM-stored credentials.

Usage:
    python scripts/create_love_god_and_friends_calendars.py
"""

import json

import boto3
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_parameter(name):
    ssm = boto3.client("ssm", region_name="us-east-1")
    r = ssm.get_parameter(Name=name, WithDecryption=True)
    return r["Parameter"]["Value"]


def main():
    print("Loading credentials from SSM...")
    creds_json = get_parameter("/action-dashboard/calendar-credentials")
    token_json = get_parameter("/action-dashboard/calendar-token")

    creds_data = json.loads(creds_json)
    token_data = json.loads(token_json)

    client_cfg = creds_data.get("installed", creds_data.get("web", {}))

    creds = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_cfg.get("client_id"),
        client_secret=client_cfg.get("client_secret"),
        scopes=SCOPES,
    )

    service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    calendars_to_create = [
        {
            "summary": "Love God",
            "description": "Events and plans for loving God — devotions, prayer, worship, church",
        },
        {
            "summary": "Love Friends and Family",
            "description": "Events and plans for friends and extended family",
        },
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


if __name__ == "__main__":
    main()
