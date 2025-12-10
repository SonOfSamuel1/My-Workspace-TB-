"""
YNAB API Service for Transaction Review System

Handles all interactions with YNAB API including fetching uncategorized transactions,
updating categories, and managing split transactions.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import cache service (optional - won't fail if not in Lambda)
try:
    from cache_service import get_cache, CacheService
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Transaction:
    """Represents a YNAB transaction with all relevant fields"""
    id: str
    date: str
    amount: float  # In dollars (converted from milliunits)
    payee_name: str
    payee_id: Optional[str]
    category_name: Optional[str]
    category_id: Optional[str]
    account_name: str
    account_id: str
    memo: Optional[str]
    cleared: str
    approved: bool
    flag_color: Optional[str]
    import_id: Optional[str]
    subtransactions: List[Dict] = None

    def __post_init__(self):
        if self.subtransactions is None:
            self.subtransactions = []

    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            'id': self.id,
            'date': self.date,
            'amount': self.amount,
            'payee_name': self.payee_name,
            'category_name': self.category_name,
            'account_name': self.account_name,
            'memo': self.memo,
            'cleared': self.cleared,
            'subtransactions': self.subtransactions
        }


class YNABService:
    """Service class for interacting with YNAB API"""

    BASE_URL = "https://api.ynab.com/v1"

    def __init__(self, api_key: str = None, budget_id: str = None, use_cache: bool = True):
        """
        Initialize YNAB service

        Args:
            api_key: YNAB personal access token
            budget_id: Optional budget ID (uses first budget if not specified)
            use_cache: Whether to use S3 caching (default: True)
        """
        self.api_key = api_key or os.getenv('YNAB_API_KEY')
        if not self.api_key:
            raise ValueError("YNAB API key is required")

        self.budget_id = budget_id or os.getenv('YNAB_BUDGET_ID')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        # Setup session with retry logic (with exponential backoff for rate limits)
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,  # Increased backoff factor
            status_forcelist=[500, 502, 503, 504],  # Removed 429 from auto-retry
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # S3 cache service
        self._use_cache = use_cache and CACHE_AVAILABLE
        self._cache = get_cache() if self._use_cache else None
        if self._use_cache:
            logger.info("S3 caching enabled for YNAB API responses")

        # In-memory cache for budget data (populated from S3 or API)
        self._budget_cache = {}
        self._category_cache = {}
        self._account_cache = {}
        self._payee_cache = {}

        # Get budget ID if not specified
        if not self.budget_id:
            self.budget_id = self._get_first_budget_id()

    def _get_first_budget_id(self) -> str:
        """Get the first budget ID from the user's account"""
        response = self._make_request('GET', '/budgets')
        budgets = response.get('data', {}).get('budgets', [])
        if not budgets:
            raise ValueError("No budgets found in YNAB account")
        return budgets[0]['id']

    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """
        Make a request to YNAB API with error handling

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Optional request data

        Returns:
            Response data as dictionary
        """
        url = f"{self.BASE_URL}{endpoint}"

        import time
        max_retries = 5
        retry_delay = 60  # Start with 60 seconds for rate limit recovery

        for attempt in range(max_retries):
            try:
                if method == 'GET':
                    response = self.session.get(url, headers=self.headers)
                elif method == 'POST':
                    response = self.session.post(url, headers=self.headers, json=data)
                elif method == 'PUT':
                    response = self.session.put(url, headers=self.headers, json=data)
                elif method == 'PATCH':
                    response = self.session.patch(url, headers=self.headers, json=data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Check for rate limit
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        logger.warning(f"Rate limited. Waiting {retry_delay} seconds before retry...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        logger.error("Max retries reached for rate limit")

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1 and hasattr(e, 'response') and e.response.status_code == 429:
                    logger.warning(f"Rate limited. Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue

                logger.error(f"YNAB API request failed: {e}")
                if hasattr(e, 'response') and hasattr(e.response, 'text'):
                    logger.error(f"Response: {e.response.text}")
                raise

    @staticmethod
    def milliunits_to_dollars(milliunits: int) -> float:
        """Convert YNAB milliunits to dollars"""
        return milliunits / 1000.0

    @staticmethod
    def dollars_to_milliunits(dollars: float) -> int:
        """Convert dollars to YNAB milliunits"""
        return int(dollars * 1000)

    def get_uncategorized_transactions(self,
                                      days_back: int = 30,
                                      include_pending: bool = True) -> List[Transaction]:
        """
        Get all uncategorized transactions from YNAB

        Args:
            days_back: Number of days to look back
            include_pending: Whether to include unapproved transactions

        Returns:
            List of uncategorized Transaction objects
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Fetch transactions
        endpoint = f"/budgets/{self.budget_id}/transactions"
        params = f"?since_date={start_date.strftime('%Y-%m-%d')}"
        response = self._make_request('GET', endpoint + params)

        transactions = response.get('data', {}).get('transactions', [])

        # Load caches if needed
        if not self._category_cache:
            self._load_categories()
        if not self._account_cache:
            self._load_accounts()
        if not self._payee_cache:
            self._load_payees()

        # Filter for uncategorized transactions
        uncategorized = []
        for txn in transactions:
            # Skip if approved and we're not including pending
            if not include_pending and not txn.get('approved', True):
                continue

            # Check if uncategorized
            category_id = txn.get('category_id')
            if not category_id or category_id == 'immediate-income-subcategory':
                # Convert to Transaction object
                transaction = self._parse_transaction(txn)
                uncategorized.append(transaction)

        # Sort by date (newest first)
        uncategorized.sort(key=lambda t: t.date, reverse=True)

        logger.info(f"Found {len(uncategorized)} uncategorized transactions")
        return uncategorized

    def _parse_transaction(self, txn: Dict) -> Transaction:
        """Parse raw transaction data into Transaction object"""
        # Get names from caches
        category_name = None
        if txn.get('category_id'):
            category_name = self._category_cache.get(txn['category_id'], {}).get('name')

        account_name = self._account_cache.get(txn['account_id'], {}).get('name', 'Unknown')

        payee_name = 'Unknown'
        if txn.get('payee_id'):
            payee_name = self._payee_cache.get(txn['payee_id'], {}).get('name', 'Unknown')
        elif txn.get('payee_name'):
            payee_name = txn['payee_name']

        return Transaction(
            id=txn['id'],
            date=txn['date'],
            amount=self.milliunits_to_dollars(txn['amount']),
            payee_name=payee_name,
            payee_id=txn.get('payee_id'),
            category_name=category_name,
            category_id=txn.get('category_id'),
            account_name=account_name,
            account_id=txn['account_id'],
            memo=txn.get('memo'),
            cleared=txn.get('cleared', 'uncleared'),
            approved=txn.get('approved', False),
            flag_color=txn.get('flag_color'),
            import_id=txn.get('import_id'),
            subtransactions=txn.get('subtransactions', [])
        )

    def _load_categories(self):
        """Load and cache all categories (with S3 caching)"""
        cache_key = f"categories-{self.budget_id}"

        # Try S3 cache first
        if self._use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                self._category_cache = cached
                logger.info(f"Loaded {len(cached)} categories from S3 cache")
                return

        # Fetch from API
        endpoint = f"/budgets/{self.budget_id}/categories"
        response = self._make_request('GET', endpoint)

        for group in response.get('data', {}).get('category_groups', []):
            for category in group.get('categories', []):
                self._category_cache[category['id']] = {
                    'name': category['name'],
                    'group_name': group['name'],
                    'hidden': category.get('hidden', False)
                }

        # Store in S3 cache
        if self._use_cache and self._category_cache:
            self._cache.set(cache_key, self._category_cache)
            logger.info(f"Cached {len(self._category_cache)} categories to S3")

    def _load_accounts(self):
        """Load and cache all accounts (with S3 caching)"""
        cache_key = f"accounts-{self.budget_id}"

        # Try S3 cache first
        if self._use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                self._account_cache = cached
                logger.info(f"Loaded {len(cached)} accounts from S3 cache")
                return

        # Fetch from API
        endpoint = f"/budgets/{self.budget_id}/accounts"
        response = self._make_request('GET', endpoint)

        for account in response.get('data', {}).get('accounts', []):
            self._account_cache[account['id']] = {
                'name': account['name'],
                'type': account.get('type'),
                'on_budget': account.get('on_budget', True),
                'closed': account.get('closed', False)
            }

        # Store in S3 cache
        if self._use_cache and self._account_cache:
            self._cache.set(cache_key, self._account_cache)
            logger.info(f"Cached {len(self._account_cache)} accounts to S3")

    def _load_payees(self):
        """Load and cache all payees (with S3 caching)"""
        cache_key = f"payees-{self.budget_id}"

        # Try S3 cache first
        if self._use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                self._payee_cache = cached
                logger.info(f"Loaded {len(cached)} payees from S3 cache")
                return

        # Fetch from API
        endpoint = f"/budgets/{self.budget_id}/payees"
        response = self._make_request('GET', endpoint)

        for payee in response.get('data', {}).get('payees', []):
            self._payee_cache[payee['id']] = {
                'name': payee['name']
            }

        # Store in S3 cache
        if self._use_cache and self._payee_cache:
            self._cache.set(cache_key, self._payee_cache)
            logger.info(f"Cached {len(self._payee_cache)} payees to S3")

    def categorize_transaction(self, transaction_id: str, category_id: str) -> bool:
        """
        Categorize a single transaction

        Args:
            transaction_id: Transaction ID
            category_id: Category ID to assign

        Returns:
            True if successful
        """
        endpoint = f"/budgets/{self.budget_id}/transactions/{transaction_id}"
        data = {
            'transaction': {
                'category_id': category_id
            }
        }

        try:
            self._make_request('PUT', endpoint, data)
            logger.info(f"Categorized transaction {transaction_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to categorize transaction {transaction_id}: {e}")
            return False

    def create_split_transaction(self,
                                transaction_id: str,
                                splits: List[Dict[str, Any]]) -> bool:
        """
        Convert a transaction to a split transaction

        Args:
            transaction_id: Transaction ID to split
            splits: List of split dictionaries with amount, category_id, and optional memo

        Returns:
            True if successful
        """
        # Prepare subtransactions
        subtransactions = []
        for split in splits:
            subtransactions.append({
                'amount': self.dollars_to_milliunits(split['amount']),
                'category_id': split['category_id'],
                'memo': split.get('memo', '')
            })

        endpoint = f"/budgets/{self.budget_id}/transactions/{transaction_id}"
        data = {
            'transaction': {
                'subtransactions': subtransactions
            }
        }

        try:
            self._make_request('PUT', endpoint, data)
            logger.info(f"Created split transaction for {transaction_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create split transaction {transaction_id}: {e}")
            return False

    def get_categories(self) -> Dict[str, List[Dict]]:
        """
        Get all categories organized by group

        Returns:
            Dictionary with category groups as keys
        """
        if not self._category_cache:
            self._load_categories()

        # Organize by group
        groups = {}
        for cat_id, cat_info in self._category_cache.items():
            if cat_info['hidden']:
                continue

            group_name = cat_info['group_name']
            if group_name not in groups:
                groups[group_name] = []

            groups[group_name].append({
                'id': cat_id,
                'name': cat_info['name']
            })

        return groups

    def get_transaction_history_for_payee(self,
                                         payee_name: str,
                                         limit: int = 10) -> List[Transaction]:
        """
        Get historical transactions for a specific payee

        Args:
            payee_name: Name of the payee
            limit: Maximum number of transactions to return

        Returns:
            List of historical transactions
        """
        # Find payee ID
        payee_id = None
        for pid, pinfo in self._payee_cache.items():
            if pinfo['name'].lower() == payee_name.lower():
                payee_id = pid
                break

        if not payee_id:
            logger.warning(f"Payee not found: {payee_name}")
            return []

        # Fetch transactions for this payee
        endpoint = f"/budgets/{self.budget_id}/payees/{payee_id}/transactions"
        response = self._make_request('GET', endpoint)

        transactions = response.get('data', {}).get('transactions', [])

        # Parse and filter to categorized only
        history = []
        for txn in transactions[:limit]:
            if txn.get('category_id') and txn['category_id'] != 'immediate-income-subcategory':
                history.append(self._parse_transaction(txn))

        return history

    def get_unapproved_transactions(self, days_back: int = 30) -> List[Transaction]:
        """
        Get all transactions that need approval (approved=False)

        Args:
            days_back: Number of days to look back

        Returns:
            List of unapproved Transaction objects
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Fetch transactions
        endpoint = f"/budgets/{self.budget_id}/transactions"
        params = f"?since_date={start_date.strftime('%Y-%m-%d')}"
        response = self._make_request('GET', endpoint + params)

        transactions = response.get('data', {}).get('transactions', [])

        # Load caches if needed
        if not self._category_cache:
            self._load_categories()
        if not self._account_cache:
            self._load_accounts()
        if not self._payee_cache:
            self._load_payees()

        # Filter for unapproved transactions
        unapproved = []
        for txn in transactions:
            if not txn.get('approved', True):
                transaction = self._parse_transaction(txn)
                unapproved.append(transaction)

        # Sort by date (newest first)
        unapproved.sort(key=lambda t: t.date, reverse=True)

        logger.info(f"Found {len(unapproved)} unapproved transactions")
        return unapproved

    def validate_connection(self) -> bool:
        """
        Validate YNAB API connection

        Returns:
            True if connection is valid
        """
        try:
            response = self._make_request('GET', '/user')
            user = response.get('data', {}).get('user', {})
            logger.info(f"Connected to YNAB as user: {user.get('id')}")
            return True
        except Exception as e:
            logger.error(f"YNAB connection validation failed: {e}")
            return False