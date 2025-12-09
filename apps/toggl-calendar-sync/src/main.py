#!/usr/bin/env python3
"""
Toggl to Google Calendar Sync - Main Entry Point

This script synchronizes Toggl Track time entries to Google Calendar.
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timedelta
from sync_service import SyncService


def setup_logging():
    """Setup logging configuration."""
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'sync.log')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)

    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Sync Toggl Track time entries to Google Calendar'
    )
    parser.add_argument(
        '--mode',
        choices=['today', 'yesterday', 'week', 'date', 'validate'],
        default='today',
        help='Sync mode (default: today)'
    )
    parser.add_argument(
        '--date',
        type=str,
        help='Specific date to sync (YYYY-MM-DD) - requires --mode date'
    )
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run continuously with interval checks'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Interval in minutes for continuous mode (default: 5)'
    )

    args = parser.parse_args()

    try:
        # Initialize sync service
        logger.info("=== Toggl to Calendar Sync Started ===")
        sync = SyncService()

        # Validate services
        if args.mode == 'validate':
            logger.info("Validating services...")
            if sync.validate_services():
                logger.info("✓ All services validated successfully")
                stats = sync.get_sync_stats()
                logger.info(f"Sync enabled: {stats['sync_enabled']}")
                logger.info(f"Total synced entries: {stats['total_synced_entries']}")
                logger.info(f"Last sync: {stats['last_sync'] or 'Never'}")
                return 0
            else:
                logger.error("✗ Service validation failed")
                return 1

        # Check if sync is enabled
        if not sync.sync_enabled:
            logger.warning("Sync is disabled in configuration")
            return 0

        # Perform sync based on mode
        if args.mode == 'today':
            logger.info("Syncing today's entries...")
            result = sync.sync_today()

        elif args.mode == 'yesterday':
            logger.info("Syncing yesterday's entries...")
            result = sync.sync_yesterday()

        elif args.mode == 'week':
            logger.info("Syncing current week's entries...")
            result = sync.sync_week()

        elif args.mode == 'date':
            if not args.date:
                logger.error("--date argument required for date mode")
                return 1

            try:
                date = datetime.strptime(args.date, '%Y-%m-%d')
                logger.info(f"Syncing entries for {args.date}...")
                result = sync.sync_date_range(
                    start_date=date.replace(hour=0, minute=0, second=0),
                    end_date=date.replace(hour=23, minute=59, second=59)
                )
            except ValueError:
                logger.error("Invalid date format. Use YYYY-MM-DD")
                return 1

        # Log results
        logger.info("=== Sync Complete ===")
        logger.info(f"Total entries: {result['total_entries']}")
        logger.info(f"Newly synced: {result['synced']}")
        logger.info(f"Updated: {result['updated']}")
        logger.info(f"Skipped: {result['skipped']}")
        logger.info(f"Failed: {result['failed']}")

        if result.get('errors'):
            logger.error(f"Errors encountered: {len(result['errors'])}")
            for error in result['errors']:
                logger.error(f"  - {error}")

        # Continuous mode
        if args.continuous:
            logger.info(f"Entering continuous mode (interval: {args.interval} minutes)")
            import time

            while True:
                time.sleep(args.interval * 60)
                logger.info("Running scheduled sync...")

                try:
                    result = sync.sync_today()
                    logger.info(f"Synced: {result['synced']}, Updated: {result['updated']}, Failed: {result['failed']}")
                except Exception as e:
                    logger.error(f"Error during scheduled sync: {str(e)}")

        return 0

    except KeyboardInterrupt:
        logger.info("Sync interrupted by user")
        return 0

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
