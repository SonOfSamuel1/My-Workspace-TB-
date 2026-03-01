#!/usr/bin/env python3
"""
JT Teaching Newsletter - Main Entry Point

Daily morning email with 2 Jesus' Teachings from the Obsidian vault,
each with key verse and 2 AI-generated reflection questions.

Usage:
  python src/teaching_main.py --validate        # Validate config and credentials
  python src/teaching_main.py --generate        # Generate and send email
  python src/teaching_main.py --generate --no-email  # Dry run (print to console)
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

# Add src to path for sibling imports
sys.path.insert(0, str(Path(__file__).parent))

from email_formatter import EmailFormatter  # noqa: E402
from obsidian_reader import ObsidianReader  # noqa: E402
from ses_email_sender import SESEmailSender  # noqa: E402
from teaching_selector import TeachingSelector  # noqa: E402

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml not found at {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_environment():
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        logger.warning(".env not found — using environment variables only")
        return
    if HAS_DOTENV:
        load_dotenv(env_path)
        logger.info("Environment loaded via python-dotenv")
        return
    # Manual fallback
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), value)


def setup_logging(config: dict):
    log_config = config.get("logging", {})
    log_level = getattr(logging, log_config.get("level", "INFO"))
    log_format = log_config.get(
        "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log_file = log_config.get("file", "logs/teaching_newsletter.log")

    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.append(logging.FileHandler(log_file))
    except Exception:
        pass  # In Lambda /tmp only is writable; handler added by lambda_handler

    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)


def _get_required(env_var: str, config_fallback: str = None) -> str:
    value = os.getenv(env_var) or config_fallback
    if not value:
        raise EnvironmentError(f"Required environment variable not set: {env_var}")
    return value


# ---------------------------------------------------------------------------
# Core workflow
# ---------------------------------------------------------------------------

MAX_VERSE_RETRIES = 10


def _ensure_has_verse(
    teaching: dict, key: str, label: str, reader, selector, all_keys
) -> tuple:
    """Replace a teaching with the next queue entry if it has no verse."""
    for attempt in range(MAX_VERSE_RETRIES):
        if teaching.get("verse", "").strip():
            return teaching, key
        logger.warning(
            f"{label} '{key}' has no verse — skipping (attempt {attempt + 1})"
        )
        key = selector.pop_one_key(all_keys)
        teaching = reader.read_teaching(key)
    if not teaching.get("verse", "").strip():
        logger.warning(
            f"{label} still has no verse after {MAX_VERSE_RETRIES} retries — sending anyway"
        )
    return teaching, key


def generate_email(config: dict, send_email: bool = True):
    """Full workflow: pick teachings → email."""
    newsletter_cfg = config.get("newsletter", {})
    aws_cfg = config.get("aws", {})

    bucket = _get_required("JT_S3_BUCKET", aws_cfg.get("s3_bucket"))
    region = os.getenv("AWS_REGION", aws_cfg.get("region", "us-east-1"))
    recipient = _get_required(
        "JT_EMAIL_RECIPIENT", newsletter_cfg.get("email", {}).get("recipient")
    )
    sender_email = os.getenv(
        "SES_SENDER_EMAIL", newsletter_cfg.get("email", {}).get("sender", "")
    )

    # 1. List all teachings from S3
    logger.info("Listing teachings from S3...")
    vault_path = config.get("vault", {}).get("path")
    reader = ObsidianReader(bucket=bucket, region=region, vault_path=vault_path)
    all_keys = reader.list_teachings(prefix="JT-")

    if len(all_keys) < 2:
        raise ValueError(
            f"Not enough teachings in S3 (found {len(all_keys)}). Run sync_to_s3.py first."
        )

    logger.info(f"Found {len(all_keys)} teachings in S3")

    # 2. Pick next 2
    selector = TeachingSelector(bucket=bucket, region=region)
    key1, key2 = selector.pick_next_two(all_keys)
    status = selector.get_queue_status()
    logger.info(
        f"Queue: {status['position']}/{status['total']} (~{status['days_until_reset']} days until reshuffle)"
    )

    # 3. Read teaching content
    logger.info(f"Reading teaching 1: {key1}")
    teaching1 = reader.read_teaching(key1)
    logger.info(f"Reading teaching 2: {key2}")
    teaching2 = reader.read_teaching(key2)

    # 4. Skip any teaching with no verse
    teaching1, key1 = _ensure_has_verse(
        teaching1, key1, "Teaching 1", reader, selector, all_keys
    )
    teaching2, key2 = _ensure_has_verse(
        teaching2, key2, "Teaching 2", reader, selector, all_keys
    )

    # 5. Build email
    formatter = EmailFormatter()
    email_content = formatter.format_email(
        teachings=[teaching1, teaching2],
        date=datetime.now(),
    )

    # Print preview
    print(f"\n{'='*60}")
    print("EMAIL PREVIEW")
    print(f"{'='*60}")
    print(f"Subject: {email_content['subject']}")
    print()
    print("--- PLAIN TEXT ---")
    print(email_content["text"])
    print(f"{'='*60}\n")

    # 6. Send (or skip)
    if send_email:
        logger.info(f"Sending email to {recipient}...")
        ses = SESEmailSender(region=region, sender_email=sender_email)
        success = ses.send_html_email(
            to=recipient,
            subject=email_content["subject"],
            html_content=email_content["html"],
            text_content=email_content["text"],
        )
        if success:
            print(f"Email sent successfully to {recipient}")
        else:
            print("Email send FAILED — check logs")
            sys.exit(1)
    else:
        print("--no-email flag set: skipping send")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_setup(config: dict) -> bool:
    print("\n" + "=" * 60)
    print("JT TEACHING NEWSLETTER — SETUP VALIDATION")
    print("=" * 60 + "\n")

    all_ok = True
    newsletter_cfg = config.get("newsletter", {})
    aws_cfg = config.get("aws", {})

    # Required env vars
    required = {
        "JT_S3_BUCKET": "S3 bucket name (or set in config.yaml)",
        "JT_EMAIL_RECIPIENT": "Recipient email address",
        "SES_SENDER_EMAIL": "Verified SES sender email",
    }

    # Allow config fallbacks
    bucket_fallback = aws_cfg.get("s3_bucket")
    recipient_fallback = newsletter_cfg.get("email", {}).get("recipient")
    sender_fallback = newsletter_cfg.get("email", {}).get("sender")

    for var, desc in required.items():
        value = os.getenv(var)
        if not value:
            # Check config fallbacks
            if var == "JT_S3_BUCKET" and bucket_fallback:
                print(f"  OK  {var} (from config.yaml: {bucket_fallback})")
                continue
            if var == "JT_EMAIL_RECIPIENT" and recipient_fallback:
                print(f"  OK  {var} (from config.yaml: {recipient_fallback})")
                continue
            if var == "SES_SENDER_EMAIL" and sender_fallback:
                print(f"  OK  {var} (from config.yaml: {sender_fallback})")
                continue
            print(f"  MISSING  {var} — {desc}")
            all_ok = False
        else:
            masked = value[:4] + "***" if len(value) > 4 else "***"
            print(f"  OK  {var} = {masked}")

    # Test S3 access
    bucket = os.getenv("JT_S3_BUCKET") or bucket_fallback
    region = os.getenv("AWS_REGION", aws_cfg.get("region", "us-east-1"))

    if bucket:
        print(f"\n  Testing S3 access to bucket: {bucket}")
        try:
            reader = ObsidianReader(bucket=bucket, region=region)
            keys = reader.list_teachings(prefix="JT-")
            print(f"  OK  S3 accessible — {len(keys)} JT- teachings found")
            if len(keys) == 0:
                print(
                    "  WARNING  No JT- files found. Run: python scripts/sync_to_s3.py"
                )
        except Exception as e:
            print(f"  FAILED  S3 access error: {e}")
            all_ok = False

    # Test SES
    sender = os.getenv("SES_SENDER_EMAIL") or sender_fallback
    if sender:
        print("\n  Testing SES credentials...")
        try:
            ses = SESEmailSender(region=region, sender_email=sender)
            if ses.validate_credentials():
                print("  OK  SES credentials valid")
                if ses.check_email_verified(sender):
                    print(f"  OK  Sender {sender} is verified in SES")
                else:
                    print(f"  WARNING  Sender {sender} not yet verified in SES")
            else:
                print("  FAILED  SES credential validation failed")
                all_ok = False
        except Exception as e:
            print(f"  FAILED  SES error: {e}")
            all_ok = False

    print()
    if all_ok:
        print("ALL VALIDATIONS PASSED\n")
        print("Next steps:")
        print(
            "  python scripts/sync_to_s3.py --vault /path/to/vault --bucket "
            + (bucket or "<bucket>")
        )
        print("  python src/teaching_main.py --generate --no-email")
        print("  python src/teaching_main.py --generate")
    else:
        print("VALIDATION FAILED — fix issues above before proceeding\n")

    return all_ok


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="JT Teaching Newsletter")
    parser.add_argument(
        "--validate", action="store_true", help="Validate configuration and credentials"
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate and send daily teachings email",
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Generate but do not send email (dry run)",
    )
    args = parser.parse_args()

    load_environment()
    config = load_config()
    setup_logging(config)

    logger.info("=" * 60)
    logger.info("JT Teaching Newsletter")
    logger.info("=" * 60)

    if args.validate:
        success = validate_setup(config)
        sys.exit(0 if success else 1)
    elif args.generate:
        generate_email(config, send_email=not args.no_email)
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python src/teaching_main.py --validate")
        print("  python src/teaching_main.py --generate --no-email")
        print("  python src/teaching_main.py --generate")


if __name__ == "__main__":
    main()
