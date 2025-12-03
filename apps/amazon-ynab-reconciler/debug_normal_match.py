#!/usr/bin/env python3
"""Debug why normal match isn't working."""

import sys
import os
sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from transaction_matcher import TransactionMatcher
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

matcher = TransactionMatcher(config['reconciliation'])

# Create the specific transactions
base_date = datetime(2024, 11, 20)

amazon_txn = {
    'order_id': '111-8888888-3333333',
    'date': base_date + timedelta(days=2),
    'total': 49.99,
    'items': [{'name': 'Keyboard', 'price': 49.99}],
    'payment_method': 'Apple Card'
}

ynab_txn = {
    'id': 'ynab-004',
    'date': (base_date + timedelta(days=2)).isoformat(),
    'amount': -49990,  # $49.99 in milliunits
    'account_name': 'Apple Card',
    'payee_name': 'Amazon',
    'memo': None
}

# Test the confidence calculation
confidence = matcher.calculate_match_confidence(amazon_txn, ynab_txn)
print(f"Confidence score: {confidence}")

# Test payment method matching
amazon_payment = amazon_txn['payment_method'].lower()
ynab_account = ynab_txn['account_name'].lower()
payment_match = matcher._fuzzy_match_payment_method(amazon_payment, ynab_account)
print(f"Payment method match: {payment_match}")

# Check amounts
ynab_amount = abs(ynab_txn['amount'] / 1000)
print(f"Amazon amount: ${amazon_txn['total']:.2f}")
print(f"YNAB amount: ${ynab_amount:.2f}")
print(f"Difference: ${abs(amazon_txn['total'] - ynab_amount):.2f}")

# Check dates
ynab_date = datetime.fromisoformat(ynab_txn['date'])
date_diff = abs((amazon_txn['date'] - ynab_date).days)
print(f"Date difference: {date_diff} days")

# Check threshold
print(f"\nMatch threshold: {config['reconciliation']['match_threshold']}")
print(f"Would match? {confidence >= config['reconciliation']['match_threshold']}")