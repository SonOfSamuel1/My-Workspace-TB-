"""
IMAP email client implementing the EmailClientBase interface.
Supports mail.com and other IMAP providers.
"""

import os
import imaplib
import email
import logging
from datetime import datetime, timedelta
from email.header import decode_header
from typing import List, Optional, Dict, Tuple
import ssl

from email_client_base import (
    EmailClientBase,
    EmailAccountConfig,
    EmailMessage,
    AuthenticationError,
    EmailClientError
)

logger = logging.getLogger(__name__)

# Well-known IMAP server configurations
KNOWN_IMAP_SERVERS = {
    'mail.com': {
        'server': 'imap.mail.com',
        'port': 993,
        'use_ssl': True
    },
    'gmx.com': {
        'server': 'imap.gmx.com',
        'port': 993,
        'use_ssl': True
    },
    'outlook.com': {
        'server': 'outlook.office365.com',
        'port': 993,
        'use_ssl': True
    },
    'hotmail.com': {
        'server': 'outlook.office365.com',
        'port': 993,
        'use_ssl': True
    },
    'yahoo.com': {
        'server': 'imap.mail.yahoo.com',
        'port': 993,
        'use_ssl': True
    },
    'icloud.com': {
        'server': 'imap.mail.me.com',
        'port': 993,
        'use_ssl': True
    }
}


class IMAPEmailClient(EmailClientBase):
    """
    IMAP email client for custom domain and standard providers.

    Supports SSL/TLS connections and auto-detects server settings
    for known providers like mail.com.
    """

    def __init__(self, config: EmailAccountConfig):
        """
        Initialize the IMAP client.

        Args:
            config: EmailAccountConfig with IMAP-specific settings
        """
        super().__init__(config)

        # Auto-detect server settings if not provided
        if not config.imap_server and config.username:
            self._auto_detect_server(config.username)

        self._connection: Optional[imaplib.IMAP4_SSL] = None
        self._password: Optional[str] = None

    def _auto_detect_server(self, email_address: str) -> None:
        """
        Auto-detect IMAP server settings based on email domain.

        Args:
            email_address: User's email address
        """
        domain = email_address.split('@')[-1].lower()

        if domain in KNOWN_IMAP_SERVERS:
            settings = KNOWN_IMAP_SERVERS[domain]
            self.config.imap_server = settings['server']
            self.config.imap_port = settings['port']
            self.config.use_ssl = settings['use_ssl']
            logger.info(f"[{self.name}] Auto-detected IMAP server: {settings['server']}")
        else:
            # Try common patterns
            self.config.imap_server = f"imap.{domain}"
            self.config.imap_port = 993
            self.config.use_ssl = True
            logger.info(f"[{self.name}] Using default IMAP pattern: imap.{domain}")

    def _get_password(self) -> str:
        """
        Get the IMAP password from environment variables.

        Returns:
            Password string

        Raises:
            AuthenticationError: If password not found
        """
        if self._password:
            return self._password

        # Try various environment variable patterns
        username = self.config.username or ''
        username_part = username.split('@')[0].upper().replace('.', '_')
        domain_part = username.split('@')[-1].split('.')[0].upper() if '@' in username else ''

        env_vars_to_try = [
            f'IMAP_PASSWORD_{username_part}',
            f'IMAP_PASSWORD_{domain_part}',
            f'{username_part}_IMAP_PASSWORD',
            'IMAP_PASSWORD',
            f'EMAIL_PASSWORD_{username_part}',
        ]

        for env_var in env_vars_to_try:
            password = os.environ.get(env_var)
            if password:
                logger.debug(f"[{self.name}] Found password in {env_var}")
                self._password = password
                return password

        raise AuthenticationError(
            f"IMAP password not found. Set one of: {', '.join(env_vars_to_try[:3])}",
            provider="imap"
        )

    def authenticate(self) -> bool:
        """
        Authenticate with the IMAP server.

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            password = self._get_password()

            server = self.config.imap_server
            port = self.config.imap_port

            logger.info(f"[{self.name}] Connecting to IMAP server: {server}:{port}")

            # Create SSL context
            if self.config.use_ssl:
                ssl_context = ssl.create_default_context()
                self._connection = imaplib.IMAP4_SSL(
                    server,
                    port,
                    ssl_context=ssl_context
                )
            else:
                self._connection = imaplib.IMAP4(server, port)
                self._connection.starttls()

            # Login
            self._connection.login(self.config.username, password)

            self.is_authenticated = True
            self._user_email = self.config.username

            logger.info(f"[{self.name}] IMAP authentication successful")
            return True

        except imaplib.IMAP4.error as e:
            logger.error(f"[{self.name}] IMAP authentication failed: {e}")
            raise AuthenticationError(str(e), provider="imap")
        except Exception as e:
            logger.error(f"[{self.name}] IMAP connection error: {e}")
            raise AuthenticationError(str(e), provider="imap")

    def _ensure_connected(self) -> None:
        """Ensure the IMAP connection is active."""
        if not self._connection or not self.is_authenticated:
            self.authenticate()

        # Check if connection is still alive
        try:
            self._connection.noop()
        except Exception:
            logger.info(f"[{self.name}] Reconnecting to IMAP server...")
            self.authenticate()

    def search_messages(
        self,
        senders: Optional[List[str]] = None,
        days_back: int = 7,
        subject_contains: Optional[str] = None,
        max_results: int = 100
    ) -> List[EmailMessage]:
        """
        Search for email messages via IMAP.

        Args:
            senders: List of sender email addresses to search for
            days_back: Number of days to look back
            subject_contains: Optional subject filter
            max_results: Maximum number of messages to return

        Returns:
            List of EmailMessage objects
        """
        self._ensure_connected()

        try:
            # Select inbox
            self._connection.select('INBOX')

            # Build IMAP search criteria
            since_date = (datetime.now() - timedelta(days=days_back)).strftime('%d-%b-%Y')

            # IMAP doesn't support OR for FROM, so we need to search separately
            all_message_ids = set()

            if senders:
                for sender in senders:
                    search_criteria = f'(SINCE {since_date} FROM "{sender}")'
                    if subject_contains:
                        search_criteria = f'(SINCE {since_date} FROM "{sender}" SUBJECT "{subject_contains}")'

                    logger.debug(f"[{self.name}] IMAP search: {search_criteria}")

                    status, data = self._connection.search(None, search_criteria)
                    if status == 'OK' and data[0]:
                        message_ids = data[0].split()
                        all_message_ids.update(message_ids)
            else:
                # Search all emails from date
                search_criteria = f'(SINCE {since_date})'
                if subject_contains:
                    search_criteria = f'(SINCE {since_date} SUBJECT "{subject_contains}")'

                status, data = self._connection.search(None, search_criteria)
                if status == 'OK' and data[0]:
                    all_message_ids.update(data[0].split())

            logger.info(f"[{self.name}] Found {len(all_message_ids)} messages")

            # Fetch messages (limit to max_results)
            message_ids = list(all_message_ids)[:max_results]
            messages = []

            for msg_id in message_ids:
                try:
                    message = self._fetch_message(msg_id)
                    if message:
                        messages.append(message)
                except Exception as e:
                    logger.error(f"[{self.name}] Error fetching message {msg_id}: {e}")
                    continue

            # Sort by date descending
            messages.sort(key=lambda m: m.date, reverse=True)

            return messages

        except Exception as e:
            logger.error(f"[{self.name}] IMAP search error: {e}")
            raise EmailClientError(f"IMAP search error: {e}", provider="imap")

    def _fetch_message(self, message_id: bytes) -> Optional[EmailMessage]:
        """
        Fetch a single message by IMAP ID.

        Args:
            message_id: IMAP message ID (bytes)

        Returns:
            EmailMessage or None
        """
        try:
            status, data = self._connection.fetch(message_id, '(RFC822)')

            if status != 'OK' or not data or not data[0]:
                return None

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            return self._parse_email_message(msg, message_id.decode())

        except Exception as e:
            logger.error(f"[{self.name}] Error parsing message: {e}")
            return None

    def _parse_email_message(
        self,
        msg: email.message.Message,
        message_id: str
    ) -> EmailMessage:
        """
        Parse an email.message.Message into EmailMessage.

        Args:
            msg: Python email message object
            message_id: IMAP message ID

        Returns:
            EmailMessage object
        """
        # Decode subject
        subject = self._decode_header(msg.get('Subject', ''))

        # Get sender
        sender = self._decode_header(msg.get('From', ''))

        # Parse date
        date_str = msg.get('Date', '')
        try:
            from email.utils import parsedate_to_datetime
            message_date = parsedate_to_datetime(date_str).replace(tzinfo=None)
        except Exception:
            message_date = datetime.now()

        # Extract headers
        headers = {k.lower(): self._decode_header(v) for k, v in msg.items()}

        # Extract body
        body_text, body_html = self._extract_body(msg)

        return EmailMessage(
            id=message_id,
            subject=subject,
            sender=sender,
            date=message_date,
            body_text=body_text,
            body_html=body_html,
            headers=headers,
            raw_message=msg
        )

    def _decode_header(self, header_value: str) -> str:
        """Decode an email header value."""
        if not header_value:
            return ''

        try:
            decoded_parts = decode_header(header_value)
            result = []
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    charset = charset or 'utf-8'
                    try:
                        result.append(part.decode(charset))
                    except Exception:
                        result.append(part.decode('utf-8', errors='replace'))
                else:
                    result.append(part)
            return ''.join(result)
        except Exception:
            return str(header_value)

    def _extract_body(
        self,
        msg: email.message.Message
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract text and HTML body from email message.

        Args:
            msg: Email message object

        Returns:
            Tuple of (body_text, body_html)
        """
        body_text = None
        body_html = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))

                # Skip attachments
                if 'attachment' in content_disposition:
                    continue

                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        text = payload.decode(charset, errors='replace')

                        if content_type == 'text/plain' and not body_text:
                            body_text = text
                        elif content_type == 'text/html' and not body_html:
                            body_html = text
                except Exception as e:
                    logger.debug(f"Error extracting part: {e}")
                    continue
        else:
            content_type = msg.get_content_type()
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    text = payload.decode(charset, errors='replace')

                    if content_type == 'text/plain':
                        body_text = text
                    elif content_type == 'text/html':
                        body_html = text
            except Exception as e:
                logger.debug(f"Error extracting body: {e}")

        return body_text, body_html

    def get_message(self, message_id: str) -> Optional[EmailMessage]:
        """
        Retrieve a specific email message by ID.

        Args:
            message_id: IMAP message ID

        Returns:
            EmailMessage if found, None otherwise
        """
        self._ensure_connected()

        try:
            self._connection.select('INBOX')
            return self._fetch_message(message_id.encode())
        except Exception as e:
            logger.error(f"[{self.name}] Error fetching message {message_id}: {e}")
            return None

    def get_user_email(self) -> Optional[str]:
        """
        Get the user's email address.

        Returns:
            Email address string
        """
        return self.config.username

    def test_connection(self) -> bool:
        """
        Test the IMAP connection.

        Returns:
            True if connection is working
        """
        try:
            self._ensure_connected()

            # Try to select inbox
            status, _ = self._connection.select('INBOX')
            if status == 'OK':
                logger.info(f"[{self.name}] IMAP connected: {self.config.username}")
                return True
            return False

        except Exception as e:
            logger.error(f"[{self.name}] IMAP connection test failed: {e}")
            return False

    def close(self) -> None:
        """Close the IMAP connection."""
        if self._connection:
            try:
                self._connection.close()
                self._connection.logout()
            except Exception:
                pass
            finally:
                self._connection = None
                self.is_authenticated = False

    def __del__(self):
        """Cleanup on destruction."""
        self.close()


# Factory function for creating IMAP clients
def create_imap_client(
    name: str,
    username: str,
    server: Optional[str] = None,
    port: int = 993,
    use_ssl: bool = True
) -> IMAPEmailClient:
    """
    Create an IMAP email client with the given configuration.

    Args:
        name: Display name for the account
        username: Email address / IMAP username
        server: IMAP server (auto-detected if not provided)
        port: IMAP port (default 993)
        use_ssl: Use SSL/TLS (default True)

    Returns:
        Configured IMAPEmailClient instance
    """
    config = EmailAccountConfig(
        name=name,
        account_type='imap',
        imap_server=server,
        imap_port=port,
        use_ssl=use_ssl,
        username=username
    )
    return IMAPEmailClient(config)


if __name__ == "__main__":
    # Test IMAP client
    logging.basicConfig(level=logging.INFO)
    print("Testing IMAP Email Client...")

    # Example: Test with mail.com
    test_email = os.environ.get('IMAP_EMAIL_BRITTANY', 'brittanybrandon@mail.com')

    try:
        client = create_imap_client(
            name="Brittany Mail.com",
            username=test_email
        )

        print(f"Server auto-detected: {client.config.imap_server}")

        if client.test_connection():
            print(f"Successfully authenticated as: {client.get_user_email()}")

            # Test Amazon email search
            print("\nSearching for Amazon emails...")
            messages = client.search_amazon_emails(days_back=7)
            print(f"Found {len(messages)} Amazon emails")

            for msg in messages[:3]:
                print(f"  - {msg.subject[:60]}... from {msg.sender}")

            client.close()
        else:
            print("Connection test failed")
    except AuthenticationError as e:
        print(f"Authentication error: {e}")
        print("Make sure to set IMAP_PASSWORD_BRITTANY environment variable")
    except Exception as e:
        print(f"Error: {e}")
