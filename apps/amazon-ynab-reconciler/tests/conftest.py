"""
Pytest configuration and shared fixtures for amazon-ynab-reconciler tests.
"""

import pytest
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import tempfile
import json

# Add src directory to path for imports
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))


# ============================================================================
# Amazon Transaction Fixtures
# ============================================================================

@pytest.fixture
def sample_amazon_transaction() -> Dict:
    """Single Amazon transaction for testing."""
    return {
        'order_id': '111-1234567-1234567',
        'date': datetime.now() - timedelta(days=5),
        'total': 49.99,
        'subtotal': 46.29,
        'tax': 3.70,
        'items': [{
            'name': 'Echo Dot (5th Gen)',
            'category': 'Electronics',
            'asin': 'B09B8V1LZ3',
            'price': 49.99,
            'quantity': 1,
            'link': 'https://www.amazon.com/dp/B09B8V1LZ3'
        }],
        'status': 'Delivered',
        'payment_method': 'Chase Credit Card'
    }


@pytest.fixture
def sample_amazon_transactions() -> List[Dict]:
    """Multiple Amazon transactions for testing."""
    base_date = datetime.now()
    return [
        {
            'order_id': '111-1234567-0000001',
            'date': base_date - timedelta(days=3),
            'total': 29.99,
            'subtotal': 27.77,
            'tax': 2.22,
            'items': [{'name': 'USB Cable', 'category': 'Electronics', 'asin': 'B001', 'price': 29.99, 'quantity': 1, 'link': ''}],
            'status': 'Delivered',
            'payment_method': 'Chase Credit Card'
        },
        {
            'order_id': '111-1234567-0000002',
            'date': base_date - timedelta(days=5),
            'total': 89.99,
            'subtotal': 83.33,
            'tax': 6.66,
            'items': [{'name': 'Headphones', 'category': 'Electronics', 'asin': 'B002', 'price': 89.99, 'quantity': 1, 'link': ''}],
            'status': 'Delivered',
            'payment_method': 'Amazon Business Prime Card'
        },
        {
            'order_id': '111-1234567-0000003',
            'date': base_date - timedelta(days=7),
            'total': 15.49,
            'subtotal': 14.34,
            'tax': 1.15,
            'items': [{'name': 'Book', 'category': 'Books', 'asin': 'B003', 'price': 15.49, 'quantity': 1, 'link': ''}],
            'status': 'Delivered',
            'payment_method': 'Chase Credit Card'
        },
    ]


# ============================================================================
# YNAB Transaction Fixtures
# ============================================================================

@pytest.fixture
def sample_ynab_transaction() -> Dict:
    """Single YNAB transaction for testing."""
    return {
        'id': 'ynab-txn-001',
        'date': datetime.now() - timedelta(days=5),
        'amount': -49990,  # YNAB milliunits (negative for outflow)
        'payee_name': 'Amazon.com',
        'category_name': 'Shopping',
        'memo': '',
        'cleared': 'uncleared',
        'account_id': 'acc-001',
        'account_name': 'Chase Freedom',
        'import_id': None,
        'flag_color': None
    }


@pytest.fixture
def sample_ynab_transactions() -> List[Dict]:
    """Multiple YNAB transactions for testing."""
    base_date = datetime.now()
    return [
        {
            'id': 'ynab-txn-001',
            'date': base_date - timedelta(days=3),
            'amount': -29990,  # $29.99 in milliunits
            'payee_name': 'Amazon.com',
            'category_name': 'Shopping',
            'memo': '',
            'cleared': 'uncleared',
            'account_id': 'acc-001',
            'account_name': 'Chase Freedom',
            'import_id': None,
            'flag_color': None
        },
        {
            'id': 'ynab-txn-002',
            'date': base_date - timedelta(days=5),
            'amount': -89990,  # $89.99 in milliunits
            'payee_name': 'AMAZON.COM',
            'category_name': 'Electronics',
            'memo': '',
            'cleared': 'uncleared',
            'account_id': 'acc-002',
            'account_name': 'Amazon Business Prime Card',
            'import_id': None,
            'flag_color': None
        },
        {
            'id': 'ynab-txn-003',
            'date': base_date - timedelta(days=7),
            'amount': -15490,  # $15.49 in milliunits
            'payee_name': 'Amazon',
            'category_name': 'Books',
            'memo': '',
            'cleared': 'uncleared',
            'account_id': 'acc-001',
            'account_name': 'Chase Freedom',
            'import_id': None,
            'flag_color': None
        },
    ]


# ============================================================================
# Match Fixtures
# ============================================================================

@pytest.fixture
def sample_match(sample_amazon_transaction, sample_ynab_transaction) -> Dict:
    """Sample match record."""
    return {
        'amazon_transaction': sample_amazon_transaction,
        'ynab_transaction': sample_ynab_transaction,
        'confidence': 95.0,
        'amount_diff': 0.0,
        'date_diff': 0,
        'matched_at': datetime.now().isoformat()
    }


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def matcher_config() -> Dict:
    """Configuration for TransactionMatcher."""
    return {
        'match_threshold': 80,
        'date_tolerance_days': 2,
        'amount_tolerance_cents': 50,
        'enable_state_tracking': False,
        'batch_detection': {
            'enabled': False,
            'max_batch_size': 5
        }
    }


@pytest.fixture
def reconciler_config() -> Dict:
    """Full reconciler configuration."""
    return {
        'reconciliation': {
            'lookback_days': 30,
            'match_threshold': 80,
            'date_tolerance_days': 2,
            'amount_tolerance_cents': 50,
            'enable_state_tracking': False,
            'batch_detection': {
                'enabled': False
            }
        },
        'amazon': {
            'order_history_url': 'https://www.amazon.com/gp/your-account/order-history',
            'max_pages': 10
        },
        'ynab': {
            'budget_name': 'Test Budget',
            'account_names': ['Chase Freedom', 'Amazon Business Prime Card'],
            'only_uncleared': True
        },
        'email': {
            'enabled': False
        }
    }


# ============================================================================
# File/Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_data_dir(tmp_path) -> Path:
    """Temporary data directory for tests."""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def temp_logs_dir(tmp_path) -> Path:
    """Temporary logs directory for tests."""
    logs_dir = tmp_path / 'logs'
    logs_dir.mkdir()
    return logs_dir


@pytest.fixture
def sample_csv_content() -> str:
    """Sample Amazon CSV content."""
    return '''Order Date,Order ID,Title,Category,ASIN/ISBN,Item Total,Payment Instrument Type
11/20/2024,111-1234567-0000001,USB Cable,Electronics,B001,$29.99,Chase Credit Card
11/18/2024,111-1234567-0000002,Headphones,Electronics,B002,$89.99,Amazon Business Prime Card
11/16/2024,111-1234567-0000003,Book,Books,B003,$15.49,Chase Credit Card'''


@pytest.fixture
def sample_csv_file(temp_data_dir, sample_csv_content) -> Path:
    """Create sample Amazon CSV file."""
    csv_path = temp_data_dir / 'amazon_orders.csv'
    csv_path.write_text(sample_csv_content)
    return csv_path


@pytest.fixture
def sample_state_file(temp_logs_dir) -> Path:
    """Create sample state file."""
    state_path = temp_logs_dir / 'reconciliation_state.json'
    state_data = {
        'matched_pairs': [],
        'last_run': datetime.now().isoformat()
    }
    state_path.write_text(json.dumps(state_data))
    return state_path


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_ynab_service(sample_ynab_transactions):
    """Mock YNAB service for testing."""
    class MockYNABService:
        def __init__(self):
            self.transactions = sample_ynab_transactions
            self.updates = []
            self.flags = []

        def validate_connection(self):
            return True

        def get_budget_id(self):
            return 'budget-001'

        def get_transactions(self, since_date=None, account_names=None):
            return self.transactions

        def update_transaction_memo(self, transaction_id, amazon_data, dry_run=False):
            if not dry_run:
                self.updates.append({
                    'transaction_id': transaction_id,
                    'amazon_data': amazon_data
                })
            return True

        def add_flag_to_transaction(self, transaction_id, flag_color, dry_run=False):
            if not dry_run:
                self.flags.append({
                    'transaction_id': transaction_id,
                    'flag_color': flag_color
                })
            return True

    return MockYNABService()


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail service for testing."""
    class MockGmailService:
        def __init__(self):
            self.messages = []

        def users(self):
            return self

        def messages(self):
            return self

        def list(self, userId=None, q=None, maxResults=None):
            return self

        def execute(self):
            return {'messages': []}

    return MockGmailService()


# ============================================================================
# Utility Functions
# ============================================================================

def create_amazon_transaction(
    order_id: str = None,
    date: datetime = None,
    total: float = 49.99,
    item_name: str = 'Test Item',
    payment_method: str = 'Chase Credit Card'
) -> Dict:
    """Helper to create Amazon transaction with custom values."""
    return {
        'order_id': order_id or f'111-{datetime.now().timestamp():.0f}',
        'date': date or datetime.now(),
        'total': total,
        'subtotal': total * 0.92,
        'tax': total * 0.08,
        'items': [{
            'name': item_name,
            'category': 'Test',
            'asin': 'B000TEST',
            'price': total,
            'quantity': 1,
            'link': ''
        }],
        'status': 'Delivered',
        'payment_method': payment_method
    }


def create_ynab_transaction(
    txn_id: str = None,
    date: datetime = None,
    amount_dollars: float = 49.99,
    payee_name: str = 'Amazon.com',
    account_name: str = 'Chase Freedom',
    memo: str = ''
) -> Dict:
    """Helper to create YNAB transaction with custom values."""
    return {
        'id': txn_id or f'ynab-{datetime.now().timestamp():.0f}',
        'date': date or datetime.now(),
        'amount': int(-amount_dollars * 1000),  # Convert to milliunits
        'payee_name': payee_name,
        'category_name': 'Shopping',
        'memo': memo,
        'cleared': 'uncleared',
        'account_id': 'acc-001',
        'account_name': account_name,
        'import_id': None,
        'flag_color': None
    }
