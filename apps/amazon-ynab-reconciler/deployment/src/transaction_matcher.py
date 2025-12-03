"""
Smart transaction matching engine with fuzzy matching capabilities.
Matches Amazon orders to YNAB transactions using date and amount tolerances.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class TransactionMatcher:
    """Smart matching engine for reconciling transactions."""

    def __init__(self, config: Dict):
        """Initialize the transaction matcher."""
        self.config = config
        self.match_threshold = config.get('match_threshold', 80)
        self.date_tolerance_days = config.get('date_tolerance_days', 2)
        self.amount_tolerance_cents = config.get('amount_tolerance_cents', 50)
        self.enable_state_tracking = config.get('enable_state_tracking', True)
        self.state_file = config.get('state_file', '../logs/reconciliation_state.json')

        # Load previous reconciliation state
        self.reconciliation_state = self._load_state()

    def _load_state(self) -> Dict:
        """Load previous reconciliation state from file."""
        if not self.enable_state_tracking:
            return {'matched_pairs': [], 'last_run': None}

        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load state file: {str(e)}")

        return {'matched_pairs': [], 'last_run': None}

    def _save_state(self):
        """Save reconciliation state to file."""
        if not self.enable_state_tracking:
            return

        try:
            # Ensure directory exists
            Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)

            self.reconciliation_state['last_run'] = datetime.now().isoformat()

            with open(self.state_file, 'w') as f:
                json.dump(self.reconciliation_state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Could not save state file: {str(e)}")

    def match_transactions(
        self,
        amazon_transactions: List[Dict],
        ynab_transactions: List[Dict]
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Match Amazon transactions to YNAB transactions.

        Args:
            amazon_transactions: List of Amazon orders
            ynab_transactions: List of YNAB transactions

        Returns:
            Tuple of (matches, unmatched_amazon, unmatched_ynab)
        """
        matches = []
        matched_amazon_ids = set()
        matched_ynab_ids = set()

        # Debug input
        logger.debug(f"Received {len(amazon_transactions)} Amazon, {len(ynab_transactions)} YNAB transactions")

        # Sort transactions by date for efficient matching
        amazon_sorted = sorted(amazon_transactions, key=lambda x: x['date'])
        ynab_sorted = sorted(ynab_transactions, key=lambda x: x['date'])

        logger.info(f"Starting matching process: {len(amazon_transactions)} Amazon, {len(ynab_transactions)} YNAB")

        # Debug: Show what we're matching
        if amazon_transactions:
            logger.debug(f"First Amazon: {amazon_transactions[0]['date']} | ${amazon_transactions[0]['total']}")
        if ynab_transactions:
            logger.debug(f"First YNAB: {ynab_transactions[0]['date']} | ${ynab_transactions[0]['amount']}")

        # Match each Amazon transaction
        for amazon_txn in amazon_sorted:
            # Skip if already matched in a previous run
            if self._is_previously_matched(amazon_txn):
                logger.debug(f"Skipping previously matched Amazon order {amazon_txn['order_id']}")
                matched_amazon_ids.add(amazon_txn['order_id'])
                continue

            best_match = None
            best_confidence = 0

            # Find best matching YNAB transaction
            for ynab_txn in ynab_sorted:
                # Skip if already matched
                if ynab_txn['id'] in matched_ynab_ids:
                    continue

                # Skip if already has Amazon data in memo
                memo = ynab_txn.get('memo') or ''
                if 'Amazon:' in memo:
                    continue

                # Calculate match confidence
                confidence = self.calculate_match_confidence(amazon_txn, ynab_txn)

                if confidence >= self.match_threshold and confidence > best_confidence:
                    best_match = ynab_txn
                    best_confidence = confidence

            # Record match if found
            if best_match:
                match = self._create_match_record(amazon_txn, best_match, best_confidence)
                matches.append(match)
                matched_amazon_ids.add(amazon_txn['order_id'])
                matched_ynab_ids.add(best_match['id'])

                # Record in state
                self._record_match(amazon_txn['order_id'], best_match['id'])

                logger.info(
                    f"Matched Amazon order {amazon_txn['order_id'][:10]}... "
                    f"to YNAB transaction {best_match['id'][:10]}... "
                    f"(confidence: {best_confidence}%)"
                )

        # Identify unmatched transactions
        unmatched_amazon = [
            txn for txn in amazon_transactions
            if txn['order_id'] not in matched_amazon_ids
        ]

        unmatched_ynab = [
            txn for txn in ynab_transactions
            if txn['id'] not in matched_ynab_ids
            and 'Amazon:' not in (txn.get('memo') or '')  # Don't report already reconciled
        ]

        # Save state
        self._save_state()

        logger.info(
            f"Matching complete: {len(matches)} matches, "
            f"{len(unmatched_amazon)} unmatched Amazon, "
            f"{len(unmatched_ynab)} unmatched YNAB"
        )

        return matches, unmatched_amazon, unmatched_ynab

    def calculate_match_confidence(self, amazon_txn: Dict, ynab_txn: Dict) -> float:
        """
        Calculate confidence score for a potential match.

        Args:
            amazon_txn: Amazon transaction
            ynab_txn: YNAB transaction

        Returns:
            Confidence score (0-100)
        """
        confidence = 0

        # Date proximity (0-40 points)
        date_diff = abs((amazon_txn['date'] - ynab_txn['date']).days)
        if date_diff <= self.date_tolerance_days:
            date_score = 40 * (1 - (date_diff / (self.date_tolerance_days + 1)))
            confidence += date_score
        else:
            # No match if outside date tolerance
            return 0

        # Amount proximity (0-60 points)
        amount_diff_cents = abs(amazon_txn['total'] * 100 - ynab_txn['amount'] * 100)
        if amount_diff_cents <= self.amount_tolerance_cents:
            amount_score = 60 * (1 - (amount_diff_cents / (self.amount_tolerance_cents + 1)))
            confidence += amount_score
        else:
            # No match if outside amount tolerance
            return 0

        # Bonus points for exact matches
        if date_diff == 0:
            confidence += 5  # Same day bonus

        if amount_diff_cents < 1:
            confidence += 5  # Exact amount bonus

        # Check payment method if available
        if 'payment_method' in amazon_txn and 'account_name' in ynab_txn:
            # Fuzzy match on account names
            amazon_payment = amazon_txn['payment_method'].lower()
            ynab_account = ynab_txn['account_name'].lower()

            if self._fuzzy_match_payment_method(amazon_payment, ynab_account):
                confidence += 10  # Payment method match bonus

        return min(confidence, 100)  # Cap at 100

    def _fuzzy_match_payment_method(self, amazon_payment: str, ynab_account: str) -> bool:
        """
        Fuzzy match payment methods between Amazon and YNAB.

        Args:
            amazon_payment: Payment method from Amazon
            ynab_account: Account name from YNAB

        Returns:
            True if likely the same payment method
        """
        # Common mappings
        mappings = {
            'chase': ['chase', 'freedom', 'sapphire'],
            'amex': ['amex', 'american express', 'blue cash', 'gold', 'platinum'],
            'boa': ['bank of america', 'boa', 'bofa'],
            'citi': ['citi', 'citibank', 'costco'],
            'discover': ['discover'],
            'capital one': ['capital one', 'venture', 'savor'],
            'visa': ['visa'],
            'mastercard': ['mastercard', 'mc']
        }

        # Check each mapping
        for key, variations in mappings.items():
            amazon_match = any(v in amazon_payment for v in variations)
            ynab_match = any(v in ynab_account for v in variations)

            if amazon_match and ynab_match:
                return True

        # Direct substring match
        return any(word in ynab_account for word in amazon_payment.split())

    def _create_match_record(
        self,
        amazon_txn: Dict,
        ynab_txn: Dict,
        confidence: float
    ) -> Dict:
        """
        Create a match record with all necessary details.

        Args:
            amazon_txn: Amazon transaction
            ynab_txn: YNAB transaction
            confidence: Match confidence score

        Returns:
            Match record dictionary
        """
        # Get primary item details (first item or aggregate)
        if amazon_txn['items']:
            primary_item = amazon_txn['items'][0]
            item_names = [item['name'] for item in amazon_txn['items']]

            if len(item_names) > 1:
                item_display = f"{primary_item['name']} (+{len(item_names)-1} more)"
            else:
                item_display = primary_item['name']
        else:
            primary_item = {
                'name': 'Amazon Purchase',
                'category': 'Unknown',
                'link': ''
            }
            item_display = 'Amazon Purchase'

        return {
            'amazon_order_id': amazon_txn['order_id'],
            'ynab_transaction_id': ynab_txn['id'],
            'confidence': confidence,
            'amazon_date': amazon_txn['date'],
            'ynab_date': ynab_txn['date'],
            'amazon_total': amazon_txn['total'],
            'ynab_amount': ynab_txn['amount'],
            'date_diff_days': abs((amazon_txn['date'] - ynab_txn['date']).days),
            'amount_diff_cents': abs(amazon_txn['total'] * 100 - ynab_txn['amount'] * 100),
            'amazon_data': {
                'category': primary_item.get('category', 'Unknown'),
                'item_name': item_display,
                'item_link': primary_item.get('link', ''),
                'all_items': amazon_txn['items']
            },
            'ynab_data': {
                'payee_name': ynab_txn.get('payee_name', ''),
                'category_name': ynab_txn.get('category_name', ''),
                'account_name': ynab_txn.get('account_name', ''),
                'existing_memo': ynab_txn.get('memo', '')
            }
        }

    def _is_previously_matched(self, amazon_txn: Dict) -> bool:
        """Check if an Amazon transaction was previously matched."""
        if not self.enable_state_tracking:
            return False

        matched_pairs = self.reconciliation_state.get('matched_pairs', [])
        return any(
            pair['amazon_order_id'] == amazon_txn['order_id']
            for pair in matched_pairs
        )

    def _record_match(self, amazon_order_id: str, ynab_transaction_id: str):
        """Record a match in the state."""
        if not self.enable_state_tracking:
            return

        match_record = {
            'amazon_order_id': amazon_order_id,
            'ynab_transaction_id': ynab_transaction_id,
            'matched_at': datetime.now().isoformat()
        }

        if 'matched_pairs' not in self.reconciliation_state:
            self.reconciliation_state['matched_pairs'] = []

        self.reconciliation_state['matched_pairs'].append(match_record)

        # Keep only last 90 days of matches to prevent file from growing too large
        cutoff_date = datetime.now() - timedelta(days=90)
        self.reconciliation_state['matched_pairs'] = [
            pair for pair in self.reconciliation_state['matched_pairs']
            if datetime.fromisoformat(pair['matched_at']) > cutoff_date
        ]

    def get_match_statistics(self, matches: List[Dict]) -> Dict:
        """
        Calculate statistics about the matches.

        Args:
            matches: List of match records

        Returns:
            Statistics dictionary
        """
        if not matches:
            return {
                'total_matches': 0,
                'avg_confidence': 0,
                'high_confidence_count': 0,
                'medium_confidence_count': 0,
                'low_confidence_count': 0,
                'exact_amount_matches': 0,
                'same_day_matches': 0
            }

        confidences = [m['confidence'] for m in matches]

        return {
            'total_matches': len(matches),
            'avg_confidence': sum(confidences) / len(confidences),
            'high_confidence_count': sum(1 for c in confidences if c >= 90),
            'medium_confidence_count': sum(1 for c in confidences if 70 <= c < 90),
            'low_confidence_count': sum(1 for c in confidences if c < 70),
            'exact_amount_matches': sum(1 for m in matches if m['amount_diff_cents'] < 1),
            'same_day_matches': sum(1 for m in matches if m['date_diff_days'] == 0),
            'total_amazon_amount': sum(m['amazon_total'] for m in matches),
            'total_ynab_amount': sum(m['ynab_amount'] for m in matches)
        }