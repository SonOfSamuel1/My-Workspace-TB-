"""
Budget Analyzer

Analyzes YNAB transactions and budget data to generate insights
for the weekly budget report, including Tiller-style annual budget tracking.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
from calendar import monthrange
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

    # =========================================================================
    # Annual Budget Analysis Methods (Tiller-Style Dashboard)
    # =========================================================================

    def calculate_annual_budget(
        self,
        annual_budget_data: Dict[str, Dict],
        year: int
    ) -> Dict[str, Any]:
        """Calculate annual budget totals and summaries.

        Args:
            annual_budget_data: Aggregated annual budget from YNAB service
            year: The year being analyzed

        Returns:
            Dictionary with annual budget summary:
            {
                'year': int,
                'total_budgeted': float,
                'total_spent': float,
                'total_remaining': float,
                'categories': List of category summaries
            }
        """
        self.logger.info(f"Calculating annual budget for {year}...")

        total_budgeted = 0
        total_spent = 0
        categories = []

        exclude_categories = self.report_config.get('exclude_categories', [])

        for cat_id, cat_data in annual_budget_data.items():
            cat_name = cat_data['name']

            # Skip excluded categories
            if cat_name in exclude_categories:
                continue

            annual_budgeted = cat_data['annual_budgeted']
            annual_spent = cat_data['annual_activity']

            # Only include categories with a budget
            if annual_budgeted > 0:
                total_budgeted += annual_budgeted
                total_spent += annual_spent

                categories.append({
                    'category_id': cat_id,
                    'name': cat_name,
                    'annual_budgeted': annual_budgeted,
                    'annual_spent': annual_spent,
                    'remaining': annual_budgeted - annual_spent,
                    'percentage_used': (annual_spent / annual_budgeted * 100) if annual_budgeted > 0 else 0,
                    'monthly_breakdown': cat_data.get('monthly_breakdown', {})
                })

        # Sort by annual spent (descending)
        categories.sort(key=lambda x: x['annual_spent'], reverse=True)

        return {
            'year': year,
            'total_budgeted': total_budgeted,
            'total_spent': total_spent,
            'total_remaining': total_budgeted - total_spent,
            'overall_percentage_used': (total_spent / total_budgeted * 100) if total_budgeted > 0 else 0,
            'categories': categories
        }

    def calculate_ytd_spending(
        self,
        transactions: List[Dict],
        categories: List[Dict],
        year: int
    ) -> Dict[str, Any]:
        """Calculate year-to-date spending by category.

        Args:
            transactions: List of transactions for the year
            categories: Category groups from YNAB
            year: The year being analyzed

        Returns:
            Dictionary with YTD spending summary
        """
        self.logger.info(f"Calculating YTD spending for {year}...")

        category_map = self._build_category_map(categories)
        exclude_categories = self.report_config.get('exclude_categories', [])

        # Calculate days elapsed in year
        now = datetime.now()
        year_start = datetime(year, 1, 1)

        if year == now.year:
            days_elapsed = (now - year_start).days + 1
            days_in_year = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
            days_remaining = days_in_year - days_elapsed
        else:
            days_elapsed = 365
            days_remaining = 0
            days_in_year = 365

        # Aggregate spending by category
        ytd_by_category = defaultdict(lambda: {'spent': 0, 'count': 0})
        total_income = 0
        total_expenses = 0

        for txn in transactions:
            # Skip transfers
            if txn.get('transfer_account_id'):
                continue

            amount = txn['amount'] / 1000.0  # Convert to dollars

            category_id = txn.get('category_id')
            if category_id and category_id in category_map:
                cat_name = category_map[category_id]['name']
                if cat_name in exclude_categories:
                    continue
            else:
                cat_name = 'Uncategorized'

            if amount > 0:
                total_income += amount
            else:
                total_expenses += abs(amount)
                ytd_by_category[cat_name]['spent'] += abs(amount)
                ytd_by_category[cat_name]['count'] += 1

        # Calculate monthly averages
        months_elapsed = now.month if year == now.year else 12
        avg_monthly_income = total_income / months_elapsed if months_elapsed > 0 else 0
        avg_monthly_expenses = total_expenses / months_elapsed if months_elapsed > 0 else 0

        # Convert to list and sort
        category_list = [
            {
                'category': name,
                'ytd_spent': data['spent'],
                'transaction_count': data['count'],
                'monthly_average': data['spent'] / months_elapsed if months_elapsed > 0 else 0
            }
            for name, data in ytd_by_category.items()
        ]
        category_list.sort(key=lambda x: x['ytd_spent'], reverse=True)

        return {
            'year': year,
            'days_elapsed': days_elapsed,
            'days_remaining': days_remaining,
            'months_elapsed': months_elapsed,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_savings': total_income - total_expenses,
            'savings_rate': ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0,
            'avg_monthly_income': avg_monthly_income,
            'avg_monthly_expenses': avg_monthly_expenses,
            'categories': category_list
        }

    def calculate_monthly_breakdown(
        self,
        transactions: List[Dict],
        categories: List[Dict],
        year: int
    ) -> Dict[str, Dict]:
        """Calculate spending breakdown by month for each category.

        Args:
            transactions: List of transactions for the year
            categories: Category groups from YNAB
            year: The year being analyzed

        Returns:
            Dictionary mapping category name to monthly breakdown
        """
        self.logger.info(f"Calculating monthly breakdown for {year}...")

        category_map = self._build_category_map(categories)
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        # Initialize breakdown structure
        breakdown = defaultdict(lambda: {m: 0 for m in month_names})

        exclude_categories = self.report_config.get('exclude_categories', [])

        for txn in transactions:
            # Skip transfers and inflows
            if txn.get('transfer_account_id') or txn['amount'] > 0:
                continue

            # Parse month from date
            txn_date = datetime.strptime(txn['date'], '%Y-%m-%d')
            month_name = month_names[txn_date.month - 1]

            # Get category name
            category_id = txn.get('category_id')
            if category_id and category_id in category_map:
                cat_name = category_map[category_id]['name']
                if cat_name in exclude_categories:
                    continue
            else:
                cat_name = 'Uncategorized'

            amount = abs(txn['amount'] / 1000.0)
            breakdown[cat_name][month_name] += amount

        return dict(breakdown)

    def project_year_end_spending(
        self,
        annual_budget: Dict[str, Any],
        ytd_spending: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Project year-end spending based on current pace.

        Args:
            annual_budget: Annual budget summary
            ytd_spending: YTD spending summary

        Returns:
            Dictionary with projections for each category
        """
        self.logger.info("Calculating year-end projections...")

        days_elapsed = ytd_spending['days_elapsed']
        days_remaining = ytd_spending['days_remaining']
        total_days = days_elapsed + days_remaining

        if days_elapsed == 0:
            return {'categories': [], 'summary': {}}

        projections = []
        total_projected_spending = 0
        total_annual_budget = annual_budget['total_budgeted']

        for category in annual_budget['categories']:
            cat_name = category['name']
            annual_budgeted = category['annual_budgeted']
            current_spent = category['annual_spent']

            # Calculate daily spending rate
            daily_rate = current_spent / days_elapsed

            # Project to year end
            projected_spending = daily_rate * total_days
            projected_remaining = annual_budgeted - projected_spending

            # Determine pace status
            expected_pct_elapsed = (days_elapsed / total_days) * 100
            actual_pct_used = category['percentage_used']
            pace_ratio = actual_pct_used / expected_pct_elapsed if expected_pct_elapsed > 0 else 0

            pace_status = self._determine_pace_status(pace_ratio)

            projections.append({
                'category': cat_name,
                'annual_budget': annual_budgeted,
                'ytd_spent': current_spent,
                'daily_rate': daily_rate,
                'projected_spending': projected_spending,
                'projected_remaining': projected_remaining,
                'projected_over_under': projected_remaining,  # Positive = under, negative = over
                'pace_ratio': pace_ratio,
                'pace_status': pace_status,
                'expected_pct_elapsed': expected_pct_elapsed,
                'actual_pct_used': actual_pct_used
            })

            total_projected_spending += projected_spending

        # Sort by projected over/under (most over budget first)
        projections.sort(key=lambda x: x['projected_remaining'])

        # Summary stats
        return {
            'categories': projections,
            'summary': {
                'total_annual_budget': total_annual_budget,
                'total_projected_spending': total_projected_spending,
                'projected_surplus_deficit': total_annual_budget - total_projected_spending,
                'days_elapsed': days_elapsed,
                'days_remaining': days_remaining,
                'pct_year_elapsed': (days_elapsed / total_days) * 100
            }
        }

    def _determine_pace_status(self, pace_ratio: float) -> str:
        """Determine pace status based on ratio of actual vs expected spending.

        Args:
            pace_ratio: Ratio of actual % used to expected % elapsed

        Returns:
            Status string: 'on_track', 'warning', 'danger', or 'under_budget'
        """
        annual_config = self.config.get('annual_budget', {})
        warning_threshold = annual_config.get('pace_warning_threshold', 0.8)
        danger_threshold = annual_config.get('pace_danger_threshold', 1.0)

        if pace_ratio >= danger_threshold:
            return 'danger'  # Over pace - will exceed budget
        elif pace_ratio >= warning_threshold:
            return 'warning'  # Approaching budget
        elif pace_ratio < 0.5:
            return 'under_budget'  # Significantly under
        else:
            return 'on_track'  # Within expected range

    def calculate_annual_remaining(
        self,
        annual_budget: Dict[str, Any],
        ytd_spending: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate remaining budget for the year.

        Args:
            annual_budget: Annual budget summary
            ytd_spending: YTD spending summary

        Returns:
            Dictionary with remaining budget analysis
        """
        self.logger.info("Calculating annual remaining budget...")

        days_remaining = ytd_spending['days_remaining']
        remaining_analysis = []

        for category in annual_budget['categories']:
            cat_name = category['name']
            remaining = category['remaining']

            # Calculate daily budget remaining
            daily_remaining = remaining / days_remaining if days_remaining > 0 else 0

            remaining_analysis.append({
                'category': cat_name,
                'annual_budget': category['annual_budgeted'],
                'spent': category['annual_spent'],
                'remaining': remaining,
                'daily_remaining': daily_remaining,
                'is_over_budget': remaining < 0
            })

        # Sort by remaining (lowest first to highlight problem areas)
        remaining_analysis.sort(key=lambda x: x['remaining'])

        return {
            'categories': remaining_analysis,
            'total_remaining': annual_budget['total_remaining'],
            'days_remaining': days_remaining
        }

    def generate_annual_alerts(
        self,
        annual_budget: Dict[str, Any],
        projections: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate alerts based on annual budget performance.

        Args:
            annual_budget: Annual budget summary
            projections: Year-end projections

        Returns:
            List of alert dictionaries
        """
        alerts = []
        pct_year_elapsed = projections['summary'].get('pct_year_elapsed', 0)

        for projection in projections.get('categories', []):
            cat_name = projection['category']
            pace_status = projection['pace_status']
            actual_pct = projection['actual_pct_used']
            projected_over = -projection['projected_remaining']  # Negative remaining = over budget

            if pace_status == 'danger':
                if projected_over > 0:
                    alerts.append({
                        'level': 'critical',
                        'category': cat_name,
                        'message': f'{actual_pct:.0f}% of annual budget used with {100-pct_year_elapsed:.0f}% of year remaining. '
                                   f'Projected ${projected_over:,.0f} over budget.'
                    })
                else:
                    alerts.append({
                        'level': 'critical',
                        'category': cat_name,
                        'message': f'Spending rate exceeds budget pace ({actual_pct:.0f}% used vs {pct_year_elapsed:.0f}% of year elapsed)'
                    })
            elif pace_status == 'warning':
                alerts.append({
                    'level': 'warning',
                    'category': cat_name,
                    'message': f'Approaching annual budget limit ({actual_pct:.0f}% used with {100-pct_year_elapsed:.0f}% of year remaining)'
                })

        # Overall budget alert
        overall_pct = annual_budget.get('overall_percentage_used', 0)
        if overall_pct > pct_year_elapsed * 1.1:  # 10% over pace
            projected_deficit = projections['summary'].get('projected_surplus_deficit', 0)
            if projected_deficit < 0:
                alerts.append({
                    'level': 'critical',
                    'category': 'Overall Annual Budget',
                    'message': f'On pace to exceed annual budget by ${abs(projected_deficit):,.0f}'
                })

        return alerts

    def get_pace_indicator(self, pace_status: str) -> Tuple[str, str]:
        """Get pace indicator symbol and color class.

        Args:
            pace_status: Status string from _determine_pace_status

        Returns:
            Tuple of (symbol, css_class)
        """
        indicators = {
            'danger': ('X', 'pace-danger'),
            'warning': ('!', 'pace-warning'),
            'on_track': ('OK', 'pace-ok'),
            'under_budget': ('OK', 'pace-under')
        }
        return indicators.get(pace_status, ('?', 'pace-unknown'))
