#!/usr/bin/env python3
"""Debug script to investigate reconciliation issues."""

import sys
import os
sys.path.insert(0, 'src')
os.environ['USE_DOWNLOADS'] = 'true'

from datetime import datetime, timedelta
from amazon_scraper import AmazonScraper
from ynab_service import YNABService
from transaction_matcher import TransactionMatcher
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Get Amazon transactions
print("=" * 60)
print("FETCHING AMAZON TRANSACTIONS")
print("=" * 60)
scraper = AmazonScraper(config['amazon'])
start_date = datetime.now() - timedelta(days=30)
amazon_txns = scraper.get_transactions(start_date)

print(f"\nFound {len(amazon_txns)} Amazon transactions in date range")
print("\nFirst 5 Amazon transactions:")
for i, txn in enumerate(amazon_txns[:5]):
    print(f"\n{i+1}. Date: {txn['date'].date()}")
    print(f"   Amount: ${txn['total']:.2f}")
    print(f"   Payment: {txn.get('payment_method', 'Unknown')}")
    if txn.get('items'):
        print(f"   Items: {', '.join(item['name'][:30] for item in txn['items'][:2])}")

# Get YNAB transactions
print("\n" + "=" * 60)
print("FETCHING YNAB TRANSACTIONS")
print("=" * 60)
ynab = YNABService(config['ynab'])

# Need to call the method correctly
ynab_txns = []
for account_name in config['ynab']['account_names']:
    account_txns = ynab.get_transactions_by_account(
        account_name=account_name,
        since_date=start_date
    )
    ynab_txns.extend(account_txns)

print(f"\nFound {len(ynab_txns)} YNAB transactions")
print("\nFirst 5 YNAB transactions:")
for i, txn in enumerate(ynab_txns[:5]):
    date = datetime.fromisoformat(txn['date'])
    amount = abs(txn['amount'] / 1000)
    print(f"\n{i+1}. Date: {date.date()}")
    print(f"   Amount: ${amount:.2f}")
    print(f"   Account: {txn.get('account_name', 'Unknown')}")
    print(f"   Payee: {txn.get('payee_name', 'Unknown')}")
    print(f"   Memo: {txn.get('memo', 'No memo')[:50]}")

# Try matching
print("\n" + "=" * 60)
print("ATTEMPTING TO MATCH TRANSACTIONS")
print("=" * 60)
matcher = TransactionMatcher(config['reconciliation'])
matches, unmatched_amazon, unmatched_ynab = matcher.match_transactions(amazon_txns, ynab_txns)

print(f"\nMatches found: {len(matches)}")
if matches:
    print("\nMatched transactions:")
    for match in matches[:5]:
        print(f"\n  Amazon Order {match['amazon_order_id']}:")
        print(f"    Confidence: {match['confidence']:.1f}%")
        print(f"    Date diff: {match['date_diff_days']} days")
        print(f"    Amount diff: ${match['amount_diff_cents']/100:.2f}")
else:
    print("\nNo matches found!")

    # Debug why no matches
    if amazon_txns and ynab_txns:
        print("\nChecking potential matches (first Amazon vs all YNAB):")
        a = amazon_txns[0]
        print(f"\nAmazon transaction:")
        print(f"  Date: {a['date'].date()}")
        print(f"  Amount: ${a['total']:.2f}")
        print(f"  Payment: {a.get('payment_method', 'Unknown')}")

        print("\nChecking against YNAB transactions:")
        for y in ynab_txns[:5]:
            y_date = datetime.fromisoformat(y['date'])
            y_amount = abs(y['amount'] / 1000)
            date_diff = abs((a['date'] - y_date).days)
            amount_diff = abs(a['total'] - y_amount)

            print(f"\n  YNAB: {y_date.date()} ${y_amount:.2f} {y.get('account_name', 'Unknown')}")
            print(f"    Date diff: {date_diff} days (tolerance: {config['reconciliation']['date_tolerance_days']})")
            print(f"    Amount diff: ${amount_diff:.2f} (tolerance: ${config['reconciliation']['amount_tolerance_cents']/100:.2f})")

            # Check if this would match
            date_ok = date_diff <= config['reconciliation']['date_tolerance_days']
            amount_ok = amount_diff <= (config['reconciliation']['amount_tolerance_cents'] / 100)

            if date_ok and amount_ok:
                print(f"    ✓ Should match!")
            elif date_ok:
                print(f"    ✗ Date OK but amount differs too much")
            elif amount_ok:
                print(f"    ✗ Amount OK but date differs too much")
            else:
                print(f"    ✗ Both date and amount differ too much")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Amazon transactions: {len(amazon_txns)}")
print(f"YNAB transactions: {len(ynab_txns)}")
print(f"Matches: {len(matches)}")
print(f"Unmatched Amazon: {len(unmatched_amazon)}")
print(f"Unmatched YNAB: {len(unmatched_ynab)}")