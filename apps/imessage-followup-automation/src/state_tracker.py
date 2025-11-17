"""
State Tracker - Manages notification state to prevent duplicates

Tracks which conversations have been notified and when,
preventing duplicate notifications.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Set

logger = logging.getLogger(__name__)


class StateTracker:
    """Tracks notification state for conversations."""

    def __init__(self, database_path: str, retention_days: int = 30):
        """
        Initialize state tracker.

        Args:
            database_path: Path to SQLite database for state storage
            retention_days: Days to keep notification history
        """
        self.database_path = Path(database_path)
        self.retention_days = retention_days

        # Create database directory if it doesn't exist
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._initialize_database()

        logger.info(f"State tracker initialized with database: {self.database_path}")

    def _initialize_database(self):
        """Create the database schema if it doesn't exist."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        # Create notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                contact_name TEXT NOT NULL,
                last_message_date TEXT NOT NULL,
                notified_at TEXT NOT NULL,
                priority TEXT,
                reason TEXT,
                resolved BOOLEAN DEFAULT 0,
                resolved_at TEXT
            )
        """)

        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_id
            ON notifications(chat_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notified_at
            ON notifications(notified_at)
        """)

        conn.commit()
        conn.close()

        logger.info("State database initialized")

    def should_notify(
        self,
        chat_id: int,
        last_message_date: datetime,
        renotify_after_days: int = 3
    ) -> bool:
        """
        Check if we should send a notification for this conversation.

        Args:
            chat_id: Chat ID from iMessage database
            last_message_date: Timestamp of last message in conversation
            renotify_after_days: Days before re-notifying about same conversation

        Returns:
            True if notification should be sent, False otherwise
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        # Check if we've notified about this conversation recently
        renotify_threshold = datetime.now() - timedelta(days=renotify_after_days)

        cursor.execute("""
            SELECT notified_at, last_message_date, resolved
            FROM notifications
            WHERE chat_id = ?
            ORDER BY notified_at DESC
            LIMIT 1
        """, (chat_id,))

        result = cursor.fetchone()
        conn.close()

        if not result:
            # Never notified before
            return True

        last_notified_str, last_tracked_message_str, resolved = result

        # Parse dates
        last_notified = datetime.fromisoformat(last_notified_str)
        last_tracked_message = datetime.fromisoformat(last_tracked_message_str)

        # If already resolved, don't notify again unless there's a new message
        if resolved:
            return last_message_date > last_tracked_message

        # If not resolved, only re-notify after the threshold period
        if last_notified >= renotify_threshold:
            # Already notified recently
            return False

        # Re-notify if enough time has passed
        return True

    def record_notification(
        self,
        chat_id: int,
        contact_name: str,
        last_message_date: datetime,
        priority: str,
        reason: str
    ):
        """
        Record that a notification was sent.

        Args:
            chat_id: Chat ID from iMessage database
            contact_name: Display name for the contact
            last_message_date: Timestamp of last message
            priority: Priority level
            reason: Reason for notification
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO notifications
            (chat_id, contact_name, last_message_date, notified_at, priority, reason, resolved)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (
            chat_id,
            contact_name,
            last_message_date.isoformat(),
            datetime.now().isoformat(),
            priority,
            reason
        ))

        conn.commit()
        conn.close()

        logger.info(f"Recorded notification for chat {chat_id} ({contact_name})")

    def mark_resolved(self, chat_id: int):
        """
        Mark a conversation as resolved (follow-up completed).

        Args:
            chat_id: Chat ID to mark as resolved
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE notifications
            SET resolved = 1, resolved_at = ?
            WHERE chat_id = ?
            AND resolved = 0
        """, (datetime.now().isoformat(), chat_id))

        conn.commit()
        conn.close()

        logger.info(f"Marked chat {chat_id} as resolved")

    def get_unresolved_notifications(self) -> Set[int]:
        """
        Get all chat IDs with unresolved notifications.

        Returns:
            Set of chat IDs
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT chat_id
            FROM notifications
            WHERE resolved = 0
        """)

        chat_ids = {row[0] for row in cursor.fetchall()}
        conn.close()

        return chat_ids

    def cleanup_old_records(self):
        """Remove notification records older than retention period."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        cursor.execute("""
            DELETE FROM notifications
            WHERE notified_at < ?
        """, (cutoff_date.isoformat(),))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old notification records")

    def get_stats(self) -> dict:
        """
        Get statistics about notifications.

        Returns:
            Dictionary with stats
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        # Total notifications
        cursor.execute("SELECT COUNT(*) FROM notifications")
        total = cursor.fetchone()[0]

        # Unresolved notifications
        cursor.execute("SELECT COUNT(*) FROM notifications WHERE resolved = 0")
        unresolved = cursor.fetchone()[0]

        # Notifications in last 7 days
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM notifications
            WHERE notified_at >= ?
        """, (week_ago,))
        last_week = cursor.fetchone()[0]

        conn.close()

        return {
            'total_notifications': total,
            'unresolved': unresolved,
            'last_week': last_week
        }
