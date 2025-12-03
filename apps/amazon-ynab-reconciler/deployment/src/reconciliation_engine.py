"""
Reconciliation engine that applies matched transactions to YNAB.
Handles batch updates and transaction state management.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ReconciliationEngine:
    """Engine for applying reconciliation updates to YNAB."""

    def __init__(self, ynab_service, config: Dict, dry_run: bool = False):
        """
        Initialize the reconciliation engine.

        Args:
            ynab_service: Instance of YNABService
            config: Reconciliation configuration
            dry_run: If True, don't actually update YNAB
        """
        self.ynab_service = ynab_service
        self.config = config
        self.dry_run = dry_run

        # Track update statistics
        self.stats = {
            'total_processed': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'skipped_updates': 0
        }

    def apply_updates(self, matches: List[Dict]) -> int:
        """
        Apply reconciliation updates to YNAB transactions.

        Args:
            matches: List of match records from TransactionMatcher

        Returns:
            Number of successful updates
        """
        logger.info(f"Applying {len(matches)} reconciliation updates (dry_run={self.dry_run})")

        # Reset statistics
        self.stats = {
            'total_processed': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'skipped_updates': 0
        }

        # Process each match
        for match in matches:
            self.stats['total_processed'] += 1

            try:
                if self._should_skip_update(match):
                    self.stats['skipped_updates'] += 1
                    logger.debug(f"Skipping update for match {match['ynab_transaction_id']}")
                    continue

                # Apply the update
                success = self._apply_single_update(match)

                if success:
                    self.stats['successful_updates'] += 1
                else:
                    self.stats['failed_updates'] += 1

            except Exception as e:
                logger.error(f"Error processing match {match['ynab_transaction_id']}: {str(e)}")
                self.stats['failed_updates'] += 1

        # Log summary
        logger.info(
            f"Reconciliation complete: {self.stats['successful_updates']} successful, "
            f"{self.stats['failed_updates']} failed, "
            f"{self.stats['skipped_updates']} skipped"
        )

        return self.stats['successful_updates']

    def _should_skip_update(self, match: Dict) -> bool:
        """
        Determine if an update should be skipped.

        Args:
            match: Match record

        Returns:
            True if update should be skipped
        """
        # Skip if confidence is too low
        if match['confidence'] < self.config.get('match_threshold', 80):
            logger.warning(
                f"Skipping match with low confidence ({match['confidence']}%) "
                f"for transaction {match['ynab_transaction_id']}"
            )
            return True

        # Skip if already has Amazon data in memo
        existing_memo = match['ynab_data'].get('existing_memo') or ''
        if 'Amazon:' in existing_memo:
            logger.debug(f"Transaction {match['ynab_transaction_id']} already reconciled")
            return True

        # Skip if amount difference is too large (safety check)
        max_diff = self.config.get('amount_tolerance_cents', 50) * 2  # Double tolerance for safety
        if match['amount_diff_cents'] > max_diff:
            logger.warning(
                f"Skipping match with large amount difference "
                f"(${match['amount_diff_cents']/100:.2f}) "
                f"for transaction {match['ynab_transaction_id']}"
            )
            return True

        return False

    def _apply_single_update(self, match: Dict) -> bool:
        """
        Apply a single reconciliation update to YNAB.

        Args:
            match: Match record

        Returns:
            True if update successful
        """
        transaction_id = match['ynab_transaction_id']
        amazon_data = match['amazon_data']

        # Log the update
        logger.info(
            f"Updating transaction {transaction_id[:10]}... "
            f"with Amazon order {match['amazon_order_id'][:10]}... "
            f"(confidence: {match['confidence']:.1f}%)"
        )

        # Update the memo
        success = self.ynab_service.update_transaction_memo(
            transaction_id=transaction_id,
            amazon_data=amazon_data,
            dry_run=self.dry_run
        )

        if success and not self.dry_run:
            # Optionally clear the transaction if configured
            if self.config.get('auto_clear_matched', False):
                self.ynab_service.mark_transaction_cleared(
                    transaction_id=transaction_id,
                    dry_run=self.dry_run
                )

            # Add flag for high-confidence matches
            if match['confidence'] >= 95:
                self.ynab_service.add_flag_to_transaction(
                    transaction_id=transaction_id,
                    flag_color='green',
                    dry_run=self.dry_run
                )
            elif match['confidence'] >= 85:
                self.ynab_service.add_flag_to_transaction(
                    transaction_id=transaction_id,
                    flag_color='yellow',
                    dry_run=self.dry_run
                )

        return success

    def batch_process_matches(
        self,
        matches: List[Dict],
        batch_size: int = 10
    ) -> Dict:
        """
        Process matches in batches for efficiency.

        Args:
            matches: List of match records
            batch_size: Number of updates per batch

        Returns:
            Processing statistics
        """
        total_batches = (len(matches) + batch_size - 1) // batch_size
        logger.info(f"Processing {len(matches)} matches in {total_batches} batches")

        results = {
            'batches_processed': 0,
            'total_successful': 0,
            'total_failed': 0,
            'batch_results': []
        }

        for i in range(0, len(matches), batch_size):
            batch = matches[i:i + batch_size]
            batch_num = i // batch_size + 1

            logger.info(f"Processing batch {batch_num}/{total_batches}")

            # Process batch
            batch_updates = []
            for match in batch:
                if not self._should_skip_update(match):
                    batch_updates.append({
                        'transaction_id': match['ynab_transaction_id'],
                        'amazon_data': match['amazon_data']
                    })

            # Apply batch updates
            if batch_updates:
                successful = self.ynab_service.batch_update_transactions(
                    updates=batch_updates,
                    dry_run=self.dry_run
                )

                results['total_successful'] += successful
                results['total_failed'] += len(batch_updates) - successful
            else:
                successful = 0

            results['batches_processed'] += 1
            results['batch_results'].append({
                'batch_num': batch_num,
                'matches_in_batch': len(batch),
                'updates_attempted': len(batch_updates),
                'successful': successful
            })

        return results

    def generate_reconciliation_summary(
        self,
        matches: List[Dict],
        unmatched_amazon: List[Dict],
        unmatched_ynab: List[Dict]
    ) -> Dict:
        """
        Generate a comprehensive reconciliation summary.

        Args:
            matches: List of matched transactions
            unmatched_amazon: List of unmatched Amazon transactions
            unmatched_ynab: List of unmatched YNAB transactions

        Returns:
            Summary dictionary
        """
        summary = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': self.dry_run,
            'statistics': self.stats,
            'matches': {
                'total': len(matches),
                'high_confidence': sum(1 for m in matches if m['confidence'] >= 90),
                'medium_confidence': sum(1 for m in matches if 70 <= m['confidence'] < 90),
                'low_confidence': sum(1 for m in matches if m['confidence'] < 70),
                'total_amount': sum(m['amazon_total'] for m in matches)
            },
            'unmatched': {
                'amazon_count': len(unmatched_amazon),
                'amazon_total': sum(t['total'] for t in unmatched_amazon),
                'ynab_count': len(unmatched_ynab),
                'ynab_total': sum(t['amount'] for t in unmatched_ynab)
            }
        }

        # Add top categories
        if matches:
            categories = {}
            for match in matches:
                cat = match['amazon_data'].get('category', 'Unknown')
                categories[cat] = categories.get(cat, 0) + 1

            summary['top_categories'] = sorted(
                categories.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

        # Add date range
        all_dates = []
        if matches:
            all_dates.extend([m['amazon_date'] for m in matches])
        if unmatched_amazon:
            all_dates.extend([t['date'] for t in unmatched_amazon])

        if all_dates:
            summary['date_range'] = {
                'start': min(all_dates).isoformat(),
                'end': max(all_dates).isoformat()
            }

        return summary

    def validate_reconciliation(self, matches: List[Dict]) -> List[Dict]:
        """
        Validate reconciliation matches for potential issues.

        Args:
            matches: List of match records

        Returns:
            List of validation warnings
        """
        warnings = []

        for match in matches:
            # Check for large date differences
            if match['date_diff_days'] > 5:
                warnings.append({
                    'type': 'large_date_diff',
                    'transaction_id': match['ynab_transaction_id'],
                    'message': f"Date difference of {match['date_diff_days']} days",
                    'severity': 'medium'
                })

            # Check for amount differences
            if match['amount_diff_cents'] > 100:
                warnings.append({
                    'type': 'large_amount_diff',
                    'transaction_id': match['ynab_transaction_id'],
                    'message': f"Amount difference of ${match['amount_diff_cents']/100:.2f}",
                    'severity': 'high'
                })

            # Check for low confidence matches
            if match['confidence'] < 70:
                warnings.append({
                    'type': 'low_confidence',
                    'transaction_id': match['ynab_transaction_id'],
                    'message': f"Low confidence match ({match['confidence']:.1f}%)",
                    'severity': 'medium'
                })

        return warnings