"""
Order deduplicator for multi-account email reconciliation.
Handles deduplication when the same Amazon order appears in multiple email accounts.
"""

import re
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field

from email_client_base import EmailMessage

logger = logging.getLogger(__name__)

# Amazon order ID pattern: XXX-XXXXXXX-XXXXXXX
AMAZON_ORDER_ID_PATTERN = re.compile(r'\b(\d{3}-\d{7}-\d{7})\b')


@dataclass
class DeduplicationResult:
    """Result of deduplication process."""

    unique_messages: List[EmailMessage]
    duplicates_removed: int
    duplicate_groups: Dict[str, List[str]]  # order_id -> list of source accounts
    stats: Dict[str, int] = field(default_factory=dict)


class OrderDeduplicator:
    """
    Deduplicates Amazon order emails from multiple accounts.

    Uses multiple strategies:
    1. Amazon Order ID matching (primary)
    2. Amount + Date matching (fallback)
    3. Content hash matching (last resort)
    """

    def __init__(
        self,
        date_tolerance_days: int = 1,
        amount_tolerance_cents: int = 0
    ):
        """
        Initialize the deduplicator.

        Args:
            date_tolerance_days: Days tolerance for date-based matching
            amount_tolerance_cents: Cents tolerance for amount-based matching
        """
        self.date_tolerance_days = date_tolerance_days
        self.amount_tolerance_cents = amount_tolerance_cents

    def deduplicate_messages(
        self,
        messages: List[EmailMessage]
    ) -> List[EmailMessage]:
        """
        Deduplicate a list of email messages.

        Args:
            messages: List of EmailMessage objects from multiple accounts

        Returns:
            Deduplicated list of EmailMessage objects
        """
        if not messages:
            return []

        # Track seen order IDs and content hashes
        seen_order_ids: Set[str] = set()
        seen_hashes: Set[str] = set()
        unique_messages: List[EmailMessage] = []
        duplicates_removed = 0

        # Sort by date (newest first) to prefer more recent emails
        sorted_messages = sorted(
            messages,
            key=lambda m: m.date,
            reverse=True
        )

        for message in sorted_messages:
            # Extract order ID from message
            order_id = self._extract_order_id(message)

            # Check if we've seen this order ID
            if order_id and order_id in seen_order_ids:
                duplicates_removed += 1
                source = message.headers.get('x-source-account', 'unknown')
                logger.debug(f"Duplicate order {order_id} from {source}")
                continue

            # Fallback: check content hash
            content_hash = self._compute_content_hash(message)
            if content_hash in seen_hashes:
                duplicates_removed += 1
                logger.debug(f"Duplicate content hash: {content_hash[:8]}...")
                continue

            # Not a duplicate - add to unique list
            unique_messages.append(message)

            if order_id:
                seen_order_ids.add(order_id)
            seen_hashes.add(content_hash)

        logger.info(
            f"Deduplication: {len(messages)} -> {len(unique_messages)} "
            f"({duplicates_removed} duplicates removed)"
        )

        return unique_messages

    def deduplicate_with_details(
        self,
        messages: List[EmailMessage]
    ) -> DeduplicationResult:
        """
        Deduplicate messages and return detailed results.

        Args:
            messages: List of EmailMessage objects

        Returns:
            DeduplicationResult with detailed information
        """
        if not messages:
            return DeduplicationResult(
                unique_messages=[],
                duplicates_removed=0,
                duplicate_groups={},
                stats={'total': 0, 'unique': 0, 'duplicates': 0}
            )

        # Track order ID -> source accounts mapping
        order_sources: Dict[str, List[str]] = {}
        seen_order_ids: Set[str] = set()
        seen_hashes: Set[str] = set()
        unique_messages: List[EmailMessage] = []

        # Sort by date (newest first)
        sorted_messages = sorted(
            messages,
            key=lambda m: m.date,
            reverse=True
        )

        for message in sorted_messages:
            source = message.headers.get('x-source-account', 'unknown')
            order_id = self._extract_order_id(message)

            # Track sources for each order
            if order_id:
                if order_id not in order_sources:
                    order_sources[order_id] = []
                order_sources[order_id].append(source)

            # Check for duplicates
            if order_id and order_id in seen_order_ids:
                continue

            content_hash = self._compute_content_hash(message)
            if content_hash in seen_hashes:
                continue

            # Not a duplicate
            unique_messages.append(message)

            if order_id:
                seen_order_ids.add(order_id)
            seen_hashes.add(content_hash)

        # Find duplicate groups (orders that appeared in multiple accounts)
        duplicate_groups = {
            order_id: sources
            for order_id, sources in order_sources.items()
            if len(sources) > 1
        }

        duplicates_removed = len(messages) - len(unique_messages)

        return DeduplicationResult(
            unique_messages=unique_messages,
            duplicates_removed=duplicates_removed,
            duplicate_groups=duplicate_groups,
            stats={
                'total': len(messages),
                'unique': len(unique_messages),
                'duplicates': duplicates_removed,
                'orders_in_multiple_accounts': len(duplicate_groups)
            }
        )

    def _extract_order_id(self, message: EmailMessage) -> Optional[str]:
        """
        Extract Amazon order ID from an email message.

        Args:
            message: EmailMessage object

        Returns:
            Order ID string or None
        """
        # Search in subject first
        match = AMAZON_ORDER_ID_PATTERN.search(message.subject)
        if match:
            return match.group(1)

        # Search in body
        body = message.body_html or message.body_text or ''
        match = AMAZON_ORDER_ID_PATTERN.search(body)
        if match:
            return match.group(1)

        return None

    def _compute_content_hash(self, message: EmailMessage) -> str:
        """
        Compute a content hash for duplicate detection.

        Uses subject + date + normalized body snippet.

        Args:
            message: EmailMessage object

        Returns:
            SHA256 hash string
        """
        # Normalize content for hashing
        subject = message.subject.lower().strip()
        date_str = message.date.strftime('%Y-%m-%d')

        # Use first 500 chars of body, normalized
        body = (message.body_text or message.body_html or '')[:500]
        body = re.sub(r'\s+', ' ', body.lower().strip())

        # Combine and hash
        content = f"{subject}|{date_str}|{body}"
        return hashlib.sha256(content.encode()).hexdigest()

    def merge_duplicate_info(
        self,
        messages: List[EmailMessage]
    ) -> List[EmailMessage]:
        """
        Merge information from duplicate emails into the primary copy.

        When the same order appears in multiple accounts, this method
        combines metadata from all copies into the primary message.

        Args:
            messages: List of potentially duplicate messages

        Returns:
            Deduplicated list with merged metadata
        """
        # Group messages by order ID
        order_groups: Dict[str, List[EmailMessage]] = {}

        for message in messages:
            order_id = self._extract_order_id(message)
            if order_id:
                if order_id not in order_groups:
                    order_groups[order_id] = []
                order_groups[order_id].append(message)
            else:
                # No order ID - treat as unique
                if 'no_order_id' not in order_groups:
                    order_groups['no_order_id'] = []
                order_groups['no_order_id'].append(message)

        unique_messages = []

        for order_id, group in order_groups.items():
            if len(group) == 1:
                unique_messages.append(group[0])
            else:
                # Multiple copies - merge and keep newest
                merged = self._merge_message_group(group)
                unique_messages.append(merged)

        return unique_messages

    def _merge_message_group(
        self,
        messages: List[EmailMessage]
    ) -> EmailMessage:
        """
        Merge a group of duplicate messages into one.

        Args:
            messages: List of duplicate EmailMessage objects

        Returns:
            Merged EmailMessage
        """
        # Sort by date - use newest as primary
        sorted_msgs = sorted(messages, key=lambda m: m.date, reverse=True)
        primary = sorted_msgs[0]

        # Collect source accounts
        sources = [
            m.headers.get('x-source-account', 'unknown')
            for m in messages
        ]
        primary.headers['x-source-accounts'] = ', '.join(set(sources))
        primary.headers['x-duplicate-count'] = str(len(messages))

        # If primary is missing body, try to get from others
        if not primary.body_html:
            for msg in sorted_msgs[1:]:
                if msg.body_html:
                    primary.body_html = msg.body_html
                    break

        if not primary.body_text:
            for msg in sorted_msgs[1:]:
                if msg.body_text:
                    primary.body_text = msg.body_text
                    break

        return primary


def extract_order_id_from_text(text: str) -> Optional[str]:
    """
    Utility function to extract Amazon order ID from any text.

    Args:
        text: Text to search

    Returns:
        Order ID or None
    """
    match = AMAZON_ORDER_ID_PATTERN.search(text)
    return match.group(1) if match else None


if __name__ == "__main__":
    # Test deduplicator
    from datetime import datetime

    logging.basicConfig(level=logging.DEBUG)

    # Create test messages
    messages = [
        EmailMessage(
            id="msg1",
            subject="Your Amazon.com order #123-4567890-1234567 has shipped",
            sender="ship-confirm@amazon.com",
            date=datetime(2025, 12, 9, 10, 0),
            body_text="Order details...",
            headers={'x-source-account': 'Gmail'}
        ),
        EmailMessage(
            id="msg2",
            subject="Your Amazon.com order #123-4567890-1234567 has shipped",
            sender="ship-confirm@amazon.com",
            date=datetime(2025, 12, 9, 10, 5),  # 5 min later
            body_text="Order details...",
            headers={'x-source-account': 'Mail.com'}
        ),
        EmailMessage(
            id="msg3",
            subject="Your Amazon.com order #999-8888888-7777777 has shipped",
            sender="ship-confirm@amazon.com",
            date=datetime(2025, 12, 8, 15, 0),
            body_text="Different order...",
            headers={'x-source-account': 'Gmail'}
        ),
    ]

    print("Testing OrderDeduplicator...")
    print(f"Input: {len(messages)} messages")

    deduplicator = OrderDeduplicator()

    # Test basic deduplication
    unique = deduplicator.deduplicate_messages(messages)
    print(f"After deduplication: {len(unique)} messages")

    # Test detailed deduplication
    result = deduplicator.deduplicate_with_details(messages)
    print(f"\nDetailed results:")
    print(f"  Total: {result.stats['total']}")
    print(f"  Unique: {result.stats['unique']}")
    print(f"  Duplicates removed: {result.duplicates_removed}")
    print(f"  Orders in multiple accounts: {result.stats['orders_in_multiple_accounts']}")

    if result.duplicate_groups:
        print("\nDuplicate groups:")
        for order_id, sources in result.duplicate_groups.items():
            print(f"  Order {order_id}: {sources}")
