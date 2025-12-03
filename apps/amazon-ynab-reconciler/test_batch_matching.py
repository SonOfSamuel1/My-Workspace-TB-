#!/usr/bin/env python3
"""Test script to verify batch matching capabilities."""

import sys
import os
sys.path.insert(0, 'src')
os.environ['USE_DOWNLOADS'] = 'true'

from datetime import datetime, timedelta
from amazon_scraper import AmazonScraper
from ynab_service import YNABService
from transaction_matcher import TransactionMatcher
import yaml
import json

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

print("=" * 60)
print("BATCH MATCHING TEST")
print("=" * 60)

# Initialize services
scraper = AmazonScraper(config['amazon'])
ynab = YNABService(config['ynab'])
matcher = TransactionMatcher(config['reconciliation'])

# Get recent transactions
start_date = datetime.now() - timedelta(days=30)
if start_date.year > 2024:
    start_date = start_date.replace(year=2024)

print("\nFetching Amazon transactions...")
amazon_txns = scraper.get_transactions(start_date)
print(f"Found {len(amazon_txns)} Amazon transactions")

# Look for potential split payments
print("\nAnalyzing Amazon transactions for split payment evidence...")
split_candidates = []
for txn in amazon_txns:
    if txn.get('is_split_payment'):
        split_candidates.append(txn)
        print(f"  - Order {txn.get('order_id')}: ${txn['total']:.2f}")
        if txn.get('payment_references'):
            print(f"    Payment refs: {', '.join(txn['payment_references'][:3])}")

print(f"\nFound {len(split_candidates)} potential split payments")

print("\nFetching YNAB transactions...")
ynab_txns = ynab.get_transactions(
    since_date=start_date,
    account_names=config['ynab']['account_names']
)
print(f"Found {len(ynab_txns)} YNAB transactions")

print("\n" + "=" * 60)
print("RUNNING BATCH-AWARE MATCHING")
print("=" * 60)

# Run batch matching
normal_matches, batch_matches, unmatched_amazon, unmatched_ynab = matcher.match_transactions_with_batches(
    amazon_txns, ynab_txns
)

print(f"\nResults:")
print(f"  Normal matches (1-to-1): {len(normal_matches)}")
print(f"  Batch matches: {len(batch_matches)}")
print(f"  Unmatched Amazon: {len(unmatched_amazon)}")
print(f"  Unmatched YNAB: {len(unmatched_ynab)}")

# Analyze batch matches
if batch_matches:
    print("\nBatch Match Details:")
    for i, batch in enumerate(batch_matches[:5], 1):  # Show first 5
        print(f"\n  {i}. {batch['type'].replace('_', ' ').title()}:")

        if batch['type'] == 'split_payment':
            amazon_order = batch['amazon_transaction']
            ynab_parts = batch['ynab_transactions']
            print(f"     Amazon Order: {amazon_order.get('order_id', 'Unknown')}")
            print(f"     Amazon Total: ${amazon_order['total']:.2f}")
            print(f"     Split into {len(ynab_parts)} YNAB transactions:")
            for y in ynab_parts:
                amount = abs(y['amount'] / 1000)
                date = datetime.fromisoformat(y['date'])
                print(f"       - ${amount:.2f} on {date.date()}")
            print(f"     Total match: ${batch['ynab_total']:.2f}")
            print(f"     Confidence: {batch['confidence']:.1f}%")

        elif batch['type'] == 'consolidated_charge':
            amazon_orders = batch['amazon_transactions']
            ynab_txn = batch['ynab_transaction']
            print(f"     {len(amazon_orders)} Amazon orders:")
            for a in amazon_orders:
                print(f"       - {a.get('order_id', 'Unknown')}: ${a['total']:.2f}")
            print(f"     Combined Total: ${batch['amazon_total']:.2f}")
            ynab_amount = abs(ynab_txn['amount'] / 1000)
            ynab_date = datetime.fromisoformat(ynab_txn['date'])
            print(f"     YNAB charge: ${ynab_amount:.2f} on {ynab_date.date()}")
            print(f"     Confidence: {batch['confidence']:.1f}%")
else:
    print("\nNo batch matches found.")

# Check for patterns in unmatched transactions
if unmatched_amazon and unmatched_ynab:
    print("\n" + "=" * 60)
    print("ANALYZING UNMATCHED TRANSACTIONS")
    print("=" * 60)

    # Group unmatched Amazon by date
    amazon_by_date = {}
    for txn in unmatched_amazon[:10]:  # First 10
        date_key = txn['date'].date()
        if date_key not in amazon_by_date:
            amazon_by_date[date_key] = []
        amazon_by_date[date_key].append(txn)

    # Look for potential matches
    print("\nPotential batch opportunities in unmatched:")
    for date, amazon_list in amazon_by_date.items():
        if len(amazon_list) > 1:
            total = sum(t['total'] for t in amazon_list)
            print(f"\n  {date}: {len(amazon_list)} Amazon orders totaling ${total:.2f}")

            # Check if any YNAB transactions are close
            for y in unmatched_ynab:
                y_date = datetime.fromisoformat(y['date'])
                y_amount = abs(y['amount'] / 1000)
                date_diff = abs((y_date.date() - date).days)

                if date_diff <= 7 and abs(total - y_amount) <= 2.00:
                    print(f"    → Potential match: YNAB ${y_amount:.2f} on {y_date.date()}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)

# Save results for analysis
results = {
    'test_date': datetime.now().isoformat(),
    'amazon_count': len(amazon_txns),
    'ynab_count': len(ynab_txns),
    'normal_matches': len(normal_matches),
    'batch_matches': len(batch_matches),
    'split_payments': sum(1 for m in batch_matches if m['type'] == 'split_payment'),
    'consolidated_charges': sum(1 for m in batch_matches if m['type'] == 'consolidated_charge'),
    'unmatched_amazon': len(unmatched_amazon),
    'unmatched_ynab': len(unmatched_ynab)
}

results_file = 'logs/batch_test_results.json'
os.makedirs('logs', exist_ok=True)
with open(results_file, 'w') as f:
    json.dump(results, f, indent=2, default=str)

print(f"\nResults saved to {results_file}")