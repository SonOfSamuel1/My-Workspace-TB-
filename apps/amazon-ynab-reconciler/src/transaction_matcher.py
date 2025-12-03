"""
Smart transaction matching engine with fuzzy matching capabilities.
Matches Amazon orders to YNAB transactions using date and amount tolerances.

Uses index-based matching for improved performance on large datasets.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict
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
        self.state_retention_days = config.get('state_retention_days', 90)

        # Handle state file path - use absolute path if relative
        state_file = config.get('state_file', 'logs/reconciliation_state.json')
        if not os.path.isabs(state_file):
            # Make relative to app root (parent of src directory)
            app_root = Path(__file__).parent.parent
            state_file = str(app_root / state_file)
        self.state_file = state_file

        # Index configuration for performance optimization
        self._date_bucket_days = 3  # Group transactions into 3-day buckets
        self._amount_bucket_dollars = 5  # Group by $5 ranges

        # Load previous reconciliation state and clean up old entries
        self.reconciliation_state = self._load_state()
        self._cleanup_old_state()

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

    def _cleanup_old_state(self):
        """Remove state entries older than retention period."""
        if not self.enable_state_tracking:
            return

        cutoff_date = datetime.now() - timedelta(days=self.state_retention_days)
        original_count = len(self.reconciliation_state.get('matched_pairs', []))

        self.reconciliation_state['matched_pairs'] = [
            pair for pair in self.reconciliation_state.get('matched_pairs', [])
            if datetime.fromisoformat(pair['matched_at']) > cutoff_date
        ]

        removed_count = original_count - len(self.reconciliation_state['matched_pairs'])
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old state entries (older than {self.state_retention_days} days)")
            self._save_state()

    def _build_date_index(self, transactions: List[Dict], is_ynab: bool = False) -> Dict[int, List[Dict]]:
        """
        Build a date-based index for transactions.

        Groups transactions into buckets based on date ordinal divided by bucket size.
        This allows O(1) lookup of transactions within a date range.

        Args:
            transactions: List of transactions to index
            is_ynab: Whether these are YNAB transactions (affects date parsing)

        Returns:
            Dict mapping bucket keys to lists of transactions
        """
        index = defaultdict(list)
        for txn in transactions:
            date = txn['date']
            if is_ynab and isinstance(date, str):
                date = datetime.fromisoformat(date)
            bucket_key = date.toordinal() // self._date_bucket_days
            index[bucket_key].append(txn)
        return index

    def _build_amount_index(self, transactions: List[Dict], is_ynab: bool = False) -> Dict[int, List[Dict]]:
        """
        Build an amount-based index for transactions.

        Groups transactions into buckets based on amount divided by bucket size.

        Args:
            transactions: List of transactions to index
            is_ynab: Whether these are YNAB transactions (amounts in milliunits)

        Returns:
            Dict mapping bucket keys to lists of transactions
        """
        index = defaultdict(list)
        for txn in transactions:
            if is_ynab:
                amount = abs(txn['amount'] / 1000)  # Convert milliunits to dollars
            else:
                amount = txn['total']
            bucket_key = int(amount // self._amount_bucket_dollars)
            index[bucket_key].append(txn)
        return index

    def _get_candidate_transactions(
        self,
        amazon_txn: Dict,
        ynab_date_index: Dict[int, List[Dict]],
        ynab_amount_index: Dict[int, List[Dict]],
        matched_ynab_ids: Set[str]
    ) -> List[Dict]:
        """
        Get candidate YNAB transactions that could match an Amazon transaction.

        Uses indices to efficiently find transactions within date and amount tolerances.

        Args:
            amazon_txn: Amazon transaction to match
            ynab_date_index: Date-indexed YNAB transactions
            ynab_amount_index: Amount-indexed YNAB transactions
            matched_ynab_ids: Set of already-matched YNAB transaction IDs

        Returns:
            List of candidate YNAB transactions
        """
        # Get date bucket range
        amazon_date = amazon_txn['date']
        base_bucket = amazon_date.toordinal() // self._date_bucket_days

        # Include neighboring buckets to handle tolerance
        date_range = max(1, (self.date_tolerance_days // self._date_bucket_days) + 1)
        date_candidates = set()
        for offset in range(-date_range, date_range + 1):
            bucket_key = base_bucket + offset
            for txn in ynab_date_index.get(bucket_key, []):
                if txn['id'] not in matched_ynab_ids:
                    date_candidates.add(txn['id'])

        # Get amount bucket range
        amazon_amount = amazon_txn['total']
        base_amount_bucket = int(amazon_amount // self._amount_bucket_dollars)

        # Include neighboring buckets for amount tolerance
        amount_tolerance_buckets = max(1, int((self.amount_tolerance_cents / 100) // self._amount_bucket_dollars) + 1)
        amount_candidates = set()
        for offset in range(-amount_tolerance_buckets, amount_tolerance_buckets + 1):
            bucket_key = base_amount_bucket + offset
            for txn in ynab_amount_index.get(bucket_key, []):
                if txn['id'] not in matched_ynab_ids:
                    amount_candidates.add(txn['id'])

        # Return transactions that appear in both indices (intersection)
        candidate_ids = date_candidates & amount_candidates

        # Build list of actual transactions
        candidates = []
        for bucket in ynab_date_index.values():
            for txn in bucket:
                if txn['id'] in candidate_ids:
                    candidates.append(txn)
                    candidate_ids.remove(txn['id'])  # Avoid duplicates
                    if not candidate_ids:
                        break
            if not candidate_ids:
                break

        return candidates

    def match_transactions(
        self,
        amazon_transactions: List[Dict],
        ynab_transactions: List[Dict]
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Match Amazon transactions to YNAB transactions.

        Uses index-based matching for improved performance on large datasets.
        Time complexity reduced from O(n*m) to approximately O(n*log(m)).

        Args:
            amazon_transactions: List of Amazon orders
            ynab_transactions: List of YNAB transactions

        Returns:
            Tuple of (matches, unmatched_amazon, unmatched_ynab)
        """
        matches = []
        matched_amazon_ids: Set[str] = set()
        matched_ynab_ids: Set[str] = set()

        # Debug input
        logger.debug(f"Received {len(amazon_transactions)} Amazon, {len(ynab_transactions)} YNAB transactions")

        logger.info(f"Starting matching process: {len(amazon_transactions)} Amazon, {len(ynab_transactions)} YNAB")

        # Build indices for efficient lookup
        logger.debug("Building transaction indices for optimized matching")
        ynab_date_index = self._build_date_index(ynab_transactions, is_ynab=True)
        ynab_amount_index = self._build_amount_index(ynab_transactions, is_ynab=True)

        # Debug: Show what we're matching
        if amazon_transactions:
            logger.debug(f"First Amazon: {amazon_transactions[0]['date']} | ${amazon_transactions[0]['total']}")
        if ynab_transactions:
            logger.debug(f"First YNAB: {ynab_transactions[0]['date']} | ${ynab_transactions[0]['amount']}")

        # Sort Amazon transactions by date for consistent ordering
        amazon_sorted = sorted(amazon_transactions, key=lambda x: x['date'])

        # Match each Amazon transaction
        for amazon_txn in amazon_sorted:
            # Skip if already matched in a previous run
            if self._is_previously_matched(amazon_txn):
                logger.debug(f"Skipping previously matched Amazon order {amazon_txn['order_id']}")
                matched_amazon_ids.add(amazon_txn['order_id'])
                continue

            best_match = None
            best_confidence = 0

            # Get candidate transactions using indices (much faster than iterating all)
            candidates = self._get_candidate_transactions(
                amazon_txn, ynab_date_index, ynab_amount_index, matched_ynab_ids
            )

            # Find best matching YNAB transaction from candidates
            for ynab_txn in candidates:
                # Skip if already has Amazon data in memo
                memo = ynab_txn.get('memo') or ''
                if 'Amazon:' in memo:
                    continue

                # Calculate match confidence
                confidence = self.calculate_match_confidence(amazon_txn, ynab_txn)

                if confidence >= self.match_threshold and confidence > best_confidence:
                    best_match = ynab_txn
                    best_confidence = confidence

                    # Early termination for perfect matches
                    if confidence >= 100:
                        break

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
                    f"(confidence: {best_confidence:.0f}%)"
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
        # Handle YNAB date as string if needed
        ynab_date = ynab_txn['date']
        if isinstance(ynab_date, str):
            ynab_date = datetime.fromisoformat(ynab_date)
        date_diff = abs((amazon_txn['date'] - ynab_date).days)
        if date_diff <= self.date_tolerance_days:
            date_score = 40 * (1 - (date_diff / (self.date_tolerance_days + 1)))
            confidence += date_score
        else:
            # No match if outside date tolerance
            return 0

        # Amount proximity (0-60 points)
        # YNAB amounts are in milliunits (1/1000 of currency unit)
        ynab_amount_dollars = abs(ynab_txn['amount'] / 1000)
        amount_diff_cents = abs(amazon_txn['total'] - ynab_amount_dollars) * 100
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
            'chase': ['chase', 'freedom', 'sapphire', 'reserve'],
            'amex': ['amex', 'american express', 'blue cash', 'gold', 'platinum', 'simplycash'],
            'amazon': ['amazon', 'prime', 'business prime'],
            'apple': ['apple', 'apple card'],
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

        # Parse YNAB date if needed
        ynab_date = ynab_txn['date']
        if isinstance(ynab_date, str):
            ynab_date = datetime.fromisoformat(ynab_date)

        # Calculate differences correctly
        ynab_amount_dollars = abs(ynab_txn['amount'] / 1000)
        amount_diff_cents = abs(amazon_txn['total'] - ynab_amount_dollars) * 100

        return {
            'amazon_order_id': amazon_txn['order_id'],
            'ynab_transaction_id': ynab_txn['id'],
            'confidence': confidence,
            'amazon_date': amazon_txn['date'],
            'ynab_date': ynab_date,
            'amazon_total': amazon_txn['total'],
            'ynab_amount': ynab_amount_dollars,
            'date_diff_days': abs((amazon_txn['date'] - ynab_date).days),
            'amount_diff_cents': amount_diff_cents,
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

    def match_transactions_with_batches(
        self,
        amazon_transactions: List[Dict],
        ynab_transactions: List[Dict]
    ) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
        """
        Enhanced matching that handles batch transactions.

        Returns:
            - Normal matches (1-to-1)
            - Batch matches (consolidated charges or split payments)
            - Unmatched Amazon transactions
            - Unmatched YNAB transactions
        """
        logger.info("Starting batch-aware transaction matching")

        # First, do normal 1-to-1 matching
        normal_matches, unmatched_amazon, unmatched_ynab = self.match_transactions(
            amazon_transactions, ynab_transactions
        )

        batch_matches = []

        # Try to find consolidated charges (many Amazon -> one YNAB)
        if unmatched_amazon and unmatched_ynab:
            consolidated = self._find_consolidated_charges(
                unmatched_amazon, unmatched_ynab
            )
            for match in consolidated:
                batch_matches.append(match)
                # Remove matched items
                for amazon_txn in match['amazon_transactions']:
                    if amazon_txn in unmatched_amazon:
                        unmatched_amazon.remove(amazon_txn)
                if match['ynab_transaction'] in unmatched_ynab:
                    unmatched_ynab.remove(match['ynab_transaction'])

        # Try to find split payments (one Amazon -> many YNAB)
        if unmatched_amazon and unmatched_ynab:
            split_payments = self._find_split_payments(
                unmatched_amazon, unmatched_ynab
            )
            for match in split_payments:
                batch_matches.append(match)
                # Remove matched items
                if match['amazon_transaction'] in unmatched_amazon:
                    unmatched_amazon.remove(match['amazon_transaction'])
                for ynab_txn in match['ynab_transactions']:
                    if ynab_txn in unmatched_ynab:
                        unmatched_ynab.remove(ynab_txn)

        logger.info(f"Found {len(batch_matches)} batch matches")

        return normal_matches, batch_matches, unmatched_amazon, unmatched_ynab

    def _find_consolidated_charges(
        self,
        amazon_transactions: List[Dict],
        ynab_transactions: List[Dict]
    ) -> List[Dict]:
        """
        Find cases where multiple Amazon orders were charged as one YNAB transaction.
        """
        consolidated_matches = []

        # Group Amazon transactions by date (within tolerance)
        date_groups = {}
        for amazon_txn in amazon_transactions:
            date_key = amazon_txn['date'].date()
            if date_key not in date_groups:
                date_groups[date_key] = []
            date_groups[date_key].append(amazon_txn)

        # For each YNAB transaction, try to find Amazon groups that sum to it
        for ynab_txn in ynab_transactions:
            # Handle YNAB date as string or datetime
            ynab_date = ynab_txn['date']
            if isinstance(ynab_date, str):
                ynab_date = datetime.fromisoformat(ynab_date)
            ynab_amount = abs(ynab_txn['amount'] / 1000)

            # Check date groups within tolerance
            for days_offset in range(-self.date_tolerance_days, self.date_tolerance_days + 1):
                check_date = ynab_date.date() + timedelta(days=days_offset)

                if check_date in date_groups:
                    amazon_group = date_groups[check_date]

                    # Try combinations of 2-5 Amazon transactions
                    from itertools import combinations
                    for r in range(2, min(6, len(amazon_group) + 1)):
                        for combo in combinations(amazon_group, r):
                            total = sum(txn['total'] for txn in combo)

                            # Check if sum matches within tolerance
                            if abs(total - ynab_amount) <= (self.amount_tolerance_cents / 100):
                                # Check payment methods
                                payment_methods = set(txn.get('payment_method', '') for txn in combo)

                                # If all same payment method, check if it matches YNAB
                                if len(payment_methods) == 1:
                                    amazon_payment = list(payment_methods)[0].lower()
                                    if self._fuzzy_match_payment_method(
                                        amazon_payment,
                                        ynab_txn.get('account_name', '').lower()
                                    ):
                                        consolidated_matches.append({
                                            'type': 'consolidated_charge',
                                            'amazon_transactions': list(combo),
                                            'ynab_transaction': ynab_txn,
                                            'amazon_total': total,
                                            'ynab_amount': ynab_amount,
                                            'amount_diff': abs(total - ynab_amount),
                                            'confidence': self._calculate_batch_confidence(
                                                list(combo), [ynab_txn], total, ynab_amount
                                            )
                                        })

                                        logger.info(
                                            f"Found consolidated charge: {len(combo)} Amazon orders "
                                            f"= 1 YNAB transaction (${ynab_amount:.2f})"
                                        )
                                        break

        return consolidated_matches

    def _find_split_payments(
        self,
        amazon_transactions: List[Dict],
        ynab_transactions: List[Dict]
    ) -> List[Dict]:
        """
        Find cases where one Amazon order was split into multiple YNAB charges.
        """
        split_matches = []

        for amazon_txn in amazon_transactions:
            # Check if this transaction has split payment evidence
            is_split = amazon_txn.get('is_split_payment', False)
            payment_refs = amazon_txn.get('payment_references', [])

            # Look for YNAB transactions around the same date that sum to Amazon total
            amazon_date = amazon_txn['date']
            amazon_total = amazon_txn['total']

            potential_ynab = []
            for ynab_txn in ynab_transactions:
                # Handle YNAB date as string or datetime
                ynab_date = ynab_txn['date']
                if isinstance(ynab_date, str):
                    ynab_date = datetime.fromisoformat(ynab_date)
                date_diff = abs((amazon_date - ynab_date).days)

                if date_diff <= self.date_tolerance_days:
                    ynab_amount = abs(ynab_txn['amount'] / 1000)

                    # Check if this could be part of a split
                    if ynab_amount < amazon_total:
                        # Check payment method
                        if self._fuzzy_match_payment_method(
                            amazon_txn.get('payment_method', '').lower(),
                            ynab_txn.get('account_name', '').lower()
                        ):
                            potential_ynab.append(ynab_txn)

            # Try combinations of YNAB transactions
            if len(potential_ynab) >= 2:
                from itertools import combinations
                for r in range(2, min(6, len(potential_ynab) + 1)):
                    for combo in combinations(potential_ynab, r):
                        total = sum(abs(txn['amount'] / 1000) for txn in combo)

                        # Check if sum matches within tolerance
                        if abs(total - amazon_total) <= (self.amount_tolerance_cents / 100):
                            split_matches.append({
                                'type': 'split_payment',
                                'amazon_transaction': amazon_txn,
                                'ynab_transactions': list(combo),
                                'amazon_total': amazon_total,
                                'ynab_total': total,
                                'amount_diff': abs(total - amazon_total),
                                'confidence': self._calculate_batch_confidence(
                                    [amazon_txn], list(combo), amazon_total, total
                                )
                            })

                            logger.info(
                                f"Found split payment: 1 Amazon order ({amazon_txn.get('order_id', 'Unknown')}) "
                                f"= {len(combo)} YNAB transactions (${amazon_total:.2f})"
                            )
                            break

        return split_matches

    def _calculate_batch_confidence(
        self,
        amazon_txns: List[Dict],
        ynab_txns: List[Dict],
        amazon_total: float,
        ynab_total: float
    ) -> float:
        """
        Calculate confidence score for batch matches.
        """
        confidence = 70.0  # Base confidence for batch matches

        # Amount match bonus
        amount_diff = abs(amazon_total - ynab_total)
        if amount_diff < 0.01:
            confidence += 20
        elif amount_diff <= 0.50:
            confidence += 15
        elif amount_diff <= 1.00:
            confidence += 10
        elif amount_diff <= 2.00:
            confidence += 5

        # Date consistency bonus
        if len(amazon_txns) == 1:
            # Split payment - check if all YNAB dates are close
            amazon_date = amazon_txns[0]['date']
            max_date_diff = max(
                abs((amazon_date - (y['date'] if isinstance(y['date'], datetime) else datetime.fromisoformat(y['date']))).days)
                for y in ynab_txns
            )
            if max_date_diff <= 1:
                confidence += 5
        else:
            # Consolidated charge - check if all Amazon dates are close
            dates = [txn['date'] for txn in amazon_txns]
            date_range = (max(dates) - min(dates)).days
            if date_range <= 1:
                confidence += 5

        return min(confidence, 95.0)  # Cap at 95% for batch matches