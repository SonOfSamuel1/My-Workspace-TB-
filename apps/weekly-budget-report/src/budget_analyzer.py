"""
Budget Analyzer

Analyzes YNAB transactions and budget data to generate insights
for the weekly budget report.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import pytz


class BudgetAnalyzer:
    """Analyzes budget data and generates insights."""

    def __init__(self, config: Dict):
        """Initialize budget analyzer.

        Args:
            config: Configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.report_config = config.get('budget_report', {}).get('report', {})

    def analyze_transactions(
        self,
        transactions: List[Dict],
        categories: List[Dict],
        payees: List[Dict],
        accounts: List[Dict],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Analyze transactions for the reporting period.

        Args:
            transactions: List of transaction dictionaries
            categories: List of category group dictionaries
            payees: List of payee dictionaries
            accounts: List of account dictionaries
            start_date: Start of reporting period
            end_date: End of reporting period

        Returns:
            Dictionary with analysis results
        """
        self.logger.info(f"Analyzing transactions from {start_date} to {end_date}...")

        # Build lookup dictionaries
        category_map = self._build_category_map(categories)
        payee_map = {p['id']: p for p in payees}
        account_map = {a['id']: a for a in accounts}

        # Filter transactions for the reporting period
        period_transactions = self._filter_transactions_by_date(
            transactions, start_date, end_date
        )

        # Calculate summary statistics
        summary = self._calculate_summary(period_transactions, category_map)

        # Analyze by category
        category_breakdown = self._analyze_by_category(
            period_transactions, category_map
        )

        # Analyze by payee
        payee_breakdown = self._analyze_by_payee(
            period_transactions, payee_map
        )

        # Find notable transactions
        notable_transactions = self._find_notable_transactions(
            period_transactions, category_map, payee_map
        )

        # Analyze by account
        account_breakdown = self._analyze_by_account(
            period_transactions, account_map
        )

        return {
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'days': (end_date - start_date).days
            },
            'summary': summary,
            'category_breakdown': category_breakdown,
            'payee_breakdown': payee_breakdown,
            'account_breakdown': account_breakdown,
            'notable_transactions': notable_transactions,
            'transaction_count': len(period_transactions)
        }

    def compare_to_budget(
        self,
        category_breakdown: Dict,
        month_budget: Dict
    ) -> Dict[str, Any]:
        """Compare actual spending to budgeted amounts.

        Args:
            category_breakdown: Category spending breakdown
            month_budget: Month budget data from YNAB

        Returns:
            Dictionary with budget comparison results
        """
        self.logger.info("Comparing spending to budget...")

        comparisons = []
        total_budgeted = 0
        total_spent = 0

        for category_data in month_budget.get('categories', []):
            category_id = category_data['id']
            category_name = category_data['name']
            budgeted = category_data.get('budgeted', 0) / 1000.0  # Convert to dollars
            activity = abs(category_data.get('activity', 0) / 1000.0)  # Convert to dollars

            if budgeted > 0:
                total_budgeted += budgeted
                total_spent += activity

                percentage_used = (activity / budgeted * 100) if budgeted > 0 else 0
                remaining = budgeted - activity

                comparisons.append({
                    'category_id': category_id,
                    'category_name': category_name,
                    'budgeted': budgeted,
                    'spent': activity,
                    'remaining': remaining,
                    'percentage_used': percentage_used,
                    'over_budget': activity > budgeted
                })

        # Sort by percentage used (descending)
        comparisons.sort(key=lambda x: x['percentage_used'], reverse=True)

        return {
            'total_budgeted': total_budgeted,
            'total_spent': total_spent,
            'total_remaining': total_budgeted - total_spent,
            'overall_percentage_used': (total_spent / total_budgeted * 100) if total_budgeted > 0 else 0,
            'categories': comparisons
        }

    def generate_alerts(
        self,
        budget_comparison: Dict,
        category_breakdown: Dict
    ) -> List[Dict[str, str]]:
        """Generate alerts based on spending patterns.

        Args:
            budget_comparison: Budget comparison results
            category_breakdown: Category spending breakdown

        Returns:
            List of alert dictionaries
        """
        alerts = []
        thresholds = self.config.get('budget_report', {}).get('alerts', {})

        overspending_threshold = thresholds.get('overspending_threshold', 10)
        total_threshold = thresholds.get('total_spending_threshold', 90)

        # Check overall spending
        overall_pct = budget_comparison.get('overall_percentage_used', 0)
        if overall_pct >= total_threshold:
            alerts.append({
                'level': 'warning' if overall_pct < 100 else 'critical',
                'category': 'Overall Budget',
                'message': f'Overall spending at {overall_pct:.1f}% of budget'
            })

        # Check category overspending
        for category in budget_comparison.get('categories', []):
            if category['over_budget']:
                overspend_amount = category['spent'] - category['budgeted']
                overspend_pct = (overspend_amount / category['budgeted'] * 100)

                if overspend_pct >= overspending_threshold:
                    alerts.append({
                        'level': 'critical',
                        'category': category['category_name'],
                        'message': f'Over budget by ${overspend_amount:.2f} ({overspend_pct:.1f}%)'
                    })

        return alerts

    def _build_category_map(self, category_groups: List[Dict]) -> Dict[str, Dict]:
        """Build a flat map of category IDs to category info.

        Args:
            category_groups: List of category group dictionaries

        Returns:
            Dictionary mapping category ID to category info
        """
        category_map = {}
        for group in category_groups:
            group_name = group['name']
            for category in group.get('categories', []):
                category_map[category['id']] = {
                    'id': category['id'],
                    'name': category['name'],
                    'group': group_name,
                    'hidden': category.get('hidden', False),
                    'deleted': category.get('deleted', False)
                }
        return category_map

    def _filter_transactions_by_date(
        self,
        transactions: List[Dict],
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Filter transactions by date range.

        Args:
            transactions: List of all transactions
            start_date: Start of period
            end_date: End of period

        Returns:
            Filtered list of transactions
        """
        filtered = []
        # Strip timezone info for comparison since YNAB dates are naive
        start_naive = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
        end_naive = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date

        for txn in transactions:
            txn_date = datetime.strptime(txn['date'], '%Y-%m-%d')
            if start_naive <= txn_date <= end_naive:
                filtered.append(txn)
        return filtered

    def _calculate_summary(
        self,
        transactions: List[Dict],
        category_map: Dict[str, Dict]
    ) -> Dict[str, float]:
        """Calculate summary statistics.

        Args:
            transactions: List of transactions
            category_map: Category ID to info mapping

        Returns:
            Summary statistics dictionary
        """
        total_inflow = 0
        total_outflow = 0
        total_net = 0

        exclude_categories = self.report_config.get('exclude_categories', [])

        for txn in transactions:
            # Skip transfers and excluded categories
            if txn.get('transfer_account_id'):
                continue

            category_id = txn.get('category_id')
            if category_id and category_id in category_map:
                category_name = category_map[category_id]['name']
                if category_name in exclude_categories:
                    continue

            amount = txn['amount'] / 1000.0  # Convert to dollars

            if amount > 0:
                total_inflow += amount
            else:
                total_outflow += abs(amount)

            total_net += amount

        return {
            'total_inflow': total_inflow,
            'total_outflow': total_outflow,
            'net': total_net,
            'transaction_count': len(transactions)
        }

    def _analyze_by_category(
        self,
        transactions: List[Dict],
        category_map: Dict[str, Dict]
    ) -> List[Dict]:
        """Analyze spending by category.

        Args:
            transactions: List of transactions
            category_map: Category ID to info mapping

        Returns:
            List of category spending dictionaries
        """
        category_spending = defaultdict(lambda: {'amount': 0, 'count': 0})

        exclude_categories = self.report_config.get('exclude_categories', [])

        for txn in transactions:
            # Skip transfers
            if txn.get('transfer_account_id'):
                continue

            category_id = txn.get('category_id')
            if not category_id or category_id not in category_map:
                category_id = 'uncategorized'
                category_name = 'Uncategorized'
                category_group = 'Other'
            else:
                category_info = category_map[category_id]
                category_name = category_info['name']
                category_group = category_info['group']

                if category_name in exclude_categories:
                    continue

            amount = abs(txn['amount'] / 1000.0)  # Convert to dollars

            # Only count outflows
            if txn['amount'] < 0:
                category_spending[category_id]['amount'] += amount
                category_spending[category_id]['count'] += 1
                category_spending[category_id]['name'] = category_name
                category_spending[category_id]['group'] = category_group

        # Convert to list and sort by amount
        result = [
            {
                'category_id': cat_id,
                'category_name': data['name'],
                'category_group': data['group'],
                'amount': data['amount'],
                'transaction_count': data['count']
            }
            for cat_id, data in category_spending.items()
        ]
        result.sort(key=lambda x: x['amount'], reverse=True)

        # Limit to top N categories
        top_n = self.report_config.get('top_categories_count', 10)
        return result[:top_n]

    def _analyze_by_payee(
        self,
        transactions: List[Dict],
        payee_map: Dict[str, Dict]
    ) -> List[Dict]:
        """Analyze spending by payee.

        Args:
            transactions: List of transactions
            payee_map: Payee ID to info mapping

        Returns:
            List of payee spending dictionaries
        """
        payee_spending = defaultdict(lambda: {'amount': 0, 'count': 0})

        for txn in transactions:
            # Skip transfers and inflows
            if txn.get('transfer_account_id') or txn['amount'] > 0:
                continue

            payee_id = txn.get('payee_id')
            if not payee_id or payee_id not in payee_map:
                payee_name = txn.get('payee_name', 'Unknown')
            else:
                payee_name = payee_map[payee_id].get('name', 'Unknown')

            amount = abs(txn['amount'] / 1000.0)

            payee_spending[payee_name]['amount'] += amount
            payee_spending[payee_name]['count'] += 1

        # Convert to list and sort by amount
        result = [
            {
                'payee_name': name,
                'amount': data['amount'],
                'transaction_count': data['count']
            }
            for name, data in payee_spending.items()
        ]
        result.sort(key=lambda x: x['amount'], reverse=True)

        # Limit to top N payees
        top_n = self.report_config.get('top_payees_count', 10)
        return result[:top_n]

    def _find_notable_transactions(
        self,
        transactions: List[Dict],
        category_map: Dict[str, Dict],
        payee_map: Dict[str, Dict]
    ) -> List[Dict]:
        """Find notable (large) transactions.

        Args:
            transactions: List of transactions
            category_map: Category ID to info mapping
            payee_map: Payee ID to info mapping

        Returns:
            List of notable transaction dictionaries
        """
        threshold = self.report_config.get('notable_transaction_threshold', 100)
        notable = []

        for txn in transactions:
            amount = abs(txn['amount'] / 1000.0)

            if amount >= threshold:
                # Get category name
                category_id = txn.get('category_id')
                if category_id and category_id in category_map:
                    category_name = category_map[category_id]['name']
                else:
                    category_name = 'Uncategorized'

                # Get payee name
                payee_id = txn.get('payee_id')
                if payee_id and payee_id in payee_map:
                    payee_name = payee_map[payee_id].get('name', 'Unknown')
                else:
                    payee_name = txn.get('payee_name', 'Unknown')

                notable.append({
                    'id': txn['id'],
                    'date': txn['date'],
                    'payee': payee_name,
                    'category': category_name,
                    'amount': amount,
                    'memo': txn.get('memo', ''),
                    'is_inflow': txn['amount'] > 0
                })

        # Sort by amount (descending)
        notable.sort(key=lambda x: x['amount'], reverse=True)
        return notable

    def _analyze_by_account(
        self,
        transactions: List[Dict],
        account_map: Dict[str, Dict]
    ) -> List[Dict]:
        """Analyze spending by account.

        Args:
            transactions: List of transactions
            account_map: Account ID to info mapping

        Returns:
            List of account activity dictionaries
        """
        account_activity = defaultdict(lambda: {'inflow': 0, 'outflow': 0, 'count': 0})

        for txn in transactions:
            account_id = txn.get('account_id')
            if not account_id or account_id not in account_map:
                continue

            account_name = account_map[account_id].get('name', 'Unknown')
            amount = txn['amount'] / 1000.0

            if amount > 0:
                account_activity[account_name]['inflow'] += amount
            else:
                account_activity[account_name]['outflow'] += abs(amount)

            account_activity[account_name]['count'] += 1

        # Convert to list and sort by outflow
        result = [
            {
                'account_name': name,
                'inflow': data['inflow'],
                'outflow': data['outflow'],
                'net': data['inflow'] - data['outflow'],
                'transaction_count': data['count']
            }
            for name, data in account_activity.items()
        ]
        result.sort(key=lambda x: x['outflow'], reverse=True)

        return result
