#!/usr/bin/env python3
"""
Main entry point for Kaelin Development Tracking Automation

This script orchestrates the Love Kaelin development tracking system,
generating comprehensive reports on father-daughter activities.
"""

import os
import sys
import logging
import yaml
import argparse
from datetime import datetime
from pathlib import Path
import pytz

# Add project root and shared directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'love-brittany-tracker' / 'src'))

from kaelin_tracker import KaelinTracker
from kaelin_report import KaelinReportGenerator

# Import shared services from love-brittany-tracker
try:
    from calendar_service import CalendarService
    from toggl_service import TogglService
    from docs_service import DocsService
    from email_sender import EmailSender
except ImportError:
    print("Error: Could not import shared services from love-brittany-tracker")
    print("Make sure love-brittany-tracker is set up properly")
    sys.exit(1)


def setup_logging(config: dict):
    """Setup logging configuration."""
    log_config = config.get('logging', {})

    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = log_config.get('file', 'logs/kaelin_tracker.log')

    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def load_config() -> dict:
    """Load configuration from config.yaml."""
    config_path = Path('config.yaml')

    if not config_path.exists():
        raise FileNotFoundError(
            "Configuration file 'config.yaml' not found. "
            "Please create it from the template."
        )

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config


def load_environment():
    """Load environment variables from .env file."""
    # Try to load from parent directory (shared with love-brittany-tracker)
    env_paths = [
        Path('.env'),
        Path('../.env'),
        Path('../../.env')
    ]

    env_loaded = False
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            env_loaded = True
            break

    if not env_loaded:
        raise FileNotFoundError(
            "Environment file '.env' not found. "
            "Please create it or use the shared .env from love-brittany-tracker"
        )


def validate_configuration(config: dict) -> bool:
    """
    Validate that required configuration is present.

    Args:
        config: Configuration dictionary

    Returns:
        True if valid, False otherwise
    """
    logger = logging.getLogger(__name__)

    # Check required environment variables
    required_env_vars = [
        'GOOGLE_CREDENTIALS_FILE',
        'TOGGL_API_TOKEN'
    ]

    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please update your .env file with these values")
        return False

    # Check kaelin tracking enabled
    if not config.get('kaelin_tracking', {}).get('enabled'):
        logger.warning("Kaelin tracking is disabled in config.yaml")
        return False

    # Check tracking document ID
    tracking_config = config.get('kaelin_tracking', {})
    if not tracking_config.get('tracking_doc_id'):
        logger.error("Tracking document ID not configured")
        logger.error("Set 'tracking_doc_id' in config.yaml")
        return False

    logger.info("Configuration validation passed")
    return True


def initialize_services(config: dict):
    """
    Initialize all required services.

    Args:
        config: Configuration dictionary

    Returns:
        Tuple of (calendar_service, docs_service, toggl_service)
    """
    logger = logging.getLogger(__name__)

    credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', '../credentials/credentials.json')
    token_file = os.getenv('GOOGLE_TOKEN_FILE', '../credentials/token.pickle')

    logger.info("Initializing Calendar Service...")
    calendar_service = CalendarService()

    logger.info("Initializing Docs Service...")
    docs_service = DocsService(credentials_file, token_file)
    docs_service.authenticate()

    logger.info("Initializing Toggl Service...")
    toggl_service = TogglService()

    logger.info("All services initialized successfully")
    return calendar_service, docs_service, toggl_service


def generate_report(config: dict, send_email: bool = True):
    """
    Generate and optionally send Kaelin development tracking report.

    Args:
        config: Configuration dictionary
        send_email: Whether to send the report via email
    """
    logger = logging.getLogger(__name__)

    try:
        # Initialize services
        calendar_service, docs_service, toggl_service = initialize_services(config)

        # Get tracking configuration
        tracking_config = config['kaelin_tracking']

        # Create tracker
        logger.info("Creating Kaelin Development Tracker...")
        tracker = KaelinTracker(
            calendar_service=calendar_service,
            docs_service=docs_service,
            toggl_service=toggl_service,
            config=tracking_config
        )

        # Generate report data
        logger.info("Generating Kaelin development report data...")
        report_data = tracker.generate_report()

        # Generate HTML report
        logger.info("Generating HTML email...")
        report_generator = KaelinReportGenerator(tracking_config)
        html_content = report_generator.generate_html_report(report_data)

        # Save HTML to file for review
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'kaelin_report_{timestamp}.html'

        with open(output_file, 'w') as f:
            f.write(html_content)

        logger.info(f"Report saved to: {output_file}")
        print(f"\n✅ Report generated successfully!")
        print(f"📄 Saved to: {output_file}")

        # Send email if requested
        if send_email:
            recipient = tracking_config.get('email', {}).get('recipient')

            if not recipient:
                logger.error("No email recipient configured")
                print("\n⚠️  Email not sent: No recipient configured")
                return

            logger.info(f"Sending email to {recipient}...")

            # Initialize email sender
            credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', '../credentials/credentials.json')
            token_file = os.getenv('GOOGLE_TOKEN_FILE', '../credentials/token.pickle')

            email_sender = EmailSender(
                credentials_path=credentials_file,
                token_path=token_file
            )

            # Generate subject
            now = datetime.now(pytz.timezone(tracking_config.get('timezone', 'America/New_York')))
            subject_template = tracking_config.get('email', {}).get(
                'subject_template',
                'Love Kaelin Development Report - {date}'
            )
            subject = subject_template.format(date=now.strftime('%B %d, %Y'))

            # Send email
            success = email_sender.send_html_email(
                to=recipient,
                subject=subject,
                html_content=html_content
            )

            if success:
                print(f"📧 Email sent successfully to {recipient}")
                logger.info(f"Email sent successfully to {recipient}")
            else:
                print(f"\n❌ Failed to send email to {recipient}")
                logger.error(f"Failed to send email to {recipient}")

        # Print summary
        print(f"\n{'='*60}")
        print("REPORT SUMMARY")
        print(f"{'='*60}")

        critical_alerts = [a for a in report_data['alerts'] if a['level'] == 'critical']
        warning_alerts = [a for a in report_data['alerts'] if a['level'] == 'warning']
        play_time = report_data['play_time']
        teachings = report_data['jesus_teachings']

        print(f"🚨 Critical Alerts: {len(critical_alerts)}")
        print(f"⚠️  Warnings: {len(warning_alerts)}")
        print(f"🎮 Days Played (Last 7 Days): {play_time['days_played_last_7_days']}")
        print(f"📊 100-Day Average: {play_time['rolling_100_avg_percentage']:.1f}%")
        print(f"✝️  Teachings Progress: {teachings['taught_count']}/{teachings['total_teachings']}")

        if critical_alerts:
            print(f"\n⚠️  CRITICAL ITEMS NEED ATTENTION:")
            for alert in critical_alerts[:3]:
                print(f"   • {alert['category']}: {alert['message']}")

        print(f"{'='*60}\n")

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


def validate_setup():
    """Validate that all services are properly configured."""
    logger = logging.getLogger(__name__)

    print("\n" + "="*60)
    print("KAELIN DEVELOPMENT TRACKING SETUP VALIDATION")
    print("="*60 + "\n")

    try:
        # Load config
        print("📋 Loading configuration...")
        config = load_config()
        print("✅ Config loaded")

        # Load environment
        print("🔐 Loading environment variables...")
        load_environment()
        print("✅ Environment loaded")

        # Validate configuration
        print("✔️  Validating configuration...")
        if not validate_configuration(config):
            print("❌ Configuration validation failed")
            return False
        print("✅ Configuration valid")

        # Test Calendar service
        print("\n📅 Testing Google Calendar connection...")
        calendar_service = CalendarService()
        if calendar_service.validate_credentials():
            print("✅ Calendar connection successful")
        else:
            print("❌ Calendar connection failed")
            return False

        # Test Docs service
        print("📄 Testing Google Docs connection...")
        credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', '../credentials/credentials.json')
        token_file = os.getenv('GOOGLE_TOKEN_FILE', '../credentials/token.pickle')

        docs_service = DocsService(credentials_file, token_file)
        docs_service.authenticate()

        doc_id = config['kaelin_tracking'].get('tracking_doc_id')
        if doc_id:
            try:
                metadata = docs_service.get_document_metadata(doc_id)
                print(f"✅ Docs connection successful - Found document: {metadata.get('title')}")
            except Exception as e:
                print(f"⚠️  Could not access tracking document: {e}")
                print("   Please create your tracking document using the template")
        else:
            print("⚠️  No tracking document ID configured")

        # Test Toggl service
        print("⏱️  Testing Toggl connection...")
        toggl_service = TogglService()
        if toggl_service.validate_credentials():
            print("✅ Toggl connection successful")
        else:
            print("❌ Toggl connection failed")
            return False

        # Test Email service
        print("📧 Testing Gmail connection...")
        email_sender = EmailSender(credentials_file, token_file)
        if email_sender.validate_credentials():
            print("✅ Gmail connection successful")
        else:
            print("❌ Gmail connection failed")
            return False

        print("\n" + "="*60)
        print("✅ ALL VALIDATIONS PASSED!")
        print("="*60 + "\n")

        print("Next steps:")
        print("1. Create your tracking document using docs/KAELIN_TRACKING_TEMPLATE.md")
        print("2. Add the document ID to config.yaml")
        print("3. Run: python src/kaelin_main.py --generate")
        print("4. Review the generated report in output/\n")

        return True

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        print(f"\n❌ Validation failed: {str(e)}\n")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Love Kaelin Development Tracker'
    )

    parser.add_argument(
        '--generate',
        action='store_true',
        help='Generate and send Kaelin development tracking report'
    )

    parser.add_argument(
        '--no-email',
        action='store_true',
        help='Generate report but do not send email'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate setup and configuration'
    )

    args = parser.parse_args()

    # Load config
    config = load_config()

    # Setup logging
    setup_logging(config)

    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("Starting Kaelin Development Tracking Automation")
    logger.info("="*60)

    # Load environment
    load_environment()

    if args.validate:
        # Run validation
        sys.exit(0 if validate_setup() else 1)

    elif args.generate:
        # Validate first
        if not validate_configuration(config):
            sys.exit(1)

        # Generate report
        send_email = not args.no_email
        generate_report(config, send_email=send_email)

    else:
        # Default: show help
        parser.print_help()
        print("\nExamples:")
        print("  python src/kaelin_main.py --validate")
        print("  python src/kaelin_main.py --generate")
        print("  python src/kaelin_main.py --generate --no-email")


if __name__ == '__main__':
    main()
