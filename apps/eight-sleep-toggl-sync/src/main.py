"""Eight Sleep -> Toggl Track sleep sync.

Fetches last night's sleep data from Eight Sleep and creates a
time entry in Toggl Track with sleep stats in the description.
"""

import os
import logging
from datetime import datetime, timedelta, timezone

from eight_sleep import EightSleepClient
from toggl import TogglClient

logger = logging.getLogger(__name__)

SLEEP_PROJECT_ID = 217190223  # "Sleep" project in Toggl


def format_duration(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h}h {m}m"


def build_description(day: dict) -> str:
    """Build a rich Toggl time entry description from Eight Sleep data."""
    score = day.get("score", "N/A")
    sleep_dur = format_duration(day.get("sleepDuration", 0))
    deep_min = day.get("deepDuration", 0) // 60
    deep_pct = round(day.get("deepPercent", 0) * 100)
    rem_min = day.get("remDuration", 0) // 60
    rem_pct = round(day.get("remPercent", 0) * 100)
    light_min = day.get("lightDuration", 0) // 60
    tnt = day.get("tnt", 0)

    quality = day.get("sleepQualityScore", {})
    hr = quality.get("heartRate", {}).get("current", "N/A")
    hrv = quality.get("hrv", {}).get("current", "N/A")
    rr = quality.get("respiratoryRate", {}).get("current", "N/A")

    lines = [
        f"Score: {score}/100 | Slept: {sleep_dur}",
        f"Deep: {deep_min}m ({deep_pct}%) | REM: {rem_min}m ({rem_pct}%) | Light: {light_min}m",
        f"HR: {hr} bpm | HRV: {hrv} ms | RR: {rr} br/min | T&T: {tnt}",
    ]
    return " | ".join(lines)


def already_synced(toggl: TogglClient, presence_start: str) -> bool:
    """Check if a sleep entry already exists for this session."""
    start_dt = datetime.fromisoformat(presence_start.replace("Z", "+00:00"))
    check_from = (start_dt - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    check_to = (start_dt + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    entries = toggl.get_time_entries(check_from, check_to)
    for entry in entries:
        if entry.get("project_id") == SLEEP_PROJECT_ID:
            return True
        desc = entry.get("description", "")
        if "Score:" in desc and "Slept:" in desc:
            return True
    return False


def sync():
    """Main sync function."""
    eight_email = os.environ["EIGHT_SLEEP_EMAIL"]
    eight_password = os.environ["EIGHT_SLEEP_PASSWORD"]
    toggl_token = os.environ["TOGGL_API_TOKEN"]
    toggl_workspace = int(os.environ["TOGGL_WORKSPACE_ID"])

    # Fetch sleep data
    es = EightSleepClient(eight_email, eight_password)
    es.authenticate()
    logger.info("Eight Sleep authenticated")

    day = es.get_last_night_sleep()
    if not day:
        logger.info("No sleep data found for last night")
        return {"synced": False, "reason": "no_data"}

    logger.info(f"Found sleep data for {day['day']}: score={day.get('score')}")

    # Check for duplicates
    toggl = TogglClient(toggl_token, toggl_workspace)
    presence_start = day["presenceStart"]

    if already_synced(toggl, presence_start):
        logger.info("Sleep entry already exists in Toggl, skipping")
        return {"synced": False, "reason": "already_exists"}

    # Create Toggl entry
    presence_end = day["presenceEnd"]
    start_dt = datetime.fromisoformat(presence_start.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(presence_end.replace("Z", "+00:00"))
    duration = int((end_dt - start_dt).total_seconds())

    description = build_description(day)

    entry = toggl.create_time_entry(
        description=description,
        start=presence_start,
        duration_seconds=duration,
        project_id=SLEEP_PROJECT_ID,
        tags=["sleep", "eight-sleep", "auto"],
    )

    logger.info(f"Created Toggl entry {entry['id']}: {format_duration(duration)}")
    return {
        "synced": True,
        "toggl_entry_id": entry["id"],
        "date": day["day"],
        "score": day.get("score"),
        "duration": format_duration(duration),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = sync()
    print(result)
