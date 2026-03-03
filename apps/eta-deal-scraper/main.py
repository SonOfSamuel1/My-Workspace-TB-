"""
ETA Deal Scraper
================
Scans 83+ broker websites for newly posted off-market business-for-sale listings.

Usage:
    python main.py            # run scraper, report new listings
    python main.py --reset    # clear state and start fresh (first run)
    python main.py --dry-run  # scrape but don't update state
"""

import argparse
import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from scraper import BrokerScraper
from notifier import send_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent
BROKERS_CSV = ROOT / "brokers.csv"
STATE_FILE = ROOT / "state.json"

# Seconds to wait between broker requests (be polite)
REQUEST_DELAY = 2.0


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_brokers() -> list[dict]:
    with open(BROKERS_CSV, newline="") as f:
        return list(csv.DictReader(f))


def run(dry_run: bool = False) -> list[dict]:
    state = load_state()
    brokers = load_brokers()
    scraper = BrokerScraper()

    all_new: list[dict] = []
    scraped_count = 0

    for broker in brokers:
        name = broker["Firm Name"]
        url = broker["Website"]
        logger.info(f"[{scraped_count + 1}/{len(brokers)}] {name}")

        try:
            listings = scraper.get_listings(url)
        except Exception as e:
            logger.warning(f"  Error scraping {name}: {e}")
            time.sleep(REQUEST_DELAY)
            continue

        scraped_count += 1
        seen_urls: set[str] = set(state.get(name, []))
        new_listings = [l for l in listings if l["url"] not in seen_urls]

        if new_listings:
            logger.info(f"  NEW: {len(new_listings)} new listing(s)")
            for item in new_listings:
                item["broker"] = name
                item["broker_url"] = url
                item["found_at"] = datetime.now().isoformat()
            all_new.extend(new_listings)
        else:
            logger.info(f"  No new listings")

        if not dry_run:
            # Merge seen URLs (keep history to avoid re-alerting on old listings)
            all_urls = list(seen_urls | {l["url"] for l in listings})
            state[name] = all_urls

        time.sleep(REQUEST_DELAY)

    if not dry_run:
        save_state(state)

    if all_new:
        logger.info(f"\nTotal new listings: {len(all_new)}")
        send_report(all_new, total_scraped=scraped_count)
    else:
        logger.info("\nNo new listings found across all brokers.")

    return all_new


def main() -> None:
    parser = argparse.ArgumentParser(description="ETA Deal Scraper")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear all state so every listing appears 'new' on next run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and report but do not persist state changes",
    )
    args = parser.parse_args()

    if args.reset:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
            logger.info("State cleared. All listings will appear new on the next run.")
        else:
            logger.info("No state file found — nothing to clear.")
        return

    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
