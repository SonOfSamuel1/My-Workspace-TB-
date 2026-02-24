#!/usr/bin/env python3
"""
Teaching Selector

Manages a shuffled queue of JT- teaching files stored in S3 state.json.
Picks the next 2 teachings each day, cycling through the full library
before reshuffling (~380 day cycle for 761 notes).
"""

import json
import random
import logging
from typing import Tuple, List
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

STATE_KEY = "state.json"


class TeachingSelector:
    """Selects next 2 teachings from a shuffled queue persisted in S3."""

    def __init__(self, bucket: str, region: str = "us-east-1"):
        self.bucket = bucket
        self.s3 = boto3.client("s3", region_name=region)

    def pick_next_two(self, all_teaching_keys: List[str]) -> Tuple[str, str]:
        """
        Return the next 2 teaching S3 keys to send today.

        Loads state from S3, advances position by 2, saves state back.
        Skips any 0-byte files (Obsidian Sync stubs not yet downloaded).

        Args:
            all_teaching_keys: Full list of JT-*.md S3 keys (for reshuffle)

        Returns:
            Tuple of (teaching_key_1, teaching_key_2)
        """
        # Filter to only keys with real content in S3
        valid_keys = self._filter_nonempty_keys(all_teaching_keys)
        if len(valid_keys) < 2:
            raise ValueError(
                f"Only {len(valid_keys)} non-empty teaching files found in S3. "
                "Run sync_to_s3.py after opening Obsidian to download stubs."
            )

        state = self._load_state()

        # First run or queue contains stale/empty keys → reinitialize
        if not state.get("queue") or len(state["queue"]) < 2:
            logger.info("Initializing teaching queue with shuffle...")
            state = self._initialize_queue(valid_keys)

        queue = state["queue"]
        position = state.get("position", 0)

        # Guard against corrupted/stale position value
        if position < 0 or position >= len(queue):
            logger.warning(
                f"State position {position} out of bounds for queue len {len(queue)} — resetting"
            )
            state = self._initialize_queue(valid_keys)
            queue = state["queue"]
            position = 0

        # Reshuffle if fewer than 2 slots remain
        if position + 2 > len(queue):
            logger.info(
                f"Queue exhausted at position {position}/{len(queue)}. Reshuffling..."
            )
            state = self._initialize_queue(valid_keys)
            queue = state["queue"]
            position = 0

        teaching_1 = queue[position]
        teaching_2 = queue[position + 1]

        # Advance and save
        state["position"] = position + 2
        self._save_state(state)

        logger.info(f"Selected teachings at positions {position} and {position + 1}:")
        logger.info(f"  1: {teaching_1}")
        logger.info(f"  2: {teaching_2}")

        return teaching_1, teaching_2

    def _filter_nonempty_keys(self, keys: List[str]) -> List[str]:
        """Return only keys that have actual content in S3 (size > 0)."""
        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            sizes = {}
            for page in paginator.paginate(Bucket=self.bucket):
                for obj in page.get("Contents", []):
                    sizes[obj["Key"]] = obj["Size"]

            MIN_CONTENT_BYTES = 1500
            valid = [k for k in keys if sizes.get(k, 0) >= MIN_CONTENT_BYTES]
            skipped = len(keys) - len(valid)
            if skipped:
                logger.info(
                    f"Skipping {skipped} files below {MIN_CONTENT_BYTES} bytes (stubs or near-empty notes)"
                )
            logger.info(f"Using {len(valid)} teachings with content")
            return valid
        except ClientError as e:
            logger.warning(f"Could not filter empty keys: {e}. Using all keys.")
            return keys

    def pop_one_key(self, all_teaching_keys: List[str]) -> str:
        """Return and consume the next single key in the queue (used to replace a skipped teaching)."""
        valid_keys = self._filter_nonempty_keys(all_teaching_keys)
        state = self._load_state()
        queue = state["queue"]
        position = state.get("position", 0)

        if position >= len(queue):
            state = self._initialize_queue(valid_keys)
            queue = state["queue"]
            position = 0

        key = queue[position]
        state["position"] = position + 1
        self._save_state(state)
        logger.info(f"Popped replacement teaching at position {position}: {key}")
        return key

    def get_queue_status(self) -> dict:
        """Return current queue progress for logging/debugging."""
        state = self._load_state()
        queue = state.get("queue", [])
        position = state.get("position", 0)
        remaining = max(0, len(queue) - position)
        return {
            "total": len(queue),
            "position": position,
            "remaining": remaining,
            "days_until_reset": remaining // 2,
        }

    def _initialize_queue(self, all_teaching_keys: List[str]) -> dict:
        """Create a new shuffled queue and save it to S3."""
        shuffled = list(all_teaching_keys)
        random.shuffle(shuffled)

        # Ensure even length so we always have pairs
        if len(shuffled) % 2 != 0:
            shuffled.append(shuffled[0])

        state = {"queue": shuffled, "position": 0}
        self._save_state(state)
        logger.info(f"Queue initialized with {len(shuffled)} teachings")
        return state

    def _load_state(self) -> dict:
        """Load state.json from S3. Returns empty dict if not found."""
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=STATE_KEY)
            data = json.loads(response["Body"].read().decode("utf-8"))
            logger.debug(
                f"Loaded state: position={data.get('position')}, queue_len={len(data.get('queue', []))}"
            )
            return data
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.info("No state.json found in S3, starting fresh")
                return {}
            logger.error(f"Error loading state from S3: {e}")
            raise

    def _save_state(self, state: dict):
        """Save state.json to S3."""
        try:
            body = json.dumps(state, indent=2)
            self.s3.put_object(
                Bucket=self.bucket,
                Key=STATE_KEY,
                Body=body.encode("utf-8"),
                ContentType="application/json",
            )
            logger.debug(
                f"Saved state: position={state.get('position')}, queue_len={len(state.get('queue', []))}"
            )
        except ClientError as e:
            logger.error(f"Error saving state to S3: {e}")
            raise
