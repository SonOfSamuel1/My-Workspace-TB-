"""
Email Receipt Reconciler

Matches YNAB transactions with email receipts from Gmail and mail.com,
then updates YNAB memos with clickable email links.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ynab_service import YNABService
from general_email_matcher import GeneralEmailMatcher
from multi_account_email_service import MultiAccountEmailService

logger = logging.getLogger(__name__)


class EmailReceiptReconciler:
    """
    Orchestrates email receipt matching for YNAB transactions.

    Workflow:
    1. Fetch pending (unapproved/uncleared) YNAB transactions
    2. For each transaction, search emails for matching receipt
    3. Update YNAB memo with email link
    4. Apply flag based on email source (purple=mail.com, blue=Gmail)
    """

    def __init__(
        self,
        ynab_config: Dict,
        email_config_path: str = '../config.yaml',
        dry_run: bool = False
    ):
        """
        Initialize the email receipt reconciler.

        Args:
            ynab_config: YNAB configuration dict
            email_config_path: Path to config.yaml with email settings
            dry_run: If True, don't make actual updates
        """
        self.dry_run = dry_run

        # Initialize YNAB service
        self.ynab_service = YNABService(ynab_config)

        # Initialize email service
        self.email_service = MultiAccountEmailService(config_path=email_config_path)

        # Initialize email matcher
        self.email_matcher = GeneralEmailMatcher(self.email_service)

        # Stats
        self.stats = {
            'transactions_processed': 0,
            'emails_matched': 0,
            'memos_updated': 0,
            'flags_applied': 0,
            'errors': 0
        }

    def run(self, lookback_days: int = 30) -> Dict:
        """
        Run email receipt reconciliation.

        Args:
            lookback_days: Number of days to look back for transactions

        Returns:
            Dict with results summary
        """
        logger.info(f"Starting email receipt reconciliation (lookback: {lookback_days} days)")

        # Reset stats
        self.stats = {
            'transactions_processed': 0,
            'emails_matched': 0,
            'memos_updated': 0,
            'flags_applied': 0,
            'errors': 0
        }

        results = {
            'matches': [],
            'unmatched': [],
            'errors': []
        }

        try:
            # Validate YNAB connection
            if not self.ynab_service.validate_connection():
                raise Exception("YNAB connection failed")

            # Fetch pending transactions
            since_date = datetime.now() - timedelta(days=lookback_days)
            transactions = self.ynab_service.get_pending_transactions(since_date)

            logger.info(f"Found {len(transactions)} pending transactions to process")

            # Process each transaction
            for txn in transactions:
                self.stats['transactions_processed'] += 1

                try:
                    match_result = self._process_transaction(txn)

                    if match_result['matched']:
                        results['matches'].append(match_result)
                    else:
                        results['unmatched'].append(match_result)

                except Exception as e:
                    logger.error(f"Error processing transaction {txn['id']}: {e}")
                    self.stats['errors'] += 1
                    results['errors'].append({
                        'transaction': txn,
                        'error': str(e)
                    })

            # Close email connections
            self.email_service.close_all()

        except Exception as e:
            logger.error(f"Email receipt reconciliation failed: {e}")
            self.stats['errors'] += 1
            results['errors'].append({'error': str(e)})

        # Add stats to results
        results['stats'] = self.stats

        logger.info(
            f"Reconciliation complete: {self.stats['emails_matched']} matches, "
            f"{self.stats['memos_updated']} memos updated"
        )

        return results

    def _process_transaction(self, txn: Dict) -> Dict:
        """
        Process a single transaction - search for email and update memo.

        Args:
            txn: YNAB transaction dict

        Returns:
            Dict with match result
        """
        payee_name = txn.get('payee_name', '')
        amount = txn.get('amount', 0)
        txn_date = txn.get('date')

        result = {
            'transaction_id': txn['id'],
            'payee_name': payee_name,
            'amount': amount,
            'date': txn_date,
            'account_name': txn.get('account_name', ''),
            'matched': False,
            'email_data': None,
            'memo_updated': False,
            'flag_applied': False
        }

        # Skip transactions without payee
        if not payee_name:
            return result

        # Skip very small transactions (under $1)
        if amount < 1.0:
            return result

        # Skip if memo already has email link (disabled to force re-processing with new format)
        # existing_memo = txn.get('memo', '')
        # if existing_memo and ('mail.google.com' in existing_memo or 'Mail.com' in existing_memo):
        #     logger.debug(f"Skipping {payee_name} - already has email link in memo")
        #     return result

        # Search for matching email
        email_match = self.email_matcher.find_receipt_email(
            payee_name=payee_name,
            amount=amount,
            txn_date=txn_date,
            days_tolerance=7
        )

        if email_match:
            result['matched'] = True
            result['email_data'] = email_match
            self.stats['emails_matched'] += 1

            # Update memo with email link (pass payee_name to avoid extra API call)
            memo_updated = self.ynab_service.update_transaction_with_email_link(
                transaction_id=txn['id'],
                email_data=email_match,
                payee_name=txn.get('payee_name', ''),
                dry_run=self.dry_run
            )

            if memo_updated:
                result['memo_updated'] = True
                self.stats['memos_updated'] += 1

                # Apply flag based on source account
                if not self.dry_run:
                    flag_applied = self._apply_source_flag(
                        transaction_id=txn['id'],
                        source_account=email_match.get('source_account', '')
                    )
                    if flag_applied:
                        result['flag_applied'] = True
                        self.stats['flags_applied'] += 1

        return result

    def _apply_source_flag(self, transaction_id: str, source_account: str) -> bool:
        """
        Apply flag color based on email source account.

        Args:
            transaction_id: YNAB transaction ID
            source_account: Email source account name

        Returns:
            True if flag applied successfully
        """
        source_lower = source_account.lower()

        if 'brittany' in source_lower or 'mail.com' in source_lower:
            # Purple for Brittany's mail.com account
            return self.ynab_service.add_flag_to_transaction(
                transaction_id=transaction_id,
                flag_color='purple',
                dry_run=self.dry_run
            )
        else:
            # Blue for Gmail accounts
            return self.ynab_service.add_flag_to_transaction(
                transaction_id=transaction_id,
                flag_color='blue',
                dry_run=self.dry_run
            )

    def get_summary_report(self, results: Dict) -> str:
        """
        Generate a human-readable summary report.

        Args:
            results: Results from run()

        Returns:
            Formatted summary string
        """
        stats = results.get('stats', {})
        matches = results.get('matches', [])

        lines = [
            "=" * 50,
            "Email Receipt Reconciliation Report",
            "=" * 50,
            "",
            f"Transactions Processed: {stats.get('transactions_processed', 0)}",
            f"Email Matches Found:    {stats.get('emails_matched', 0)}",
            f"Memos Updated:          {stats.get('memos_updated', 0)}",
            f"Flags Applied:          {stats.get('flags_applied', 0)}",
            f"Errors:                 {stats.get('errors', 0)}",
            "",
        ]

        if matches:
            lines.append("Matches:")
            lines.append("-" * 40)
            for match in matches[:10]:  # Show first 10
                payee = match.get('payee_name', 'Unknown')[:20]
                amount = match.get('amount', 0)
                email_src = match.get('email_data', {}).get('source_account', 'Unknown')
                lines.append(f"  ${amount:.2f} {payee} <- {email_src}")

            if len(matches) > 10:
                lines.append(f"  ... and {len(matches) - 10} more")

        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)


def main():
    """Run email receipt reconciler from command line."""
    import argparse

    parser = argparse.ArgumentParser(description='Email Receipt Reconciler')
    parser.add_argument('--days', type=int, default=30,
                        help='Number of days to look back (default: 30)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without making updates')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose logging')

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load YNAB config
    ynab_config = {
        'budget_name': "Terrance Brandon's Plan",
        'account_names': [],  # Empty = all accounts
        'only_uncleared': False  # We want pending transactions
    }

    # Run reconciler
    reconciler = EmailReceiptReconciler(
        ynab_config=ynab_config,
        email_config_path='../config.yaml',
        dry_run=args.dry_run
    )

    results = reconciler.run(lookback_days=args.days)

    # Print summary
    print(reconciler.get_summary_report(results))


if __name__ == '__main__':
    main()
