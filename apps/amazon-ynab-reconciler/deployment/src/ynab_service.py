"""
YNAB service for fetching and updating transactions.
Interfaces with YNAB API for transaction management.
"""

import os
import re
import json
import time
import logging
import requests
from datetime import datetime, date
from typing import List, Dict, Optional
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache settings
CACHE_DIR = Path(__file__).parent.parent / '.cache'
CACHE_TTL_TRANSACTIONS = 300  # 5 minutes for transactions
CACHE_TTL_CATEGORIES = 3600   # 1 hour for categories (rarely change)
CACHE_TTL_ACCOUNTS = 3600     # 1 hour for accounts
RATE_LIMIT_BUFFER = 20        # Keep 20 requests in reserve
MAX_RETRIES = 3


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

        # Enhanced caching
        self._category_cache = {}      # {category_id: (name, timestamp)}
        self._transactions_cache = {}  # {cache_key: (data, timestamp)}
        self._rate_limit_remaining = 200
        self._rate_limit_reset = None

        # Ensure cache directory exists
        CACHE_DIR.mkdir(exist_ok=True)

    def _get_cache_path(self, cache_type: str) -> Path:
        """Get path for persistent cache file."""
        return CACHE_DIR / f'{cache_type}_cache.json'

    def _load_persistent_cache(self, cache_type: str) -> Dict:
        """Load cache from disk."""
        cache_path = self._get_cache_path(cache_type)
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    # Check if cache is still valid
                    if time.time() - data.get('timestamp', 0) < data.get('ttl', 0):
                        return data.get('data', {})
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save_persistent_cache(self, cache_type: str, data: Dict, ttl: int):
        """Save cache to disk."""
        cache_path = self._get_cache_path(cache_type)
        try:
            with open(cache_path, 'w') as f:
                json.dump({
                    'timestamp': time.time(),
                    'ttl': ttl,
                    'data': data
                }, f)
        except IOError as e:
            logger.warning(f"Failed to save cache: {e}")

    def _update_rate_limit(self, response):
        """Update rate limit tracking from response headers."""
        if 'X-Rate-Limit' in response.headers:
            self._rate_limit_remaining = int(response.headers.get('X-Rate-Limit', 200))
        if 'Retry-After' in response.headers:
            self._rate_limit_reset = time.time() + int(response.headers.get('Retry-After', 60))

    def _check_rate_limit(self):
        """Check if we should throttle requests."""
        if self._rate_limit_remaining <= RATE_LIMIT_BUFFER:
            if self._rate_limit_reset and time.time() < self._rate_limit_reset:
                wait_time = self._rate_limit_reset - time.time()
                logger.warning(f"Rate limit approaching, waiting {wait_time:.0f}s")
                time.sleep(min(wait_time, 60))  # Wait up to 60s

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make API request with rate limiting and retry logic."""
        self._check_rate_limit()

        for attempt in range(MAX_RETRIES):
            try:
                response = getattr(requests, method)(url, headers=self.headers, **kwargs)
                self._update_rate_limit(response)

                if response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited. Waiting {retry_after}s before retry...")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    raise

        raise Exception(f"Request failed after {MAX_RETRIES} attempts")

    def validate_connection(self) -> bool:
        """Validate YNAB API connection."""
        if not self.api_key:
            logger.error("YNAB API key not configured")
            return False

        try:
            response = self._make_request('get', f"{self.base_url}/user")
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
            response = self._make_request('get', f"{self.base_url}/budgets")
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
            response = self._make_request(
                'get',
                f"{self.base_url}/budgets/{budget_id}/accounts"
            )
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

            response = self._make_request(
                'get',
                f"{self.base_url}/budgets/{budget_id}/accounts/{account_id}/transactions",
                params=params
            )

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

    def get_amazon_transactions(
        self,
        since_date: datetime,
        include_cleared: bool = True,
        payee_patterns: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Fetch all transactions where payee contains 'Amazon' (or similar patterns).

        This method searches ALL accounts (not just configured ones) for Amazon purchases.

        Args:
            since_date: Start date for transactions
            include_cleared: If True, include cleared transactions (default: True for memo updates)
            payee_patterns: List of payee name patterns to match (default: ['Amazon', 'AMZN', 'AMZ'])

        Returns:
            List of transaction dictionaries for Amazon purchases
        """
        budget_id = self.get_budget_id()

        # Default patterns for Amazon transactions
        if payee_patterns is None:
            payee_patterns = ['amazon', 'amzn', 'amz']

        # Normalize patterns to lowercase
        payee_patterns = [p.lower() for p in payee_patterns]

        # Ensure accounts cache is populated
        if not self._accounts_cache:
            response = self._make_request(
                'get',
                f"{self.base_url}/budgets/{budget_id}/accounts"
            )
            self._accounts_cache = response.json()['data']['accounts']

        # Get all credit card and checking accounts (where Amazon purchases typically appear)
        account_ids = [
            acc['id'] for acc in self._accounts_cache
            if not acc['closed'] and acc['type'] in ['creditCard', 'checking']
        ]

        amazon_transactions = []

        for account_id in account_ids:
            params = {
                'since_date': since_date.strftime('%Y-%m-%d')
            }

            response = self._make_request(
                'get',
                f"{self.base_url}/budgets/{budget_id}/accounts/{account_id}/transactions",
                params=params
            )

            transactions = response.json()['data']['transactions']

            for txn in transactions:
                # Filter by cleared status if needed
                if not include_cleared and txn['cleared'] == 'cleared':
                    continue

                # Check if payee matches Amazon patterns
                payee_name = (txn.get('payee_name') or '').lower()
                is_amazon = any(pattern in payee_name for pattern in payee_patterns)

                if not is_amazon:
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

                amazon_transactions.append(transaction)

        logger.info(f"Found {len(amazon_transactions)} Amazon transactions in YNAB")
        return amazon_transactions

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
        response = self._make_request(
            'get',
            f"{self.base_url}/budgets/{budget_id}/transactions/{transaction_id}"
        )
        existing_txn = response.json()['data']['transaction']

        # Format new memo with enhanced purchase details
        order_id = amazon_data.get('order_id', '')
        items = amazon_data.get('items', [])

        if items:
            # Build detailed memo from items with product links
            item_details = []
            first_asin = None

            for item in items[:2]:  # Limit to first 2 items to leave room for link
                item_name = item.get('name', 'Unknown Item')[:40]  # Truncate long names
                item_qty = item.get('quantity', 1)
                asin = item.get('asin', '')

                # Capture the first ASIN for the product link
                if not first_asin and asin and asin != 'UNKNOWN':
                    first_asin = asin

                if item_qty > 1:
                    item_details.append(f"{item_name} (x{item_qty})")
                else:
                    item_details.append(item_name)

            # Format the memo: Product Name only
            new_memo = f"{', '.join(item_details)}"

            # Add item count if more than shown
            if len(items) > 2:
                new_memo += f" (+{len(items)-2} more)"
        else:
            # Fall back to old format if no items detail
            new_memo = self.memo_format.format(
                category=amazon_data.get('category', 'Unknown'),
                item_name=amazon_data.get('item_name', 'Amazon Purchase'),
                item_link=amazon_data.get('item_link', '')
            )

        # Preserve existing memo if configured
        if self.preserve_existing_memo and existing_txn.get('memo'):
            existing_memo = existing_txn['memo']
            # Don't duplicate if already reconciled
            if 'Amazon' not in existing_memo and '#' not in existing_memo:
                # Add existing memo at the end if space permits
                if len(new_memo) + len(existing_memo) < 180:
                    new_memo = f"{new_memo} | {existing_memo}"

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
            response = self._make_request(
                'patch',
                f"{self.base_url}/budgets/{budget_id}/transactions/{transaction_id}",
                json=update_data
            )
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
        """Get category name by ID with caching."""
        if not category_id:
            return 'Uncategorized'

        # Check in-memory cache first
        if category_id in self._category_cache:
            name, timestamp = self._category_cache[category_id]
            if time.time() - timestamp < CACHE_TTL_CATEGORIES:
                return name

        # Check persistent cache
        persistent_cache = self._load_persistent_cache('categories')
        if category_id in persistent_cache:
            name = persistent_cache[category_id]
            self._category_cache[category_id] = (name, time.time())
            return name

        # Fetch from API
        try:
            response = self._make_request(
                'get',
                f"{self.base_url}/budgets/{budget_id}/categories/{category_id}"
            )
            name = response.json()['data']['category']['name']

            # Update caches
            self._category_cache[category_id] = (name, time.time())
            persistent_cache[category_id] = name
            self._save_persistent_cache('categories', persistent_cache, CACHE_TTL_CATEGORIES)

            return name
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
            response = self._make_request(
                'patch',
                f"{self.base_url}/budgets/{budget_id}/transactions/{transaction_id}",
                json=update_data
            )
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
            response = self._make_request(
                'patch',
                f"{self.base_url}/budgets/{budget_id}/transactions/{transaction_id}",
                json=update_data
            )
            logger.info(f"Added {flag_color} flag to transaction {transaction_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to flag transaction {transaction_id}: {str(e)}")
            return False

    def get_pending_transactions(
        self,
        since_date: datetime
    ) -> List[Dict]:
        """
        Fetch all pending transactions (unapproved OR uncleared) with caching.

        Args:
            since_date: Start date for transactions

        Returns:
            List of transaction dictionaries
        """
        # Generate cache key based on date
        cache_key = f"pending_{since_date.strftime('%Y-%m-%d')}"

        # Check in-memory cache
        if cache_key in self._transactions_cache:
            data, timestamp = self._transactions_cache[cache_key]
            if time.time() - timestamp < CACHE_TTL_TRANSACTIONS:
                logger.info(f"Using cached pending transactions ({len(data)} transactions)")
                return data

        budget_id = self.get_budget_id()

        # Ensure accounts cache is populated
        if not self._accounts_cache:
            response = self._make_request(
                'get',
                f"{self.base_url}/budgets/{budget_id}/accounts"
            )
            self._accounts_cache = response.json()['data']['accounts']

        # Get all credit card and checking accounts
        account_ids = [
            acc['id'] for acc in self._accounts_cache
            if not acc['closed'] and acc['type'] in ['creditCard', 'checking']
        ]

        pending_transactions = []

        for account_id in account_ids:
            params = {
                'since_date': since_date.strftime('%Y-%m-%d')
            }

            response = self._make_request(
                'get',
                f"{self.base_url}/budgets/{budget_id}/accounts/{account_id}/transactions",
                params=params
            )

            transactions = response.json()['data']['transactions']

            for txn in transactions:
                # Include if unapproved OR uncleared
                is_unapproved = not txn.get('approved', True)
                is_uncleared = txn['cleared'] != 'cleared'

                if not (is_unapproved or is_uncleared):
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
                    'approved': txn.get('approved', True),
                    'account_id': account_id,
                    'account_name': self._get_account_name(account_id),
                    'import_id': txn.get('import_id'),
                    'flag_color': txn.get('flag_color')
                }

                pending_transactions.append(transaction)

        # Cache the results
        self._transactions_cache[cache_key] = (pending_transactions, time.time())

        logger.info(f"Fetched {len(pending_transactions)} pending transactions from YNAB")
        return pending_transactions

    def _is_amazon_transaction(self, payee_name: str) -> bool:
        """Check if transaction is from Amazon based on payee name."""
        if not payee_name:
            return False
        payee_lower = payee_name.lower()
        return any(term in payee_lower for term in ['amazon', 'amzn', 'amz'])

    def _extract_amazon_product_name(self, email_data: Dict) -> str:
        """Extract product name from Amazon email subject or body."""
        subject = email_data.get('subject', '')
        body = email_data.get('body_text', '')

        # Try subject: 'Your Amazon.com order of "Product Name..."'
        # Handle cases with quantity prefix like "2" x ProductName
        subject_match = re.search(r'order of\s*["\']?(?:\d+["\']?\s*x\s*)?([^"\']{5,})["\']?', subject, re.IGNORECASE)
        if subject_match:
            product = subject_match.group(1).strip()
            # Remove trailing "..." if present
            product = re.sub(r'\.{3,}$', '', product)
            if len(product) > 5:
                return product[:80]

        # Try extracting from "Your Amazon.com order of" format with quantity
        subject_match = re.search(r'order of\s*["\'](\d+)["\']?\s*x\s+(.+)', subject, re.IGNORECASE)
        if subject_match:
            qty = subject_match.group(1)
            product = subject_match.group(2).strip()
            return f"{qty}x {product[:75]}"

        # Try body for product patterns
        body_match = re.search(r'(?:ordered|shipped|delivered)[:\s]+([^\n]{5,80})', body, re.IGNORECASE)
        if body_match:
            return body_match.group(1).strip()[:80]

        # Fallback: clean subject - remove "Your Amazon.com order" prefix
        cleaned = re.sub(r'^Your Amazon\.com order.*?of\s*', '', subject, flags=re.IGNORECASE)
        # Remove quantity prefix like "2" x or "2" X
        cleaned = re.sub(r'^["\']?\d+["\']?\s*[xX]\s*', '', cleaned)
        if cleaned and cleaned != subject and len(cleaned) > 5:
            return cleaned[:80]

        return "Amazon Order"

    def _extract_product_from_email(self, email_data: Dict) -> str:
        """Extract product/item name from non-Amazon email body (priority) or subject."""
        subject = email_data.get('subject', '')
        body = email_data.get('body_text', '')

        # PRIORITY: Search body first for product/item names
        if body:
            # Common patterns for product names in receipt emails
            body_patterns = [
                # "Item: Product Name" or "Product: Name"
                r'(?:item|product)[:\s]+([^\n\r$]{5,80})',
                # "1x Product Name" or "2 x Product Name"
                r'\d+\s*x\s+([^\n\r$]{5,80})',
                # "Qty: 1 Product Name"
                r'(?:qty|quantity)[:\s]*\d+\s+([^\n\r$]{5,80})',
                # Lines that look like product listings (start with product-like text)
                r'^([A-Z][a-zA-Z0-9\s\-\'\"]{10,60})\s+\$?\d+',
                # "You ordered: Product"
                r'(?:you\s+)?(?:ordered|purchased|bought)[:\s]+([^\n\r]{5,80})',
                # "Order details:" followed by product on next line
                r'(?:order\s+)?details?[:\s]*\n+([^\n\r$]{5,80})',
            ]

            for pattern in body_patterns:
                match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
                if match:
                    product = match.group(1).strip()
                    # Clean up the product name
                    product = re.sub(r'\s+', ' ', product)  # Normalize whitespace
                    product = re.sub(r'\$[\d,]+\.?\d*$', '', product).strip()  # Remove trailing price
                    if len(product) > 5:  # Make sure we got something meaningful
                        return product[:100]

        # Fallback: try to extract from subject
        if subject:
            # Remove common email prefixes to get to the meat
            cleaned = subject
            prefixes = [
                r'^Your\s+', r'^Order\s+', r'^Receipt\s+for\s+',
                r'^Thank you for your\s+', r'^\[.*?\]\s*',
                r'^Confirmation[:\s]+', r'^Purchase[:\s]+',
            ]
            for prefix in prefixes:
                cleaned = re.sub(prefix, '', cleaned, flags=re.IGNORECASE)

            if cleaned and len(cleaned) > 5 and cleaned != subject:
                return cleaned[:100]

        # Final fallback
        return subject[:100] if subject else "Receipt"

    def update_transaction_with_email_link(
        self,
        transaction_id: str,
        email_data: Dict,
        payee_name: str = '',
        dry_run: bool = False
    ) -> bool:
        """
        Update a YNAB transaction memo with email deep link.

        Args:
            transaction_id: YNAB transaction ID
            email_data: Dict with email match info:
                - message_id: str
                - subject: str
                - date: datetime
                - source_account: str
                - account_type: str ('gmail' or 'imap')
                - deep_link: Optional[str]
            payee_name: Payee name (avoids extra API call if provided)
            dry_run: If True, don't actually update

        Returns:
            True if update successful
        """
        budget_id = self.get_budget_id()

        # Use passed payee_name to avoid extra GET call
        # Only fetch if payee_name not provided (backward compatibility)
        if not payee_name:
            response = self._make_request(
                'get',
                f"{self.base_url}/budgets/{budget_id}/transactions/{transaction_id}"
            )
            payee_name = response.json()['data']['transaction'].get('payee_name', 'Transaction')

        # Build new memo - just product/item name, no links
        if self._is_amazon_transaction(payee_name):
            # Amazon: extract product name from email
            new_memo = self._extract_amazon_product_name(email_data)
        else:
            # Non-Amazon: extract product/item from email body or subject
            new_memo = self._extract_product_from_email(email_data)

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
            response = self._make_request(
                'patch',
                f"{self.base_url}/budgets/{budget_id}/transactions/{transaction_id}",
                json=update_data
            )
            logger.info(f"Updated transaction {transaction_id} with email link")
            return True

        except Exception as e:
            logger.error(f"Failed to update transaction {transaction_id}: {str(e)}")
            return False