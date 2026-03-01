#!/usr/bin/env python3
"""
Scheduler for Daily Productivity Reports

Handles scheduled execution of productivity reports based on configuration.
Schedule:
- Mon-Fri: 6:00 AM and 7:00 PM
- Saturday: 7:30 PM only
- Sunday: 6:00 AM and 7:00 PM
"""

import os
import sys
import logging
import time
from datetime import datetime
import schedule
import pytz

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from main import generate_and_send_report, load_config, load_environment


logger = logging.getLogger(__name__)


def get_current_time_in_timezone(timezone_str: str = 'America/New_York') -> datetime:
    """Get current time in specified timezone."""
    tz = pytz.timezone(timezone_str)
    return datetime.now(tz)


def should_run_morning_report() -> bool:
    """Check if morning report should run (not on Saturday)."""
    now = get_current_time_in_timezone()
    # Saturday is weekday 5
    return now.weekday() != 5


def scheduled_report_job(config: dict, period: str = "auto"):
    """
    Job to run scheduled report.

    Args:
        config: Configuration dictionary
        period: "Morning", "Evening", or "auto" to detect
    """
    logger.info(f"=== Scheduled Report Job Started ({period}) ===")

    try:
        success = generate_and_send_report(config)
        if success:
            logger.info("Scheduled report completed successfully")
        else:
            logger.error("Scheduled report failed")
    except Exception as e:
        logger.error(f"Error in scheduled job: {str(e)}", exc_info=True)


def morning_report_job(config: dict):
    """Morning report job - skips Saturday."""
    if should_run_morning_report():
        scheduled_report_job(config, "Morning")
    else:
        logger.info("Skipping morning report (Saturday)")


def evening_report_job(config: dict):
    """Evening report job - runs every day."""
    scheduled_report_job(config, "Evening")


def saturday_evening_job(config: dict):
    """Saturday evening report at 7:30 PM."""
    now = get_current_time_in_timezone()
    if now.weekday() == 5:  # Saturday
        scheduled_report_job(config, "Evening")


def setup_schedule(config: dict):
    """
    Setup the schedule based on configuration.

    Schedule:
    - Mon-Fri: 6:00 AM and 7:00 PM
    - Saturday: 7:30 PM only
    - Sunday: 6:00 AM and 7:00 PM
    """
    logger.info("Setting up schedule...")

    # Clear any existing jobs
    schedule.clear()

    # Morning reports: 6:00 AM (Mon-Fri, Sun) - handled by morning_report_job which skips Saturday
    schedule.every().day.at("06:00").do(morning_report_job, config)
    logger.info("Scheduled: Morning report at 6:00 AM (Mon-Fri, Sun)")

    # Evening reports: 7:00 PM (Sun-Fri)
    schedule.every().sunday.at("19:00").do(evening_report_job, config)
    schedule.every().monday.at("19:00").do(evening_report_job, config)
    schedule.every().tuesday.at("19:00").do(evening_report_job, config)
    schedule.every().wednesday.at("19:00").do(evening_report_job, config)
    schedule.every().thursday.at("19:00").do(evening_report_job, config)
    schedule.every().friday.at("19:00").do(evening_report_job, config)
    logger.info("Scheduled: Evening report at 7:00 PM (Sun-Fri)")

    # Saturday evening: 7:30 PM
    schedule.every().saturday.at("19:30").do(saturday_evening_job, config)
    logger.info("Scheduled: Saturday evening report at 7:30 PM")

    logger.info(f"Total jobs scheduled: {len(schedule.get_jobs())}")


def run_scheduler(config: dict):
    """
    Run the scheduler daemon.

    Args:
        config: Configuration dictionary
    """
    logger.info("=== Starting Productivity Report Scheduler ===")

    timezone = config.get('timezone', 'America/New_York')
    logger.info(f"Timezone: {timezone}")

    # Setup schedule
    setup_schedule(config)

    # Show next run times
    for job in schedule.get_jobs():
        logger.info(f"Next run: {job.next_run}")

    logger.info("Scheduler running. Press Ctrl+C to stop.")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load config
    load_environment()

    try:
        config = load_config()
    except FileNotFoundError:
        logger.error("Config file not found")
        sys.exit(1)

    # Check for --test flag
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        logger.info("Running immediate test report...")
        generate_and_send_report(config, test_mode=True)
    else:
        run_scheduler(config)
