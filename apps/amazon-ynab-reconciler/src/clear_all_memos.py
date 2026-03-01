#!/usr/bin/env python3
"""
Clear all memos from YNAB transactions.
Run this before the reconciler to start fresh.
"""

import logging
import os
import sys
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

API_KEY = os.getenv("YNAB_API_KEY")
BASE_URL = "https://api.ynab.com/v1"

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def get_budget_id() -> str:
    """Get the first budget ID from YNAB."""
    budget_id = os.getenv("YNAB_BUDGET_ID")
    if budget_id:
        return budget_id

    url = f"{BASE_URL}/budgets"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    budgets = response.json()["data"]["budgets"]
    if budgets:
        return budgets[0]["id"]
    raise ValueError("No budgets found")


def get_all_transactions(budget_id: str, days_back: int = 30) -> list:
    """Get all transactions from the last N days."""
    since_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    url = f"{BASE_URL}/budgets/{budget_id}/transactions"
    params = {"since_date": since_date}

    for attempt in range(5):
        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code == 429:
            wait_time = 120 * (attempt + 1)  # 2min, 4min, 6min, 8min, 10min
            logger.info(
                f"Rate limited. Waiting {wait_time}s (attempt {attempt+1}/5)..."
            )
            time.sleep(wait_time)
            continue
        response.raise_for_status()
        return response.json()["data"]["transactions"]

    raise Exception(
        "Failed to fetch transactions after 5 retries - rate limit may need more time to reset"
    )


def clear_memo(budget_id: str, transaction_id: str, dry_run: bool = False) -> tuple:
    """Clear memo for a single transaction. Returns (success, error_msg)."""
    if dry_run:
        return True, None

    url = f"{BASE_URL}/budgets/{budget_id}/transactions/{transaction_id}"
    data = {"transaction": {"memo": ""}}

    response = requests.patch(url, headers=HEADERS, json=data)
    if response.status_code == 200:
        return True, None
    elif response.status_code == 429:
        return False, "RATE_LIMITED"
    else:
        return False, f"{response.status_code}: {response.text[:100]}"


def main():
    dry_run = "--dry-run" in sys.argv
    days_back = 30

    # Parse days argument
    for arg in sys.argv:
        if arg.startswith("--days="):
            days_back = int(arg.split("=")[1])

    if dry_run:
        logger.info("=== DRY RUN MODE ===")

    budget_id = get_budget_id()
    logger.info(f"Using budget ID: {budget_id}")

    logger.info(f"Fetching transactions from last {days_back} days...")
    transactions = get_all_transactions(budget_id, days_back)

    # Filter to transactions with memos
    with_memos = [t for t in transactions if t.get("memo")]

    logger.info(f"Found {len(transactions)} total transactions")
    logger.info(f"Found {len(with_memos)} transactions with memos")

    if not with_memos:
        logger.info("No memos to clear!")
        return

    # Show what will be cleared
    logger.info("\nMemos to clear:")
    for t in with_memos[:20]:  # Show first 20
        payee = t.get("payee_name", "Unknown")[:30]
        memo = t.get("memo", "")[:50]
        logger.info(f"  {payee}: {memo}")

    if len(with_memos) > 20:
        logger.info(f"  ... and {len(with_memos) - 20} more")

    if dry_run:
        logger.info(f"\nDry run: Would clear {len(with_memos)} memos")
        return

    # Confirm
    logger.info(f"\nAbout to clear {len(with_memos)} memos. Continue? (y/n)")
    confirm = input().strip().lower()
    if confirm != "y":
        logger.info("Cancelled.")
        return

    # Clear memos
    cleared = 0
    failed = 0
    rate_limited = False

    for i, t in enumerate(with_memos):
        payee = t.get("payee_name", "Unknown")[:30]

        success, error = clear_memo(budget_id, t["id"])
        if success:
            cleared += 1
            logger.info(f"[{i+1}/{len(with_memos)}] Cleared: {payee}")
        else:
            failed += 1
            if error == "RATE_LIMITED":
                logger.error(f"[{i+1}/{len(with_memos)}] RATE LIMITED! Waiting 60s...")
                rate_limited = True
                time.sleep(60)
                # Retry after wait
                success, error = clear_memo(budget_id, t["id"])
                if success:
                    failed -= 1
                    cleared += 1
                    logger.info(f"[{i+1}/{len(with_memos)}] Retry succeeded: {payee}")
            else:
                logger.error(f"[{i+1}/{len(with_memos)}] FAILED: {payee} - {error}")

        # Rate limiting - YNAB allows 200 req/hour
        time.sleep(1.0 if rate_limited else 0.5)

    logger.info("\n=== COMPLETE ===")
    logger.info(f"Cleared: {cleared}")
    logger.info(f"Failed: {failed}")


if __name__ == "__main__":
    main()
