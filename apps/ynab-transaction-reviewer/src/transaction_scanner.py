"""
Transaction Scanner Module

Fetches and processes uncategorized transactions from YNAB,
tracking review state to avoid duplicate notifications.
"""

import json
import logging
from typing import List, Dict, Set, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import asdict

from ynab_service import YNABService, Transaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TransactionScanner:
    """Scans for uncategorized transactions and manages review state"""

    def __init__(self, ynab_service: YNABService, state_file: str = None):
        """
        Initialize transaction scanner

        Args:
            ynab_service: YNAB service instance
            state_file: Path to state file for tracking reviewed transactions
        """
        self.ynab = ynab_service
        self.state_file = state_file or 'data/review_state.json'
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load review state from file"""
        state_path = Path(self.state_file)
        if state_path.exists():
            try:
                with open(state_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load state file: {e}")

        # Default state structure
        return {
            'reviewed_transactions': {},  # txn_id: review_date
            'pending_review': {},  # txn_id: first_seen_date
            'categorization_history': [],  # List of categorization events
            'last_scan': None
        }

    def _save_state(self):
        """Save review state to file"""
        state_path = Path(self.state_file)
        state_path.parent.mkdir(parents=True, exist_ok=True)

        with open(state_path, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)

    def scan_for_uncategorized(self,
                              days_back: int = 30,
                              include_pending: bool = True,
                              skip_reviewed: bool = True) -> List[Transaction]:
        """
        Scan for uncategorized transactions

        Args:
            days_back: Number of days to look back
            include_pending: Include unapproved transactions
            skip_reviewed: Skip transactions already sent for review

        Returns:
            List of uncategorized transactions needing review
        """
        logger.info(f"Scanning for uncategorized transactions (last {days_back} days)")

        # Get uncategorized transactions from YNAB
        transactions = self.ynab.get_uncategorized_transactions(
            days_back=days_back,
            include_pending=include_pending
        )

        # Filter out already reviewed if requested
        if skip_reviewed:
            transactions = self._filter_reviewed(transactions)

        # Update pending review state
        for txn in transactions:
            if txn.id not in self.state['pending_review']:
                self.state['pending_review'][txn.id] = datetime.now().isoformat()

        # Update last scan time
        self.state['last_scan'] = datetime.now().isoformat()
        self._save_state()

        # Group by account for better organization
        grouped = self._group_by_account(transactions)

        logger.info(f"Found {len(transactions)} transactions needing review across {len(grouped)} accounts")
        return transactions

    def _filter_reviewed(self, transactions: List[Transaction]) -> List[Transaction]:
        """Filter out transactions that have already been reviewed"""
        # Clean up old reviewed transactions (older than 90 days)
        cutoff_date = datetime.now() - timedelta(days=90)
        reviewed_copy = dict(self.state['reviewed_transactions'])

        for txn_id, review_date in reviewed_copy.items():
            if isinstance(review_date, str):
                review_dt = datetime.fromisoformat(review_date)
            else:
                review_dt = review_date

            if review_dt < cutoff_date:
                del self.state['reviewed_transactions'][txn_id]

        # Filter transactions
        unreviewed = []
        for txn in transactions:
            if txn.id not in self.state['reviewed_transactions']:
                unreviewed.append(txn)

        logger.info(f"Filtered {len(transactions) - len(unreviewed)} already reviewed transactions")
        return unreviewed

    def _group_by_account(self, transactions: List[Transaction]) -> Dict[str, List[Transaction]]:
        """Group transactions by account"""
        grouped = {}
        for txn in transactions:
            if txn.account_name not in grouped:
                grouped[txn.account_name] = []
            grouped[txn.account_name].append(txn)

        return grouped

    def mark_as_reviewed(self, transaction_ids: List[str]):
        """Mark transactions as reviewed"""
        for txn_id in transaction_ids:
            self.state['reviewed_transactions'][txn_id] = datetime.now().isoformat()
            if txn_id in self.state['pending_review']:
                del self.state['pending_review'][txn_id]

        self._save_state()
        logger.info(f"Marked {len(transaction_ids)} transactions as reviewed")

    def record_categorization(self, transaction_id: str, category_name: str, confidence: float = None):
        """Record a categorization event for learning"""
        event = {
            'transaction_id': transaction_id,
            'category_name': category_name,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        }

        self.state['categorization_history'].append(event)

        # Keep only last 1000 events
        if len(self.state['categorization_history']) > 1000:
            self.state['categorization_history'] = self.state['categorization_history'][-1000:]

        self._save_state()

    def get_pending_count(self) -> int:
        """Get count of transactions pending review"""
        return len(self.state['pending_review'])

    def get_oldest_pending(self) -> Optional[datetime]:
        """Get date of oldest pending transaction"""
        if not self.state['pending_review']:
            return None

        oldest_date = min(self.state['pending_review'].values())
        if isinstance(oldest_date, str):
            return datetime.fromisoformat(oldest_date)
        return oldest_date

    def get_statistics(self) -> Dict:
        """Get scanner statistics"""
        stats = {
            'total_reviewed': len(self.state['reviewed_transactions']),
            'pending_review': len(self.state['pending_review']),
            'categorizations_recorded': len(self.state['categorization_history']),
            'last_scan': self.state['last_scan']
        }

        # Add oldest pending if exists
        oldest = self.get_oldest_pending()
        if oldest:
            stats['oldest_pending_days'] = (datetime.now() - oldest).days

        return stats

    def should_include_saturday_transactions(self) -> bool:
        """
        Check if today is Sunday and we should include Saturday transactions

        Returns:
            True if it's Sunday and we should include Saturday's transactions
        """
        today = datetime.now()
        return today.weekday() == 6  # Sunday is 6

    def get_transactions_by_date_range(self,
                                      include_saturday: bool = False) -> List[Transaction]:
        """
        Get transactions for daily review, optionally including Saturday's

        Args:
            include_saturday: Whether to include Saturday transactions (for Sunday)

        Returns:
            List of transactions for review
        """
        if include_saturday and self.should_include_saturday_transactions():
            # Get last 2 days (Saturday and Sunday)
            days_back = 2
        else:
            # Get just today
            days_back = 1

        return self.scan_for_uncategorized(days_back=days_back)

    def cleanup_old_state(self, days_to_keep: int = 90):
        """Clean up old state data"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        # Clean reviewed transactions
        reviewed_copy = dict(self.state['reviewed_transactions'])
        for txn_id, review_date in reviewed_copy.items():
            if isinstance(review_date, str):
                review_dt = datetime.fromisoformat(review_date)
            else:
                review_dt = review_date

            if review_dt < cutoff_date:
                del self.state['reviewed_transactions'][txn_id]

        # Clean pending review (remove very old pending)
        pending_copy = dict(self.state['pending_review'])
        for txn_id, first_seen in pending_copy.items():
            if isinstance(first_seen, str):
                seen_dt = datetime.fromisoformat(first_seen)
            else:
                seen_dt = first_seen

            # Remove if pending for more than 30 days
            if seen_dt < (datetime.now() - timedelta(days=30)):
                del self.state['pending_review'][txn_id]

        self._save_state()
        logger.info("Cleaned up old state data")

    def scan_for_unapproved(self, days_back: int = 30) -> List[Transaction]:
        """
        Scan for transactions needing approval

        Args:
            days_back: Number of days to look back

        Returns:
            List of unapproved transactions
        """
        logger.info(f"Scanning for unapproved transactions (last {days_back} days)")

        # Get unapproved transactions from YNAB
        transactions = self.ynab.get_unapproved_transactions(days_back=days_back)

        # Group by account for logging
        grouped = self._group_by_account(transactions)

        logger.info(f"Found {len(transactions)} unapproved transactions across {len(grouped)} accounts")
        return transactions