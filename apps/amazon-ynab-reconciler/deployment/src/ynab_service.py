"""
YNAB service for fetching and updating transactions.
Interfaces with YNAB API for transaction management.
"""

import os
import logging
import requests
from datetime import datetime, date
from typing import List, Dict, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


class YNABService:
    """Service for interacting with YNAB API."""

    def __init__(self, config: Dict):
        """Initialize YNAB service with configuration."""
        self.config = config
        self.api_key = os.getenv('YNAB_API_KEY')
        self.base_url = 'https://api.ynab.com/v1'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        self.budget_name = config.get('budget_name', 'Main Budget')
        self.budget_id = os.getenv('YNAB_BUDGET_ID')
        self.account_names = config.get('account_names', [])
        self.only_uncleared = config.get('only_uncleared', True)
        self.memo_format = config.get('memo_format', '[Amazon: {category}] | {item_name} | {item_link}')
        self.preserve_existing_memo = config.get('preserve_existing_memo', True)

        # Cache for budget and account data
        self._budget_cache = None
        self._accounts_cache = None

    def validate_connection(self) -> bool:
        """Validate YNAB API connection."""
        if not self.api_key:
            logger.error("YNAB API key not configured")
            return False

        try:
            response = requests.get(
                f"{self.base_url}/user",
                headers=self.headers
            )
            response.raise_for_status()
            logger.info("YNAB connection validated successfully")
            return True
        except Exception as e:
            logger.error(f"YNAB connection validation failed: {str(e)}")
            return False

    def get_budget_id(self) -> str:
        """Get budget ID by name or use configured ID."""
        if self.budget_id:
            return self.budget_id

        if not self._budget_cache:
            response = requests.get(
                f"{self.base_url}/budgets",
                headers=self.headers
            )
            response.raise_for_status()
            self._budget_cache = response.json()['data']['budgets']

        # Find budget by name
        for budget in self._budget_cache:
            if budget['name'] == self.budget_name:
                self.budget_id = budget['id']
                return self.budget_id

        # Use first budget if name not found
        if self._budget_cache:
            self.budget_id = self._budget_cache[0]['id']
            logger.warning(f"Budget '{self.budget_name}' not found, using '{self._budget_cache[0]['name']}'")
            return self.budget_id

        raise ValueError("No budgets found in YNAB")

    def get_account_ids(self) -> List[str]:
        """Get account IDs for configured account names."""
        budget_id = self.get_budget_id()

        if not self._accounts_cache:
            response = requests.get(
                f"{self.base_url}/budgets/{budget_id}/accounts",
                headers=self.headers
            )
            response.raise_for_status()
            self._accounts_cache = response.json()['data']['accounts']

        account_ids = []
        for account in self._accounts_cache:
            if account['name'] in self.account_names and not account['closed']:
                account_ids.append(account['id'])

        if not account_ids and self._accounts_cache:
            # Use all open accounts if none specified
            account_ids = [
                acc['id'] for acc in self._accounts_cache
                if not acc['closed'] and acc['type'] in ['creditCard', 'checking']
            ]

        return account_ids

    def get_transactions(
        self,
        since_date: datetime,
        account_names: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Fetch transactions from YNAB.

        Args:
            since_date: Start date for transactions
            account_names: Optional list of account names to filter

        Returns:
            List of transaction dictionaries
        """
        budget_id = self.get_budget_id()

        # Override account names if provided
        if account_names:
            self.account_names = account_names

        account_ids = self.get_account_ids()

        all_transactions = []

        for account_id in account_ids:
            params = {
                'since_date': since_date.strftime('%Y-%m-%d')
            }

            response = requests.get(
                f"{self.base_url}/budgets/{budget_id}/accounts/{account_id}/transactions",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()

            transactions = response.json()['data']['transactions']

            for txn in transactions:
                # Filter by cleared status if configured
                if self.only_uncleared and txn['cleared'] == 'cleared':
                    continue

                # Convert milliunits to dollars
                amount = abs(txn['amount']) / 1000.0

                # Parse date
                txn_date = datetime.strptime(txn['date'], '%Y-%m-%d')

                transaction = {
                    'id': txn['id'],
                    'date': txn_date,
                    'amount': amount,
                    'payee_name': txn.get('payee_name', ''),
                    'category_name': self._get_category_name(budget_id, txn.get('category_id')),
                    'memo': txn.get('memo', ''),
                    'cleared': txn['cleared'],
                    'account_id': account_id,
                    'account_name': self._get_account_name(account_id),
                    'import_id': txn.get('import_id'),
                    'flag_color': txn.get('flag_color')
                }

                all_transactions.append(transaction)

        logger.info(f"Fetched {len(all_transactions)} transactions from YNAB")
        return all_transactions

    def update_transaction_memo(
        self,
        transaction_id: str,
        amazon_data: Dict,
        dry_run: bool = False
    ) -> bool:
        """
        Update a YNAB transaction memo with Amazon data.

        Args:
            transaction_id: YNAB transaction ID
            amazon_data: Dictionary with Amazon item details
            dry_run: If True, don't actually update

        Returns:
            True if update successful
        """
        budget_id = self.get_budget_id()

        # Get existing transaction to preserve data
        response = requests.get(
            f"{self.base_url}/budgets/{budget_id}/transactions/{transaction_id}",
            headers=self.headers
        )
        response.raise_for_status()
        existing_txn = response.json()['data']['transaction']

        # Format new memo
        new_memo = self.memo_format.format(
            category=amazon_data.get('category', 'Unknown'),
            item_name=amazon_data.get('item_name', 'Amazon Purchase'),
            item_link=amazon_data.get('item_link', '')
        )

        # Preserve existing memo if configured
        if self.preserve_existing_memo and existing_txn.get('memo'):
            existing_memo = existing_txn['memo']
            # Don't duplicate if already reconciled
            if 'Amazon:' not in existing_memo:
                new_memo = f"{new_memo} | {existing_memo}"

        # Add reconciliation timestamp
        new_memo += f" | Reconciled: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Truncate if too long (YNAB limit is 200 chars)
        if len(new_memo) > 200:
            new_memo = new_memo[:197] + "..."

        if dry_run:
            logger.info(f"DRY RUN: Would update transaction {transaction_id} with memo: {new_memo}")
            return True

        # Update transaction
        update_data = {
            'transaction': {
                'memo': new_memo
            }
        }

        try:
            response = requests.patch(
                f"{self.base_url}/budgets/{budget_id}/transactions/{transaction_id}",
                headers=self.headers,
                json=update_data
            )
            response.raise_for_status()
            logger.info(f"Updated transaction {transaction_id} with Amazon data")
            return True

        except Exception as e:
            logger.error(f"Failed to update transaction {transaction_id}: {str(e)}")
            return False

    def batch_update_transactions(
        self,
        updates: List[Dict],
        dry_run: bool = False
    ) -> int:
        """
        Batch update multiple transactions.

        Args:
            updates: List of update dictionaries with transaction_id and amazon_data
            dry_run: If True, don't actually update

        Returns:
            Number of successful updates
        """
        successful = 0

        for update in updates:
            if self.update_transaction_memo(
                transaction_id=update['transaction_id'],
                amazon_data=update['amazon_data'],
                dry_run=dry_run
            ):
                successful += 1

        return successful

    def _get_category_name(self, budget_id: str, category_id: Optional[str]) -> str:
        """Get category name by ID."""
        if not category_id:
            return 'Uncategorized'

        try:
            response = requests.get(
                f"{self.base_url}/budgets/{budget_id}/categories/{category_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()['data']['category']['name']
        except:
            return 'Unknown'

    def _get_account_name(self, account_id: str) -> str:
        """Get account name by ID."""
        if self._accounts_cache:
            for account in self._accounts_cache:
                if account['id'] == account_id:
                    return account['name']
        return 'Unknown Account'

    def mark_transaction_cleared(
        self,
        transaction_id: str,
        dry_run: bool = False
    ) -> bool:
        """
        Mark a transaction as cleared.

        Args:
            transaction_id: YNAB transaction ID
            dry_run: If True, don't actually update

        Returns:
            True if successful
        """
        if dry_run:
            logger.info(f"DRY RUN: Would mark transaction {transaction_id} as cleared")
            return True

        budget_id = self.get_budget_id()

        update_data = {
            'transaction': {
                'cleared': 'cleared'
            }
        }

        try:
            response = requests.patch(
                f"{self.base_url}/budgets/{budget_id}/transactions/{transaction_id}",
                headers=self.headers,
                json=update_data
            )
            response.raise_for_status()
            logger.info(f"Marked transaction {transaction_id} as cleared")
            return True

        except Exception as e:
            logger.error(f"Failed to clear transaction {transaction_id}: {str(e)}")
            return False

    def add_flag_to_transaction(
        self,
        transaction_id: str,
        flag_color: str,
        dry_run: bool = False
    ) -> bool:
        """
        Add a flag color to a transaction.

        Args:
            transaction_id: YNAB transaction ID
            flag_color: Color name (red, orange, yellow, green, blue, purple)
            dry_run: If True, don't actually update

        Returns:
            True if successful
        """
        if dry_run:
            logger.info(f"DRY RUN: Would add {flag_color} flag to transaction {transaction_id}")
            return True

        budget_id = self.get_budget_id()

        update_data = {
            'transaction': {
                'flag_color': flag_color
            }
        }

        try:
            response = requests.patch(
                f"{self.base_url}/budgets/{budget_id}/transactions/{transaction_id}",
                headers=self.headers,
                json=update_data
            )
            response.raise_for_status()
            logger.info(f"Added {flag_color} flag to transaction {transaction_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to flag transaction {transaction_id}: {str(e)}")
            return False