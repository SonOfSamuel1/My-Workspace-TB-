"""
Smart Suggestion Engine

Provides intelligent category suggestions based on merchant identification,
historical patterns, and amount analysis.
"""

import json
import logging
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from dataclasses import dataclass

from ynab_service import Transaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CategorySuggestion:
    """Represents a category suggestion with confidence"""
    category_id: str
    category_name: str
    confidence: float
    reason: str
    based_on_count: int = 0


class SuggestionEngine:
    """Generates smart category suggestions for transactions"""

    def __init__(self, ynab_service, merchant_db_file: str = None):
        """
        Initialize suggestion engine

        Args:
            ynab_service: YNAB service instance
            merchant_db_file: Path to merchant database file
        """
        self.ynab = ynab_service
        self.merchant_db_file = merchant_db_file or 'data/merchants.json'
        self.merchant_db = self._load_merchant_db()
        self._build_merchant_patterns()

    def _load_merchant_db(self) -> Dict:
        """Load merchant database from file"""
        db_path = Path(self.merchant_db_file)
        if db_path.exists():
            try:
                with open(db_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load merchant database: {e}")

        # Default database structure
        return {
            'known_merchants': {},  # payee_name: {category_id, category_name, count}
            'merchant_patterns': {},  # pattern: {category_id, category_name, confidence}
            'category_stats': {},  # category_id: {avg_amount, min_amount, max_amount}
            'last_updated': None
        }

    def _save_merchant_db(self):
        """Save merchant database to file"""
        db_path = Path(self.merchant_db_file)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.merchant_db['last_updated'] = datetime.now().isoformat()
        with open(db_path, 'w') as f:
            json.dump(self.merchant_db, f, indent=2)

    def _build_merchant_patterns(self):
        """Build regex patterns for common merchant types"""
        self.merchant_type_patterns = {
            'grocery': re.compile(
                r'(whole foods|kroger|publix|safeway|trader joe|'
                r'supermarket|grocery|market|food lion|wegmans|'
                r'aldi|harris teeter|fresh market)',
                re.IGNORECASE
            ),
            'gas_station': re.compile(
                r'(shell|exxon|mobil|bp|chevron|texaco|citgo|'
                r'gas station|fuel|petroleum|7-eleven|wawa|sheetz)',
                re.IGNORECASE
            ),
            'restaurant': re.compile(
                r'(restaurant|cafe|coffee|starbucks|dunkin|mcdonald|'
                r'burger|pizza|sushi|thai|chinese|mexican|italian|'
                r'bar|grill|kitchen|bistro|diner|chick-fil-a|chipotle)',
                re.IGNORECASE
            ),
            'pharmacy': re.compile(
                r'(cvs|walgreens|rite aid|pharmacy|drugstore|rx)',
                re.IGNORECASE
            ),
            'entertainment': re.compile(
                r'(netflix|spotify|hulu|disney|amazon prime|apple music|'
                r'youtube|hbo|movie|theater|cinema|concert|ticket)',
                re.IGNORECASE
            ),
            'utilities': re.compile(
                r'(electric|power|water|gas company|utility|internet|'
                r'comcast|verizon|at&t|t-mobile|sprint)',
                re.IGNORECASE
            ),
            'shopping': re.compile(
                r'(amazon|walmart|target|best buy|home depot|lowes|'
                r'costco|sam\'s club|tj maxx|marshalls|nordstrom|'
                r'macy\'s|old navy|gap|nike|apple store)',
                re.IGNORECASE
            ),
            'transportation': re.compile(
                r'(uber|lyft|taxi|parking|toll|metro|subway|train|'
                r'airline|delta|united|southwest|amtrak)',
                re.IGNORECASE
            ),
            'healthcare': re.compile(
                r'(hospital|clinic|doctor|dentist|medical|health|'
                r'lab|radiology|urgent care|physician)',
                re.IGNORECASE
            ),
            'fitness': re.compile(
                r'(gym|fitness|yoga|pilates|crossfit|planet fitness|'
                r'la fitness|equinox|orange theory|peloton)',
                re.IGNORECASE
            )
        }

        # Category mappings for merchant types
        self.type_to_category_hints = {
            'grocery': 'Groceries',
            'gas_station': 'Auto & Transport: Gas',
            'restaurant': 'Dining Out',
            'pharmacy': 'Medical & Healthcare',
            'entertainment': 'Entertainment',
            'utilities': 'Bills & Utilities',
            'shopping': 'Shopping',
            'transportation': 'Auto & Transport',
            'healthcare': 'Medical & Healthcare',
            'fitness': 'Health & Fitness'
        }

    def suggest_category(self, transaction: Transaction) -> List[CategorySuggestion]:
        """
        Generate category suggestions for a transaction

        Args:
            transaction: Transaction to analyze

        Returns:
            List of category suggestions ordered by confidence
        """
        suggestions = []

        # 1. Check exact payee match in known merchants
        exact_suggestion = self._check_known_merchant(transaction)
        if exact_suggestion:
            suggestions.append(exact_suggestion)

        # 2. Check historical patterns for this payee
        historical_suggestion = self._check_historical_patterns(transaction)
        if historical_suggestion:
            suggestions.append(historical_suggestion)

        # 3. Check merchant type patterns
        type_suggestion = self._check_merchant_type(transaction)
        if type_suggestion:
            suggestions.append(type_suggestion)

        # 4. Check amount-based patterns
        amount_suggestion = self._check_amount_patterns(transaction)
        if amount_suggestion:
            suggestions.append(amount_suggestion)

        # Remove duplicates and sort by confidence
        unique_suggestions = {}
        for suggestion in suggestions:
            if suggestion.category_id not in unique_suggestions:
                unique_suggestions[suggestion.category_id] = suggestion
            else:
                # Keep higher confidence one
                if suggestion.confidence > unique_suggestions[suggestion.category_id].confidence:
                    unique_suggestions[suggestion.category_id] = suggestion

        # Sort by confidence (highest first)
        sorted_suggestions = sorted(
            unique_suggestions.values(),
            key=lambda s: s.confidence,
            reverse=True
        )

        return sorted_suggestions[:3]  # Return top 3 suggestions

    def _check_known_merchant(self, transaction: Transaction) -> Optional[CategorySuggestion]:
        """Check if merchant is in known database"""
        payee_lower = transaction.payee_name.lower()

        if payee_lower in self.merchant_db['known_merchants']:
            merchant_info = self.merchant_db['known_merchants'][payee_lower]
            count = merchant_info.get('count', 0)

            # Higher confidence if we've seen this merchant more often
            confidence = min(95, 70 + (count * 2))

            return CategorySuggestion(
                category_id=merchant_info['category_id'],
                category_name=merchant_info['category_name'],
                confidence=confidence,
                reason=f"Based on {count} previous transactions at {transaction.payee_name}",
                based_on_count=count
            )

        return None

    def _check_historical_patterns(self, transaction: Transaction) -> Optional[CategorySuggestion]:
        """Check historical patterns for this payee"""
        history = self.ynab.get_transaction_history_for_payee(
            transaction.payee_name,
            limit=20
        )

        if not history:
            return None

        # Count categories used for this payee
        category_counts = Counter()
        for hist_txn in history:
            if hist_txn.category_name:
                category_counts[hist_txn.category_name] += 1

        if not category_counts:
            return None

        # Get most common category
        most_common = category_counts.most_common(1)[0]
        category_name = most_common[0]
        count = most_common[1]

        # Calculate confidence based on consistency
        total_categorized = sum(category_counts.values())
        consistency = count / total_categorized
        confidence = min(90, consistency * 100)

        # Find category ID
        categories = self.ynab.get_categories()
        category_id = None
        for group, cats in categories.items():
            for cat in cats:
                if cat['name'] == category_name:
                    category_id = cat['id']
                    break

        if category_id:
            return CategorySuggestion(
                category_id=category_id,
                category_name=category_name,
                confidence=confidence,
                reason=f"Most common category for {transaction.payee_name} ({count}/{total_categorized} times)",
                based_on_count=count
            )

        return None

    def _check_merchant_type(self, transaction: Transaction) -> Optional[CategorySuggestion]:
        """Check merchant type patterns"""
        payee_lower = transaction.payee_name.lower()

        for merchant_type, pattern in self.merchant_type_patterns.items():
            if pattern.search(payee_lower):
                # Get suggested category for this type
                suggested_category = self.type_to_category_hints.get(merchant_type)

                if suggested_category:
                    # Find category ID
                    categories = self.ynab.get_categories()
                    for group, cats in categories.items():
                        for cat in cats:
                            if suggested_category in cat['name']:
                                return CategorySuggestion(
                                    category_id=cat['id'],
                                    category_name=cat['name'],
                                    confidence=75,
                                    reason=f"Merchant type detected: {merchant_type.replace('_', ' ').title()}"
                                )

        return None

    def _check_amount_patterns(self, transaction: Transaction) -> Optional[CategorySuggestion]:
        """Check amount-based patterns"""
        amount = abs(transaction.amount)

        # Common amount patterns
        patterns = [
            (1, 5, 'Coffee Shops', 80),
            (5, 15, 'Fast Food', 70),
            (15, 30, 'Lunch', 65),
            (30, 80, 'Dining Out', 60),
            (20, 60, 'Auto & Transport: Gas', 65),
            (80, 200, 'Groceries', 60),
            (200, 500, 'Shopping', 55),
        ]

        for min_amt, max_amt, category_hint, confidence in patterns:
            if min_amt <= amount <= max_amt:
                # Check if this matches merchant type too
                if self._matches_merchant_context(transaction, category_hint):
                    confidence += 10

                # Find category ID
                categories = self.ynab.get_categories()
                for group, cats in categories.items():
                    for cat in cats:
                        if category_hint in cat['name']:
                            return CategorySuggestion(
                                category_id=cat['id'],
                                category_name=cat['name'],
                                confidence=min(85, confidence),
                                reason=f"Amount pattern suggests {category_hint} (${amount:.2f})"
                            )

        return None

    def _matches_merchant_context(self, transaction: Transaction, category_hint: str) -> bool:
        """Check if merchant name matches expected context for category"""
        payee_lower = transaction.payee_name.lower()
        hint_lower = category_hint.lower()

        # Simple keyword matching
        if 'coffee' in hint_lower and any(word in payee_lower for word in ['coffee', 'cafe', 'starbucks']):
            return True
        if 'gas' in hint_lower and any(word in payee_lower for word in ['gas', 'fuel', 'shell', 'exxon']):
            return True
        if 'groceries' in hint_lower and any(word in payee_lower for word in ['market', 'grocery', 'foods']):
            return True
        if 'dining' in hint_lower and any(word in payee_lower for word in ['restaurant', 'grill', 'kitchen']):
            return True

        return False

    def learn_from_categorization(self,
                                 transaction: Transaction,
                                 category_id: str,
                                 category_name: str):
        """
        Learn from user's categorization choice

        Args:
            transaction: Categorized transaction
            category_id: Chosen category ID
            category_name: Chosen category name
        """
        payee_lower = transaction.payee_name.lower()

        # Update known merchants
        if payee_lower not in self.merchant_db['known_merchants']:
            self.merchant_db['known_merchants'][payee_lower] = {
                'category_id': category_id,
                'category_name': category_name,
                'count': 1
            }
        else:
            merchant_info = self.merchant_db['known_merchants'][payee_lower]
            if merchant_info['category_id'] == category_id:
                merchant_info['count'] += 1
            else:
                # Different category chosen - update if this is more common
                if merchant_info['count'] < 3:
                    merchant_info['category_id'] = category_id
                    merchant_info['category_name'] = category_name
                    merchant_info['count'] = 1

        # Update category statistics
        if category_id not in self.merchant_db['category_stats']:
            self.merchant_db['category_stats'][category_id] = {
                'total_amount': 0,
                'count': 0,
                'amounts': []
            }

        stats = self.merchant_db['category_stats'][category_id]
        stats['total_amount'] += abs(transaction.amount)
        stats['count'] += 1
        stats['amounts'].append(abs(transaction.amount))

        # Keep only last 100 amounts for statistics
        if len(stats['amounts']) > 100:
            stats['amounts'] = stats['amounts'][-100:]

        # Calculate statistics
        if stats['amounts']:
            stats['avg_amount'] = stats['total_amount'] / stats['count']
            stats['min_amount'] = min(stats['amounts'])
            stats['max_amount'] = max(stats['amounts'])

        self._save_merchant_db()
        logger.info(f"Learned categorization: {transaction.payee_name} -> {category_name}")

    def get_merchant_stats(self) -> Dict:
        """Get merchant database statistics"""
        return {
            'total_known_merchants': len(self.merchant_db['known_merchants']),
            'total_patterns': len(self.merchant_db['merchant_patterns']),
            'categories_tracked': len(self.merchant_db['category_stats']),
            'last_updated': self.merchant_db.get('last_updated')
        }