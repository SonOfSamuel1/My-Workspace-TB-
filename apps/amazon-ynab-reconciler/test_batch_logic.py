#!/usr/bin/env python3
"""Test batch matching logic with mock data."""

import sys
import os
sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from transaction_matcher import TransactionMatcher
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

print("=" * 60)
print("BATCH MATCHING LOGIC TEST")
print("=" * 60)

# Create matcher
matcher = TransactionMatcher(config['reconciliation'])

# Create mock data
base_date = datetime(2024, 11, 20)

# Mock Amazon transactions
amazon_txns = [
    # Split payment scenario - one order split into two charges
    {
        'order_id': '111-6596663-4455466',
        'date': base_date,
        'total': 33.34,
        'subtotal': 30.00,
        'tax': 3.34,
        'items': [
            {'name': 'USB Cable', 'price': 15.00},
            {'name': 'Phone Case', 'price': 15.00}
        ],
        'payment_method': 'Amazon Business Prime Card',
        'is_split_payment': True,
        'payment_references': ['PMT-001', 'PMT-002']
    },

    # Consolidated charge scenario - two orders charged together
    {
        'order_id': '111-7777777-1111111',
        'date': base_date + timedelta(days=1),
        'total': 25.00,
        'items': [{'name': 'Book', 'price': 25.00}],
        'payment_method': 'Chase Reserve CC'
    },
    {
        'order_id': '111-7777777-2222222',
        'date': base_date + timedelta(days=1),
        'total': 35.00,
        'items': [{'name': 'Headphones', 'price': 35.00}],
        'payment_method': 'Chase Reserve CC'
    },

    # Normal single transaction
    {
        'order_id': '111-8888888-3333333',
        'date': base_date + timedelta(days=2),
        'total': 49.99,
        'items': [{'name': 'Keyboard', 'price': 49.99}],
        'payment_method': 'Apple Card'
    }
]

# Mock YNAB transactions
ynab_txns = [
    # Split payment parts
    {
        'id': 'ynab-001',
        'date': base_date.isoformat(),
        'amount': -23810,  # $23.81 in milliunits
        'account_name': 'Amazon Business Prime Card – 3008',
        'payee_name': 'Amazon',
        'memo': None
    },
    {
        'id': 'ynab-002',
        'date': (base_date + timedelta(days=1)).isoformat(),
        'amount': -9530,  # $9.53 in milliunits
        'account_name': 'Amazon Business Prime Card – 3008',
        'payee_name': 'Amazon',
        'memo': None
    },

    # Consolidated charge
    {
        'id': 'ynab-003',
        'date': (base_date + timedelta(days=1)).isoformat(),
        'amount': -60000,  # $60.00 in milliunits
        'account_name': 'Chase Reserve CC – 1516',
        'payee_name': 'Amazon',
        'memo': None
    },

    # Normal transaction
    {
        'id': 'ynab-004',
        'date': (base_date + timedelta(days=2)).isoformat(),
        'amount': -49990,  # $49.99 in milliunits
        'account_name': 'Apple Card',
        'payee_name': 'Amazon',
        'memo': None
    }
]

print("\nMock Data Created:")
print(f"  Amazon transactions: {len(amazon_txns)}")
print(f"  YNAB transactions: {len(ynab_txns)}")

print("\n" + "=" * 60)
print("TESTING BATCH-AWARE MATCHING")
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

# Show normal matches
if normal_matches:
    print("\nNormal Matches:")
    for match in normal_matches:
        print(f"  - Amazon {match['amazon_order_id'][:15]}... → YNAB {match['ynab_transaction_id']}")
        print(f"    Confidence: {match['confidence']:.1f}%")

# Show batch matches
if batch_matches:
    print("\nBatch Matches:")
    for batch in batch_matches:
        if batch['type'] == 'split_payment':
            print(f"  - Split Payment:")
            print(f"    Amazon Order: {batch['amazon_transaction']['order_id']}")
            print(f"    Total: ${batch['amazon_total']:.2f}")
            print(f"    Split into {len(batch['ynab_transactions'])} YNAB transactions")
            print(f"    Confidence: {batch['confidence']:.1f}%")

        elif batch['type'] == 'consolidated_charge':
            print(f"  - Consolidated Charge:")
            order_ids = [t['order_id'] for t in batch['amazon_transactions']]
            print(f"    Amazon Orders: {', '.join(order_ids)}")
            print(f"    Combined Total: ${batch['amazon_total']:.2f}")
            print(f"    Single YNAB charge: ${batch['ynab_amount']:.2f}")
            print(f"    Confidence: {batch['confidence']:.1f}%")

# Show unmatched
if unmatched_amazon:
    print(f"\nUnmatched Amazon: {[t['order_id'] for t in unmatched_amazon]}")
if unmatched_ynab:
    print(f"Unmatched YNAB: {[t['id'] for t in unmatched_ynab]}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)

# Test specific scenarios
print("\nScenario Tests:")

# Test 1: Should detect split payment
split_found = any(
    m['type'] == 'split_payment' and
    m['amazon_transaction']['order_id'] == '111-6596663-4455466'
    for m in batch_matches
)
print(f"✓ Split payment detected: {split_found}")

# Test 2: Should detect consolidated charge
consolidated_found = any(
    m['type'] == 'consolidated_charge' and
    len(m['amazon_transactions']) == 2
    for m in batch_matches
)
print(f"✓ Consolidated charge detected: {consolidated_found}")

# Test 3: Should have normal match
normal_found = any(
    m['amazon_order_id'] == '111-8888888-3333333'
    for m in normal_matches
)
print(f"✓ Normal match found: {normal_found}")

print("\nAll tests passed!" if all([split_found, consolidated_found, normal_found]) else "\nSome tests failed!")