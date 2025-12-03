"""
Integration tests for Weekly Budget Report.

These tests verify the full workflow works correctly with mocked external services.
"""
import pytest
import responses
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytz

from budget_analyzer import BudgetAnalyzer
from budget_report import BudgetReportGenerator
from ynab_service import YNABService


class TestFullWorkflow:
    """Integration tests for the full report generation workflow."""

    @pytest.fixture
    def mock_ynab_responses(
        self, sample_budgets, sample_transactions, sample_categories,
        sample_payees, sample_accounts, sample_month_budget
    ):
        """Setup mock YNAB API responses."""
        # Budgets
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets',
            json={'data': {'budgets': sample_budgets}},
            status=200
        )

        # Transactions
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/transactions',
            json={'data': {'transactions': sample_transactions}},
            status=200
        )

        # Categories
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/categories',
            json={'data': {'category_groups': sample_categories}},
            status=200
        )

        # Payees
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/payees',
            json={'data': {'payees': sample_payees}},
            status=200
        )

        # Accounts
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/accounts',
            json={'data': {'accounts': sample_accounts}},
            status=200
        )

        # Month budget
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/months/2025-11-01',
            json={'data': {'month': sample_month_budget}},
            status=200
        )

    @responses.activate
    def test_weekly_report_workflow(
        self, mock_env_vars, mock_ynab_responses, sample_config, date_range
    ):
        """Test the full weekly report generation workflow."""
        start_date, end_date = date_range

        # 1. Initialize services
        ynab_service = YNABService()
        analyzer = BudgetAnalyzer(sample_config)
        report_generator = BudgetReportGenerator(sample_config['budget_report'])

        # 2. Fetch data
        budget_id = 'budget-123'
        transactions = ynab_service.get_transactions(budget_id)
        categories = ynab_service.get_categories(budget_id)
        payees = ynab_service.get_payees(budget_id)
        accounts = ynab_service.get_accounts(budget_id)
        month_budget = ynab_service.get_month_budget(budget_id, '2025-11-01')

        # 3. Analyze data
        analysis = analyzer.analyze_transactions(
            transactions=transactions,
            categories=categories,
            payees=payees,
            accounts=accounts,
            start_date=start_date,
            end_date=end_date
        )

        budget_comparison = analyzer.compare_to_budget(
            analysis['category_breakdown'],
            month_budget
        )

        alerts = analyzer.generate_alerts(budget_comparison, analysis['category_breakdown'])

        # 4. Compile report data
        report_data = {
            'period': analysis['period'],
            'analysis': analysis,
            'budget_comparison': budget_comparison,
            'alerts': alerts
        }

        # 5. Generate HTML report
        html = report_generator.generate_html_report(report_data)

        # Verify report was generated
        assert html is not None
        assert len(html) > 0
        assert '<!DOCTYPE html>' in html
        assert '</html>' in html


class TestAnnualWorkflow:
    """Integration tests for annual budget workflow."""

    @pytest.fixture
    def mock_annual_ynab_responses(
        self, sample_budgets, sample_annual_transactions, sample_categories,
        sample_payees, sample_accounts, sample_month_budget
    ):
        """Setup mock YNAB API responses for annual data."""
        # Budgets
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets',
            json={'data': {'budgets': sample_budgets}},
            status=200
        )

        # Annual transactions
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/transactions',
            json={'data': {'transactions': sample_annual_transactions}},
            status=200
        )

        # Categories
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/categories',
            json={'data': {'category_groups': sample_categories}},
            status=200
        )

        # Payees
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/payees',
            json={'data': {'payees': sample_payees}},
            status=200
        )

        # Accounts
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/accounts',
            json={'data': {'accounts': sample_accounts}},
            status=200
        )

        # Monthly budgets for each month
        for month in range(1, 12):
            month_str = f'2025-{month:02d}-01'
            budget_data = sample_month_budget.copy()
            budget_data['month'] = month_str
            responses.add(
                responses.GET,
                f'https://api.ynab.com/v1/budgets/budget-123/months/{month_str}',
                json={'data': {'month': budget_data}},
                status=200
            )

    @responses.activate
    def test_annual_report_workflow(
        self, mock_env_vars, mock_annual_ynab_responses,
        sample_annual_budget_config, date_range, sample_categories
    ):
        """Test the full annual report generation workflow."""
        start_date, end_date = date_range
        year = 2025

        # 1. Initialize services
        ynab_service = YNABService()
        analyzer = BudgetAnalyzer(sample_annual_budget_config)
        report_generator = BudgetReportGenerator(
            sample_annual_budget_config['budget_report']
        )

        # 2. Fetch annual data
        budget_id = 'budget-123'
        annual_transactions = ynab_service.get_annual_transactions(budget_id, year)
        categories = ynab_service.get_categories(budget_id)
        monthly_budgets = ynab_service.get_monthly_budgets(budget_id, year)

        # 3. Aggregate annual budget
        annual_budget_data = ynab_service.aggregate_annual_budget(monthly_budgets)

        # 4. Calculate annual metrics
        annual_budget = analyzer.calculate_annual_budget(annual_budget_data, year)
        ytd_spending = analyzer.calculate_ytd_spending(
            annual_transactions, categories, year
        )
        projections = analyzer.project_year_end_spending(annual_budget, ytd_spending)
        annual_alerts = analyzer.generate_annual_alerts(annual_budget, projections)

        # 5. Also generate weekly analysis
        payees = ynab_service.get_payees(budget_id)
        accounts = ynab_service.get_accounts(budget_id)

        weekly_analysis = analyzer.analyze_transactions(
            transactions=annual_transactions,  # Filter would normally apply
            categories=categories,
            payees=payees,
            accounts=accounts,
            start_date=start_date,
            end_date=end_date
        )

        # 6. Compile full report data
        report_data = {
            'period': weekly_analysis['period'],
            'analysis': weekly_analysis,
            'budget_comparison': {},
            'alerts': annual_alerts,
            'annual_budget': annual_budget,
            'ytd_spending': ytd_spending,
            'projections': projections
        }

        # 7. Generate annual HTML report
        html = report_generator.generate_annual_report(report_data)

        # Verify report was generated
        assert html is not None
        assert len(html) > 0
        assert '<!DOCTYPE html>' in html
        assert 'Annual' in html or '2025' in html


class TestErrorRecovery:
    """Tests for error handling and recovery."""

    @responses.activate
    def test_handles_partial_api_failure(self, mock_env_vars, sample_config):
        """Test workflow handles partial API failures gracefully."""
        # Setup: budgets works, categories fails
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets',
            json={'data': {'budgets': [{'id': 'budget-123', 'name': 'Test'}]}},
            status=200
        )
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/categories',
            json={'error': {'message': 'Server error'}},
            status=500
        )

        ynab_service = YNABService()

        # Should work
        budgets = ynab_service.get_budgets()
        assert len(budgets) == 1

        # Should raise
        with pytest.raises(Exception):
            ynab_service.get_categories('budget-123')

    def test_analyzer_handles_empty_data(self, sample_config, date_range):
        """Test analyzer handles empty transaction data."""
        analyzer = BudgetAnalyzer(sample_config)
        start_date, end_date = date_range

        # Empty data should not crash
        analysis = analyzer.analyze_transactions(
            transactions=[],
            categories=[],
            payees=[],
            accounts=[],
            start_date=start_date,
            end_date=end_date
        )

        assert analysis['transaction_count'] == 0
        assert analysis['summary']['total_inflow'] == 0
        assert analysis['summary']['total_outflow'] == 0

    def test_report_generator_handles_missing_sections(self, sample_config):
        """Test report generator handles missing data sections."""
        generator = BudgetReportGenerator(sample_config['budget_report'])

        # Minimal report data with missing sections
        minimal_data = {
            'period': {'start_date': '2025-11-19', 'end_date': '2025-11-26', 'days': 7},
            'analysis': {
                'summary': {'total_inflow': 0, 'total_outflow': 0, 'net': 0, 'transaction_count': 0},
                'category_breakdown': [],
                'payee_breakdown': [],
                'notable_transactions': [],
                'account_breakdown': []
            },
            # Missing budget_comparison and alerts
        }

        html = generator.generate_html_report(minimal_data)
        assert '<!DOCTYPE html>' in html


class TestPerformance:
    """Performance-related tests."""

    def test_analyzer_handles_large_transaction_set(self, sample_config, sample_categories, date_range):
        """Test analyzer can handle large number of transactions."""
        analyzer = BudgetAnalyzer(sample_config)
        start_date, end_date = date_range

        # Generate large transaction set
        large_transactions = []
        base_date = datetime.now() - timedelta(days=3)

        for i in range(1000):
            large_transactions.append({
                'id': f'txn-{i}',
                'date': (base_date - timedelta(days=i % 7)).strftime('%Y-%m-%d'),
                'amount': -10000 * (i % 10 + 1),  # $10-$100
                'payee_id': f'payee-{i % 50}',
                'payee_name': f'Payee {i % 50}',
                'category_id': 'cat-1',
                'account_id': 'account-1',
                'memo': f'Transaction {i}',
                'cleared': 'cleared',
                'approved': True,
                'transfer_account_id': None
            })

        # Should complete without timeout
        analysis = analyzer.analyze_transactions(
            transactions=large_transactions,
            categories=sample_categories,
            payees=[],
            accounts=[],
            start_date=start_date,
            end_date=end_date
        )

        assert analysis['transaction_count'] >= 0
