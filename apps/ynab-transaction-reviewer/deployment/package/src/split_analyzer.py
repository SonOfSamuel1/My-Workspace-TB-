"""
Split Transaction Analyzer

Detects transactions that likely need to be split and suggests
appropriate split amounts and categories.

REFACTORED: Now uses BudgetDataContext for all category lookups
instead of making API calls. This reduces API calls to 0.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime

# Import Transaction from data_context (new location)
from data_context import Transaction, BudgetDataContext

if TYPE_CHECKING:
    from ynab_service import YNABService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SplitSuggestion:
    """Represents a suggested split for a transaction"""
    amount: float
    category_id: Optional[str]
    category_name: str
    memo: str
    confidence: float


class SplitAnalyzer:
    """
    Analyzes transactions to detect and suggest splits.

    REFACTORED: Uses pre-fetched BudgetDataContext instead of making
    API calls for category lookups.
    """

    def __init__(self, data_context: BudgetDataContext = None, ynab_service: 'YNABService' = None):
        """
        Initialize split analyzer

        Args:
            data_context: Pre-fetched budget data context (preferred)
            ynab_service: YNAB service instance (legacy, for backward compatibility)
        """
        self.context = data_context
        self.ynab = ynab_service  # Keep for backward compatibility
        self._build_split_patterns()

        # Cache for categories and category map
        self._categories_cache = None
        self._category_map_cache = None

    def _build_split_patterns(self):
        """Build patterns for detecting splittable transactions"""
        # Merchants that commonly have mixed categories
        self.split_merchants = {
            'amazon': {
                'pattern': re.compile(r'amazon|amzn', re.IGNORECASE),
                'common_splits': ['Shopping', 'Household Goods', 'Electronics', 'Books', 'Groceries'],
                'confidence': 85
            },
            'costco': {
                'pattern': re.compile(r'costco', re.IGNORECASE),
                'common_splits': ['Groceries', 'Household Goods', 'Gas', 'Clothing'],
                'confidence': 80
            },
            'walmart': {
                'pattern': re.compile(r'walmart|wal-mart|wm supercenter', re.IGNORECASE),
                'common_splits': ['Groceries', 'Household Goods', 'Clothing', 'Electronics'],
                'confidence': 75
            },
            'target': {
                'pattern': re.compile(r'target', re.IGNORECASE),
                'common_splits': ['Groceries', 'Household Goods', 'Clothing', 'Home Improvement'],
                'confidence': 75
            },
            'sams_club': {
                'pattern': re.compile(r'sam\'?s club|sams club', re.IGNORECASE),
                'common_splits': ['Groceries', 'Household Goods', 'Gas'],
                'confidence': 80
            },
            'home_depot': {
                'pattern': re.compile(r'home depot', re.IGNORECASE),
                'common_splits': ['Home Improvement', 'Garden', 'Tools'],
                'confidence': 70
            },
            'lowes': {
                'pattern': re.compile(r'lowes|lowe\'s', re.IGNORECASE),
                'common_splits': ['Home Improvement', 'Garden', 'Appliances'],
                'confidence': 70
            }
        }

        # Amount thresholds that suggest splits
        self.amount_thresholds = {
            'amazon': 50.00,
            'costco': 100.00,
            'walmart': 75.00,
            'target': 75.00,
            'sams_club': 100.00,
            'home_depot': 100.00,
            'lowes': 100.00,
            'default': 150.00
        }

        # Common split patterns (for restaurants, etc.)
        self.common_patterns = {
            'tip_split': {
                'pattern': re.compile(r'restaurant|cafe|bar|grill|diner', re.IGNORECASE),
                'tip_percentage': 0.18,  # 18% tip estimate
                'categories': ['Dining Out', 'Tips']
            }
        }

    def _get_categories(self) -> Dict[str, List[Dict]]:
        """
        Get categories from context or YNAB service (cached).

        This ensures we only make 1 API call max, regardless of
        how many times it's called.
        """
        # Prefer context (no API calls)
        if self.context is not None:
            return self.context.get_categories_formatted()

        # Fallback to YNAB service with caching
        if self._categories_cache is None and self.ynab is not None:
            self._categories_cache = self.ynab.get_categories()

        return self._categories_cache or {}

    def _get_category_map(self) -> Dict[str, str]:
        """
        Get category name to ID map.

        Returns: Dict mapping category name to category ID
        """
        if self._category_map_cache is not None:
            return self._category_map_cache

        # Build from context if available
        if self.context is not None:
            self._category_map_cache = dict(self.context.category_name_to_id)
            return self._category_map_cache

        # Build from categories
        categories = self._get_categories()
        self._category_map_cache = {}
        for group, cats in categories.items():
            for cat in cats:
                self._category_map_cache[cat['name']] = cat['id']

        return self._category_map_cache

    def analyze_for_split(self, transaction: Transaction) -> Optional[List[SplitSuggestion]]:
        """
        Analyze a transaction to determine if it should be split

        Args:
            transaction: Transaction to analyze

        Returns:
            List of split suggestions if applicable, None otherwise
        """
        # Skip if already split
        if transaction.subtransactions:
            return None

        # Check merchant patterns
        merchant_suggestions = self._check_merchant_patterns(transaction)
        if merchant_suggestions:
            return merchant_suggestions

        # Check for tip splits (restaurants)
        tip_suggestions = self._check_tip_pattern(transaction)
        if tip_suggestions:
            return tip_suggestions

        # Check amount thresholds
        if self._should_split_by_amount(transaction):
            return self._suggest_generic_split(transaction)

        return None

    def _check_merchant_patterns(self, transaction: Transaction) -> Optional[List[SplitSuggestion]]:
        """Check if merchant matches known split patterns"""
        if not transaction.payee_name:
            return None

        payee_lower = transaction.payee_name.lower()

        for merchant_key, merchant_info in self.split_merchants.items():
            if merchant_info['pattern'].search(payee_lower):
                # Check if amount is above threshold
                threshold = self.amount_thresholds.get(merchant_key, self.amount_thresholds['default'])
                if abs(transaction.amount) < threshold:
                    continue

                # Generate split suggestions
                return self._generate_merchant_splits(
                    transaction,
                    merchant_key,
                    merchant_info
                )

        return None

    def _generate_merchant_splits(self,
                                 transaction: Transaction,
                                 merchant_key: str,
                                 merchant_info: Dict) -> List[SplitSuggestion]:
        """Generate split suggestions for known merchant"""
        suggestions = []
        amount = abs(transaction.amount)

        # Get category map using cached helper (no API call)
        category_map = self._get_category_map()

        # Special handling for different merchants
        if merchant_key == 'amazon':
            suggestions = self._generate_amazon_splits(transaction, category_map)
        elif merchant_key == 'costco' or merchant_key == 'sams_club':
            suggestions = self._generate_warehouse_splits(transaction, category_map, merchant_info)
        else:
            suggestions = self._generate_default_splits(transaction, category_map, merchant_info)

        return suggestions if suggestions else None

    def _generate_amazon_splits(self, transaction: Transaction, category_map: Dict) -> List[SplitSuggestion]:
        """Generate split suggestions for Amazon transactions"""
        amount = abs(transaction.amount)
        suggestions = []

        # Check memo for clues
        memo_lower = (transaction.memo or '').lower()

        # Common Amazon purchase patterns
        if amount < 30:
            # Likely single category small item
            return None
        elif amount < 100:
            # Possibly 2 items
            suggestions = [
                SplitSuggestion(
                    amount=amount * 0.6,
                    category_id=category_map.get('Shopping'),
                    category_name='Shopping',
                    memo='Primary item',
                    confidence=70
                ),
                SplitSuggestion(
                    amount=amount * 0.4,
                    category_id=category_map.get('Household Goods'),
                    category_name='Household Goods',
                    memo='Additional items',
                    confidence=70
                )
            ]
        else:
            # Multiple items likely
            suggestions = [
                SplitSuggestion(
                    amount=amount * 0.5,
                    category_id=category_map.get('Shopping'),
                    category_name='Shopping',
                    memo='Main purchase',
                    confidence=75
                ),
                SplitSuggestion(
                    amount=amount * 0.3,
                    category_id=category_map.get('Household Goods'),
                    category_name='Household Goods',
                    memo='Household items',
                    confidence=70
                ),
                SplitSuggestion(
                    amount=amount * 0.2,
                    category_id=category_map.get('Electronics'),
                    category_name='Electronics',
                    memo='Electronics/accessories',
                    confidence=65
                )
            ]

        # Ensure amounts sum correctly (handle rounding)
        total = sum(s.amount for s in suggestions)
        if suggestions and abs(total - amount) > 0.01:
            suggestions[-1].amount += (amount - total)

        return suggestions

    def _generate_warehouse_splits(self,
                                  transaction: Transaction,
                                  category_map: Dict,
                                  merchant_info: Dict) -> List[SplitSuggestion]:
        """Generate split suggestions for warehouse stores (Costco, Sam's Club)"""
        amount = abs(transaction.amount)
        suggestions = []

        # Typical warehouse shopping pattern
        if amount > 200:
            # Large haul
            suggestions = [
                SplitSuggestion(
                    amount=amount * 0.6,
                    category_id=category_map.get('Groceries'),
                    category_name='Groceries',
                    memo='Bulk groceries',
                    confidence=80
                ),
                SplitSuggestion(
                    amount=amount * 0.25,
                    category_id=category_map.get('Household Goods'),
                    category_name='Household Goods',
                    memo='Household supplies',
                    confidence=75
                ),
                SplitSuggestion(
                    amount=amount * 0.15,
                    category_id=category_map.get('Personal Care'),
                    category_name='Personal Care',
                    memo='Personal care items',
                    confidence=70
                )
            ]
        else:
            # Smaller trip
            suggestions = [
                SplitSuggestion(
                    amount=amount * 0.7,
                    category_id=category_map.get('Groceries'),
                    category_name='Groceries',
                    memo='Groceries',
                    confidence=75
                ),
                SplitSuggestion(
                    amount=amount * 0.3,
                    category_id=category_map.get('Household Goods'),
                    category_name='Household Goods',
                    memo='Other items',
                    confidence=70
                )
            ]

        # Ensure amounts sum correctly
        total = sum(s.amount for s in suggestions)
        if suggestions and abs(total - amount) > 0.01:
            suggestions[-1].amount += (amount - total)

        return suggestions

    def _generate_default_splits(self,
                                transaction: Transaction,
                                category_map: Dict,
                                merchant_info: Dict) -> List[SplitSuggestion]:
        """Generate default split suggestions"""
        amount = abs(transaction.amount)
        suggestions = []

        # Use common splits from merchant info
        common_categories = merchant_info['common_splits'][:2]  # Take top 2

        if len(common_categories) >= 2:
            suggestions = [
                SplitSuggestion(
                    amount=amount * 0.6,
                    category_id=category_map.get(common_categories[0]),
                    category_name=common_categories[0],
                    memo=f'{common_categories[0]} items',
                    confidence=merchant_info['confidence'] * 0.8
                ),
                SplitSuggestion(
                    amount=amount * 0.4,
                    category_id=category_map.get(common_categories[1]),
                    category_name=common_categories[1],
                    memo=f'{common_categories[1]} items',
                    confidence=merchant_info['confidence'] * 0.7
                )
            ]

        return suggestions

    def _check_tip_pattern(self, transaction: Transaction) -> Optional[List[SplitSuggestion]]:
        """Check for restaurant/tip split pattern"""
        if not transaction.payee_name:
            return None

        payee_lower = transaction.payee_name.lower()

        for pattern_info in [self.common_patterns['tip_split']]:
            if pattern_info['pattern'].search(payee_lower):
                amount = abs(transaction.amount)

                # Only suggest tip split for reasonable restaurant amounts
                if amount < 15 or amount > 500:
                    continue

                # Calculate tip amount (estimate)
                tip_percentage = pattern_info['tip_percentage']
                base_amount = amount / (1 + tip_percentage)
                tip_amount = amount - base_amount

                # Get category IDs using cached categories (no API call)
                categories = self._get_categories()
                dining_cat_id = None
                tip_cat_id = None

                for group, cats in categories.items():
                    for cat in cats:
                        if 'Dining Out' in cat['name']:
                            dining_cat_id = cat['id']
                        elif 'Tips' in cat['name'] or 'Tip' in cat['name']:
                            tip_cat_id = cat['id']

                # If no tip category, just use dining for all
                if not tip_cat_id:
                    return None

                return [
                    SplitSuggestion(
                        amount=round(base_amount, 2),
                        category_id=dining_cat_id,
                        category_name='Dining Out',
                        memo='Food and drinks',
                        confidence=70
                    ),
                    SplitSuggestion(
                        amount=round(tip_amount, 2),
                        category_id=tip_cat_id,
                        category_name='Tips',
                        memo=f'Estimated {int(tip_percentage*100)}% tip',
                        confidence=65
                    )
                ]

        return None

    def _should_split_by_amount(self, transaction: Transaction) -> bool:
        """Check if transaction amount suggests it should be split"""
        amount = abs(transaction.amount)

        # Check against default threshold
        if amount >= self.amount_thresholds['default']:
            # Additional checks
            memo_lower = (transaction.memo or '').lower()
            if any(word in memo_lower for word in ['multiple', 'various', 'mixed', 'assorted']):
                return True

            # Check if it's a round number (less likely to be single item)
            if amount % 50 == 0 and amount >= 200:
                return True

        return False

    def _suggest_generic_split(self, transaction: Transaction) -> List[SplitSuggestion]:
        """Suggest a generic split for high-amount transactions"""
        amount = abs(transaction.amount)

        # Get category map using cached helper (no API call)
        category_map = self._get_category_map()

        # Generic 60/40 split
        return [
            SplitSuggestion(
                amount=amount * 0.6,
                category_id=category_map.get('Shopping'),
                category_name='Shopping',
                memo='Primary purchase',
                confidence=50
            ),
            SplitSuggestion(
                amount=amount * 0.4,
                category_id=category_map.get('Household Goods'),
                category_name='Household Goods',
                memo='Additional items',
                confidence=50
            )
        ]

    def format_split_for_api(self, suggestions: List[SplitSuggestion]) -> List[Dict]:
        """
        Format split suggestions for YNAB API

        Args:
            suggestions: List of split suggestions

        Returns:
            List of dictionaries formatted for API
        """
        splits = []
        for suggestion in suggestions:
            splits.append({
                'amount': -abs(suggestion.amount),  # Negative for expenses
                'category_id': suggestion.category_id,
                'memo': suggestion.memo
            })

        return splits