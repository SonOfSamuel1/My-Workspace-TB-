"""
Simplifi Service - Fetches account data from Quicken Simplifi.

Uses the unofficial simplifiapi library (https://github.com/rijn/simplifiapi).
Authentication requires a token obtained via initial interactive login.
"""

import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SimplifiService:
    """Service for fetching account data from Quicken Simplifi."""

    def __init__(
        self,
        token: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """Initialize Simplifi service.

        Preferred: pass a token (from previous auth). Fallback: email/password.
        Token can also come from SIMPLIFI_TOKEN env var.
        Email/password from SIMPLIFI_EMAIL and SIMPLIFI_PASSWORD env vars.
        """
        self.token = token or os.getenv("SIMPLIFI_TOKEN")
        self.email = email or os.getenv("SIMPLIFI_EMAIL")
        self.password = password or os.getenv("SIMPLIFI_PASSWORD")
        self._client = None
        self._dataset_id = None

    def _get_client(self):
        """Lazy-initialize the Simplifi API client."""
        if self._client is not None:
            return self._client

        try:
            from simplifiapi.client import Client
        except ImportError:
            raise ImportError(
                "simplifiapi not installed. Install with: "
                "pip install git+https://github.com/rijn/simplifiapi"
            )

        self._client = Client()

        # Authenticate with token or credentials
        if self.token:
            logger.info("Authenticating with Simplifi using token...")
            if not self._client.verify_token(self.token):
                logger.warning(
                    "Simplifi token verification failed, token may be expired"
                )
                if self.email and self.password:
                    logger.info("Falling back to email/password auth...")
                    self.token = self._client.get_token(
                        email=self.email, password=self.password
                    )
                else:
                    raise ValueError(
                        "Simplifi token expired and no email/password provided for re-auth"
                    )
        elif self.email and self.password:
            logger.info("Authenticating with Simplifi using email/password...")
            self.token = self._client.get_token(
                email=self.email, password=self.password
            )
        else:
            raise ValueError(
                "Simplifi credentials required. Set SIMPLIFI_TOKEN or "
                "SIMPLIFI_EMAIL + SIMPLIFI_PASSWORD environment variables."
            )

        logger.info("Simplifi authentication successful")
        return self._client

    def _get_dataset_id(self) -> str:
        """Get the primary dataset ID."""
        if self._dataset_id:
            return self._dataset_id

        client = self._get_client()
        datasets = client.get_datasets()

        if not datasets:
            raise ValueError("No datasets found in Simplifi account")

        self._dataset_id = datasets[0]["id"]
        logger.info(f"Using Simplifi dataset: {self._dataset_id}")
        return self._dataset_id

    def get_accounts(self) -> List[Dict]:
        """Fetch all accounts from Simplifi.

        Returns:
            List of account dicts with keys like: name, balance, type, etc.
        """
        client = self._get_client()
        dataset_id = self._get_dataset_id()

        logger.info("Fetching Simplifi accounts...")
        accounts = client.get_accounts(dataset_id)
        logger.info(f"Fetched {len(accounts)} accounts from Simplifi")

        return accounts

    def get_net_worth_data(self) -> Dict:
        """Fetch accounts and compute net worth summary.

        Simplifi account objects typically have:
        - name: account name
        - balance: current balance (positive for assets, negative for liabilities)
        - accountType: e.g. "BANK", "CREDIT", "INVESTMENT", "LOAN", "PROPERTY", "VEHICLE"
        - isAsset: boolean (some versions)
        - group: e.g. "PERSONAL"

        Returns dict with:
        - total_assets, total_liabilities, net_worth
        - asset_accounts, liability_accounts
        - accounts_by_type
        - raw_accounts (original data)
        """
        accounts = self.get_accounts()

        # Simplifi account type mapping
        asset_types = {
            "BANK",
            "INVESTMENT",
            "PROPERTY",
            "VEHICLE",
            "OTHER_ASSET",
            "CASH",
        }
        liability_types = {"CREDIT", "LOAN", "OTHER_LIABILITY"}

        asset_accounts = []
        liability_accounts = []
        accounts_by_type = {}

        for account in accounts:
            name = account.get("name", "Unknown")
            # Balance in Simplifi is typically in dollars already (not milliunits)
            balance = account.get("balance", 0)
            if isinstance(balance, str):
                try:
                    balance = float(balance)
                except (ValueError, TypeError):
                    balance = 0.0

            acct_type = account.get(
                "accountType", account.get("type", "UNKNOWN")
            ).upper()

            entry = {
                "name": name,
                "balance": balance,
                "type": acct_type,
                "source": "simplifi",
            }

            # Group by type
            type_key = acct_type.lower()
            if type_key not in accounts_by_type:
                accounts_by_type[type_key] = []
            accounts_by_type[type_key].append(entry)

            if acct_type in asset_types:
                asset_accounts.append(
                    {"name": name, "balance": abs(balance), "type": acct_type}
                )
            elif acct_type in liability_types:
                liability_accounts.append(
                    {"name": name, "balance": abs(balance), "type": acct_type}
                )
            else:
                # Unknown type: positive balance = asset, negative = liability
                if balance >= 0:
                    asset_accounts.append(
                        {"name": name, "balance": abs(balance), "type": acct_type}
                    )
                else:
                    liability_accounts.append(
                        {"name": name, "balance": abs(balance), "type": acct_type}
                    )

        total_assets = sum(a["balance"] for a in asset_accounts)
        total_liabilities = sum(a["balance"] for a in liability_accounts)
        net_worth = total_assets - total_liabilities

        logger.info(
            "Simplifi net worth: assets=%.2f liabilities=%.2f net=%.2f",
            total_assets,
            total_liabilities,
            net_worth,
        )

        return {
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_worth": net_worth,
            "asset_accounts": asset_accounts,
            "liability_accounts": liability_accounts,
            "accounts_by_type": accounts_by_type,
            "raw_accounts": accounts,
        }

    def validate_credentials(self) -> bool:
        """Test whether authentication works."""
        try:
            self._get_client()
            self._get_dataset_id()
            return True
        except Exception as e:
            logger.error(f"Simplifi credential validation failed: {e}")
            return False
