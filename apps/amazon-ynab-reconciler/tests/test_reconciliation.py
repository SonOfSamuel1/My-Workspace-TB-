"""
Test script for Amazon-YNAB reconciliation with sample data.
Run this to test the matching logic without real API calls.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from transaction_matcher import TransactionMatcher
from reconciliation_engine import ReconciliationEngine


def generate_test_data():
    """Generate test Amazon and YNAB transactions."""

    # Base date for transactions
    base_date = datetime.now() - timedelta(days=10)

    # Sample Amazon transactions
    amazon_transactions = [
        {
            'order_id': '111-1234567-1234567',
            'date': base_date,
            'total': 49.99,
            'subtotal': 49.99,
            'tax': 0,
            'items': [{
                'name': 'Echo Dot (5th Gen)',
                'category': 'Electronics',
                'asin': 'B09B8V1LZ3',
                'price': 49.99,
                'quantity': 1,
                'link': 'https://www.amazon.com/dp/B09B8V1LZ3'
            }],
            'status': 'Delivered',
            'payment_method': 'Chase Credit Card'
        },
        {
            'order_id': '111-2345678-2345678',
            'date': base_date - timedelta(days=2),
            'total': 35.47,
            'subtotal': 32.99,
            'tax': 2.48,
            'items': [{
                'name': 'Organic Coffee Beans',
                'category': 'Grocery',
                'asin': 'B07R4J9BQG',
                'price': 14.99,
                'quantity': 1,
                'link': 'https://www.amazon.com/dp/B07R4J9BQG'
            }, {
                'name': 'Coffee Filters',
                'category': 'Grocery',
                'asin': 'B01LWJ5N8V',
                'price': 8.99,
                'quantity': 2,
                'link': 'https://www.amazon.com/dp/B01LWJ5N8V'
            }],
            'status': 'Delivered',
            'payment_method': 'Amex'
        },
        {
            'order_id': '111-3456789-3456789',
            'date': base_date - timedelta(days=5),
            'total': 89.99,
            'subtotal': 89.99,
            'tax': 0,
            'items': [{
                'name': 'Running Shoes',
                'category': 'Clothing & Shoes',
                'asin': 'B08N6LWLNB',
                'price': 89.99,
                'quantity': 1,
                'link': 'https://www.amazon.com/dp/B08N6LWLNB'
            }],
            'status': 'Delivered',
            'payment_method': 'Chase Credit Card'
        },
        {
            'order_id': '111-4567890-4567890',
            'date': base_date - timedelta(days=7),
            'total': 24.99,
            'subtotal': 24.99,
            'tax': 0,
            'items': [{
                'name': 'Book: Atomic Habits',
                'category': 'Books',
                'asin': '0735211299',
                'price': 16.99,
                'quantity': 1,
                'link': 'https://www.amazon.com/dp/0735211299'
            }],
            'status': 'Delivered',
            'payment_method': 'Bank of America Credit Card'
        }
    ]

    # Sample YNAB transactions (some will match, some won't)
    ynab_transactions = [
        {
            'id': 'ynab-txn-001',
            'date': base_date,  # Exact match for Echo Dot
            'amount': 49.99,
            'payee_name': 'Amazon',
            'category_name': 'Shopping',
            'memo': '',
            'cleared': 'uncleared',
            'account_id': 'acc-001',
            'account_name': 'Chase Freedom',
            'import_id': None,
            'flag_color': None
        },
        {
            'id': 'ynab-txn-002',
            'date': base_date - timedelta(days=1),  # 1 day off for coffee
            'amount': 35.50,  # 3 cents off
            'payee_name': 'AMZN Mktp',
            'category_name': 'Groceries',
            'memo': '',
            'cleared': 'uncleared',
            'account_id': 'acc-002',
            'account_name': 'American Express',
            'import_id': None,
            'flag_color': None
        },
        {
            'id': 'ynab-txn-003',
            'date': base_date - timedelta(days=6),  # 1 day off for shoes
            'amount': 89.99,  # Exact amount match
            'payee_name': 'Amazon.com',
            'category_name': 'Clothing',
            'memo': '',
            'cleared': 'uncleared',
            'account_id': 'acc-001',
            'account_name': 'Chase Freedom',
            'import_id': None,
            'flag_color': None
        },
        {
            'id': 'ynab-txn-004',
            'date': base_date - timedelta(days=3),
            'amount': 125.00,  # Won't match anything
            'payee_name': 'Target',
            'category_name': 'Shopping',
            'memo': '',
            'cleared': 'uncleared',
            'account_id': 'acc-003',
            'account_name': 'Bank of America',
            'import_id': None,
            'flag_color': None
        },
        {
            'id': 'ynab-txn-005',
            'date': base_date - timedelta(days=7),
            'amount': 25.00,  # Close to book order
            'payee_name': 'Amazon',
            'category_name': 'Books',
            'memo': '',
            'cleared': 'uncleared',
            'account_id': 'acc-003',
            'account_name': 'Bank of America',
            'import_id': None,
            'flag_color': None
        }
    ]

    return amazon_transactions, ynab_transactions


def test_matching_engine():
    """Test the transaction matching engine."""
    print("="*60)
    print("TESTING TRANSACTION MATCHING ENGINE")
    print("="*60)

    # Initialize matcher with test config
    config = {
        'match_threshold': 80,
        'date_tolerance_days': 2,
        'amount_tolerance_cents': 50,
        'enable_state_tracking': False  # Disable for testing
    }

    matcher = TransactionMatcher(config)

    # Generate test data
    amazon_txns, ynab_txns = generate_test_data()

    print(f"\nTest Data:")
    print(f"- Amazon transactions: {len(amazon_txns)}")
    print(f"- YNAB transactions: {len(ynab_txns)}")

    # Run matching
    matches, unmatched_amazon, unmatched_ynab = matcher.match_transactions(
        amazon_transactions=amazon_txns,
        ynab_transactions=ynab_txns
    )

    # Display results
    print(f"\nMatching Results:")
    print(f"- Matches found: {len(matches)}")
    print(f"- Unmatched Amazon: {len(unmatched_amazon)}")
    print(f"- Unmatched YNAB: {len(unmatched_ynab)}")

    # Show detailed matches
    print("\n" + "-"*60)
    print("MATCHED TRANSACTIONS:")
    print("-"*60)

    for i, match in enumerate(matches, 1):
        print(f"\nMatch #{i}:")
        print(f"  Amazon Order: {match['amazon_order_id']}")
        print(f"  YNAB Transaction: {match['ynab_transaction_id']}")
        print(f"  Confidence: {match['confidence']:.1f}%")
        print(f"  Date Diff: {match['date_diff_days']} days")
        print(f"  Amount Diff: ${match['amount_diff_cents']/100:.2f}")
        print(f"  Amazon Item: {match['amazon_data']['item_name']}")
        print(f"  Amazon Category: {match['amazon_data']['category']}")
        print(f"  YNAB Payee: {match['ynab_data']['payee_name']}")
        print(f"  YNAB Account: {match['ynab_data']['account_name']}")

    # Show unmatched
    if unmatched_amazon:
        print("\n" + "-"*60)
        print("UNMATCHED AMAZON ORDERS:")
        print("-"*60)
        for txn in unmatched_amazon:
            items = ', '.join([item['name'] for item in txn['items']])
            print(f"  {txn['order_id']}: ${txn['total']:.2f} - {items}")

    if unmatched_ynab:
        print("\n" + "-"*60)
        print("UNMATCHED YNAB TRANSACTIONS:")
        print("-"*60)
        for txn in unmatched_ynab:
            print(f"  {txn['id']}: ${txn['amount']:.2f} - {txn['payee_name']}")

    # Get statistics
    stats = matcher.get_match_statistics(matches)

    print("\n" + "-"*60)
    print("MATCH STATISTICS:")
    print("-"*60)
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    return matches


def test_confidence_scoring():
    """Test confidence scoring with various scenarios."""
    print("\n" + "="*60)
    print("TESTING CONFIDENCE SCORING")
    print("="*60)

    config = {
        'match_threshold': 80,
        'date_tolerance_days': 2,
        'amount_tolerance_cents': 50,
        'enable_state_tracking': False
    }

    matcher = TransactionMatcher(config)

    # Test scenarios
    test_cases = [
        {
            'name': 'Perfect Match',
            'amazon': {'date': datetime.now(), 'total': 49.99, 'payment_method': 'Chase'},
            'ynab': {'date': datetime.now(), 'amount': 49.99, 'account_name': 'Chase Freedom'}
        },
        {
            'name': '1 Day Off, Exact Amount',
            'amazon': {'date': datetime.now(), 'total': 49.99, 'payment_method': 'Chase'},
            'ynab': {'date': datetime.now() - timedelta(days=1), 'amount': 49.99, 'account_name': 'Chase'}
        },
        {
            'name': 'Same Day, Small Amount Diff',
            'amazon': {'date': datetime.now(), 'total': 49.99, 'payment_method': 'Amex'},
            'ynab': {'date': datetime.now(), 'amount': 50.24, 'account_name': 'American Express'}
        },
        {
            'name': '2 Days Off, $0.50 Diff',
            'amazon': {'date': datetime.now(), 'total': 49.99, 'payment_method': 'Visa'},
            'ynab': {'date': datetime.now() - timedelta(days=2), 'amount': 50.49, 'account_name': 'Bank Visa'}
        },
        {
            'name': 'Outside Tolerance',
            'amazon': {'date': datetime.now(), 'total': 49.99, 'payment_method': 'Visa'},
            'ynab': {'date': datetime.now() - timedelta(days=5), 'amount': 49.99, 'account_name': 'Visa'}
        }
    ]

    print("\nConfidence Scores for Different Scenarios:")
    print("-"*60)

    for test in test_cases:
        confidence = matcher.calculate_match_confidence(
            test['amazon'],
            test['ynab']
        )

        status = "✓ MATCH" if confidence >= config['match_threshold'] else "✗ NO MATCH"
        print(f"{test['name']:30} | Confidence: {confidence:6.2f}% | {status}")


def test_dry_run():
    """Test dry run mode to ensure no actual updates occur."""
    print("\n" + "="*60)
    print("TESTING DRY RUN MODE")
    print("="*60)

    # Mock YNAB service for testing
    class MockYNABService:
        def update_transaction_memo(self, transaction_id, amazon_data, dry_run=False):
            if dry_run:
                print(f"  [DRY RUN] Would update {transaction_id} with {amazon_data['item_name']}")
            return True

        def batch_update_transactions(self, updates, dry_run=False):
            if dry_run:
                print(f"  [DRY RUN] Would update {len(updates)} transactions")
            return len(updates) if not dry_run else 0

    # Initialize engine in dry run mode
    ynab_service = MockYNABService()
    config = {'match_threshold': 80}
    engine = ReconciliationEngine(ynab_service, config, dry_run=True)

    # Generate test matches
    matches = test_matching_engine()

    print("\nApplying updates in DRY RUN mode:")
    print("-"*60)

    # Apply updates
    updates_applied = engine.apply_updates(matches)

    print(f"\nDry run complete: {updates_applied} updates applied (should be 0)")
    print(f"Statistics: {engine.stats}")


def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# AMAZON-YNAB RECONCILIATION TEST SUITE")
    print("#"*60)

    # Test confidence scoring
    test_confidence_scoring()

    # Test matching engine
    matches = test_matching_engine()

    # Test dry run mode
    test_dry_run()

    print("\n" + "#"*60)
    print("# ALL TESTS COMPLETED")
    print("#"*60)


if __name__ == "__main__":
    main()