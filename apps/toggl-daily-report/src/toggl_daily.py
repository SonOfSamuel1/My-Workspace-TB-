#!/usr/bin/env python3
"""
Toggl Daily Report - Main Entry Point

Generates and sends daily performance reports for Toggl Track time tracking.
"""

import os
import sys
import logging
import argparse
import yaml
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from toggl_service import TogglService
from daily_report_generator import DailyReportGenerator
from report_formatter import ReportFormatter
from email_sender import EmailSender


class TogglDailyReport:
    """Main orchestrator for Toggl daily reports."""

    def __init__(self, config_path: str = 'config.yaml', env_path: str = '.env'):
        """
        Initialize Toggl Daily Report system.

        Args:
            config_path: Path to configuration file
            env_path: Path to environment file
        """
        self.logger = self._setup_logging()
        self.config = self._load_config(config_path)
        self.env_path = env_path

        # Initialize services
        self.toggl = None
        self.generator = None
        self.formatter = None
        self.email_sender = None

    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/daily_report.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )

        return logging.getLogger(__name__)

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"Configuration loaded from {config_path}")
            return config
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing configuration: {e}")
            raise

    def _initialize_services(self) -> bool:
        """
        Initialize all required services.

        Returns:
            True if all services initialized successfully, False otherwise
        """
        try:
            # Initialize Toggl service
            self.logger.info("Initializing Toggl service...")
            self.toggl = TogglService(self.env_path)

            # Validate Toggl credentials
            if not self.toggl.validate_credentials():
                self.logger.error("Failed to validate Toggl credentials")
                return False

            # Initialize report generator
            self.logger.info("Initializing report generator...")
            self.generator = DailyReportGenerator(self.toggl, self.config)

            # Initialize report formatter
            self.logger.info("Initializing report formatter...")
            self.formatter = ReportFormatter(self.config)

            # Initialize email sender
            self.logger.info("Initializing email sender...")
            google_config = self.config.get('google', {})
            credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE',
                                        google_config.get('credentials_file'))
            token_file = os.getenv('GOOGLE_TOKEN_FILE',
                                  google_config.get('token_file'))

            self.email_sender = EmailSender(credentials_file, token_file)

            # Validate email credentials
            if not self.email_sender.validate_credentials():
                self.logger.error("Failed to validate Gmail credentials")
                return False

            self.logger.info("All services initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}", exc_info=True)
            return False

    def generate_report(self, target_date: Optional[datetime] = None) -> bool:
        """
        Generate daily report for the specified date.

        Args:
            target_date: Date to generate report for (defaults to today)

        Returns:
            True if report generated successfully, False otherwise
        """
        try:
            if not self._initialize_services():
                return False

            # Generate report data
            self.logger.info("Generating daily report...")
            report_data = self.generator.generate_daily_report(target_date)

            if report_data['total_hours'] == 0:
                self.logger.warning("No time tracked today. Report will show zero hours.")

            # Format report as HTML
            self.logger.info("Formatting report...")
            html_content = self.formatter.format_daily_report(report_data)

            # Prepare email
            email_config = self.config.get('report', {}).get('email', {})
            recipient = os.getenv('REPORT_RECIPIENT_EMAIL',
                                 email_config.get('recipient'))
            subject_template = email_config.get('subject_template',
                                               'Toggl Daily Report - {date}')
            subject = subject_template.format(date=report_data['date_formatted'])

            # Send email
            self.logger.info(f"Sending report to {recipient}...")
            success = self.email_sender.send_html_email(
                to=recipient,
                subject=subject,
                html_content=html_content
            )

            if success:
                self.logger.info("✓ Daily report sent successfully")
                return True
            else:
                self.logger.error("✗ Failed to send daily report")
                return False

        except Exception as e:
            self.logger.error(f"Error generating report: {e}", exc_info=True)
            return False

    def generate_and_save(self, output_file: str, target_date: Optional[datetime] = None) -> bool:
        """
        Generate report and save to file (for testing).

        Args:
            output_file: Path to save HTML report
            target_date: Date to generate report for (defaults to today)

        Returns:
            True if report saved successfully, False otherwise
        """
        try:
            if not self._initialize_services():
                return False

            # Generate report data
            self.logger.info("Generating daily report...")
            report_data = self.generator.generate_daily_report(target_date)

            # Format report as HTML
            self.logger.info("Formatting report...")
            html_content = self.formatter.format_daily_report(report_data)

            # Save to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            self.logger.info(f"✓ Report saved to {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving report: {e}", exc_info=True)
            return False

    def validate_setup(self) -> bool:
        """
        Validate that all required services and credentials are configured.

        Returns:
            True if all validations pass, False otherwise
        """
        self.logger.info("Validating setup...")

        # Check configuration
        required_config = ['report', 'google', 'toggl']
        for key in required_config:
            if key not in self.config:
                self.logger.error(f"Missing required configuration section: {key}")
                return False

        # Initialize and validate services
        if not self._initialize_services():
            return False

        self.logger.info("✓ Setup validation complete")
        return True


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Toggl Daily Report - Generate and send daily time tracking reports'
    )

    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )

    parser.add_argument(
        '--env',
        default='.env',
        help='Path to environment file (default: .env)'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate setup and credentials'
    )

    parser.add_argument(
        '--generate',
        action='store_true',
        help='Generate and send daily report'
    )

    parser.add_argument(
        '--save',
        type=str,
        metavar='FILE',
        help='Generate report and save to file (for testing)'
    )

    parser.add_argument(
        '--date',
        type=str,
        metavar='YYYY-MM-DD',
        help='Target date for report (default: today)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse target date if provided
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Invalid date format. Use YYYY-MM-DD")
            return 1

    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    os.chdir(parent_dir)

    # Initialize system
    try:
        system = TogglDailyReport(config_path=args.config, env_path=args.env)
    except Exception as e:
        print(f"Error initializing system: {e}")
        return 1

    # Execute command
    if args.validate:
        success = system.validate_setup()
        return 0 if success else 1

    elif args.save:
        success = system.generate_and_save(args.save, target_date)
        return 0 if success else 1

    elif args.generate:
        success = system.generate_report(target_date)
        return 0 if success else 1

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
