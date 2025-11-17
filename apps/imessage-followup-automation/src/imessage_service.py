"""
iMessage Service - Reads messages from macOS iMessage database

This service accesses the macOS chat.db SQLite database to retrieve
recent messages and conversation data.
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import pytz

logger = logging.getLogger(__name__)


class Message:
    """Represents a single iMessage."""

    def __init__(self, data: dict):
        """Initialize message from database row."""
        self.message_id = data.get('ROWID')
        self.guid = data.get('guid')
        self.text = data.get('text', '')
        self.handle_id = data.get('handle_id')
        self.sender_name = data.get('sender_name', 'Unknown')
        self.sender_identifier = data.get('sender_identifier', '')
        self.is_from_me = bool(data.get('is_from_me', 0))
        self.is_read = bool(data.get('is_read', 0))
        self.date = self._convert_apple_timestamp(data.get('date', 0))
        self.chat_id = data.get('chat_id')
        self.chat_display_name = data.get('chat_display_name', '')
        self.is_group_chat = bool(data.get('is_group_chat', 0))

    @staticmethod
    def _convert_apple_timestamp(timestamp: int) -> datetime:
        """
        Convert Apple's timestamp to Python datetime.

        Apple's timestamps are in nanoseconds since 2001-01-01.
        """
        if timestamp == 0:
            return datetime.now()

        # Convert nanoseconds to seconds
        timestamp_seconds = timestamp / 1_000_000_000

        # Apple's epoch is 2001-01-01
        apple_epoch = datetime(2001, 1, 1)

        return apple_epoch + timedelta(seconds=timestamp_seconds)

    def __repr__(self):
        direction = "→" if self.is_from_me else "←"
        return f"<Message {direction} {self.sender_name}: {self.text[:50]}...>"


class Conversation:
    """Represents a conversation thread."""

    def __init__(self, chat_id: int, display_name: str, is_group: bool):
        self.chat_id = chat_id
        self.display_name = display_name
        self.is_group = is_group
        self.messages: List[Message] = []

    def add_message(self, message: Message):
        """Add a message to this conversation."""
        self.messages.append(message)

    @property
    def last_message(self) -> Optional[Message]:
        """Get the most recent message."""
        if not self.messages:
            return None
        return max(self.messages, key=lambda m: m.date)

    @property
    def last_outgoing_message(self) -> Optional[Message]:
        """Get the most recent outgoing (from me) message."""
        outgoing = [m for m in self.messages if m.is_from_me]
        if not outgoing:
            return None
        return max(outgoing, key=lambda m: m.date)

    @property
    def last_incoming_message(self) -> Optional[Message]:
        """Get the most recent incoming message."""
        incoming = [m for m in self.messages if not m.is_from_me]
        if not incoming:
            return None
        return max(incoming, key=lambda m: m.date)

    def needs_response(self) -> bool:
        """
        Determine if this conversation needs a response.

        Returns True if the last message is from the other person.
        """
        last = self.last_message
        return last is not None and not last.is_from_me

    def __repr__(self):
        msg_count = len(self.messages)
        return f"<Conversation '{self.display_name}' ({msg_count} messages)>"


class iMessageService:
    """Service for reading iMessages from macOS database."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize iMessage service.

        Args:
            db_path: Path to chat.db. Defaults to standard macOS location.
        """
        if db_path is None:
            db_path = os.path.expanduser("~/Library/Messages/chat.db")

        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"iMessage database not found at: {self.db_path}\n"
                "Make sure you're running on macOS and have iMessage set up."
            )

        logger.info(f"iMessage database found at: {self.db_path}")

    def _connect(self) -> sqlite3.Connection:
        """Create a read-only connection to the iMessage database."""
        try:
            # Open in read-only mode to avoid any accidental writes
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to iMessage database: {e}")
            raise

    def get_recent_messages(
        self,
        lookback_hours: int = 48,
        exclude_group_chats: bool = False,
        priority_contacts: Optional[List[str]] = None
    ) -> List[Message]:
        """
        Get recent messages from the database.

        Args:
            lookback_hours: How many hours back to retrieve messages
            exclude_group_chats: Whether to exclude group conversations
            priority_contacts: List of phone numbers or emails to prioritize

        Returns:
            List of Message objects
        """
        conn = self._connect()
        cursor = conn.cursor()

        # Calculate timestamp threshold
        lookback_date = datetime.now() - timedelta(hours=lookback_hours)

        # Convert to Apple timestamp format (nanoseconds since 2001-01-01)
        apple_epoch = datetime(2001, 1, 1)
        seconds_since_epoch = (lookback_date - apple_epoch).total_seconds()
        timestamp_threshold = int(seconds_since_epoch * 1_000_000_000)

        try:
            # Build query
            query = """
                SELECT
                    message.ROWID,
                    message.guid,
                    message.text,
                    message.handle_id,
                    message.is_from_me,
                    message.is_read,
                    message.date,
                    handle.id as sender_identifier,
                    chat.chat_identifier,
                    chat.display_name as chat_display_name,
                    chat.ROWID as chat_id,
                    CASE
                        WHEN chat.chat_identifier LIKE '%chat%' THEN 1
                        ELSE 0
                    END as is_group_chat
                FROM message
                LEFT JOIN handle ON message.handle_id = handle.ROWID
                LEFT JOIN chat_message_join ON message.ROWID = chat_message_join.message_id
                LEFT JOIN chat ON chat_message_join.chat_id = chat.ROWID
                WHERE message.date >= ?
                    AND message.text IS NOT NULL
                    AND message.text != ''
            """

            if exclude_group_chats:
                query += " AND chat.chat_identifier NOT LIKE '%chat%'"

            query += " ORDER BY message.date DESC"

            cursor.execute(query, (timestamp_threshold,))
            rows = cursor.fetchall()

            messages = []
            for row in rows:
                message_data = {
                    'ROWID': row['ROWID'],
                    'guid': row['guid'],
                    'text': row['text'],
                    'handle_id': row['handle_id'],
                    'sender_identifier': row['sender_identifier'] or 'Unknown',
                    'sender_name': self._format_contact_name(row['sender_identifier']),
                    'is_from_me': row['is_from_me'],
                    'is_read': row['is_read'],
                    'date': row['date'],
                    'chat_id': row['chat_id'],
                    'chat_display_name': row['chat_display_name'] or row['sender_identifier'] or 'Unknown',
                    'is_group_chat': row['is_group_chat']
                }

                messages.append(Message(message_data))

            logger.info(f"Retrieved {len(messages)} messages from last {lookback_hours} hours")
            return messages

        except sqlite3.Error as e:
            logger.error(f"Database query error: {e}")
            raise
        finally:
            conn.close()

    def get_conversations(
        self,
        lookback_hours: int = 48,
        exclude_group_chats: bool = False,
        priority_contacts: Optional[List[str]] = None
    ) -> List[Conversation]:
        """
        Get recent conversations grouped by chat.

        Args:
            lookback_hours: How many hours back to retrieve messages
            exclude_group_chats: Whether to exclude group conversations
            priority_contacts: List of phone numbers or emails to prioritize

        Returns:
            List of Conversation objects
        """
        messages = self.get_recent_messages(
            lookback_hours=lookback_hours,
            exclude_group_chats=exclude_group_chats,
            priority_contacts=priority_contacts
        )

        # Group messages by chat_id
        conversations_dict: Dict[int, Conversation] = {}

        for message in messages:
            chat_id = message.chat_id

            if chat_id not in conversations_dict:
                conversations_dict[chat_id] = Conversation(
                    chat_id=chat_id,
                    display_name=message.chat_display_name,
                    is_group=message.is_group_chat
                )

            conversations_dict[chat_id].add_message(message)

        conversations = list(conversations_dict.values())

        # Sort by most recent message
        conversations.sort(
            key=lambda c: c.last_message.date if c.last_message else datetime.min,
            reverse=True
        )

        logger.info(f"Organized into {len(conversations)} conversations")
        return conversations

    @staticmethod
    def _format_contact_name(identifier: str) -> str:
        """
        Format a contact identifier into a display name.

        Args:
            identifier: Phone number or email address

        Returns:
            Formatted display name
        """
        if not identifier or identifier == 'Unknown':
            return 'Unknown'

        # If it's an email, use the part before @
        if '@' in identifier:
            return identifier.split('@')[0].title()

        # If it's a phone number, just return it
        return identifier

    def validate_database(self) -> bool:
        """
        Validate that the database exists and is readable.

        Returns:
            True if database is accessible, False otherwise
        """
        try:
            conn = self._connect()
            cursor = conn.cursor()

            # Try a simple query
            cursor.execute("SELECT COUNT(*) FROM message")
            count = cursor.fetchone()[0]

            logger.info(f"Database validated. Total messages: {count}")
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Database validation failed: {e}")
            return False
