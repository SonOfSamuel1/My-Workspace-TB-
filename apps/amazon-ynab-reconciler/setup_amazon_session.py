#!/usr/bin/env python3
"""
Amazon Session Setup Script
This helps you log into Amazon manually and save the session for automation.
"""

import os
import sys
import json
import time
from pathlib import Path

print("""
============================================================
AMAZON SESSION SETUP
============================================================

This script will help you set up Amazon access for automation.

Since Amazon has strict cookie requirements, we'll use one of
these approaches:

OPTION 1: CSV Download (Recommended - 5 minutes)
-------------------------------------------------
1. Open your browser
2. Go to: https://www.amazon.com/gp/b2b/reports
3. Download "Items" report for last 30 days
4. Save to: apps/amazon-ynab-reconciler/data/amazon_orders.csv
5. Run: python3 src/reconciler_main.py --use-csv --days 30

OPTION 2: Browser Extension (Advanced - 10 minutes)
-------------------------------------------------
1. Install "EditThisCookie" Chrome extension
2. Log into Amazon normally
3. Export cookies as JSON
4. Save to: apps/amazon-ynab-reconciler/browser_profile/amazon_cookies.json
5. Run: python3 src/reconciler_main.py --use-cookies --days 30

OPTION 3: Manual Copy (Quick Test - 2 minutes)
-------------------------------------------------
1. I'll create sample data that matches your YNAB transactions
2. You can test the matching algorithm immediately
3. Run: python3 src/reconciler_main.py --use-sample --days 30

Which option would you like? (1/2/3): """)

choice = input().strip()

if choice == "1":
    print("\n✅ CSV Download Method Selected")
    print("\nSteps:")
    print("1. Open: https://www.amazon.com/gp/b2b/reports")
    print("2. Sign in with your Amazon account")
    print("3. Select:")
    print("   - Report Type: Items")
    print("   - Start Date: (30 days ago)")
    print("   - End Date: Today")
    print("4. Click 'Request Report'")
    print("5. Download when ready")
    print("6. Save to: data/amazon_orders.csv")
    print("\nOnce downloaded, run:")
    print("python3 src/reconciler_main.py --use-csv --dry-run --days 30")

elif choice == "2":
    print("\n✅ Browser Extension Method Selected")
    print("\nSteps:")
    print("1. Install: https://chrome.google.com/webstore/detail/editthiscookie/")
    print("2. Log into Amazon")
    print("3. Click the cookie extension icon")
    print("4. Click 'Export' (as JSON)")
    print("5. Save to: browser_profile/amazon_cookies.json")
    print("\nOnce saved, run:")
    print("python3 src/reconciler_main.py --use-cookies --dry-run --days 30")

elif choice == "3":
    print("\n✅ Creating Sample Data")

    # Create sample Amazon data that might match YNAB
    sample_data = [
        {
            "order_id": "111-SAMPLE-001",
            "date": "2025-11-24",
            "total": 169.66,
            "items": [{
                "name": "Electronics Bundle",
                "category": "Electronics",
                "asin": "B08N6SAMPLE",
                "price": 169.66,
                "quantity": 1,
                "link": "https://www.amazon.com/dp/B08N6SAMPLE"
            }],
            "status": "Delivered",
            "payment_method": "Amazon Business Prime Card"
        },
        {
            "order_id": "111-SAMPLE-002",
            "date": "2025-11-22",
            "total": 37.95,
            "items": [{
                "name": "Apple Service",
                "category": "Digital Services",
                "asin": "APPLESERV",
                "price": 37.95,
                "quantity": 1,
                "link": "https://www.apple.com"
            }],
            "status": "Completed",
            "payment_method": "Amazon Business Prime Card"
        }
    ]

    # Save sample data
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    with open(data_dir / "amazon_orders_sample.json", "w") as f:
        json.dump(sample_data, f, indent=2)

    print(f"Sample data created at: {data_dir / 'amazon_orders_sample.json'}")
    print("\nThis includes transactions that might match your YNAB:")
    print("- $169.66 on 11/24 (matches your Amazon YNAB transaction)")
    print("- $37.95 on 11/22 (close to your Apple transaction)")
    print("\nRun reconciliation with:")
    print("python3 src/reconciler_main.py --use-sample --dry-run --days 30")

else:
    print("\n❌ Invalid choice. Please run the script again.")

print("\n" + "="*60)
print("Need help? The reconciliation system will:")
print("- Match Amazon orders to YNAB transactions")
print("- Handle date differences (±2 days)")
print("- Handle amount differences (±$0.50)")
print("- Update YNAB memos with item details")
print("="*60)