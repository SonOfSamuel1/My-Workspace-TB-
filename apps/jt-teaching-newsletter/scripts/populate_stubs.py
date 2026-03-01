#!/usr/bin/env python3
"""
Populate 0-byte JT-*.md stub files with Bible verses.

Scans the local Obsidian vault for 0-byte JT-*.md files, calls Claude via
OpenRouter in batches of 20 to identify the best matching Bible verse for
each teaching topic (derived from the filename), writes populated .md files
to the vault, uploads them to S3, and resets state.json to force a full
queue rebuild.

Usage:
  cd apps/jt-teaching-newsletter
  python scripts/populate_stubs.py [--dry-run] [--batch-size 20]

Options:
  --dry-run       Print what would be written without modifying any files
  --batch-size N  Topics per API call (default: 20)
  --vault PATH    Override vault path from config.yaml / .env
  --bucket NAME   Override S3 bucket from config.yaml / .env
"""

import argparse
import json
import logging
import os
import sys
import urllib.request
from pathlib import Path

import boto3
import yaml
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Generated file template
# ---------------------------------------------------------------------------
FILE_TEMPLATE = """\
Related:

Priority:
[[Development Priority- None]]

----

## Key Verses
{reference}
{text}
"""

# ---------------------------------------------------------------------------
# Claude prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = "You are a Bible scholar specializing in the teachings of Jesus Christ."

USER_PROMPT_TEMPLATE = """\
For each teaching topic below (paraphrases of Jesus' commands/teachings from the Gospels),
identify the single most relevant Bible verse spoken by or directly about Jesus.
Prioritize Matthew, Mark, Luke, John. Use the ESV translation.

Return ONLY a valid JSON object — no markdown, no explanation, no other text:
{{
  "<exact topic name>": {{"reference": "Luke 6:36 (ESV)", "text": "<full verse text>"}},
  ...
}}

Topics:
{topics_json}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_config() -> dict:
    """Load config.yaml from the app root (two levels up from scripts/)."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def find_stub_files(vault_path: str, prefix: str = "JT-") -> list[Path]:
    """Return sorted list of 0-byte JT-*.md files in the vault."""
    vault = Path(vault_path)
    if not vault.exists():
        log.error(f"Vault path does not exist: {vault}")
        sys.exit(1)

    stubs = [f for f in sorted(vault.glob(f"{prefix}*.md")) if f.stat().st_size == 0]
    return stubs


def topic_from_path(path: Path, prefix: str = "JT-") -> str:
    """Extract teaching topic from filename, e.g. 'JT- Be Merciful.md' → 'Be Merciful'."""
    name = path.stem  # strip .md
    if name.startswith(prefix):
        name = name[len(prefix) :]
    return name.strip()


def call_claude_openrouter(
    api_key: str,
    base_url: str,
    model: str,
    topics: list[str],
) -> dict:
    """
    Call Claude via OpenRouter and return parsed JSON dict.

    Returns dict mapping topic → {reference, text}.
    Raises ValueError on parse failure.
    """
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    url = f"{base}/v1/chat/completions"

    topics_json = json.dumps(topics, ensure_ascii=False, indent=2)
    user_content = USER_PROMPT_TEMPLATE.format(topics_json=topics_json)

    payload = {
        "model": model,
        "max_tokens": 2000,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "provider": {
            "allow_fallbacks": True,
            "order": ["Amazon Bedrock", "Google Vertex AI"],
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/SonOfSamuel1/My-Workspace-TB-",
            "X-Title": "JT Teaching Newsletter - Stub Populator",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    raw = data["choices"][0]["message"]["content"].strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Remove first and last fence lines
        raw = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

    return json.loads(raw)


def build_file_content(reference: str, text: str) -> str:
    """Render the populated .md file content."""
    return FILE_TEMPLATE.format(reference=reference, text=f'"{text}"')


def upload_to_s3(
    s3_client,
    bucket: str,
    file_path: Path,
    dry_run: bool = False,
) -> bool:
    """Upload a single file to S3. Returns True on success."""
    key = file_path.name
    if dry_run:
        log.info(f"  [DRY RUN] Would upload: {key}")
        return True
    try:
        with open(file_path, "rb") as f:
            s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=f.read(),
                ContentType="text/markdown; charset=utf-8",
            )
        return True
    except Exception as e:
        log.error(f"  S3 upload failed for {key}: {e}")
        return False


def delete_state_json(s3_client, bucket: str, dry_run: bool = False) -> None:
    """Delete state.json from S3 to force a full queue rebuild."""
    if dry_run:
        log.info("[DRY RUN] Would delete state.json from S3")
        return
    try:
        s3_client.delete_object(Bucket=bucket, Key="state.json")
        log.info("Deleted state.json from S3 (queue will rebuild on next run)")
    except ClientError as e:
        # Not found is fine — it just means it was already absent
        if e.response["Error"]["Code"] not in ("NoSuchKey", "404"):
            log.warning(f"Could not delete state.json: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Populate 0-byte JT-*.md stub files")
    parser.add_argument(
        "--dry-run", action="store_true", help="No files written or uploaded"
    )
    parser.add_argument(
        "--batch-size", type=int, default=20, help="Topics per API call"
    )
    parser.add_argument("--vault", help="Override vault path")
    parser.add_argument("--bucket", help="Override S3 bucket name")
    args = parser.parse_args()

    # Load environment and config
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    config = load_config()

    # Resolve vault path
    vault_path = (
        args.vault
        or os.getenv("JT_VAULT_PATH")
        or config.get("vault", {}).get("path", "")
    )
    if not vault_path:
        log.error(
            "Vault path not set. Use --vault, JT_VAULT_PATH env var, or config.yaml vault.path"
        )
        sys.exit(1)

    # Resolve S3 bucket
    bucket = (
        args.bucket
        or os.getenv("JT_S3_BUCKET")
        or config.get("aws", {}).get("s3_bucket", "")
    )
    if not bucket:
        log.error(
            "S3 bucket not set. Use --bucket, JT_S3_BUCKET env var, or config.yaml aws.s3_bucket"
        )
        sys.exit(1)

    # Resolve API credentials
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "")
    model = os.getenv("CLAUDE_MODEL", "anthropic/claude-3-5-haiku")

    if not api_key:
        log.error("ANTHROPIC_API_KEY not set in environment or .env")
        sys.exit(1)

    if not base_url:
        log.error(
            "ANTHROPIC_BASE_URL not set. This script requires OpenRouter "
            "(set ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1)"
        )
        sys.exit(1)

    region = os.getenv("AWS_REGION", config.get("aws", {}).get("region", "us-east-1"))

    # Find stub files
    log.info(f"Scanning vault: {vault_path}")
    stubs = find_stub_files(vault_path)
    log.info(f"Found {len(stubs)} 0-byte stub files")

    if not stubs:
        log.info("Nothing to do — no stubs found.")
        sys.exit(0)

    if args.dry_run:
        log.info("DRY RUN mode — no files will be written or uploaded\n")

    # Extract topics
    topics_with_paths = [(topic_from_path(p), p) for p in stubs]
    topic_to_path = {t: p for t, p in topics_with_paths}
    all_topics = list(topic_to_path.keys())

    log.info(f"Topics to populate: {len(all_topics)}")
    log.info(f"Batch size: {args.batch_size}")
    log.info(
        f"Estimated API calls: {(len(all_topics) + args.batch_size - 1) // args.batch_size}\n"
    )

    # Prepare S3 client
    if not args.dry_run:
        s3 = boto3.client("s3", region_name=region)
    else:
        s3 = None

    # Process in batches
    populated = 0
    uploaded = 0
    skipped = 0
    errors = 0
    error_topics = []

    batches = [
        all_topics[i : i + args.batch_size]
        for i in range(0, len(all_topics), args.batch_size)
    ]

    for batch_num, batch in enumerate(batches, 1):
        log.info(f"Batch {batch_num}/{len(batches)} — {len(batch)} topics")

        # Try up to 2 times per batch
        result = None
        for attempt in range(1, 3):
            try:
                result = call_claude_openrouter(api_key, base_url, model, batch)
                break
            except json.JSONDecodeError as e:
                log.warning(f"  JSON parse error (attempt {attempt}): {e}")
                if attempt == 2:
                    log.error("  Skipping batch after 2 failed parse attempts")
                    skipped += len(batch)
                    error_topics.extend(batch)
            except Exception as e:
                log.error(f"  API error (attempt {attempt}): {e}")
                if attempt == 2:
                    log.error("  Skipping batch")
                    skipped += len(batch)
                    error_topics.extend(batch)

        if result is None:
            errors += len(batch)
            continue

        # Write files for each topic in the batch
        for topic in batch:
            verse_data = result.get(topic)
            if not verse_data:
                # Try case-insensitive match as fallback
                for key in result:
                    if key.lower() == topic.lower():
                        verse_data = result[key]
                        break

            if not verse_data:
                log.warning(f"  No verse returned for: '{topic}'")
                skipped += 1
                error_topics.append(topic)
                continue

            reference = verse_data.get("reference", "").strip()
            text = verse_data.get("text", "").strip()

            if not reference or not text:
                log.warning(f"  Incomplete verse data for: '{topic}'")
                skipped += 1
                error_topics.append(topic)
                continue

            content = build_file_content(reference, text)
            file_path = topic_to_path[topic]

            if args.dry_run:
                log.info(f"  [DRY RUN] {file_path.name}: {reference}")
                populated += 1
                uploaded += 1
                continue

            # Write to vault
            try:
                file_path.write_text(content, encoding="utf-8")
                log.info(f"  Written: {file_path.name} — {reference}")
                populated += 1
            except Exception as e:
                log.error(f"  Failed to write {file_path.name}: {e}")
                errors += 1
                error_topics.append(topic)
                continue

            # Upload to S3
            if upload_to_s3(s3, bucket, file_path, dry_run=args.dry_run):
                uploaded += 1
            else:
                errors += 1

    # Reset state.json so the queue is rebuilt with all 760 teachings
    if populated > 0:
        delete_state_json(s3, bucket, dry_run=args.dry_run)

    # Summary
    print()
    print("=" * 60)
    print(
        f"Populated: {populated} | Uploaded: {uploaded} | Skipped: {skipped} | Errors: {errors}"
    )
    if populated > 0:
        print("Queue reset: state.json deleted from S3")
    if error_topics:
        print(f"\nFailed topics ({len(error_topics)}):")
        for t in error_topics:
            print(f"  - {t}")
    print("=" * 60)

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
