"""Eight Sleep cloud API client for fetching sleep data."""

from __future__ import annotations

import requests
from datetime import datetime, timedelta


# Extracted from Eight Sleep Android APK v7.39.17
_CLIENT_ID = "0894c7f33bb94800a03f1f4df13a4f38"
_CLIENT_SECRET = (
    "f0954a3ed5763ba3d06834c73731a32f15f168f47d4f164751275def86db0c76"
)
_AUTH_URL = "https://auth-api.8slp.net/v1/tokens"
_API_URL = "https://client-api.8slp.net/v1"


class EightSleepClient:
    def __init__(self, email: str, password: str, timezone: str = "America/New_York"):
        self.email = email
        self.password = password
        self.timezone = timezone
        self._token = None
        self._user_id = None

    def authenticate(self):
        resp = requests.post(_AUTH_URL, json={
            "client_id": _CLIENT_ID,
            "client_secret": _CLIENT_SECRET,
            "grant_type": "password",
            "username": self.email,
            "password": self.password,
        })
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._user_id = data["userId"]

    def _headers(self):
        return {"Authorization": f"Bearer {self._token}"}

    def get_sleep_data(self, date_from: str, date_to: str) -> list[dict]:
        """Fetch sleep trends for a date range. Returns list of day objects."""
        resp = requests.get(
            f"{_API_URL}/users/{self._user_id}/trends",
            params={
                "from": date_from,
                "to": date_to,
                "tz": self.timezone,
                "include-main": "false",
                "include-all-sessions": "true",
                "model-version": "v2",
            },
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json().get("days", [])

    def get_last_night_sleep(self) -> dict | None:
        """Get the most recent completed sleep session."""
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        days = self.get_sleep_data(yesterday, today)

        # Return the most recent day that has presence data and isn't incomplete
        for day in reversed(days):
            if day.get("presenceStart") and day.get("presenceEnd"):
                incomplete = day.get("incomplete", False)
                if not incomplete:
                    return day

        # Fall back to any day with data
        for day in reversed(days):
            if day.get("presenceStart") and day.get("presenceEnd"):
                return day

        return None
