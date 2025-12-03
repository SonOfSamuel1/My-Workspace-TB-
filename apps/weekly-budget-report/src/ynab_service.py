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

    # =========================================================================
    # Annual Budget Methods (Tiller-Style Dashboard)
    # =========================================================================

    def get_annual_transactions(
        self,
        budget_id: str,
        year: int
    ) -> List[Dict]:
        """Get all transactions for a specific year.

        Args:
            budget_id: ID of the budget
            year: Year to fetch transactions for (e.g., 2025)

        Returns:
            List of transaction dictionaries for the entire year
        """
        self.logger.info(f"Fetching annual transactions for {budget_id}, year {year}...")

        since_date = f"{year}-01-01"
        transactions = self.get_transactions(budget_id, since_date=since_date)

        # Filter to only include transactions from the specified year
        year_transactions = [
            txn for txn in transactions
            if txn['date'].startswith(str(year))
        ]

        self.logger.info(f"Found {len(year_transactions)} transactions for {year}")
        return year_transactions

    def get_monthly_budgets(
        self,
        budget_id: str,
        year: int
    ) -> Dict[str, Dict]:
        """Get budget data for each month of the year.

        Args:
            budget_id: ID of the budget
            year: Year to fetch budgets for

        Returns:
            Dictionary mapping month (YYYY-MM-01) to month budget data
        """
        self.logger.info(f"Fetching monthly budgets for {budget_id}, year {year}...")

        monthly_budgets = {}
        current_month = datetime.now().month
        current_year = datetime.now().year

        # Determine how many months to fetch
        if year == current_year:
            months_to_fetch = current_month
        elif year < current_year:
            months_to_fetch = 12
        else:
            # Future year - no data yet
            return {}

        for month in range(1, months_to_fetch + 1):
            month_str = f"{year}-{month:02d}-01"
            try:
                month_budget = self.get_month_budget(budget_id, month_str)
                monthly_budgets[month_str] = month_budget
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Could not fetch budget for {month_str}: {e}")
                continue

        self.logger.info(f"Fetched {len(monthly_budgets)} monthly budgets for {year}")
        return monthly_budgets

    def aggregate_annual_budget(
        self,
        monthly_budgets: Dict[str, Dict]
    ) -> Dict[str, Dict]:
        """Aggregate monthly budgets into annual totals by category.

        Args:
            monthly_budgets: Dictionary of month -> budget data

        Returns:
            Dictionary mapping category_id to annual budget info:
            {
                'category_id': {
                    'name': str,
                    'annual_budgeted': float,
                    'annual_activity': float,
                    'monthly_breakdown': {
                        'Jan': {'budgeted': float, 'activity': float},
                        ...
                    }
                }
            }
        """
        self.logger.info("Aggregating annual budget from monthly data...")

        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        annual_budget = {}

        for month_str, month_data in monthly_budgets.items():
            # Parse month index from date string
            month_idx = int(month_str.split('-')[1]) - 1
            month_name = month_names[month_idx]

            for category in month_data.get('categories', []):
                cat_id = category['id']
                cat_name = category.get('name', 'Unknown')

                if cat_id not in annual_budget:
                    annual_budget[cat_id] = {
                        'name': cat_name,
                        'annual_budgeted': 0,
                        'annual_activity': 0,
                        'monthly_breakdown': {m: {'budgeted': 0, 'activity': 0} for m in month_names}
                    }

                # Convert milliunits to dollars
                budgeted = category.get('budgeted', 0) / 1000.0
                activity = abs(category.get('activity', 0) / 1000.0)

                annual_budget[cat_id]['annual_budgeted'] += budgeted
                annual_budget[cat_id]['annual_activity'] += activity
                annual_budget[cat_id]['monthly_breakdown'][month_name] = {
                    'budgeted': budgeted,
                    'activity': activity
                }

        self.logger.info(f"Aggregated annual budget for {len(annual_budget)} categories")
        return annual_budget

    def get_budget_settings(self, budget_id: str) -> Dict:
        """Get budget settings including currency format and first month.

        Args:
            budget_id: ID of the budget

        Returns:
            Budget settings dictionary
        """
        self.logger.info(f"Fetching budget settings for {budget_id}...")
        budget = self.get_budget(budget_id)

        return {
            'name': budget.get('name'),
            'first_month': budget.get('first_month'),
            'last_month': budget.get('last_month'),
            'currency_format': budget.get('currency_format', {}),
            'date_format': budget.get('date_format', {})
        }
