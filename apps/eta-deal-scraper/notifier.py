"""Output and notification for newly found ETA listings."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent / "reports"


def send_report(new_listings: list[dict], total_scraped: int = 0) -> None:
    """Print report to stdout and save a JSON report file."""
    if not new_listings:
        return

    _print_report(new_listings, total_scraped)
    _save_json_report(new_listings)


def _print_report(listings: list[dict], total_scraped: int) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'=' * 65}")
    print(f"ETA Deal Scraper — New Listings  ({timestamp})")
    print(f"  {len(listings)} new listings found  |  {total_scraped} brokers scraped")
    print("=" * 65)

    by_broker: dict[str, list[dict]] = {}
    for listing in listings:
        broker = listing.get("broker", "Unknown")
        by_broker.setdefault(broker, []).append(listing)

    for broker, broker_listings in sorted(by_broker.items()):
        print(f"\n{broker}  ({len(broker_listings)} new)")
        for item in broker_listings:
            title = (item.get("title") or "Untitled")[:80]
            url = item.get("url", "")
            print(f"  • {title}")
            print(f"    {url}")

    print()


def _save_json_report(listings: list[dict]) -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = REPORTS_DIR / f"new_listings_{timestamp}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "count": len(listings),
        "listings": listings,
    }

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Report saved to {report_file}")
    print(f"\nReport saved → {report_file}\n")
