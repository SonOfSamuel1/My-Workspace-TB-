"""
Pytest configuration and fixtures for Weekly Budget Report tests.
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import pytz

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_config():
    """Return a sample configuration dictionary."""
    return {
        'version': '1.0.0',
        'name': 'Weekly YNAB Budget Report',
        'budget_report': {
            'enabled': True,
            'timezone': 'America/New_York',
            'budget_id': 'test-budget-123',
            'email': {
                'recipient': 'test@example.com',
                'subject_template': 'Weekly Budget Report - {date}'
            },
            'ses': {
                'sender_email': 'brandonhome.appdev@gmail.com',
                'region': 'us-east-1'
            },
            'report': {
                'lookback_days': 7,
                'trend_weeks': 4,
                'top_payees_count': 10,
                'top_categories_count': 10,
                'notable_transaction_threshold': 100,
                'exclude_categories': [
                    'Inflow: Ready to Assign',
                    'Credit Card Payment'
                ]
            },
            'alerts': {
                'overspending_threshold': 10,
                'total_spending_threshold': 90,
                'discretionary_threshold': 80
            }
        },
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': 'logs/test_budget_report.log'
        }
    }


@pytest.fixture
def sample_categories():
    """Return sample YNAB category groups."""
    return [
        {
            'id': 'group-1',
            'name': 'Immediate Obligations',
            'categories': [
                {
                    'id': 'cat-1',
                    'name': 'Rent/Mortgage',
                    'hidden': False,
                    'deleted': False,
                    'budgeted': 1500000,  # $1500 in milliunits
                    'activity': -1450000,  # $1450 spent
                    'balance': 50000
                },
                {
                    'id': 'cat-2',
                    'name': 'Utilities',
                    'hidden': False,
                    'deleted': False,
                    'budgeted': 200000,  # $200
                    'activity': -180000,  # $180 spent
                    'balance': 20000
                }
            ]
        },
        {
            'id': 'group-2',
            'name': 'True Expenses',
            'categories': [
                {
                    'id': 'cat-3',
                    'name': 'Groceries',
                    'hidden': False,
                    'deleted': False,
                    'budgeted': 600000,  # $600
                    'activity': -650000,  # $650 spent (over budget)
                    'balance': -50000
                },
                {
                    'id': 'cat-4',
                    'name': 'Transportation',
                    'hidden': False,
                    'deleted': False,
                    'budgeted': 400000,  # $400
                    'activity': -350000,  # $350 spent
                    'balance': 50000
                }
            ]
        },
        {
            'id': 'group-3',
            'name': 'Quality of Life',
            'categories': [
                {
                    'id': 'cat-5',
                    'name': 'Dining Out',
                    'hidden': False,
                    'deleted': False,
                    'budgeted': 300000,  # $300
                    'activity': -280000,  # $280 spent
                    'balance': 20000
                },
                {
                    'id': 'cat-6',
                    'name': 'Entertainment',
                    'hidden': False,
                    'deleted': False,
                    'budgeted': 150000,  # $150
                    'activity': -120000,  # $120 spent
                    'balance': 30000
                }
            ]
        },
        {
            'id': 'group-hidden',
            'name': 'Internal Master Category',
            'categories': [
                {
                    'id': 'cat-inflow',
                    'name': 'Inflow: Ready to Assign',
                    'hidden': True,
                    'deleted': False
                }
            ]
        }
    ]


@pytest.fixture
def sample_payees():
    """Return sample YNAB payees."""
    return [
        {'id': 'payee-1', 'name': 'Whole Foods'},
        {'id': 'payee-2', 'name': 'Amazon'},
        {'id': 'payee-3', 'name': 'Shell Gas'},
        {'id': 'payee-4', 'name': 'Netflix'},
        {'id': 'payee-5', 'name': 'Landlord LLC'},
        {'id': 'payee-6', 'name': 'Power Company'},
        {'id': 'payee-7', 'name': 'Transfer: Checking'},
    ]


@pytest.fixture
def sample_accounts():
    """Return sample YNAB accounts."""
    return [
        {
            'id': 'account-1',
            'name': 'Checking',
            'type': 'checking',
            'on_budget': True,
            'closed': False,
            'balance': 5000000  # $5000
        },
        {
            'id': 'account-2',
            'name': 'Savings',
            'type': 'savings',
            'on_budget': True,
            'closed': False,
            'balance': 10000000  # $10000
        },
        {
            'id': 'account-3',
            'name': 'Credit Card',
            'type': 'creditCard',
            'on_budget': True,
            'closed': False,
            'balance': -500000  # -$500
        }
    ]


@pytest.fixture
def sample_transactions():
    """Return sample YNAB transactions for a week."""
    base_date = datetime.now() - timedelta(days=3)

    return [
        # Regular transactions
        {
            'id': 'txn-1',
            'date': (base_date - timedelta(days=1)).strftime('%Y-%m-%d'),
            'amount': -85000,  # -$85 (groceries)
            'payee_id': 'payee-1',
            'payee_name': 'Whole Foods',
            'category_id': 'cat-3',
            'account_id': 'account-1',
            'memo': 'Weekly groceries',
            'cleared': 'cleared',
            'approved': True,
            'transfer_account_id': None
        },
        {
            'id': 'txn-2',
            'date': (base_date - timedelta(days=2)).strftime('%Y-%m-%d'),
            'amount': -45000,  # -$45 (gas)
            'payee_id': 'payee-3',
            'payee_name': 'Shell Gas',
            'category_id': 'cat-4',
            'account_id': 'account-1',
            'memo': 'Fill up',
            'cleared': 'cleared',
            'approved': True,
            'transfer_account_id': None
        },
        {
            'id': 'txn-3',
            'date': (base_date - timedelta(days=3)).strftime('%Y-%m-%d'),
            'amount': -15990,  # -$15.99 (Netflix)
            'payee_id': 'payee-4',
            'payee_name': 'Netflix',
            'category_id': 'cat-6',
            'account_id': 'account-3',
            'memo': 'Monthly subscription',
            'cleared': 'cleared',
            'approved': True,
            'transfer_account_id': None
        },
        {
            'id': 'txn-4',
            'date': (base_date - timedelta(days=4)).strftime('%Y-%m-%d'),
            'amount': -1500000,  # -$1500 (rent)
            'payee_id': 'payee-5',
            'payee_name': 'Landlord LLC',
            'category_id': 'cat-1',
            'account_id': 'account-1',
            'memo': 'Monthly rent',
            'cleared': 'cleared',
            'approved': True,
            'transfer_account_id': None
        },
        {
            'id': 'txn-5',
            'date': (base_date - timedelta(days=5)).strftime('%Y-%m-%d'),
            'amount': -65000,  # -$65 (dining)
            'payee_id': None,
            'payee_name': 'Local Restaurant',
            'category_id': 'cat-5',
            'account_id': 'account-3',
            'memo': 'Dinner with friends',
            'cleared': 'cleared',
            'approved': True,
            'transfer_account_id': None
        },
        # Income transaction
        {
            'id': 'txn-6',
            'date': base_date.strftime('%Y-%m-%d'),
            'amount': 3500000,  # +$3500 (paycheck)
            'payee_id': None,
            'payee_name': 'Employer Inc',
            'category_id': 'cat-inflow',
            'account_id': 'account-1',
            'memo': 'Bi-weekly paycheck',
            'cleared': 'cleared',
            'approved': True,
            'transfer_account_id': None
        },
        # Transfer (should be excluded)
        {
            'id': 'txn-7',
            'date': base_date.strftime('%Y-%m-%d'),
            'amount': -500000,  # -$500 transfer
            'payee_id': 'payee-7',
            'payee_name': 'Transfer: Checking',
            'category_id': None,
            'account_id': 'account-1',
            'memo': 'Transfer to savings',
            'cleared': 'cleared',
            'approved': True,
            'transfer_account_id': 'account-2'
        },
        # Large transaction (notable)
        {
            'id': 'txn-8',
            'date': (base_date - timedelta(days=2)).strftime('%Y-%m-%d'),
            'amount': -250000,  # -$250 (Amazon)
            'payee_id': 'payee-2',
            'payee_name': 'Amazon',
            'category_id': 'cat-6',
            'account_id': 'account-3',
            'memo': 'New headphones',
            'cleared': 'cleared',
            'approved': True,
            'transfer_account_id': None
        }
    ]


@pytest.fixture
def sample_month_budget():
    """Return sample YNAB month budget data."""
    return {
        'month': '2025-11-01',
        'note': 'November budget',
        'income': 7000000,  # $7000
        'budgeted': 5500000,  # $5500
        'activity': -4200000,  # -$4200
        'to_be_budgeted': 500000,  # $500
        'categories': [
            {
                'id': 'cat-1',
                'name': 'Rent/Mortgage',
                'budgeted': 1500000,
                'activity': -1450000,
                'balance': 50000
            },
            {
                'id': 'cat-2',
                'name': 'Utilities',
                'budgeted': 200000,
                'activity': -180000,
                'balance': 20000
            },
            {
                'id': 'cat-3',
                'name': 'Groceries',
                'budgeted': 600000,
                'activity': -650000,
                'balance': -50000
            },
            {
                'id': 'cat-4',
                'name': 'Transportation',
                'budgeted': 400000,
                'activity': -350000,
                'balance': 50000
            },
            {
                'id': 'cat-5',
                'name': 'Dining Out',
                'budgeted': 300000,
                'activity': -280000,
                'balance': 20000
            },
            {
                'id': 'cat-6',
                'name': 'Entertainment',
                'budgeted': 150000,
                'activity': -120000,
                'balance': 30000
            }
        ]
    }


@pytest.fixture
def sample_budgets():
    """Return sample YNAB budgets list."""
    return [
        {
            'id': 'budget-123',
            'name': 'My Budget',
            'last_modified_on': '2025-11-25T10:30:00Z',
            'first_month': '2024-01-01',
            'last_month': '2025-12-01',
            'currency_format': {
                'iso_code': 'USD',
                'example_format': '$1,234.56',
                'decimal_digits': 2,
                'decimal_separator': '.',
                'symbol_first': True,
                'group_separator': ',',
                'currency_symbol': '$',
                'display_symbol': True
            }
        },
        {
            'id': 'budget-456',
            'name': 'Side Hustle Budget',
            'last_modified_on': '2025-11-20T08:15:00Z',
            'first_month': '2025-01-01',
            'last_month': '2025-12-01'
        }
    ]


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_ynab_api():
    """Create a mock for YNAB API requests."""
    with patch('src.ynab_service.requests') as mock_requests:
        yield mock_requests


@pytest.fixture
def mock_env_vars():
    """Set up mock environment variables."""
    env_vars = {
        'YNAB_API_KEY': 'test-api-key-12345',
        'YNAB_BUDGET_ID': 'budget-123',
        'BUDGET_REPORT_EMAIL': 'test@example.com',
        'SES_SENDER_EMAIL': 'brandonhome.appdev@gmail.com',
        'AWS_REGION': 'us-east-1'
    }
    with patch.dict('os.environ', env_vars, clear=False):
        yield env_vars


# ============================================================================
# Helper Functions
# ============================================================================

@pytest.fixture
def date_range():
    """Return a standard test date range (last 7 days)."""
    tz = pytz.timezone('America/New_York')
    end_date = datetime.now(tz).replace(hour=23, minute=59, second=59, microsecond=0)
    start_date = end_date - timedelta(days=7)
    return start_date, end_date


# ============================================================================
# Annual Budget Fixtures (for Tiller-style features)
# ============================================================================

@pytest.fixture
def sample_annual_transactions():
    """Return sample transactions for a full year (for annual budget testing)."""
    transactions = []
    base_date = datetime(2025, 1, 1)

    # Generate monthly transactions for the year
    for month in range(11):  # Jan through Nov
        month_date = base_date + timedelta(days=month * 30)

        # Groceries - varying amounts
        transactions.append({
            'id': f'txn-groceries-{month}',
            'date': month_date.strftime('%Y-%m-%d'),
            'amount': -580000 - (month * 10000),  # $580-$680
            'payee_id': 'payee-1',
            'payee_name': 'Grocery Store',
            'category_id': 'cat-3',
            'account_id': 'account-1',
            'memo': f'Month {month+1} groceries',
            'cleared': 'cleared',
            'approved': True,
            'transfer_account_id': None
        })

        # Rent - fixed
        transactions.append({
            'id': f'txn-rent-{month}',
            'date': month_date.strftime('%Y-%m-%d'),
            'amount': -1500000,  # $1500
            'payee_id': 'payee-5',
            'payee_name': 'Landlord LLC',
            'category_id': 'cat-1',
            'account_id': 'account-1',
            'memo': f'Month {month+1} rent',
            'cleared': 'cleared',
            'approved': True,
            'transfer_account_id': None
        })

        # Utilities - varying
        transactions.append({
            'id': f'txn-utilities-{month}',
            'date': month_date.strftime('%Y-%m-%d'),
            'amount': -150000 - (month * 5000),  # $150-$200
            'payee_id': 'payee-6',
            'payee_name': 'Power Company',
            'category_id': 'cat-2',
            'account_id': 'account-1',
            'memo': f'Month {month+1} utilities',
            'cleared': 'cleared',
            'approved': True,
            'transfer_account_id': None
        })

        # Income
        transactions.append({
            'id': f'txn-income-{month}',
            'date': month_date.strftime('%Y-%m-%d'),
            'amount': 7000000,  # $7000
            'payee_id': None,
            'payee_name': 'Employer Inc',
            'category_id': 'cat-inflow',
            'account_id': 'account-1',
            'memo': f'Month {month+1} salary',
            'cleared': 'cleared',
            'approved': True,
            'transfer_account_id': None
        })

    return transactions


@pytest.fixture
def sample_annual_budget_config():
    """Return config with annual budget settings."""
    return {
        'version': '1.0.0',
        'name': 'Weekly YNAB Budget Report',
        'budget_report': {
            'enabled': True,
            'timezone': 'America/New_York',
            'budget_id': 'test-budget-123',
            'report': {
                'lookback_days': 7,
                'exclude_categories': [
                    'Inflow: Ready to Assign',
                    'Credit Card Payment'
                ]
            },
            'alerts': {
                'overspending_threshold': 10,
                'total_spending_threshold': 90
            }
        },
        'annual_budget': {
            'enabled': True,
            'fiscal_year_start': 'january',
            'show_monthly_breakdown': True,
            'show_projections': True,
            'pace_warning_threshold': 0.8,
            'pace_danger_threshold': 1.0
        },
        'logging': {
            'level': 'INFO'
        }
    }
