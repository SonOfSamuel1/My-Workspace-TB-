#!/usr/bin/env python3
"""
Toggl Daily Productivity Report - Main Entry Point

Generates and sends daily productivity reports via email.
"""

import os
import sys
import logging
import argparse
import yaml
from datetime import datetime
from dotenv import load_dotenv

from productivity_service import ProductivityService
from report_generator import ReportGenerator
from ses_email_sender import SESEmailSender


def setup_logging(log_level: str = 'INFO'):
    """Setup logging configuration."""
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'productivity.log')

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def load_config() -> dict:
    """Load configuration from config.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config.get('productivity_report', {})


def load_environment():
    """Load environment variables from .env file."""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)


def get_period() -> str:
    """Determine if this is a morning or evening report."""
    hour = datetime.now().hour
    if hour < 12:
        return "Morning"
    else:
        return "Evening"


def generate_and_send_report(config: dict, test_mode: bool = False) -> bool:
    """
    Generate and send the productivity report.

    Args:
        config: Configuration dictionary
        test_mode: If True, don't actually send email

    Returns:
        True if successful, False otherwise
    """
    logger = logging.getLogger(__name__)

    try:
        # Initialize services
        logger.info("Initializing services...")
        productivity = ProductivityService(config)
        generator = ReportGenerator()

        # Get email config
        email_config = config.get('email', {})
        ses_config = config.get('ses', {})

        recipient = os.getenv('REPORT_RECIPIENT', email_config.get('recipient', ''))
        sender = os.getenv('SES_SENDER_EMAIL', ses_config.get('sender_email', ''))
        region = os.getenv('AWS_REGION', ses_config.get('region', 'us-east-1'))

        if not recipient:
            logger.error("No recipient email configured")
            return False

        # Generate report data
        logger.info("Generating productivity report...")
        report_data = productivity.get_productivity_report()

        # Generate HTML
        period = get_period()
        html_content = generator.generate_html_report(report_data, period)
        text_content = generator.generate_text_report(report_data, period)

        # Format subject
        subject_template = email_config.get('subject_template', 'Daily Productivity Report - {date} {period}')
        subject = subject_template.format(
            date=datetime.now().strftime('%Y-%m-%d'),
            period=period
        )

        logger.info(f"Report generated: {report_data['yesterday_total']} mins yesterday ({report_data['yesterday_percent']}%)")

        if test_mode:
            logger.info("TEST MODE - Not sending email")
            print("\n" + "=" * 50)
            print("REPORT PREVIEW")
            print("=" * 50)
            print(text_content)
            return True

        # Send email
        logger.info(f"Sending email to {recipient}...")
        email_sender = SESEmailSender(
            sender_email=sender,
            region=region
        )

        success = email_sender.send_html_email(
            to=recipient,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

        if success:
            logger.info("Email sent successfully!")
        else:
            logger.error("Failed to send email")

        return success

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        return False


def validate_configuration(config: dict) -> bool:
    """
    Validate the configuration.

    Args:
        config: Configuration dictionary

    Returns:
        True if valid, False otherwise
    """
    logger = logging.getLogger(__name__)
    logger.info("Validating configuration...")

    errors = []

    # Check Toggl credentials
    if not os.getenv('TOGGL_API_TOKEN'):
        errors.append("TOGGL_API_TOKEN not set")
    if not os.getenv('TOGGL_WORKSPACE_ID'):
        errors.append("TOGGL_WORKSPACE_ID not set")

    # Check email config
    recipient = os.getenv('REPORT_RECIPIENT', config.get('email', {}).get('recipient', ''))
    if not recipient:
        errors.append("No email recipient configured")

    # Check categories
    categories = config.get('categories', {})
    if not categories:
        logger.warning("No categories configured - all time will be 'other'")

    # Validate Toggl connection
    try:
        from toggl_service import TogglService
        toggl = TogglService()
        if toggl.validate_credentials():
            logger.info("Toggl credentials: VALID")
        else:
            errors.append("Toggl credentials invalid")
    except Exception as e:
        errors.append(f"Toggl connection error: {str(e)}")

    if errors:
        logger.error("Configuration validation FAILED:")
        for error in errors:
            logger.error(f"  - {error}")
        return False

    logger.info("Configuration validation PASSED")
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Toggl Daily Productivity Report'
    )
    parser.add_argument(
        '--generate',
        action='store_true',
        help='Generate and send report now'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate configuration'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Generate report but don\'t send email'
    )
    parser.add_argument(
        '--schedule',
        action='store_true',
        help='Run as scheduled daemon'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    args = parser.parse_args()

    # Setup
    setup_logging(args.log_level)
    load_environment()
    logger = logging.getLogger(__name__)

    try:
        config = load_config()
    except FileNotFoundError as e:
        logger.error(str(e))
        return 1

    logger.info("=== Toggl Daily Productivity Report ===")

    if args.validate:
        return 0 if validate_configuration(config) else 1

    if args.generate or args.test:
        success = generate_and_send_report(config, test_mode=args.test)
        return 0 if success else 1

    if args.schedule:
        from scheduler import run_scheduler
        run_scheduler(config)
        return 0

    # Default: show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
