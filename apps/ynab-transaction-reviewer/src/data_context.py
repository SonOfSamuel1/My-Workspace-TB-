"""
Budget Data Context

Holds all pre-fetched YNAB data for in-memory processing.
This eliminates per-transaction API calls by fetching all data upfront.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class Transaction:
    """Represents a YNAB transaction"""
    id: str
    date: str
    amount: float  # In dollars (converted from milliunits)
    payee_id: Optional[str]
    payee_name: Optional[str]
    category_id: Optional[str]
    category_name: Optional[str]
    account_id: str
    account_name: str
    memo: Optional[str]
    cleared: str
    approved: bool
    flag_color: Optional[str]
    transfer_account_id: Optional[str]
    subtransactions: List = None  # For split transactions

    @property
    def is_uncategorized(self) -> bool:
        """Check if transaction needs categorization"""
        return (
            self.category_id is None or
            self.category_name in (None, '', 'Uncategorized', 'Ready to Assign')
        )

    @property
    def is_unapproved(self) -> bool:
        """Check if transaction needs approval"""
        return not self.approved

    @property
    def is_transfer(self) -> bool:
        """Check if this is a transfer between accounts"""
        return self.transfer_account_id is not None


@dataclass
class CategoryInfo:
    """Category information"""
    id: str
    name: str
    group_name: str
    hidden: bool = False


@dataclass
class AccountInfo:
    """Account information"""
    id: str
    name: str
    type: str
    closed: bool = False
    on_budget: bool = True


@dataclass
class PayeeInfo:
    """Payee information"""
    id: str
    name: str


@dataclass
class BudgetDataContext:
    """
    Holds all pre-fetched YNAB data for in-memory processing.

    This context is populated once with 4 API calls, then all
    subsequent processing uses this cached data with 0 API calls.
    """

    # Budget identification
    budget_id: str

    # Raw data from API
    all_transactions: List[Transaction] = field(default_factory=list)
    categories: Dict[str, CategoryInfo] = field(default_factory=dict)  # id -> CategoryInfo
    accounts: Dict[str, AccountInfo] = field(default_factory=dict)     # id -> AccountInfo
    payees: Dict[str, PayeeInfo] = field(default_factory=dict)         # id -> PayeeInfo

    # Filtered transaction lists (computed after fetching)
    uncategorized_transactions: List[Transaction] = field(default_factory=list)
    unapproved_transactions: List[Transaction] = field(default_factory=list)

    # Lookup maps for quick access
    category_name_to_id: Dict[str, str] = field(default_factory=dict)  # name -> id
    category_id_to_name: Dict[str, str] = field(default_factory=dict)  # id -> name
    account_name_to_id: Dict[str, str] = field(default_factory=dict)   # name -> id
    payee_name_to_id: Dict[str, str] = field(default_factory=dict)     # name -> id

    # Formatted category structure for suggestion engine
    categories_by_group: Dict[str, List[Dict]] = field(default_factory=dict)  # group -> [{id, name}]

    # Pre-computed payee -> category histogram for suggestions
    # Maps payee_name (lowercase) to Counter of category_ids
    payee_category_histogram: Dict = field(default_factory=dict)

    # Metadata
    fetch_timestamp: datetime = field(default_factory=datetime.now)
    transaction_count: int = 0

    def build_lookup_maps(self):
        """Build all lookup maps from raw data"""
        # Category maps
        self.category_name_to_id = {}
        self.category_id_to_name = {}
        self.categories_by_group = {}

        for cat_id, cat_info in self.categories.items():
            if not cat_info.hidden:
                self.category_name_to_id[cat_info.name] = cat_id
                self.category_id_to_name[cat_id] = cat_info.name

                # Build group structure
                if cat_info.group_name not in self.categories_by_group:
                    self.categories_by_group[cat_info.group_name] = []
                self.categories_by_group[cat_info.group_name].append({
                    'id': cat_id,
                    'name': cat_info.name
                })

        # Account maps
        self.account_name_to_id = {
            acc_info.name: acc_id
            for acc_id, acc_info in self.accounts.items()
        }

        # Payee maps
        self.payee_name_to_id = {
            payee_info.name.lower(): payee_id
            for payee_id, payee_info in self.payees.items()
            if payee_info.name
        }

    def filter_transactions(self):
        """Filter transactions into uncategorized and unapproved lists"""
        self.uncategorized_transactions = [
            txn for txn in self.all_transactions
            if txn.is_uncategorized
        ]

        self.unapproved_transactions = [
            txn for txn in self.all_transactions
            if txn.is_unapproved
        ]

        self.transaction_count = len(self.all_transactions)

    def get_category_id(self, category_name: str) -> Optional[str]:
        """Get category ID by name"""
        return self.category_name_to_id.get(category_name)

    def get_category_name(self, category_id: str) -> Optional[str]:
        """Get category name by ID"""
        return self.category_id_to_name.get(category_id)

    def get_categories_formatted(self) -> Dict[str, List[Dict]]:
        """
        Get categories in the format expected by suggestion engine.
        Returns: {group_name: [{id, name}, ...]}
        """
        return self.categories_by_group
