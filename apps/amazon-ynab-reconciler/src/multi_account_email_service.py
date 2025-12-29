"""
Multi-account email service orchestrator.
Coordinates email fetching across multiple accounts (Gmail + IMAP).
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

import yaml

from email_client_base import (
    EmailClientBase,
    EmailAccountConfig,
    EmailMessage,
    AuthenticationError,
    EmailClientError
)
from gmail_email_client import GmailEmailClient
from imap_email_client import IMAPEmailClient
from order_deduplicator import OrderDeduplicator

logger = logging.getLogger(__name__)


class MultiAccountEmailService:
    """
    Orchestrates email fetching across multiple email accounts.

    Supports both Gmail (OAuth2) and IMAP accounts, searching them
    in parallel and deduplicating results.
    """

    def __init__(self, config_path: Optional[str] = None, config_dict: Optional[Dict] = None):
        """
        Initialize the multi-account email service.

        Args:
            config_path: Path to config.yaml file
            config_dict: Optional dict configuration (overrides config_path)
        """
        self.clients: List[EmailClientBase] = []
        self.deduplicator = OrderDeduplicator()
        self._config: Dict = {}

        if config_dict:
            self._config = config_dict
        elif config_path:
            self._load_config(config_path)
        else:
            # Try default config path
            default_path = Path(__file__).parent.parent / 'config.yaml'
            if default_path.exists():
                self._load_config(str(default_path))

        self._initialize_clients()

    def _load_config(self, config_path: str) -> None:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                full_config = yaml.safe_load(f)
                self._config = full_config.get('email_accounts', {})
                logger.info(f"Loaded email configuration from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            self._config = {}

    def _initialize_clients(self) -> None:
        """Initialize email clients based on configuration."""
        accounts = self._config.get('accounts', [])

        for account_config in accounts:
            if not account_config.get('enabled', True):
                logger.info(f"Skipping disabled account: {account_config.get('name')}")
                continue

            try:
                client = self._create_client(account_config)
                if client:
                    self.clients.append(client)
                    logger.info(f"Initialized email client: {client.name}")
            except Exception as e:
                logger.error(f"Failed to create client for {account_config.get('name')}: {e}")

        logger.info(f"Initialized {len(self.clients)} email clients")

    def _create_client(self, account_config: Dict) -> Optional[EmailClientBase]:
        """
        Create an email client from account configuration.

        Args:
            account_config: Account configuration dict

        Returns:
            EmailClientBase instance or None
        """
        account_type = account_config.get('type', '').lower()
        name = account_config.get('name', 'Unknown')

        if account_type == 'gmail':
            config = EmailAccountConfig(
                name=name,
                account_type='gmail',
                credentials_path=account_config.get('credentials_path'),
                token_path=account_config.get('token_path'),
                search_senders=account_config.get('search', {}).get('senders', []),
                lookback_days=account_config.get('search', {}).get('lookback_days', 30)
            )
            return GmailEmailClient(config)

        elif account_type == 'imap':
            # Handle environment variable substitution for server/username
            server = account_config.get('server', '')
            username = account_config.get('username', '')

            # Resolve environment variables (format: ${VAR_NAME})
            import os
            import re

            def resolve_env(value: str) -> str:
                if not value:
                    return value
                matches = re.findall(r'\$\{(\w+)\}', value)
                for var in matches:
                    env_value = os.environ.get(var, '')
                    value = value.replace(f'${{{var}}}', env_value)
                return value

            server = resolve_env(server)
            username = resolve_env(username)

            config = EmailAccountConfig(
                name=name,
                account_type='imap',
                imap_server=server or None,
                imap_port=account_config.get('port', 993),
                use_ssl=account_config.get('use_ssl', True),
                username=username,
                search_senders=account_config.get('search', {}).get('senders', []),
                lookback_days=account_config.get('search', {}).get('lookback_days', 30)
            )
            return IMAPEmailClient(config)

        else:
            logger.warning(f"Unknown account type: {account_type}")
            return None

    def add_gmail_account(
        self,
        name: str,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None
    ) -> None:
        """
        Add a Gmail account programmatically.

        Args:
            name: Display name for the account
            credentials_path: Path to OAuth2 credentials
            token_path: Path to token storage
        """
        config = EmailAccountConfig(
            name=name,
            account_type='gmail',
            credentials_path=credentials_path,
            token_path=token_path
        )
        client = GmailEmailClient(config)
        self.clients.append(client)
        logger.info(f"Added Gmail account: {name}")

    def add_imap_account(
        self,
        name: str,
        username: str,
        server: Optional[str] = None,
        port: int = 993,
        use_ssl: bool = True
    ) -> None:
        """
        Add an IMAP account programmatically.

        Args:
            name: Display name for the account
            username: Email address / IMAP username
            server: IMAP server (auto-detected if not provided)
            port: IMAP port
            use_ssl: Use SSL/TLS
        """
        config = EmailAccountConfig(
            name=name,
            account_type='imap',
            imap_server=server,
            imap_port=port,
            use_ssl=use_ssl,
            username=username
        )
        client = IMAPEmailClient(config)
        self.clients.append(client)
        logger.info(f"Added IMAP account: {name}")

    def authenticate_all(self) -> Dict[str, bool]:
        """
        Authenticate all configured email clients.

        Returns:
            Dict mapping account name to authentication success
        """
        results = {}

        for client in self.clients:
            try:
                success = client.authenticate()
                results[client.name] = success
                logger.info(f"[{client.name}] Authentication: {'success' if success else 'failed'}")
            except AuthenticationError as e:
                results[client.name] = False
                logger.error(f"[{client.name}] Authentication failed: {e}")

        return results

    def test_all_connections(self) -> Dict[str, bool]:
        """
        Test connections to all configured accounts.

        Returns:
            Dict mapping account name to connection status
        """
        results = {}

        for client in self.clients:
            try:
                success = client.test_connection()
                results[client.name] = success
            except Exception as e:
                results[client.name] = False
                logger.error(f"[{client.name}] Connection test failed: {e}")

        return results

    def search_all_accounts(
        self,
        days_back: int = 30,
        deduplicate: bool = True,
        parallel: bool = True
    ) -> List[EmailMessage]:
        """
        Search all accounts for Amazon order emails.

        Args:
            days_back: Number of days to look back
            deduplicate: Whether to deduplicate results
            parallel: Whether to search accounts in parallel

        Returns:
            List of EmailMessage objects
        """
        all_messages = []

        if parallel and len(self.clients) > 1:
            all_messages = self._search_parallel(days_back)
        else:
            all_messages = self._search_sequential(days_back)

        logger.info(f"Found {len(all_messages)} total messages across {len(self.clients)} accounts")

        if deduplicate:
            all_messages = self.deduplicator.deduplicate_messages(all_messages)
            logger.info(f"After deduplication: {len(all_messages)} unique messages")

        return all_messages

    def _search_parallel(self, days_back: int) -> List[EmailMessage]:
        """Search all accounts in parallel using ThreadPoolExecutor."""
        all_messages = []

        def search_account(client: EmailClientBase) -> List[EmailMessage]:
            try:
                return client.search_amazon_emails(days_back=days_back)
            except Exception as e:
                logger.error(f"[{client.name}] Search failed: {e}")
                return []

        with ThreadPoolExecutor(max_workers=len(self.clients)) as executor:
            futures = {
                executor.submit(search_account, client): client
                for client in self.clients
            }

            for future in as_completed(futures):
                client = futures[future]
                try:
                    messages = future.result()
                    # Tag messages with source account
                    for msg in messages:
                        msg.headers['x-source-account'] = client.name
                    all_messages.extend(messages)
                    logger.info(f"[{client.name}] Retrieved {len(messages)} messages")
                except Exception as e:
                    logger.error(f"[{client.name}] Error retrieving results: {e}")

        return all_messages

    def _search_sequential(self, days_back: int) -> List[EmailMessage]:
        """Search all accounts sequentially."""
        all_messages = []

        for client in self.clients:
            try:
                messages = client.search_amazon_emails(days_back=days_back)
                # Tag messages with source account
                for msg in messages:
                    msg.headers['x-source-account'] = client.name
                all_messages.extend(messages)
                logger.info(f"[{client.name}] Retrieved {len(messages)} messages")
            except Exception as e:
                logger.error(f"[{client.name}] Search failed: {e}")

        return all_messages

    def get_account_emails(self) -> List[str]:
        """
        Get list of email addresses for all configured accounts.

        Returns:
            List of email addresses
        """
        emails = []
        for client in self.clients:
            email = client.get_user_email()
            if email:
                emails.append(email)
        return emails

    def get_status(self) -> Dict[str, Any]:
        """
        Get status information for all accounts.

        Returns:
            Dict with account status information
        """
        status = {
            'total_accounts': len(self.clients),
            'accounts': []
        }

        for client in self.clients:
            account_status = {
                'name': client.name,
                'type': client.account_type,
                'email': client.get_user_email(),
                'authenticated': client.is_authenticated,
                'enabled': client.config.enabled
            }
            status['accounts'].append(account_status)

        return status

    def close_all(self) -> None:
        """Close all email client connections."""
        for client in self.clients:
            try:
                if hasattr(client, 'close'):
                    client.close()
            except Exception as e:
                logger.debug(f"Error closing {client.name}: {e}")


def create_default_service() -> MultiAccountEmailService:
    """
    Create a multi-account email service with default configuration.

    Returns:
        Configured MultiAccountEmailService instance
    """
    service = MultiAccountEmailService()

    # If no accounts configured, add defaults
    if not service.clients:
        logger.info("No accounts configured, adding default Gmail account")
        service.add_gmail_account("Primary Gmail")

    return service


if __name__ == "__main__":
    # Test multi-account service
    logging.basicConfig(level=logging.INFO)
    print("Testing Multi-Account Email Service...")

    try:
        service = MultiAccountEmailService()

        # Add accounts manually if not configured
        if not service.clients:
            print("No accounts in config, adding manually...")
            service.add_gmail_account("Primary Gmail")

            import os
            if os.environ.get('IMAP_PASSWORD_BRITTANY'):
                service.add_imap_account(
                    name="Brittany Mail.com",
                    username="brittanybrandon@mail.com"
                )

        # Test connections
        print("\nTesting connections...")
        results = service.test_all_connections()
        for account, success in results.items():
            status = "Connected" if success else "Failed"
            print(f"  {account}: {status}")

        # Search for emails
        print("\nSearching for Amazon emails (last 7 days)...")
        messages = service.search_all_accounts(days_back=7)
        print(f"Found {len(messages)} unique Amazon emails")

        for msg in messages[:5]:
            source = msg.headers.get('x-source-account', 'unknown')
            print(f"  [{source}] {msg.subject[:50]}...")

        # Get status
        print("\nService status:")
        status = service.get_status()
        print(f"  Total accounts: {status['total_accounts']}")
        for account in status['accounts']:
            print(f"  - {account['name']}: {account['email']} ({account['type']})")

        service.close_all()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
