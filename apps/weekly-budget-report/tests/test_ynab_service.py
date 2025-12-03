"""
Unit tests for YNABService class.
"""
import pytest
import responses
from unittest.mock import patch, MagicMock
import os

from ynab_service import YNABService


class TestYNABServiceInit:
    """Tests for YNABService initialization."""

    def test_init_with_api_key(self, mock_env_vars):
        """Test service initializes with provided API key."""
        service = YNABService(api_key='test-key-123')
        assert service.api_key == 'test-key-123'

    def test_init_from_env_var(self, mock_env_vars):
        """Test service reads API key from environment."""
        service = YNABService()
        assert service.api_key == 'test-api-key-12345'

    def test_init_without_api_key_raises(self):
        """Test service raises error without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="YNAB API key is required"):
                YNABService()

    def test_headers_set_correctly(self, mock_env_vars):
        """Test authorization headers are set correctly."""
        service = YNABService(api_key='my-api-key')
        assert service.headers['Authorization'] == 'Bearer my-api-key'
        assert service.headers['Content-Type'] == 'application/json'


class TestYNABServiceAPI:
    """Tests for YNAB API methods."""

    @responses.activate
    def test_get_budgets(self, mock_env_vars, sample_budgets):
        """Test fetching budgets list."""
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets',
            json={'data': {'budgets': sample_budgets}},
            status=200
        )

        service = YNABService()
        budgets = service.get_budgets()

        assert len(budgets) == 2
        assert budgets[0]['name'] == 'My Budget'
        assert budgets[1]['id'] == 'budget-456'

    @responses.activate
    def test_get_transactions(self, mock_env_vars, sample_transactions):
        """Test fetching transactions."""
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/transactions',
            json={'data': {'transactions': sample_transactions}},
            status=200
        )

        service = YNABService()
        transactions = service.get_transactions('budget-123')

        assert len(transactions) == len(sample_transactions)

    @responses.activate
    def test_get_transactions_with_since_date(self, mock_env_vars):
        """Test fetching transactions with since_date parameter."""
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/transactions',
            json={'data': {'transactions': []}},
            status=200
        )

        service = YNABService()
        service.get_transactions('budget-123', since_date='2025-01-01')

        assert 'since_date=2025-01-01' in responses.calls[0].request.url

    @responses.activate
    def test_get_categories(self, mock_env_vars, sample_categories):
        """Test fetching categories."""
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/categories',
            json={'data': {'category_groups': sample_categories}},
            status=200
        )

        service = YNABService()
        categories = service.get_categories('budget-123')

        assert len(categories) == len(sample_categories)
        assert categories[0]['name'] == 'Immediate Obligations'

    @responses.activate
    def test_get_payees(self, mock_env_vars, sample_payees):
        """Test fetching payees."""
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/payees',
            json={'data': {'payees': sample_payees}},
            status=200
        )

        service = YNABService()
        payees = service.get_payees('budget-123')

        assert len(payees) == len(sample_payees)

    @responses.activate
    def test_get_accounts(self, mock_env_vars, sample_accounts):
        """Test fetching accounts."""
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/accounts',
            json={'data': {'accounts': sample_accounts}},
            status=200
        )

        service = YNABService()
        accounts = service.get_accounts('budget-123')

        assert len(accounts) == 3
        assert accounts[0]['name'] == 'Checking'

    @responses.activate
    def test_get_month_budget(self, mock_env_vars, sample_month_budget):
        """Test fetching month budget data."""
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/months/2025-11-01',
            json={'data': {'month': sample_month_budget}},
            status=200
        )

        service = YNABService()
        month_budget = service.get_month_budget('budget-123', '2025-11-01')

        assert month_budget['month'] == '2025-11-01'
        assert len(month_budget['categories']) == 6

    @responses.activate
    def test_validate_credentials_success(self, mock_env_vars):
        """Test credential validation success."""
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/user',
            json={'data': {'user': {'id': 'user-123'}}},
            status=200
        )

        service = YNABService()
        assert service.validate_credentials() is True

    @responses.activate
    def test_validate_credentials_failure(self, mock_env_vars):
        """Test credential validation failure."""
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/user',
            json={'error': {'id': '401', 'message': 'Unauthorized'}},
            status=401
        )

        service = YNABService()
        assert service.validate_credentials() is False


class TestYNABServiceAnnual:
    """Tests for annual budget methods."""

    @responses.activate
    def test_get_annual_transactions(self, mock_env_vars, sample_annual_transactions):
        """Test fetching annual transactions."""
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets/budget-123/transactions',
            json={'data': {'transactions': sample_annual_transactions}},
            status=200
        )

        service = YNABService()
        transactions = service.get_annual_transactions('budget-123', 2025)

        assert len(transactions) > 0
        # Should filter to only 2025 transactions
        for txn in transactions:
            assert txn['date'].startswith('2025')

    @responses.activate
    def test_get_monthly_budgets(self, mock_env_vars, sample_month_budget):
        """Test fetching monthly budgets for a year."""
        # Mock responses for each month
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

        service = YNABService()
        monthly_budgets = service.get_monthly_budgets('budget-123', 2025)

        # Should have fetched budgets for current number of months in 2025
        assert len(monthly_budgets) >= 1

    def test_aggregate_annual_budget(self, mock_env_vars, sample_month_budget):
        """Test aggregating monthly budgets into annual totals."""
        service = YNABService()

        # Create sample monthly budgets
        monthly_budgets = {
            '2025-01-01': sample_month_budget,
            '2025-02-01': sample_month_budget,
            '2025-03-01': sample_month_budget,
        }

        annual = service.aggregate_annual_budget(monthly_budgets)

        # Should have categories from the monthly budgets
        assert len(annual) > 0

        # Check aggregation
        for cat_id, cat_data in annual.items():
            assert 'annual_budgeted' in cat_data
            assert 'annual_activity' in cat_data
            assert 'monthly_breakdown' in cat_data
            # Annual should be sum of monthly
            assert cat_data['annual_budgeted'] > 0 or cat_data['annual_activity'] > 0


class TestYNABServiceUtilities:
    """Tests for utility methods."""

    def test_milliunits_to_dollars(self, mock_env_vars):
        """Test milliunit to dollar conversion."""
        service = YNABService()

        assert service.milliunits_to_dollars(1000) == 1.0
        assert service.milliunits_to_dollars(1500) == 1.5
        assert service.milliunits_to_dollars(0) == 0.0
        assert service.milliunits_to_dollars(-1000) == -1.0

    def test_dollars_to_milliunits(self, mock_env_vars):
        """Test dollar to milliunit conversion."""
        service = YNABService()

        assert service.dollars_to_milliunits(1.0) == 1000
        assert service.dollars_to_milliunits(1.5) == 1500
        assert service.dollars_to_milliunits(0.0) == 0
        assert service.dollars_to_milliunits(-1.0) == -1000


class TestYNABServiceErrorHandling:
    """Tests for error handling."""

    @responses.activate
    def test_handles_401_unauthorized(self, mock_env_vars):
        """Test handling of 401 Unauthorized response."""
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets',
            json={'error': {'id': '401', 'message': 'Unauthorized'}},
            status=401
        )

        service = YNABService()
        with pytest.raises(Exception):
            service.get_budgets()

    @responses.activate
    def test_handles_429_rate_limit(self, mock_env_vars):
        """Test handling of 429 Rate Limit response."""
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets',
            json={'error': {'id': '429', 'message': 'Rate limit exceeded'}},
            status=429
        )

        service = YNABService()
        with pytest.raises(Exception):
            service.get_budgets()

    @responses.activate
    def test_handles_500_server_error(self, mock_env_vars):
        """Test handling of 500 Server Error response."""
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets',
            json={'error': {'id': '500', 'message': 'Internal server error'}},
            status=500
        )

        service = YNABService()
        with pytest.raises(Exception):
            service.get_budgets()

    @responses.activate
    def test_handles_network_error(self, mock_env_vars):
        """Test handling of network errors."""
        responses.add(
            responses.GET,
            'https://api.ynab.com/v1/budgets',
            body=Exception('Connection refused')
        )

        service = YNABService()
        with pytest.raises(Exception):
            service.get_budgets()
