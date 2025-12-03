"""
Batch Data Fetcher

Fetches all required YNAB data in minimal API calls (4-5 total).
This replaces the per-transaction API calls that caused rate limiting.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import Counter, defaultdict

from data_context import (
    BudgetDataContext,
    Transaction,
    CategoryInfo,
    AccountInfo,
    PayeeInfo
)

logger = logging.getLogger(__name__)


class BatchDataFetcher:
    """
    Fetches all YNAB data needed for transaction review in bulk.

    API Calls Made (4 total):
    1. GET /budgets/{id}/transactions?since_date={date} - All transactions
    2. GET /budgets/{id}/categories - All categories
    3. GET /budgets/{id}/accounts - All accounts
    4. GET /budgets/{id}/payees - All payees

    This replaces potentially 100+ API calls with just 4.
    """

    def __init__(self, ynab_service):
        """
        Initialize with existing YNAB service for API access.

        Args:
            ynab_service: YNABService instance with valid credentials
        """
        self.ynab = ynab_service
        self.budget_id = ynab_service.budget_id

    def fetch_complete_context(self, days_back: int = 365) -> BudgetDataContext:
        """
        Fetch ALL data needed for transaction review in one batch.

        This method makes exactly 4 API calls regardless of transaction count.

        Args:
            days_back: How many days of transaction history to fetch

        Returns:
            BudgetDataContext with all data and pre-computed analytics
        """
        if days_back == 0 or days_back >= 3650:
            logger.info("Fetching complete budget context (all time)...")
        else:
            logger.info(f"Fetching complete budget context (last {days_back} days)...")

        # Create context
        context = BudgetDataContext(budget_id=self.budget_id)

        # Fetch all data (4 API calls)
        logger.info("API Call 1/4: Fetching categories...")
        context.categories = self._fetch_categories()

        logger.info("API Call 2/4: Fetching accounts...")
        context.accounts = self._fetch_accounts()

        logger.info("API Call 3/4: Fetching payees...")
        context.payees = self._fetch_payees()

        logger.info("API Call 4/4: Fetching transactions...")
        context.all_transactions = self._fetch_all_transactions(days_back)

        # Build lookup maps (no API calls)
        logger.info("Building lookup maps...")
        context.build_lookup_maps()

        # Filter transactions (no API calls)
        logger.info("Filtering transactions...")
        context.filter_transactions()

        # Build payee-category histogram for suggestions (no API calls)
        logger.info("Building payee-category histogram...")
        context.payee_category_histogram = self._build_payee_category_histogram(
            context.all_transactions
        )

        logger.info(f"Context fetch complete:")
        logger.info(f"  - {len(context.all_transactions)} total transactions")
        logger.info(f"  - {len(context.uncategorized_transactions)} uncategorized")
        logger.info(f"  - {len(context.unapproved_transactions)} unapproved")
        logger.info(f"  - {len(context.categories)} categories")
        logger.info(f"  - {len(context.payees)} payees")
        logger.info(f"  - {len(context.payee_category_histogram)} payees with history")

        return context

    def _fetch_categories(self) -> Dict[str, CategoryInfo]:
        """Fetch all categories (1 API call)"""
        endpoint = f"/budgets/{self.budget_id}/categories"
        response = self.ynab._make_request('GET', endpoint)

        categories = {}
        for group in response.get('data', {}).get('category_groups', []):
            group_name = group.get('name', '')

            # Skip internal groups
            if group_name in ('Internal Master Category', 'Hidden Categories'):
                continue

            for category in group.get('categories', []):
                cat_id = category['id']
                categories[cat_id] = CategoryInfo(
                    id=cat_id,
                    name=category['name'],
                    group_name=group_name,
                    hidden=category.get('hidden', False)
                )

        return categories

    def _fetch_accounts(self) -> Dict[str, AccountInfo]:
        """Fetch all accounts (1 API call)"""
        endpoint = f"/budgets/{self.budget_id}/accounts"
        response = self.ynab._make_request('GET', endpoint)

        accounts = {}
        for account in response.get('data', {}).get('accounts', []):
            acc_id = account['id']
            accounts[acc_id] = AccountInfo(
                id=acc_id,
                name=account['name'],
                type=account.get('type', 'unknown'),
                closed=account.get('closed', False),
                on_budget=account.get('on_budget', True)
            )

        return accounts

    def _fetch_payees(self) -> Dict[str, PayeeInfo]:
        """Fetch all payees (1 API call)"""
        endpoint = f"/budgets/{self.budget_id}/payees"
        response = self.ynab._make_request('GET', endpoint)

        payees = {}
        for payee in response.get('data', {}).get('payees', []):
            payee_id = payee['id']
            payees[payee_id] = PayeeInfo(
                id=payee_id,
                name=payee.get('name', '')
            )

        return payees

    def _fetch_all_transactions(self, days_back: int) -> List[Transaction]:
        """
        Fetch all transactions for the budget (1 API call).

        This single call replaces N per-payee API calls.

        Args:
            days_back: How many days to look back. If 0 or >= 3650, fetches ALL transactions.
        """
        if days_back == 0 or days_back >= 3650:
            # Fetch ALL transactions (no date filter)
            endpoint = f"/budgets/{self.budget_id}/transactions"
        else:
            since_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            endpoint = f"/budgets/{self.budget_id}/transactions?since_date={since_date}"
        response = self.ynab._make_request('GET', endpoint)

        transactions = []
        for txn in response.get('data', {}).get('transactions', []):
            # Skip deleted transactions
            if txn.get('deleted', False):
                continue

            transactions.append(Transaction(
                id=txn['id'],
                date=txn['date'],
                amount=txn['amount'] / 1000.0,  # Convert milliunits to dollars
                payee_id=txn.get('payee_id'),
                payee_name=txn.get('payee_name'),
                category_id=txn.get('category_id'),
                category_name=txn.get('category_name'),
                account_id=txn['account_id'],
                account_name=txn.get('account_name', 'Unknown'),
                memo=txn.get('memo'),
                cleared=txn.get('cleared', 'uncleared'),
                approved=txn.get('approved', False),
                flag_color=txn.get('flag_color'),
                transfer_account_id=txn.get('transfer_account_id'),
                subtransactions=txn.get('subtransactions', [])
            ))

        return transactions

    def _build_payee_category_histogram(
        self,
        transactions: List[Transaction]
    ) -> Dict[str, Counter]:
        """
        Build payee -> category frequency map from ALL transactions.

        This pre-computation REPLACES the per-payee API calls in
        get_transaction_history_for_payee() that caused rate limiting.

        Args:
            transactions: List of all transactions

        Returns:
            Dict mapping payee_name (lowercase) to Counter of category_ids
        """
        histogram = defaultdict(Counter)

        for txn in transactions:
            # Only count transactions that have both payee and category
            if txn.payee_name and txn.category_id:
                # Skip transfers and special categories
                if txn.is_transfer:
                    continue
                if txn.category_id in ('immediate-income-subcategory', 'Ready to Assign'):
                    continue

                payee_lower = txn.payee_name.lower()
                histogram[payee_lower][txn.category_id] += 1

        return dict(histogram)

    def get_historical_category_for_payee(
        self,
        context: BudgetDataContext,
        payee_name: str
    ) -> Optional[Dict]:
        """
        Get the most commonly used category for a payee.

        Uses pre-computed histogram instead of API call.

        Args:
            context: BudgetDataContext with payee_category_histogram
            payee_name: Name of the payee to look up

        Returns:
            Dict with category_id, category_name, count, confidence or None
        """
        payee_lower = payee_name.lower()

        histogram = context.payee_category_histogram.get(payee_lower)
        if not histogram:
            return None

        # Get most common category
        most_common = histogram.most_common(1)
        if not most_common:
            return None

        category_id, count = most_common[0]
        total = sum(histogram.values())

        # Calculate confidence based on consistency
        confidence = min(90, (count / total) * 100)

        # Get category name from context
        category_name = context.get_category_name(category_id) or 'Unknown'

        return {
            'category_id': category_id,
            'category_name': category_name,
            'count': count,
            'total': total,
            'confidence': confidence
        }
