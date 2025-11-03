#!/usr/bin/env python3
"""
Scheduler for Relationship Tracking Reports

Runs on a schedule to automatically generate and send relationship reports.
Configured for:
- Saturday at 7:00 PM EST
- Wednesday at 6:30 PM EST
"""

import os
import sys
import logging
import yaml
import schedule
import time
from datetime import datetime
from pathlib import Path
import pytz

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from relationship_main import (
    setup_logging,
    load_config,
    load_environment,
    generate_report,
    validate_configuration
)


def scheduled_report_job():
    """Job to run on schedule."""
    logger = logging.getLogger(__name__)

    try:
        logger.info("="*60)
        logger.info("SCHEDULED REPORT GENERATION STARTED")
        logger.info("="*60)

        # Load configuration
        config = load_config()

        # Validate configuration
        if not validate_configuration(config):
            logger.error("Configuration validation failed, skipping report generation")
            return

        # Generate and send report
        generate_report(config, send_email=True)

        logger.info("="*60)
        logger.info("SCHEDULED REPORT GENERATION COMPLETED")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"Error in scheduled job: {str(e)}", exc_info=True)


def setup_schedule(config: dict):
    """
    Setup the schedule based on configuration.

    Args:
        config: Configuration dictionary
    """
    logger = logging.getLogger(__name__)

    tracking_config = config.get('relationship_tracking', {})
    timezone_str = tracking_config.get('timezone', 'America/New_York')
    tz = pytz.timezone(timezone_str)

    # Get schedule from config (defaults provided)
    schedules = tracking_config.get('schedule', [
        '0 19 * * 6',   # Saturday 7pm
        '30 18 * * 3'   # Wednesday 6:30pm
    ])

    logger.info(f"Setting up schedule in timezone: {timezone_str}")

    # Parse and schedule each time
    for schedule_str in schedules:
        parts = schedule_str.split()
        if len(parts) != 5:
            logger.warning(f"Invalid schedule format: {schedule_str}")
            continue

        minute, hour, _, _, weekday = parts

        # Convert cron weekday (0-6, 0=Sunday) to schedule weekday
        weekday_map = {
            '0': schedule.every().sunday,
            '1': schedule.every().monday,
            '2': schedule.every().tuesday,
            '3': schedule.every().wednesday,
            '4': schedule.every().thursday,
            '5': schedule.every().friday,
            '6': schedule.every().saturday,
        }

        if weekday not in weekday_map:
            logger.warning(f"Invalid weekday in schedule: {weekday}")
            continue

        # Format time
        time_str = f"{hour.zfill(2)}:{minute.zfill(2)}"

        # Schedule the job
        weekday_map[weekday].at(time_str).do(scheduled_report_job)

        day_name = [
            'Sunday', 'Monday', 'Tuesday', 'Wednesday',
            'Thursday', 'Friday', 'Saturday'
        ][int(weekday)]

        logger.info(f"✅ Scheduled: {day_name}s at {time_str} {timezone_str}")
        print(f"✅ Scheduled: {day_name}s at {time_str} {timezone_str}")

    return schedule


def run_scheduler():
    """Run the scheduler continuously."""
    logger = logging.getLogger(__name__)

    print("\n" + "="*60)
    print("RELATIONSHIP TRACKING SCHEDULER")
    print("="*60 + "\n")

    try:
        # Load configuration
        config = load_config()

        # Setup logging
        setup_logging(config)

        # Load environment
        load_environment()

        # Validate configuration
        print("Validating configuration...")
        if not validate_configuration(config):
            print("❌ Configuration validation failed")
            logger.error("Configuration validation failed")
            sys.exit(1)

        print("✅ Configuration validated\n")

        # Setup schedule
        print("Setting up schedule...")
        setup_schedule(config)

        print(f"\n{'='*60}")
        print("Scheduler is running... Press Ctrl+C to stop")
        print(f"{'='*60}\n")

        logger.info("Scheduler started successfully")

        # Run pending jobs and sleep
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        print("\n\n✋ Scheduler stopped by user")
        logger.info("Scheduler stopped by user")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Scheduler error: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Relationship Tracking Report Scheduler'
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='Run report generation immediately (test mode)'
    )

    args = parser.parse_args()

    if args.test:
        # Run report generation immediately for testing
        print("\n🧪 TEST MODE - Running report generation now...\n")

        config = load_config()
        setup_logging(config)
        load_environment()

        if validate_configuration(config):
            scheduled_report_job()
        else:
            print("❌ Configuration validation failed")
            sys.exit(1)
    else:
        # Run scheduler
        run_scheduler()


if __name__ == '__main__':
    main()
