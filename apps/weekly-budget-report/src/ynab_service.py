"""
YNAB API Service Client

Provides methods for interacting with the YNAB API to fetch
budget data, transactions, categories, and account information.
"""
import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


class YNABService:
    """Service for interacting with YNAB API."""

    BASE_URL = "https://api.ynab.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize YNAB service.

        Args:
            api_key: YNAB API key. If not provided, reads from YNAB_API_KEY env var
        """
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key or os.getenv('YNAB_API_KEY')

        if not self.api_key:
            raise ValueError("YNAB API key is required. Set YNAB_API_KEY environment variable.")

        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to YNAB API.

        Args:
            endpoint: API endpoint (e.g., '/budgets')
            params: Optional query parameters

        Returns:
            Response data dictionary
        """
        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()['data']
        except requests.exceptions.RequestException as e:
            self.logger.error(f"YNAB API request failed: {e}")
            raise

    def get_budgets(self) -> List[Dict]:
        """Get all budgets for the authenticated user.

        Returns:
            List of budget dictionaries
        """
        self.logger.info("Fetching YNAB budgets...")
        data = self._make_request('/budgets')
        return data['budgets']

    def get_budget(self, budget_id: str) -> Dict:
        """Get detailed budget information.

        Args:
            budget_id: ID of the budget

        Returns:
            Budget details dictionary
        """
        self.logger.info(f"Fetching budget details for {budget_id}...")
        data = self._make_request(f'/budgets/{budget_id}')
        return data['budget']

    def get_accounts(self, budget_id: str) -> List[Dict]:
        """Get all accounts for a budget.

        Args:
            budget_id: ID of the budget

        Returns:
            List of account dictionaries
        """
        self.logger.info(f"Fetching accounts for budget {budget_id}...")
        data = self._make_request(f'/budgets/{budget_id}/accounts')
        return data['accounts']

    def get_categories(self, budget_id: str) -> List[Dict]:
        """Get all categories for a budget.

        Args:
            budget_id: ID of the budget

        Returns:
            List of category group dictionaries
        """
        self.logger.info(f"Fetching categories for budget {budget_id}...")
        data = self._make_request(f'/budgets/{budget_id}/categories')
        return data['category_groups']

    def get_transactions(
        self,
        budget_id: str,
        since_date: Optional[str] = None,
        account_id: Optional[str] = None
    ) -> List[Dict]:
        """Get transactions for a budget.

        Args:
            budget_id: ID of the budget
            since_date: Optional ISO date string (YYYY-MM-DD) to fetch transactions from
            account_id: Optional account ID to filter transactions

        Returns:
            List of transaction dictionaries
        """
        self.logger.info(f"Fetching transactions for budget {budget_id}...")

        params = {}
        if since_date:
            params['since_date'] = since_date

        if account_id:
            endpoint = f'/budgets/{budget_id}/accounts/{account_id}/transactions'
        else:
            endpoint = f'/budgets/{budget_id}/transactions'

        data = self._make_request(endpoint, params=params)
        return data['transactions']

    def get_month_budget(self, budget_id: str, month: str) -> Dict:
        """Get budget data for a specific month.

        Args:
            budget_id: ID of the budget
            month: Month in ISO format (YYYY-MM-DD, typically first of month)

        Returns:
            Month budget dictionary
        """
        self.logger.info(f"Fetching month budget for {budget_id}, month {month}...")
        data = self._make_request(f'/budgets/{budget_id}/months/{month}')
        return data['month']

    def get_payees(self, budget_id: str) -> List[Dict]:
        """Get all payees for a budget.

        Args:
            budget_id: ID of the budget

        Returns:
            List of payee dictionaries
        """
        self.logger.info(f"Fetching payees for budget {budget_id}...")
        data = self._make_request(f'/budgets/{budget_id}/payees')
        return data['payees']

    def validate_credentials(self) -> bool:
        """Validate YNAB API credentials.

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            self._make_request('/user')
            self.logger.info("YNAB credentials validated successfully")
            return True
        except Exception as e:
            self.logger.error(f"YNAB credentials validation failed: {e}")
            return False

    def milliunits_to_dollars(self, milliunits: int) -> float:
        """Convert YNAB milliunits to dollars.

        YNAB uses milliunits where 1000 = $1.00

        Args:
            milliunits: Amount in milliunits

        Returns:
            Amount in dollars
        """
        return milliunits / 1000.0

    def dollars_to_milliunits(self, dollars: float) -> int:
        """Convert dollars to YNAB milliunits.

        Args:
            dollars: Amount in dollars

        Returns:
            Amount in milliunits
        """
        return int(dollars * 1000)
