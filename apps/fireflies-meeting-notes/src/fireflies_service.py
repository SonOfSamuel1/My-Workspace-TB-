"""Fireflies.ai GraphQL API client for fetching meeting transcripts."""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.fireflies.ai/graphql"

# Regex pattern matching common emoji Unicode ranges
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Misc Symbols & Pictographs
    "\U0001F680-\U0001F6FF"  # Transport & Map
    "\U0001F1E0-\U0001F1FF"  # Flags
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols Extended-A
    "\U00002702-\U000027B0"  # Dingbats
    "\U0000FE00-\U0000FE0F"  # Variation Selectors
    "\U0000200D"  # Zero Width Joiner
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)


def _strip_emojis(text: str) -> str:
    """Remove emoji characters from text."""
    return _EMOJI_RE.sub("", text).strip()


@dataclass
class TranscriptData:
    """Structured meeting transcript data shared across modules."""

    transcript_id: str
    title: str
    date: str
    duration_minutes: float
    participants: List[str]
    summary_overview: str
    summary_bullets: List[str]
    action_items: List[str]
    keywords: List[str]
    transcript_sentences: List[Dict[str, str]]
    audio_url: str
    organizer_email: str = ""


def _parse_bullet_string(raw: str) -> List[str]:
    """Parse Fireflies shorthand_bullet string into a list of bullet lines.

    The string contains emoji-prefixed section headers and indented bullet lines.
    We extract all non-header, non-empty lines as bullets.
    Emojis and inline timestamps like (00:00 - 02:38) are stripped.
    """
    if not raw:
        return []
    bullets = []
    for line in raw.strip().split("\n"):
        line = _strip_emojis(line).strip()
        if not line:
            continue
        # Strip inline timestamp ranges like (00:00 - 02:38)
        line = re.sub(r"\s*\(\d+:\d+\s*-\s*\d+:\d+\)\s*", " ", line).strip()
        if line:
            bullets.append(line)
    return bullets


def _parse_action_items_string(raw: str) -> List[str]:
    """Parse Fireflies action_items string into individual action items.

    The string has bold headers like **Group Name** followed by action lines.
    We extract the action lines, skipping the group headers.
    Emojis and timestamps are stripped.
    """
    if not raw:
        return []
    items = []
    for line in raw.strip().split("\n"):
        line = _strip_emojis(line).strip()
        if not line:
            continue
        # Skip group headers like **All Church Members**
        if line.startswith("**") and line.endswith("**"):
            continue
        # Strip trailing timestamp like (38:19)
        cleaned = re.sub(r"\s*\(\d+:\d+\)\s*$", "", line)
        # Strip inline timestamp ranges like (00:00 - 02:38)
        cleaned = re.sub(r"\s*\(\d+:\d+\s*-\s*\d+:\d+\)\s*", " ", cleaned).strip()
        if cleaned:
            items.append(cleaned)
    return items


class FirefliesService:
    """Client for the Fireflies.ai GraphQL API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def fetch_transcript(self, transcript_id: str) -> TranscriptData:
        """Fetch a full transcript by ID from Fireflies.

        Args:
            transcript_id: The Fireflies transcript ID.

        Returns:
            TranscriptData with all meeting details.
        """
        query = """
        query Transcript($transcriptId: String!) {
            transcript(id: $transcriptId) {
                id
                title
                date
                duration
                participants
                organizer_email
                summary {
                    overview
                    shorthand_bullet
                    action_items
                    keywords
                }
                sentences {
                    speaker_name
                    text
                }
                audio_url
            }
        }
        """

        try:
            response = requests.post(
                GRAPHQL_URL,
                headers=self.headers,
                json={
                    "query": query,
                    "variables": {"transcriptId": transcript_id},
                },
            )
            response.raise_for_status()
            result = response.json()

            if "errors" in result:
                error_msg = result["errors"][0].get("message", "Unknown error")
                raise ValueError(f"Fireflies API error: {error_msg}")

            data = result["data"]["transcript"]
            summary = data.get("summary") or {}

            # Parse duration from seconds to minutes
            duration_seconds = data.get("duration") or 0
            duration_minutes = round(duration_seconds / 60, 1)

            # Parse date (Fireflies returns epoch ms)
            date_epoch = data.get("date")
            if date_epoch:
                from datetime import datetime, timezone

                dt = datetime.fromtimestamp(int(date_epoch) / 1000, tz=timezone.utc)
                date_str = dt.strftime("%B %d, %Y at %I:%M %p UTC")
            else:
                date_str = "Unknown date"

            # Parse sentences
            sentences = []
            for s in data.get("sentences") or []:
                sentences.append(
                    {
                        "speaker": s.get("speaker_name") or "Unknown",
                        "text": s.get("text", ""),
                    }
                )

            # Parse string fields into lists
            raw_bullets = summary.get("shorthand_bullet", "")
            bullets = (
                _parse_bullet_string(raw_bullets)
                if isinstance(raw_bullets, str)
                else (raw_bullets or [])
            )

            raw_actions = summary.get("action_items", "")
            action_items = (
                _parse_action_items_string(raw_actions)
                if isinstance(raw_actions, str)
                else (raw_actions or [])
            )

            transcript = TranscriptData(
                transcript_id=transcript_id,
                title=data.get("title", "Untitled Meeting"),
                date=date_str,
                duration_minutes=duration_minutes,
                participants=data.get("participants") or [],
                summary_overview=_strip_emojis(summary.get("overview", "")),
                summary_bullets=bullets,
                action_items=action_items,
                keywords=summary.get("keywords") or [],
                transcript_sentences=sentences,
                audio_url=data.get("audio_url", ""),
                organizer_email=data.get("organizer_email", ""),
            )

            logger.info(
                f"Fetched transcript '{transcript.title}' "
                f"({len(sentences)} sentences, "
                f"{len(transcript.action_items)} action items)"
            )
            return transcript

        except requests.RequestException as e:
            logger.error(f"Failed to fetch transcript {transcript_id}: {e}")
            raise

    def fetch_all_transcripts(self, page_size: int = 50) -> List[Dict[str, Any]]:
        """Fetch all transcript IDs and basic metadata via pagination.

        Args:
            page_size: Number of transcripts per page (max 50 for Fireflies).

        Returns:
            List of dicts with id, title, date, duration for each transcript.
        """
        query = """
        query Transcripts($limit: Int!, $skip: Int!) {
            transcripts(limit: $limit, skip: $skip) {
                id
                title
                date
                duration
            }
        }
        """

        all_transcripts: List[Dict[str, Any]] = []
        skip = 0

        while True:
            response = requests.post(
                GRAPHQL_URL,
                headers=self.headers,
                json={
                    "query": query,
                    "variables": {"limit": page_size, "skip": skip},
                },
            )
            response.raise_for_status()
            result = response.json()

            if "errors" in result:
                error_msg = result["errors"][0].get("message", "Unknown error")
                raise ValueError(f"Fireflies API error: {error_msg}")

            page = result["data"]["transcripts"] or []
            all_transcripts.extend(page)
            logger.info(f"Fetched page at skip={skip}: {len(page)} transcripts")

            if len(page) < page_size:
                break
            skip += page_size

        logger.info(f"Total transcripts fetched: {len(all_transcripts)}")
        return all_transcripts
