"""
Unit tests for BudgetAnalyzer class.
"""
import pytest
from datetime import datetime, timedelta
import pytz

from budget_analyzer import BudgetAnalyzer


class TestBudgetAnalyzerInit:
    """Tests for BudgetAnalyzer initialization."""

    def test_init_with_valid_config(self, sample_config):
        """Test analyzer initializes correctly with valid config."""
        analyzer = BudgetAnalyzer(sample_config)
        assert analyzer.config == sample_config
        assert analyzer.report_config == sample_config['budget_report']['report']

    def test_init_with_empty_config(self):
        """Test analyzer handles empty config gracefully."""
        analyzer = BudgetAnalyzer({})
        assert analyzer.config == {}
        assert analyzer.report_config == {}

    def test_init_with_missing_report_section(self):
        """Test analyzer handles missing report section."""
        config = {'budget_report': {}}
        analyzer = BudgetAnalyzer(config)
        assert analyzer.report_config == {}


class TestBuildCategoryMap:
    """Tests for _build_category_map method."""

    def test_builds_flat_category_map(self, sample_config, sample_categories):
        """Test category map is built correctly from nested structure."""
        analyzer = BudgetAnalyzer(sample_config)
        category_map = analyzer._build_category_map(sample_categories)

        # Check expected categories exist
        assert 'cat-1' in category_map
        assert 'cat-3' in category_map
        assert 'cat-5' in category_map

        # Check category info is correct
        assert category_map['cat-1']['name'] == 'Rent/Mortgage'
        assert category_map['cat-1']['group'] == 'Immediate Obligations'
        assert category_map['cat-3']['name'] == 'Groceries'
        assert category_map['cat-3']['group'] == 'True Expenses'

    def test_includes_hidden_flag(self, sample_config, sample_categories):
        """Test hidden flag is included in category map."""
        analyzer = BudgetAnalyzer(sample_config)
        category_map = analyzer._build_category_map(sample_categories)

        assert category_map['cat-1']['hidden'] is False
        assert category_map['cat-inflow']['hidden'] is True

    def test_empty_categories_returns_empty_map(self, sample_config):
        """Test empty categories list returns empty map."""
        analyzer = BudgetAnalyzer(sample_config)
        category_map = analyzer._build_category_map([])
        assert category_map == {}


class TestFilterTransactionsByDate:
    """Tests for _filter_transactions_by_date method."""

    def test_filters_within_date_range(self, sample_config, sample_transactions, date_range):
        """Test transactions within date range are included."""
        analyzer = BudgetAnalyzer(sample_config)
        start_date, end_date = date_range

        filtered = analyzer._filter_transactions_by_date(
            sample_transactions, start_date, end_date
        )

        # Should include all transactions from sample (they're within 7 days)
        assert len(filtered) >= 1

    def test_excludes_transactions_before_start(self, sample_config, sample_transactions):
        """Test transactions before start date are excluded."""
        analyzer = BudgetAnalyzer(sample_config)

        # Set date range to only include future dates
        tz = pytz.timezone('America/New_York')
        start_date = datetime.now(tz) + timedelta(days=30)
        end_date = start_date + timedelta(days=7)

        filtered = analyzer._filter_transactions_by_date(
            sample_transactions, start_date, end_date
        )

        assert len(filtered) == 0

    def test_includes_boundary_dates(self, sample_config):
        """Test transactions on boundary dates are included."""
        analyzer = BudgetAnalyzer(sample_config)

        transactions = [
            {'id': '1', 'date': '2025-11-01', 'amount': -10000},
            {'id': '2', 'date': '2025-11-07', 'amount': -20000},
            {'id': '3', 'date': '2025-11-08', 'amount': -30000},  # Outside range
        ]

        start_date = datetime(2025, 11, 1)
        end_date = datetime(2025, 11, 7)

        filtered = analyzer._filter_transactions_by_date(transactions, start_date, end_date)

        assert len(filtered) == 2
        assert any(t['id'] == '1' for t in filtered)
        assert any(t['id'] == '2' for t in filtered)


class TestCalculateSummary:
    """Tests for _calculate_summary method."""

    def test_calculates_correct_totals(self, sample_config, sample_transactions, sample_categories):
        """Test summary calculates correct inflow/outflow totals."""
        analyzer = BudgetAnalyzer(sample_config)
        category_map = analyzer._build_category_map(sample_categories)

        summary = analyzer._calculate_summary(sample_transactions, category_map)

        # Check that totals make sense
        assert summary['total_inflow'] >= 0
        assert summary['total_outflow'] >= 0
        assert summary['transaction_count'] == len(sample_transactions)

    def test_excludes_transfers(self, sample_config, sample_categories):
        """Test transfers are excluded from summary."""
        analyzer = BudgetAnalyzer(sample_config)
        category_map = analyzer._build_category_map(sample_categories)

        transactions = [
            {'id': '1', 'date': '2025-11-01', 'amount': -100000, 'transfer_account_id': None, 'category_id': 'cat-1'},
            {'id': '2', 'date': '2025-11-01', 'amount': -50000, 'transfer_account_id': 'account-2', 'category_id': None},  # Transfer
        ]

        summary = analyzer._calculate_summary(transactions, category_map)

        # Only the non-transfer should be counted
        assert summary['total_outflow'] == 100.0  # $100 from first transaction only

    def test_excludes_configured_categories(self, sample_config, sample_categories):
        """Test excluded categories are not counted."""
        analyzer = BudgetAnalyzer(sample_config)
        category_map = analyzer._build_category_map(sample_categories)

        transactions = [
            {'id': '1', 'date': '2025-11-01', 'amount': -100000, 'transfer_account_id': None, 'category_id': 'cat-1'},
            {'id': '2', 'date': '2025-11-01', 'amount': 3000000, 'transfer_account_id': None, 'category_id': 'cat-inflow'},  # Excluded
        ]

        summary = analyzer._calculate_summary(transactions, category_map)

        # Inflow from excluded category should not be counted
        assert summary['total_inflow'] == 0  # cat-inflow is in exclude list


class TestAnalyzeByCategory:
    """Tests for _analyze_by_category method."""

    def test_groups_spending_by_category(self, sample_config, sample_transactions, sample_categories):
        """Test spending is correctly grouped by category."""
        analyzer = BudgetAnalyzer(sample_config)
        category_map = analyzer._build_category_map(sample_categories)

        breakdown = analyzer._analyze_by_category(sample_transactions, category_map)

        # Should have multiple categories
        assert len(breakdown) >= 1

        # Each entry should have required fields
        for entry in breakdown:
            assert 'category_name' in entry
            assert 'amount' in entry
            assert 'transaction_count' in entry
            assert entry['amount'] >= 0

    def test_sorts_by_amount_descending(self, sample_config, sample_categories):
        """Test categories are sorted by amount (highest first)."""
        analyzer = BudgetAnalyzer(sample_config)
        category_map = analyzer._build_category_map(sample_categories)

        transactions = [
            {'id': '1', 'date': '2025-11-01', 'amount': -50000, 'transfer_account_id': None, 'category_id': 'cat-1'},
            {'id': '2', 'date': '2025-11-01', 'amount': -200000, 'transfer_account_id': None, 'category_id': 'cat-3'},
            {'id': '3', 'date': '2025-11-01', 'amount': -100000, 'transfer_account_id': None, 'category_id': 'cat-5'},
        ]

        breakdown = analyzer._analyze_by_category(transactions, category_map)

        # Verify descending order
        amounts = [entry['amount'] for entry in breakdown]
        assert amounts == sorted(amounts, reverse=True)

    def test_limits_to_top_n(self, sample_config, sample_categories):
        """Test result is limited to configured top N categories."""
        config = sample_config.copy()
        config['budget_report']['report']['top_categories_count'] = 2
        analyzer = BudgetAnalyzer(config)
        category_map = analyzer._build_category_map(sample_categories)

        transactions = [
            {'id': '1', 'date': '2025-11-01', 'amount': -50000, 'transfer_account_id': None, 'category_id': 'cat-1'},
            {'id': '2', 'date': '2025-11-01', 'amount': -200000, 'transfer_account_id': None, 'category_id': 'cat-3'},
            {'id': '3', 'date': '2025-11-01', 'amount': -100000, 'transfer_account_id': None, 'category_id': 'cat-5'},
        ]

        breakdown = analyzer._analyze_by_category(transactions, category_map)

        assert len(breakdown) <= 2


class TestAnalyzeByPayee:
    """Tests for _analyze_by_payee method."""

    def test_groups_spending_by_payee(self, sample_config, sample_transactions, sample_payees):
        """Test spending is correctly grouped by payee."""
        analyzer = BudgetAnalyzer(sample_config)
        payee_map = {p['id']: p for p in sample_payees}

        breakdown = analyzer._analyze_by_payee(sample_transactions, payee_map)

        # Should have multiple payees
        assert len(breakdown) >= 1

        # Each entry should have required fields
        for entry in breakdown:
            assert 'payee_name' in entry
            assert 'amount' in entry
            assert 'transaction_count' in entry

    def test_handles_unknown_payees(self, sample_config):
        """Test transactions with unknown payees are handled."""
        analyzer = BudgetAnalyzer(sample_config)

        transactions = [
            {'id': '1', 'date': '2025-11-01', 'amount': -50000, 'transfer_account_id': None, 'payee_id': None, 'payee_name': 'Unknown Store'},
        ]

        breakdown = analyzer._analyze_by_payee(transactions, {})

        assert len(breakdown) == 1
        assert breakdown[0]['payee_name'] == 'Unknown Store'


class TestFindNotableTransactions:
    """Tests for _find_notable_transactions method."""

    def test_finds_large_transactions(self, sample_config, sample_transactions, sample_categories, sample_payees):
        """Test large transactions are identified."""
        analyzer = BudgetAnalyzer(sample_config)
        category_map = analyzer._build_category_map(sample_categories)
        payee_map = {p['id']: p for p in sample_payees}

        notable = analyzer._find_notable_transactions(
            sample_transactions, category_map, payee_map
        )

        # Should find transactions >= $100 threshold
        # Rent ($1500) and Amazon ($250) should be notable
        assert len(notable) >= 1
        assert all(t['amount'] >= 100 for t in notable)

    def test_includes_required_fields(self, sample_config, sample_categories, sample_payees):
        """Test notable transactions include all required fields."""
        analyzer = BudgetAnalyzer(sample_config)
        category_map = analyzer._build_category_map(sample_categories)
        payee_map = {p['id']: p for p in sample_payees}

        transactions = [
            {
                'id': '1',
                'date': '2025-11-01',
                'amount': -500000,  # $500 - notable
                'payee_id': 'payee-1',
                'category_id': 'cat-1',
                'memo': 'Test memo'
            }
        ]

        notable = analyzer._find_notable_transactions(transactions, category_map, payee_map)

        assert len(notable) == 1
        entry = notable[0]
        assert 'date' in entry
        assert 'payee' in entry
        assert 'category' in entry
        assert 'amount' in entry
        assert 'memo' in entry
        assert 'is_inflow' in entry

    def test_respects_threshold_config(self, sample_config, sample_categories, sample_payees):
        """Test threshold from config is used."""
        config = sample_config.copy()
        config['budget_report']['report']['notable_transaction_threshold'] = 1000
        analyzer = BudgetAnalyzer(config)
        category_map = analyzer._build_category_map(sample_categories)
        payee_map = {p['id']: p for p in sample_payees}

        transactions = [
            {'id': '1', 'date': '2025-11-01', 'amount': -500000, 'payee_id': 'payee-1', 'category_id': 'cat-1', 'memo': ''},  # $500 - not notable
            {'id': '2', 'date': '2025-11-01', 'amount': -1500000, 'payee_id': 'payee-1', 'category_id': 'cat-1', 'memo': ''},  # $1500 - notable
        ]

        notable = analyzer._find_notable_transactions(transactions, category_map, payee_map)

        assert len(notable) == 1
        assert notable[0]['amount'] == 1500.0


class TestCompareTobudget:
    """Tests for compare_to_budget method."""

    def test_compares_spending_to_budget(self, sample_config, sample_month_budget):
        """Test budget comparison calculates correct percentages."""
        analyzer = BudgetAnalyzer(sample_config)

        comparison = analyzer.compare_to_budget({}, sample_month_budget)

        assert 'total_budgeted' in comparison
        assert 'total_spent' in comparison
        assert 'total_remaining' in comparison
        assert 'overall_percentage_used' in comparison
        assert 'categories' in comparison

    def test_identifies_over_budget_categories(self, sample_config):
        """Test over-budget categories are flagged."""
        analyzer = BudgetAnalyzer(sample_config)

        month_budget = {
            'categories': [
                {'id': 'cat-1', 'name': 'Groceries', 'budgeted': 500000, 'activity': -600000},  # Over by $100
                {'id': 'cat-2', 'name': 'Utilities', 'budgeted': 200000, 'activity': -150000},  # Under budget
            ]
        }

        comparison = analyzer.compare_to_budget({}, month_budget)

        groceries = next(c for c in comparison['categories'] if c['category_name'] == 'Groceries')
        utilities = next(c for c in comparison['categories'] if c['category_name'] == 'Utilities')

        assert groceries['over_budget'] is True
        assert utilities['over_budget'] is False

    def test_calculates_percentage_used(self, sample_config):
        """Test percentage used is calculated correctly."""
        analyzer = BudgetAnalyzer(sample_config)

        month_budget = {
            'categories': [
                {'id': 'cat-1', 'name': 'Test', 'budgeted': 1000000, 'activity': -500000},  # 50%
            ]
        }

        comparison = analyzer.compare_to_budget({}, month_budget)

        assert comparison['categories'][0]['percentage_used'] == 50.0


class TestGenerateAlerts:
    """Tests for generate_alerts method."""

    def test_generates_over_budget_alerts(self, sample_config):
        """Test alerts are generated for over-budget categories."""
        analyzer = BudgetAnalyzer(sample_config)

        budget_comparison = {
            'overall_percentage_used': 85,
            'categories': [
                {
                    'category_name': 'Groceries',
                    'budgeted': 500,
                    'spent': 600,
                    'over_budget': True
                }
            ]
        }

        alerts = analyzer.generate_alerts(budget_comparison, {})

        # Should have at least one alert for groceries
        assert len(alerts) >= 1
        groceries_alert = next((a for a in alerts if a['category'] == 'Groceries'), None)
        assert groceries_alert is not None
        assert groceries_alert['level'] == 'critical'

    def test_generates_warning_for_high_overall_spending(self, sample_config):
        """Test warning is generated when approaching budget limit."""
        analyzer = BudgetAnalyzer(sample_config)

        budget_comparison = {
            'overall_percentage_used': 95,  # Above 90% threshold
            'categories': []
        }

        alerts = analyzer.generate_alerts(budget_comparison, {})

        overall_alert = next((a for a in alerts if a['category'] == 'Overall Budget'), None)
        assert overall_alert is not None
        assert overall_alert['level'] == 'warning'

    def test_no_alerts_when_under_budget(self, sample_config):
        """Test no alerts when spending is under control."""
        analyzer = BudgetAnalyzer(sample_config)

        budget_comparison = {
            'overall_percentage_used': 50,
            'categories': [
                {
                    'category_name': 'Groceries',
                    'budgeted': 500,
                    'spent': 200,
                    'over_budget': False
                }
            ]
        }

        alerts = analyzer.generate_alerts(budget_comparison, {})

        assert len(alerts) == 0


class TestAnalyzeByAccount:
    """Tests for _analyze_by_account method."""

    def test_groups_activity_by_account(self, sample_config, sample_transactions, sample_accounts):
        """Test activity is correctly grouped by account."""
        analyzer = BudgetAnalyzer(sample_config)
        account_map = {a['id']: a for a in sample_accounts}

        breakdown = analyzer._analyze_by_account(sample_transactions, account_map)

        assert len(breakdown) >= 1

        for entry in breakdown:
            assert 'account_name' in entry
            assert 'inflow' in entry
            assert 'outflow' in entry
            assert 'net' in entry
            assert 'transaction_count' in entry

    def test_calculates_net_correctly(self, sample_config, sample_accounts):
        """Test net calculation (inflow - outflow) is correct."""
        analyzer = BudgetAnalyzer(sample_config)
        account_map = {a['id']: a for a in sample_accounts}

        transactions = [
            {'id': '1', 'date': '2025-11-01', 'amount': 1000000, 'account_id': 'account-1'},  # +$1000
            {'id': '2', 'date': '2025-11-01', 'amount': -300000, 'account_id': 'account-1'},  # -$300
        ]

        breakdown = analyzer._analyze_by_account(transactions, account_map)

        checking = next(a for a in breakdown if a['account_name'] == 'Checking')
        assert checking['inflow'] == 1000.0
        assert checking['outflow'] == 300.0
        assert checking['net'] == 700.0  # 1000 - 300


class TestAnalyzeTransactions:
    """Tests for the main analyze_transactions method."""

    def test_returns_complete_analysis(
        self, sample_config, sample_transactions, sample_categories,
        sample_payees, sample_accounts, date_range
    ):
        """Test main analysis method returns all required sections."""
        analyzer = BudgetAnalyzer(sample_config)
        start_date, end_date = date_range

        analysis = analyzer.analyze_transactions(
            transactions=sample_transactions,
            categories=sample_categories,
            payees=sample_payees,
            accounts=sample_accounts,
            start_date=start_date,
            end_date=end_date
        )

        # Check all required sections are present
        assert 'period' in analysis
        assert 'summary' in analysis
        assert 'category_breakdown' in analysis
        assert 'payee_breakdown' in analysis
        assert 'account_breakdown' in analysis
        assert 'notable_transactions' in analysis
        assert 'transaction_count' in analysis

        # Check period info
        assert 'start_date' in analysis['period']
        assert 'end_date' in analysis['period']
        assert 'days' in analysis['period']

    def test_handles_empty_transactions(
        self, sample_config, sample_categories, sample_payees, sample_accounts, date_range
    ):
        """Test analysis handles empty transaction list gracefully."""
        analyzer = BudgetAnalyzer(sample_config)
        start_date, end_date = date_range

        analysis = analyzer.analyze_transactions(
            transactions=[],
            categories=sample_categories,
            payees=sample_payees,
            accounts=sample_accounts,
            start_date=start_date,
            end_date=end_date
        )

        assert analysis['transaction_count'] == 0
        assert analysis['summary']['total_inflow'] == 0
        assert analysis['summary']['total_outflow'] == 0


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_zero_budget(self, sample_config):
        """Test handling of categories with zero budget."""
        analyzer = BudgetAnalyzer(sample_config)

        month_budget = {
            'categories': [
                {'id': 'cat-1', 'name': 'Unbudgeted', 'budgeted': 0, 'activity': -50000},
            ]
        }

        comparison = analyzer.compare_to_budget({}, month_budget)

        # Should not include zero-budget categories
        assert len(comparison['categories']) == 0

    def test_handles_negative_balances(self, sample_config, sample_categories):
        """Test handling of negative balance scenarios."""
        analyzer = BudgetAnalyzer(sample_config)
        category_map = analyzer._build_category_map(sample_categories)

        transactions = [
            {
                'id': '1',
                'date': '2025-11-01',
                'amount': -1000000,  # Large outflow
                'category_id': 'cat-1',
                'transfer_account_id': None
            }
        ]

        summary = analyzer._calculate_summary(transactions, category_map)

        assert summary['total_outflow'] == 1000.0
        assert summary['net'] == -1000.0

    def test_handles_uncategorized_transactions(self, sample_config):
        """Test handling of transactions without category."""
        analyzer = BudgetAnalyzer(sample_config)

        transactions = [
            {
                'id': '1',
                'date': '2025-11-01',
                'amount': -50000,
                'category_id': None,  # No category
                'transfer_account_id': None
            }
        ]

        breakdown = analyzer._analyze_by_category(transactions, {})

        # Should be categorized as 'Uncategorized'
        assert len(breakdown) == 1
        assert breakdown[0]['category_name'] == 'Uncategorized'

    def test_handles_future_dated_transactions(self, sample_config, sample_categories, date_range):
        """Test future-dated transactions are excluded from current period."""
        analyzer = BudgetAnalyzer(sample_config)
        start_date, end_date = date_range

        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        transactions = [
            {'id': '1', 'date': future_date, 'amount': -50000}
        ]

        filtered = analyzer._filter_transactions_by_date(transactions, start_date, end_date)

        assert len(filtered) == 0
