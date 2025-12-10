"""
Downloads Monitor Module for Amazon-YNAB Reconciler

This module monitors the Downloads folder for Amazon transaction reports
and handles their import for reconciliation with YNAB.
"""

import os
import time
import hashlib
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

logger = logging.getLogger(__name__)


class AmazonCSVHandler(FileSystemEventHandler):
    """Handle file system events for Amazon CSV files."""

    def __init__(self, callback):
        self.callback = callback

    def on_created(self, event):
        if not event.is_directory and self._is_amazon_csv(event.src_path):
            logger.info(f"New Amazon CSV detected: {event.src_path}")
            self.callback(event.src_path)

    def _is_amazon_csv(self, file_path: str) -> bool:
        """Check if file matches Amazon CSV patterns."""
        patterns = [
            'amazon', 'order', 'transaction', 'purchase',
            'Amazon', 'Order', 'Transaction', 'Purchase'
        ]
        file_name = Path(file_path).name.lower()

        # Check file extension
        if not file_name.endswith('.csv'):
            return False

        # Check for Amazon-related patterns
        return any(pattern.lower() in file_name for pattern in patterns)


class DownloadsMonitor:
    """Monitor Downloads folder for Amazon transaction reports."""

    def __init__(self, downloads_dir: str = None, archive_dir: str = None,
                 state_file: str = None):
        """
        Initialize the downloads monitor.

        Args:
            downloads_dir: Path to downloads directory to monitor
            archive_dir: Path to archive processed files
            state_file: Path to state tracking file
        """
        self.downloads_dir = Path(downloads_dir or os.path.expanduser("~/Downloads"))
        self.archive_dir = Path(archive_dir or "data/processed")
        self.state_file = Path(state_file or "data/downloads_state.json")

        # Create directories if they don't exist
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Load state
        self.state = self._load_state()

        # File patterns to match
        self.file_patterns = [
            '*amazon*order*.csv',
            '*amazon*transaction*.csv',
            '*order*report*.csv',
            '*purchase*history*.csv',
            'Amazon*.csv',
            'Order*.csv'
        ]

        logger.info(f"Downloads monitor initialized - watching: {self.downloads_dir}")

    def _load_state(self) -> Dict:
        """Load processing state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading state file: {e}")

        return {
            'processed_files': {},
            'last_check': None
        }

    def _save_state(self):
        """Save processing state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving state file: {e}")

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file content."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _wait_for_file_completion(self, file_path: Path, timeout: int = 30) -> bool:
        """
        Wait for file to be completely written.

        Args:
            file_path: Path to file
            timeout: Maximum seconds to wait

        Returns:
            True if file is ready, False if timeout
        """
        start_time = time.time()
        last_size = -1

        while time.time() - start_time < timeout:
            try:
                current_size = file_path.stat().st_size

                # If size hasn't changed for 2 seconds, consider it complete
                if current_size == last_size and current_size > 0:
                    time.sleep(2)  # Final wait to be sure
                    return True

                last_size = current_size
                time.sleep(1)
            except OSError:
                # File might not be ready yet
                time.sleep(1)

        return False

    def find_amazon_csv_files(self, since: datetime = None) -> List[Path]:
        """
        Find Amazon CSV files in downloads folder.

        Args:
            since: Only find files modified after this datetime

        Returns:
            List of Path objects for matching CSV files
        """
        matching_files = []

        if not self.downloads_dir.exists():
            logger.warning(f"Downloads directory does not exist: {self.downloads_dir}")
            return matching_files

        # Set default 'since' to 24 hours ago if not provided
        if since is None:
            since = datetime.now() - timedelta(days=1)

        # Search for matching files
        for pattern in self.file_patterns:
            for file_path in self.downloads_dir.glob(pattern):
                if file_path.is_file():
                    # Check modification time
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime >= since:
                        # Check if file is large enough to be valid
                        if file_path.stat().st_size > 100:
                            matching_files.append(file_path)

        # Remove duplicates and sort by modification time (newest first)
        matching_files = list(set(matching_files))
        matching_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        logger.info(f"Found {len(matching_files)} Amazon CSV files in downloads")
        return matching_files

    def get_latest_unprocessed_csv(self) -> Optional[Path]:
        """
        Get the latest Amazon CSV file that hasn't been processed yet.

        Returns:
            Path to CSV file or None if no unprocessed files found
        """
        csv_files = self.find_amazon_csv_files()

        for csv_file in csv_files:
            file_hash = self._get_file_hash(csv_file)

            # Check if already processed
            if file_hash not in self.state['processed_files']:
                logger.info(f"Found unprocessed CSV: {csv_file.name}")
                return csv_file
            else:
                processed_info = self.state['processed_files'][file_hash]
                logger.debug(f"Skipping already processed file: {csv_file.name} "
                           f"(processed at {processed_info['processed_at']})")

        return None

    def mark_as_processed(self, file_path: Path, transaction_count: int = 0):
        """
        Mark a file as processed in the state.

        Args:
            file_path: Path to the processed file
            transaction_count: Number of transactions imported from file
        """
        file_hash = self._get_file_hash(file_path)

        self.state['processed_files'][file_hash] = {
            'file_name': file_path.name,
            'file_path': str(file_path),
            'processed_at': datetime.now().isoformat(),
            'transaction_count': transaction_count,
            'file_size': file_path.stat().st_size
        }

        # Clean up old entries (keep only last 90 days)
        cutoff_date = datetime.now() - timedelta(days=90)
        self.state['processed_files'] = {
            k: v for k, v in self.state['processed_files'].items()
            if datetime.fromisoformat(v['processed_at']) > cutoff_date
        }

        self._save_state()
        logger.info(f"Marked as processed: {file_path.name} ({transaction_count} transactions)")

    def archive_file(self, file_path: Path) -> Path:
        """
        Move processed file to archive directory.

        Args:
            file_path: Path to file to archive

        Returns:
            Path to archived file
        """
        # Create archive subdirectory with date
        date_dir = self.archive_dir / datetime.now().strftime("%Y-%m")
        date_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique archive name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{timestamp}_{file_path.name}"
        archive_path = date_dir / archive_name

        try:
            # Move file to archive
            file_path.rename(archive_path)
            logger.info(f"Archived file: {file_path.name} -> {archive_path}")
            return archive_path
        except Exception as e:
            logger.error(f"Error archiving file {file_path}: {e}")
            return file_path

    def process_csv_file(self, file_path: Path, callback=None) -> bool:
        """
        Process a CSV file with proper locking and state management.

        Args:
            file_path: Path to CSV file to process
            callback: Function to call with file path for processing

        Returns:
            True if successfully processed, False otherwise
        """
        # Wait for file to be completely written
        if not self._wait_for_file_completion(file_path):
            logger.warning(f"File not ready after timeout: {file_path}")
            return False

        # Check if already processed
        file_hash = self._get_file_hash(file_path)
        if file_hash in self.state['processed_files']:
            logger.info(f"File already processed: {file_path.name}")
            return False

        # Process the file
        if callback:
            try:
                transaction_count = callback(file_path)
                self.mark_as_processed(file_path, transaction_count)

                # Archive if enabled
                if self.archive_dir:
                    self.archive_file(file_path)

                return True
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                return False
        else:
            logger.warning("No callback provided for processing")
            return False

    def start_monitoring(self, callback, interval: int = 300):
        """
        Start continuous monitoring of downloads folder.

        Args:
            callback: Function to call when new CSV is detected
            interval: Check interval in seconds (default: 5 minutes)
        """
        logger.info(f"Starting continuous monitoring (interval: {interval}s)")

        observer = Observer()
        handler = AmazonCSVHandler(lambda path: self.process_csv_file(Path(path), callback))
        observer.schedule(handler, str(self.downloads_dir), recursive=False)
        observer.start()

        try:
            while True:
                # Also do periodic check for files that might have been missed
                csv_file = self.get_latest_unprocessed_csv()
                if csv_file:
                    self.process_csv_file(csv_file, callback)

                time.sleep(interval)
        except KeyboardInterrupt:
            observer.stop()
            logger.info("Monitoring stopped by user")

        observer.join()

    def get_processing_stats(self) -> Dict:
        """
        Get statistics about processed files.

        Returns:
            Dictionary with processing statistics
        """
        if not self.state['processed_files']:
            return {
                'total_files': 0,
                'total_transactions': 0,
                'last_processed': None
            }

        processed = self.state['processed_files'].values()

        return {
            'total_files': len(processed),
            'total_transactions': sum(p['transaction_count'] for p in processed),
            'last_processed': max(p['processed_at'] for p in processed),
            'files': [
                {
                    'name': p['file_name'],
                    'date': p['processed_at'],
                    'transactions': p['transaction_count']
                }
                for p in sorted(processed,
                              key=lambda x: x['processed_at'],
                              reverse=True)[:10]
            ]
        }


def test_monitor():
    """Test function for the downloads monitor."""
    monitor = DownloadsMonitor()

    # Find CSV files
    csv_files = monitor.find_amazon_csv_files()
    print(f"Found {len(csv_files)} Amazon CSV files:")
    for f in csv_files:
        print(f"  - {f.name} ({f.stat().st_size:,} bytes)")

    # Get latest unprocessed
    latest = monitor.get_latest_unprocessed_csv()
    if latest:
        print(f"\nLatest unprocessed: {latest.name}")
    else:
        print("\nNo unprocessed CSV files found")

    # Show stats
    stats = monitor.get_processing_stats()
    print(f"\nProcessing Stats:")
    print(f"  Total files processed: {stats['total_files']}")
    print(f"  Total transactions: {stats['total_transactions']}")
    if stats['last_processed']:
        print(f"  Last processed: {stats['last_processed']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_monitor()