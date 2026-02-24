#!/usr/bin/env python3
"""
Homeschool Events Gwinnett - Main Orchestrator

Searches for homeschooling events in Gwinnett County, GA using multi-source
web scraping (Eventbrite, GA State Parks) with optional Perplexity AI fallback,
then builds and sends a styled HTML email digest with calendar buttons.

Usage:
    python src/events_main.py --validate      # Validate configuration
    python src/events_main.py --generate      # Generate and send email
    python src/events_main.py --generate --no-email   # Generate without sending
    python src/events_main.py --generate --dry-run    # Generate, save HTML, no email
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytz
import yaml
from dotenv import load_dotenv

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from email_builder import EmailBuilder
from event_sources.aggregator import EventSourceAggregator
from event_sources.eventbrite_source import EventbriteSource
from event_sources.ga_state_parks_source import GAStateParksSource
from event_sources.gwinnett_library_source import GwinnettLibrarySource
from event_sources.perplexity_source import PerplexitySource
from ses_email_sender import SESEmailSender

logger = logging.getLogger(__name__)


def setup_logging(config: dict):
    """Configure logging based on config."""
    log_config = config.get("logging", {})
    level = getattr(logging, log_config.get("level", "INFO").upper(), logging.INFO)
    fmt = log_config.get(
        "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logging.basicConfig(level=level, format=fmt)


def load_config() -> dict:
    """Load configuration from config.yaml and environment."""
    # Load .env file if it exists
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # Load config.yaml
    config_path = Path(__file__).parent.parent / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"config.yaml not found at {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config.get("homeschool_events", config)


def _build_sources(config: dict):
    """Build the list of event sources from config."""
    sources_config = config.get("sources", {})
    search_config = config.get("search", {})
    perplexity_config = config.get("perplexity", {})
    tz_str = config.get("timezone", "America/New_York")

    sources = []

    # Eventbrite (primary, richest data)
    eb_config = sources_config.get("eventbrite", {})
    if eb_config.get("enabled", True):
        sources.append(
            EventbriteSource(
                url=eb_config.get(
                    "url",
                    "https://www.eventbrite.com/d/ga--gwinnett-county/homeschool/",
                ),
                max_pages=eb_config.get("max_pages", 3),
            )
        )

    # GA State Parks (secondary)
    ga_config = sources_config.get("ga_state_parks", {})
    if ga_config.get("enabled", True):
        sources.append(
            GAStateParksSource(
                url=ga_config.get(
                    "url",
                    "https://explore.gastateparks.org/Homeschool/Events",
                ),
            )
        )

    # Gwinnett County Library (Communico JSON API)
    lib_config = sources_config.get("gwinnett_library", {})
    if lib_config.get("enabled", True):
        sources.append(
            GwinnettLibrarySource(
                base_url=lib_config.get("base_url", "https://gwinnettpl.libnet.info"),
                search_term=lib_config.get("search_term", "homeschool"),
            )
        )

    # Perplexity AI (optional supplemental)
    px_config = sources_config.get("perplexity", {})
    if px_config.get("enabled", False):
        sources.append(
            PerplexitySource(
                api_key=os.getenv("OPENROUTER_API_KEY"),
                primary_model=perplexity_config.get(
                    "primary_model", "perplexity/sonar-pro"
                ),
                fallback_model=perplexity_config.get(
                    "fallback_model", "perplexity/sonar-reasoning-pro"
                ),
                timezone=tz_str,
                area=search_config.get("area", "Gwinnett County, Georgia"),
                categories=search_config.get("categories"),
                known_sources=search_config.get("known_sources"),
            )
        )

    return sources


def validate(config: dict) -> bool:
    """Validate all configuration and credentials."""
    print("=" * 50)
    print("  Homeschool Events Gwinnett - Validation")
    print("=" * 50)

    all_valid = True

    # Check config.yaml
    print("\n[1/4] Checking config.yaml...")
    search_config = config.get("search", {})
    if search_config.get("area"):
        print(f"  Area: {search_config['area']}")
    else:
        print("  ERROR: search.area not configured")
        all_valid = False

    lookahead = search_config.get("lookahead_days", 30)
    print(f"  Lookahead: {lookahead} days")

    categories = search_config.get("categories", [])
    print(f"  Categories: {len(categories)}")

    known = search_config.get("known_sources", [])
    print(f"  Known sources: {len(known)}")

    # Check event sources
    print("\n[2/4] Checking event sources...")
    sources = _build_sources(config)
    if not sources:
        print("  ERROR: No event sources enabled")
        all_valid = False
    else:
        for source in sources:
            reachable = source.validate()
            status = "reachable" if reachable else "UNREACHABLE"
            print(f"  {source.name}: {status}")
            if not reachable:
                all_valid = False

    # Check email recipient
    print("\n[3/4] Checking email configuration...")
    recipient = os.getenv("EVENTS_EMAIL_RECIPIENT")
    if recipient:
        print(f"  Recipient: {recipient}")
    else:
        print("  ERROR: EVENTS_EMAIL_RECIPIENT not set")
        all_valid = False

    sender = os.getenv(
        "SES_SENDER_EMAIL",
        config.get("email", {}).get("ses", {}).get("sender_email", ""),
    )
    if sender:
        print(f"  Sender: {sender}")
    else:
        print("  WARNING: SES_SENDER_EMAIL not set")

    # Check SES credentials
    print("\n[4/4] Checking AWS SES access...")
    try:
        region = os.getenv(
            "AWS_REGION",
            config.get("email", {}).get("ses", {}).get("region", "us-east-1"),
        )
        ses = SESEmailSender(region=region, sender_email=sender)
        if ses.validate_credentials():
            print("  SES credentials valid")
            if sender:
                if ses.check_email_verified(sender):
                    print("  Sender email verified in SES")
                else:
                    print("  WARNING: Sender email not verified in SES")
        else:
            print("  WARNING: SES credential validation failed")
    except Exception as e:
        print(f"  WARNING: SES check failed: {e}")

    # Summary
    print("\n" + "=" * 50)
    if all_valid:
        print("  All checks passed!")
    else:
        print("  Some checks failed. Please fix the issues above.")
    print("=" * 50)

    return all_valid


def generate_events_email(
    config: dict,
    send_email: bool = True,
    dry_run: bool = False,
) -> dict:
    """
    Main pipeline: scrape events, aggregate, build email, send.

    Returns:
        dict with results summary
    """
    search_config = config.get("search", {})
    email_config = config.get("email", {})
    tz_str = config.get("timezone", "America/New_York")

    tz = pytz.timezone(tz_str)
    now = datetime.now(tz)
    lookahead = search_config.get("lookahead_days", 30)
    end_date = now + timedelta(days=lookahead)
    date_range = f"{now.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"

    # Step 1: Fetch events from all sources
    logger.info("Step 1: Fetching events from all sources...")
    sources = _build_sources(config)
    location_filter = config.get("location_filter", {})
    relevance_filter = config.get("relevance_filter", {})
    aggregator = EventSourceAggregator(
        sources, location_filter=location_filter, relevance_filter=relevance_filter
    )
    result = aggregator.fetch_all(lookahead_days=lookahead)

    events = result["events"]
    source_counts = result["source_counts"]

    # Console summary
    print("\nSource results:")
    for src_name, count in source_counts.items():
        print(f"  {src_name}: {count} events")
    if result["errors"]:
        for err in result["errors"]:
            print(f"  ERROR: {err}")

    relevance_stats = result.get("relevance_stats")
    if relevance_stats:
        print(
            f"\nRelevance filter: {relevance_stats['before']} → {relevance_stats['after']} events "
            f"(homeschool keywords only)"
        )

    filter_stats = result.get("filter_stats")
    if filter_stats:
        print(
            f"\nLocation filter: {filter_stats['before']} → {filter_stats['after']} events "
            f"(Gwinnett County only)"
        )

    print(f"\nFound {len(events)} events:")
    for event in sorted(events, key=lambda e: e.date):
        time_str = event.start_time or "All Day"
        print(f"  [{event.category}] {event.date} {time_str} - {event.title}")
    print()

    # Step 2: Build email
    logger.info("Step 2: Building email...")
    builder = EmailBuilder(timezone=tz_str)
    html_content = builder.build_html(events, date_range)
    text_content = builder.build_plain_text(events, date_range)
    subject = builder.generate_subject(events, date_range)

    # Step 3: Save HTML output
    is_lambda = os.getenv("IS_LAMBDA", "false").lower() == "true"
    if is_lambda:
        output_dir = Path("/tmp")  # nosec B108 - Lambda writable dir
    else:
        output_dir = Path(__file__).parent.parent / "output"
        output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"homeschool_events_{now.strftime('%Y%m%d')}.html"
    with open(output_file, "w") as f:
        f.write(html_content)
    logger.info(f"HTML saved to {output_file}")
    print(f"HTML report saved to: {output_file}")

    # Step 4: Send email
    email_sent = False
    if send_email and not dry_run:
        recipient = os.getenv("EVENTS_EMAIL_RECIPIENT")
        if not recipient:
            logger.error("EVENTS_EMAIL_RECIPIENT not set, skipping email")
        else:
            logger.info(f"Step 4: Sending email to {recipient}...")
            ses_config = email_config.get("ses", {})
            region = os.getenv("AWS_REGION", ses_config.get("region", "us-east-1"))
            sender = os.getenv(
                "SES_SENDER_EMAIL",
                ses_config.get("sender_email", "brandonhome.appdev@gmail.com"),
            )

            ses = SESEmailSender(region=region, sender_email=sender)
            email_sent = ses.send_html_email(
                to=recipient,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )

            if email_sent:
                print(f"Email sent to {recipient}")
            else:
                print("ERROR: Failed to send email")
    elif dry_run:
        print("Dry run - email not sent")
    else:
        print("Email sending disabled (--no-email)")

    return {
        "events_found": len(events),
        "source_counts": source_counts,
        "html_file": str(output_file),
        "email_sent": email_sent,
        "subject": subject,
        "date_range": date_range,
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Homeschool Events Gwinnett - Weekly Event Digest"
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate configuration and credentials"
    )
    parser.add_argument(
        "--generate", action="store_true", help="Generate and send event digest"
    )
    parser.add_argument(
        "--no-email", action="store_true", help="Generate without sending email"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Generate and save HTML without sending"
    )

    args = parser.parse_args()

    if not any([args.validate, args.generate]):
        parser.print_help()
        sys.exit(1)

    # Load config
    config = load_config()
    setup_logging(config)

    if args.validate:
        success = validate(config)
        sys.exit(0 if success else 1)

    if args.generate:
        send_email = not args.no_email
        result = generate_events_email(
            config,
            send_email=send_email,
            dry_run=args.dry_run,
        )
        print(f"\nResults: {result['events_found']} events found")
        print(f"Subject: {result['subject']}")
        if result["email_sent"]:
            print("Email sent successfully!")


if __name__ == "__main__":
    main()
