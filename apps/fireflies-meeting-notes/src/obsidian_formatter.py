"""Build Obsidian-compatible markdown notes and generate direct obsidian:// URIs."""

import json
import logging
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from fireflies_service import TranscriptData

logger = logging.getLogger(__name__)

_INDEX_KEY = "index.json"


def build_markdown(transcript: TranscriptData) -> str:
    """Build an Obsidian-compatible markdown note from transcript data."""
    lines = []

    lines.append(f"## Meeting: {transcript.title}")
    participants_str = (
        ", ".join(transcript.participants) if transcript.participants else "N/A"
    )
    lines.append(
        f"**Date:** {transcript.date} | "
        f"**Duration:** {transcript.duration_minutes} min | "
        f"**Participants:** {participants_str}"
    )
    if transcript.audio_url:
        lines.append(f"**Audio:** [Listen to Recording]({transcript.audio_url})")
    lines.append("")
    lines.append("---")
    lines.append("")

    if transcript.summary_overview:
        lines.append("### Summary")
        lines.append(transcript.summary_overview)
        lines.append("")

    if transcript.summary_bullets:
        lines.append("### Key Points")
        for bullet in transcript.summary_bullets:
            lines.append(f"- {bullet}")
        lines.append("")

    if transcript.action_items:
        lines.append("### Action Items")
        for item in transcript.action_items:
            lines.append(f"- [ ] {item}")
        lines.append("")

    if transcript.keywords:
        lines.append("### Keywords")
        lines.append(", ".join(transcript.keywords))
        lines.append("")

    if transcript.transcript_sentences:
        lines.append("### Full Transcript")
        current_speaker = None
        for sentence in transcript.transcript_sentences:
            speaker = sentence.get("speaker", "Unknown")
            text = sentence.get("text", "")
            if speaker != current_speaker:
                if current_speaker is not None:
                    lines.append("")
                lines.append(f"**{speaker}:** {text}")
                current_speaker = speaker
            else:
                lines.append(text)
        lines.append("")

    return "\n".join(lines)


def build_compact_markdown(transcript: TranscriptData) -> str:
    """Build markdown note without the full transcript section."""
    lines = []

    lines.append(f"## Meeting: {transcript.title}")
    participants_str = (
        ", ".join(transcript.participants) if transcript.participants else "N/A"
    )
    lines.append(
        f"**Date:** {transcript.date} | "
        f"**Duration:** {transcript.duration_minutes} min | "
        f"**Participants:** {participants_str}"
    )
    if transcript.audio_url:
        lines.append(f"**Audio:** [Listen to Recording]({transcript.audio_url})")
    lines.append("")
    lines.append("---")
    lines.append("")

    if transcript.summary_overview:
        lines.append("### Summary")
        lines.append(transcript.summary_overview)
        lines.append("")

    if transcript.summary_bullets:
        lines.append("### Key Points")
        for bullet in transcript.summary_bullets:
            lines.append(f"- {bullet}")
        lines.append("")

    if transcript.action_items:
        lines.append("### Action Items")
        for item in transcript.action_items:
            lines.append(f"- [ ] {item}")
        lines.append("")

    if transcript.keywords:
        lines.append("### Keywords")
        lines.append(", ".join(transcript.keywords))
        lines.append("")

    return "\n".join(lines)


def build_full_markdown_safe(
    transcript: TranscriptData, max_encoded_bytes: int = 150_000
) -> str:
    """Build full markdown with transcript, truncating if URL-encoded size exceeds limit."""
    full_md = build_markdown(transcript)
    encoded_size = len(urllib.parse.quote(full_md, safe="").encode("utf-8"))

    if encoded_size <= max_encoded_bytes:
        return full_md

    logger.warning(
        f"Full markdown ({encoded_size} bytes encoded) exceeds {max_encoded_bytes} limit, "
        "truncating transcript"
    )

    compact = build_compact_markdown(transcript)

    if not transcript.transcript_sentences:
        return compact

    lines = [compact.rstrip(), "", "### Full Transcript (Truncated)"]
    current_speaker = None

    for sentence in transcript.transcript_sentences:
        speaker = sentence.get("speaker", "Unknown")
        text = sentence.get("text", "")
        if speaker != current_speaker:
            if current_speaker is not None:
                lines.append("")
            lines.append(f"**{speaker}:** {text}")
            current_speaker = speaker
        else:
            lines.append(text)

        candidate = "\n".join(lines) + "\n\n---\n*Transcript truncated for size.*\n"
        if (
            len(urllib.parse.quote(candidate, safe="").encode("utf-8"))
            > max_encoded_bytes
        ):
            lines.append("")
            lines.append("---")
            lines.append("*Transcript truncated for size.*")
            break
    else:
        return full_md

    return "\n".join(lines) + "\n"


def build_obsidian_uri(transcript: TranscriptData, vault_name: str) -> str:
    """Build a direct obsidian://advanced-uri link that appends note content to the daily note."""
    markdown = build_markdown(transcript)
    vault_encoded = urllib.parse.quote(vault_name, safe="")
    data_encoded = urllib.parse.quote(markdown, safe="")

    uri = (
        f"obsidian://advanced-uri?vault={vault_encoded}"
        f"&daily=true&mode=append&data={data_encoded}"
    )

    logger.info(
        f"Built Obsidian URI for '{transcript.title}' "
        f"(vault={vault_name}, {len(markdown)} chars)"
    )
    return uri


def store_note(transcript_id: str, content: str, s3_bucket: str) -> None:
    """Store a compact markdown note in S3 for fast retrieval at click time."""
    import boto3

    s3_key = f"notes/{transcript_id}.md"
    s3 = boto3.client("s3", region_name="us-east-1")

    s3.put_object(
        Bucket=s3_bucket,
        Key=s3_key,
        Body=content.encode("utf-8"),
        ContentType="text/markdown",
    )
    logger.info(f"Stored note in S3: {s3_key} ({len(content)} chars)")


def retrieve_note(note_id: str, s3_bucket: str) -> str:
    """Retrieve a markdown note from S3 by note ID."""
    import boto3

    s3_key = f"notes/{note_id}.md"
    s3 = boto3.client("s3", region_name="us-east-1")

    try:
        response = s3.get_object(Bucket=s3_bucket, Key=s3_key)
        content = response["Body"].read().decode("utf-8")
        logger.info(f"Retrieved note from S3: {s3_key}")
        return content
    except Exception as e:
        logger.error(f"Failed to retrieve note {note_id}: {e}")
        raise


def store_metadata(
    transcript_id: str,
    transcript: TranscriptData,
    descriptive_title: str,
    s3_bucket: str,
) -> None:
    """Store recording metadata JSON in S3 for the All Recordings web page."""
    import boto3

    metadata = {
        "transcript_id": transcript_id,
        "title": descriptive_title,
        "original_title": transcript.title,
        "date": transcript.date,
        "duration_minutes": transcript.duration_minutes,
        "participants": transcript.participants or [],
        "audio_url": transcript.audio_url or "",
        "action_item_count": (
            len(transcript.action_items) if transcript.action_items else 0
        ),
        "keyword_count": len(transcript.keywords) if transcript.keywords else 0,
        "stored_at": datetime.now(timezone.utc).isoformat(),
    }

    s3_key = f"metadata/{transcript_id}.json"
    s3 = boto3.client("s3", region_name="us-east-1")

    s3.put_object(
        Bucket=s3_bucket,
        Key=s3_key,
        Body=json.dumps(metadata).encode("utf-8"),
        ContentType="application/json",
    )
    logger.info(f"Stored metadata in S3: {s3_key}")

    # Invalidate index so it gets rebuilt on next dashboard load
    try:
        s3.delete_object(Bucket=s3_bucket, Key=_INDEX_KEY)
        logger.info("Invalidated index.json (new metadata stored)")
    except Exception:
        pass  # Non-fatal


def build_index(s3_bucket: str) -> int:
    """Read all individual metadata files and write a single index.json manifest.

    This replaces N individual S3 GETs with 1 on subsequent dashboard loads.

    Args:
        s3_bucket: S3 bucket name.

    Returns:
        Number of recordings indexed.
    """
    import boto3

    s3 = boto3.client("s3", region_name="us-east-1")
    recordings = []

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=s3_bucket, Prefix="metadata/"):
        for obj in page.get("Contents", []):
            if obj["Key"] == f"metadata/{_INDEX_KEY}":
                continue
            try:
                resp = s3.get_object(Bucket=s3_bucket, Key=obj["Key"])
                data = json.loads(resp["Body"].read().decode("utf-8"))
                recordings.append(data)
            except Exception as e:
                logger.warning(f"Skipping corrupt metadata {obj['Key']}: {e}")

    recordings.sort(key=lambda r: r.get("stored_at", ""), reverse=True)

    s3.put_object(
        Bucket=s3_bucket,
        Key=_INDEX_KEY,
        Body=json.dumps(recordings).encode("utf-8"),
        ContentType="application/json",
        CacheControl="no-cache",
    )
    logger.info(f"Built index.json with {len(recordings)} recordings")
    return len(recordings)


def list_recordings(s3_bucket: str) -> List[Dict]:
    """List all stored recording metadata, sorted by most recent first.

    Reads from index.json (1 S3 GET) if available; falls back to reading
    individual metadata files and rebuilds the index for next time.

    Args:
        s3_bucket: S3 bucket name.

    Returns:
        List of metadata dicts sorted by stored_at descending.
    """
    import boto3

    s3 = boto3.client("s3", region_name="us-east-1")

    # Fast path: read pre-built index
    try:
        resp = s3.get_object(Bucket=s3_bucket, Key=_INDEX_KEY)
        recordings = json.loads(resp["Body"].read().decode("utf-8"))
        logger.info(f"Loaded {len(recordings)} recordings from index.json (fast path)")
        return recordings
    except s3.exceptions.NoSuchKey:
        logger.info("index.json not found, reading individual metadata files")
    except Exception as e:
        logger.warning(f"index.json read failed, falling back to individual reads: {e}")

    # Slow path: read all individual files and rebuild index
    recordings = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=s3_bucket, Prefix="metadata/"):
        for obj in page.get("Contents", []):
            try:
                resp = s3.get_object(Bucket=s3_bucket, Key=obj["Key"])
                data = json.loads(resp["Body"].read().decode("utf-8"))
                recordings.append(data)
            except Exception as e:
                logger.warning(f"Skipping corrupt metadata {obj['Key']}: {e}")

    recordings.sort(key=lambda r: r.get("stored_at", ""), reverse=True)
    logger.info(f"Listed {len(recordings)} recordings from S3 (slow path)")

    # Rebuild index for next time
    try:
        s3.put_object(
            Bucket=s3_bucket,
            Key=_INDEX_KEY,
            Body=json.dumps(recordings).encode("utf-8"),
            ContentType="application/json",
            CacheControl="no-cache",
        )
        logger.info("Rebuilt index.json")
    except Exception as e:
        logger.warning(f"Failed to rebuild index.json: {e}")

    return recordings
