"""Orchestrator for Fireflies Meeting Notes processing.

Coordinates three independent outputs:
1. SES email with detailed summary + "Save to Obsidian" button
2. Todoist tasks in Inbox for each action item
3. Direct obsidian:// URI for one-click note saving (no S3 needed)
"""

import logging
import os
import urllib.parse
from typing import Any, Dict

from email_builder import send_meeting_email
from fireflies_service import FirefliesService
from obsidian_formatter import build_full_markdown_safe, store_metadata, store_note
from title_generator import generate_title
from todoist_service import MeetingTodoistService

logger = logging.getLogger(__name__)


def _classify_recording(transcript) -> str:
    """Classify a recording as 'solo' or 'meeting'.

    Solo: user talking to themselves (e.g. dictating action items).
    Meeting: conversation with others.

    Detection uses unique speaker names from the transcript sentences,
    falling back to participant count.
    """
    unique_speakers = set()
    for s in transcript.transcript_sentences:
        speaker = s.get("speaker", "").strip()
        if speaker and speaker.lower() != "unknown":
            unique_speakers.add(speaker.lower())

    participant_count = len(transcript.participants) if transcript.participants else 0

    # Solo if only one unique speaker or one participant (and no speaker data)
    if len(unique_speakers) <= 1 and participant_count <= 1:
        return "solo"
    if len(unique_speakers) > 1:
        return "meeting"
    if participant_count > 1:
        return "meeting"
    return "solo"


def process_meeting(transcript_id: str) -> Dict[str, Any]:
    """Process a completed meeting transcript through all three outputs.

    Each output is independent: failure in one doesn't block others.

    Args:
        transcript_id: The Fireflies transcript ID to process.

    Returns:
        Result dict with status of each output and any errors.
    """
    result: Dict[str, Any] = {
        "transcript_id": transcript_id,
        "email": {"status": "skipped"},
        "todoist": {"status": "skipped"},
        "obsidian": {"status": "skipped"},
        "errors": [],
    }

    # Fetch transcript from Fireflies
    fireflies_api_key = os.environ.get("FIREFLIES_API_KEY", "")
    if not fireflies_api_key:
        raise ValueError("FIREFLIES_API_KEY not set")

    service = FirefliesService(fireflies_api_key)
    transcript = service.fetch_transcript(transcript_id)
    result["title"] = transcript.title

    # Generate descriptive title via Bedrock
    descriptive_title = generate_title(
        transcript.summary_overview, transcript.keywords, transcript.title
    )
    result["descriptive_title"] = descriptive_title

    # Classify recording type
    recording_type = _classify_recording(transcript)
    result["recording_type"] = recording_type
    logger.info(
        f"Processing {recording_type} recording: {transcript.title} -> '{descriptive_title}'"
    )

    # --- Output 1: Build Obsidian button URL via Lambda Function URL ---
    # The email button points to https://<function-url>?action=save_obsidian&...
    # which serves a redirect page that opens obsidian://
    # Pre-store compact markdown in S3 so click-time avoids re-fetching from Fireflies.
    obsidian_button_url = ""
    recordings_url = ""
    try:
        function_url = os.environ.get("FUNCTION_URL", "")
        action_token = os.environ.get("ACTION_TOKEN", "")

        if function_url and action_token:
            # Pre-store full markdown in S3 for fast retrieval at click time
            s3_bucket = os.environ.get("S3_BUCKET", "")
            if s3_bucket:
                try:
                    full_md = build_full_markdown_safe(transcript)
                    store_note(transcript_id, full_md, s3_bucket)
                    logger.info(f"Pre-stored note in S3 for transcript {transcript_id}")
                except Exception as s3_err:
                    logger.warning(f"S3 pre-store failed (non-fatal): {s3_err}")

                try:
                    store_metadata(
                        transcript_id, transcript, descriptive_title, s3_bucket
                    )
                    logger.info(f"Stored metadata in S3 for transcript {transcript_id}")
                except Exception as meta_err:
                    logger.warning(f"Metadata store failed (non-fatal): {meta_err}")

            title_encoded = urllib.parse.quote(descriptive_title, safe="")
            obsidian_button_url = (
                f"{function_url.rstrip('/')}?"
                f"action=save_obsidian&transcript_id={transcript_id}"
                f"&title={title_encoded}&token={action_token}"
            )
            recordings_url = (
                f"{function_url.rstrip('/')}?" f"action=recordings&token={action_token}"
            )
            result["obsidian"] = {"status": "success"}
            logger.info("Obsidian button URL built via Function URL")
        else:
            result["obsidian"] = {
                "status": "skipped",
                "reason": "missing FUNCTION_URL or ACTION_TOKEN",
            }
            logger.warning(
                "Obsidian button skipped: missing FUNCTION_URL or ACTION_TOKEN"
            )
    except Exception as e:
        result["obsidian"] = {"status": "error", "error": str(e)}
        result["errors"].append(f"obsidian: {e}")
        logger.error(f"Obsidian button URL failed: {e}", exc_info=True)

    # --- Output 2: Create Todoist tasks ---
    tasks_created = 0
    try:
        todoist_token = os.environ.get("TODOIST_API_TOKEN", "")
        if todoist_token and transcript.action_items:
            todoist = MeetingTodoistService(todoist_token)
            tasks_created = todoist.create_action_tasks(
                transcript.action_items, transcript.title, transcript.date
            )
            result["todoist"] = {"status": "success", "tasks_created": tasks_created}
        elif not transcript.action_items:
            result["todoist"] = {"status": "skipped", "reason": "no action items"}
            logger.info("No action items found — skipping Todoist")
        else:
            result["todoist"] = {"status": "skipped", "reason": "missing config"}
    except Exception as e:
        result["todoist"] = {"status": "error", "error": str(e)}
        result["errors"].append(f"todoist: {e}")
        logger.error(f"Todoist task creation failed: {e}", exc_info=True)

    # --- Output 3: Send summary email ---
    # Solo recordings (just dictating action items) skip email entirely.
    # Meeting recordings send email with key actions + follow-up template.
    if recording_type == "solo":
        result["email"] = {"status": "skipped", "reason": "solo recording"}
        logger.info("Email skipped: solo recording (no other participants)")
    else:
        try:
            recipient = os.environ.get("REPORT_EMAIL", "")
            ses_sender = os.environ.get("SES_SENDER_EMAIL", "")

            if recipient and ses_sender:
                send_meeting_email(
                    transcript,
                    recipient,
                    ses_sender,
                    obsidian_button_url=obsidian_button_url,
                    tasks_created=tasks_created,
                    descriptive_title=descriptive_title,
                    recordings_url=recordings_url,
                    include_followup_template=True,
                )
                result["email"] = {"status": "success"}
            else:
                result["email"] = {"status": "skipped", "reason": "missing config"}
                logger.warning(
                    "Email skipped: missing REPORT_EMAIL or SES_SENDER_EMAIL"
                )
        except Exception as e:
            result["email"] = {"status": "error", "error": str(e)}
            result["errors"].append(f"email: {e}")
            logger.error(f"Email sending failed: {e}", exc_info=True)

    error_count = len(result["errors"])
    if error_count == 0:
        logger.info(f"All outputs completed successfully for '{transcript.title}'")
    else:
        logger.warning(
            f"{error_count} error(s) processing '{transcript.title}': "
            + "; ".join(result["errors"])
        )

    return result
