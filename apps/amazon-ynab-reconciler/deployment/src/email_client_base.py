"""
Abstract base class for email clients.
Provides a unified interface for Gmail OAuth2 and IMAP-based email access.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Unified email message representation across providers."""

    id: str
    subject: str
    sender: str
    date: datetime
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    raw_message: Optional[Any] = None  # Original provider-specific message

    def __repr__(self) -> str:
        return f"EmailMessage(id={self.id}, subject={self.subject[:50]}..., sender={self.sender})"


@dataclass
class EmailAccountConfig:
    """Configuration for an email account."""

    name: str
    account_type: str  # 'gmail' or 'imap'
    enabled: bool = True

    # Gmail-specific
    credentials_path: Optional[str] = None
    token_path: Optional[str] = None

    # IMAP-specific
    imap_server: Optional[str] = None
    imap_port: int = 993
    use_ssl: bool = True
    username: Optional[str] = None
    # Password should be retrieved from environment variable

    # Common search settings
    search_senders: List[str] = field(default_factory=lambda: [
        'ship-confirm@amazon.com',
        'auto-confirm@amazon.com',
        'order-update@amazon.com',
        'digital-no-reply@amazon.com',
        'no-reply@amazon.com'
    ])
    lookback_days: int = 30


class EmailClientBase(ABC):
    """
    Abstract base class for email clients.

    Provides a unified interface for different email providers (Gmail, IMAP).
    All email clients must implement these methods to ensure consistent behavior
    across the multi-account email service.
    """

    def __init__(self, config: EmailAccountConfig):
        """
        Initialize the email client with configuration.

        Args:
            config: EmailAccountConfig instance with connection details
        """
        self.config = config
        self.is_authenticated = False
        self._user_email: Optional[str] = None

    @property
    def name(self) -> str:
        """Get the configured account name."""
        return self.config.name

    @property
    def account_type(self) -> str:
        """Get the account type (gmail or imap)."""
        return self.config.account_type

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the email provider.

        Returns:
            True if authentication successful, False otherwise

        Raises:
            AuthenticationError: If authentication fails with an error
        """
        pass

    @abstractmethod
    def search_messages(
        self,
        senders: Optional[List[str]] = None,
        days_back: int = 7,
        subject_contains: Optional[str] = None,
        max_results: int = 100
    ) -> List[EmailMessage]:
        """
        Search for email messages matching criteria.

        Args:
            senders: List of sender email addresses to search for
            days_back: Number of days to look back
            subject_contains: Optional subject filter
            max_results: Maximum number of messages to return

        Returns:
            List of EmailMessage objects matching the criteria
        """
        pass

    @abstractmethod
    def get_message(self, message_id: str) -> Optional[EmailMessage]:
        """
        Retrieve a specific email message by ID.

        Args:
            message_id: Provider-specific message identifier

        Returns:
            EmailMessage if found, None otherwise
        """
        pass

    @abstractmethod
    def get_user_email(self) -> Optional[str]:
        """
        Get the authenticated user's email address.

        Returns:
            Email address string or None if not authenticated
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test the connection to the email provider.

        Returns:
            True if connection is working, False otherwise
        """
        pass

    def search_amazon_emails(self, days_back: int = 30) -> List[EmailMessage]:
        """
        Convenience method to search for Amazon order emails.

        Args:
            days_back: Number of days to look back

        Returns:
            List of Amazon-related email messages
        """
        return self.search_messages(
            senders=self.config.search_senders,
            days_back=days_back,
            max_results=100
        )

    def validate_config(self) -> bool:
        """
        Validate the account configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.config.name:
            raise ValueError("Account name is required")

        if self.config.account_type not in ('gmail', 'imap'):
            raise ValueError(f"Invalid account type: {self.config.account_type}")

        if self.config.account_type == 'gmail':
            if not self.config.credentials_path:
                raise ValueError("Gmail requires credentials_path")

        if self.config.account_type == 'imap':
            if not self.config.imap_server:
                raise ValueError("IMAP requires imap_server")
            if not self.config.username:
                raise ValueError("IMAP requires username")

        return True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.config.name}, type={self.config.account_type})"


class AuthenticationError(Exception):
    """Raised when email authentication fails."""

    def __init__(self, message: str, provider: str = "unknown"):
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class EmailClientError(Exception):
    """General email client error."""

    def __init__(self, message: str, provider: str = "unknown"):
        self.provider = provider
        super().__init__(f"[{provider}] {message}")
