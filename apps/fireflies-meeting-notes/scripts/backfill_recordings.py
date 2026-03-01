#!/usr/bin/env python3
"""Backfill all historical Fireflies transcripts into S3.

Fetches every transcript from the Fireflies API and stores its markdown note
and metadata JSON in S3 so they appear on the "All Recordings" web page.

Usage:
    cd apps/fireflies-meeting-notes
    python scripts/backfill_recordings.py
"""

import logging
import os
import sys
import time

import boto3
from dotenv import load_dotenv

# Add src/ to path so we can import project modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fireflies_service import FirefliesService  # noqa: E402
from obsidian_formatter import (  # noqa: E402
    build_full_markdown_safe,
    store_metadata,
    store_note,
)
from title_generator import generate_title  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

RATE_LIMIT_DELAY = 3.0  # seconds between transcript fetches


def metadata_exists(transcript_id: str, s3_bucket: str) -> bool:
    """Check if metadata already exists in S3 for this transcript."""
    s3 = boto3.client("s3", region_name="us-east-1")
    try:
        s3.head_object(Bucket=s3_bucket, Key=f"metadata/{transcript_id}.json")
        return True
    except s3.exceptions.ClientError:
        return False


def main():
    load_dotenv()

    api_key = os.environ.get("FIREFLIES_API_KEY", "")
    s3_bucket = os.environ.get("S3_BUCKET", "")

    if not api_key:
        logger.error("FIREFLIES_API_KEY not set")
        sys.exit(1)
    if not s3_bucket:
        logger.error("S3_BUCKET not set")
        sys.exit(1)

    service = FirefliesService(api_key)

    logger.info("Fetching all transcript IDs from Fireflies...")
    all_transcripts = service.fetch_all_transcripts()
    total = len(all_transcripts)
    logger.info(f"Found {total} transcripts")

    processed = 0
    skipped = 0
    failed = []

    for i, entry in enumerate(all_transcripts, 1):
        tid = entry["id"]
        entry_title = entry.get("title", "Unknown")

        if metadata_exists(tid, s3_bucket):
            logger.info(f"[{i}/{total}] Skipping {tid} ({entry_title}) — already in S3")
            skipped += 1
            continue

        try:
            logger.info(f"[{i}/{total}] Processing {tid} ({entry_title})...")
            transcript = service.fetch_transcript(tid)

            descriptive_title = generate_title(
                transcript.summary_overview,
                transcript.keywords,
                transcript.title,
            )

            full_md = build_full_markdown_safe(transcript)
            store_note(tid, full_md, s3_bucket)
            store_metadata(tid, transcript, descriptive_title, s3_bucket)

            processed += 1
            logger.info(f"[{i}/{total}] Stored: '{descriptive_title}'")
        except Exception as e:
            logger.error(f"[{i}/{total}] Failed {tid} ({entry_title}): {e}")
            failed.append({"id": tid, "title": entry_title, "error": str(e)})

        time.sleep(RATE_LIMIT_DELAY)

    # Summary
    logger.info("=" * 60)
    logger.info("Backfill complete")
    logger.info(f"  Total:     {total}")
    logger.info(f"  Processed: {processed}")
    logger.info(f"  Skipped:   {skipped}")
    logger.info(f"  Failed:    {len(failed)}")

    if failed:
        logger.warning("Failed transcripts:")
        for f in failed:
            logger.warning(f"  - {f['id']} ({f['title']}): {f['error']}")


if __name__ == "__main__":
    main()
