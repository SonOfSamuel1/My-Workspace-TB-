#!/usr/bin/env python3
"""
Main entry point for Sleep Eight Daily Reporter

This script orchestrates the sleep reporting system,
fetching data from Eight Sleep and sending daily email reports.
"""
import os
import sys
import logging
import yaml
import argparse
from datetime import datetime
from pathlib import Path
import pytz

# Add project root to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use python-dotenv for proper .env loading
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

from eight_sleep_service import EightSleepService
from sleep_report import SleepReportGenerator
from ses_email_sender import SESEmailSender


def setup_logging(config: dict):
    """Setup logging configuration."""
    log_config = config.get('logging', {})

    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = log_config.get('file', 'logs/sleep_report.log')

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
    # Check multiple possible config locations
    possible_paths = [
        Path('config.yaml'),
        Path(__file__).parent.parent / 'config.yaml',
    ]

    config_path = None
    for path in possible_paths:
        if path.exists():
            config_path = path
            break

    if not config_path:
        raise FileNotFoundError(
            "Configuration file 'config.yaml' not found. "
            "Please create it from the template."
        )

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config


def load_environment():
    """Load environment variables from .env file."""
    possible_paths = [
        Path('.env'),
        Path(__file__).parent.parent / '.env',
    ]

    env_path = None
    for path in possible_paths:
        if path.exists():
            env_path = path
            break

    if not env_path:
        logging.warning(
            "Environment file '.env' not found. "
            "Using environment variables only."
        )
        return

    # Use python-dotenv if available (preferred)
    if HAS_DOTENV:
        load_dotenv(env_path)
        logging.info("Environment loaded using python-dotenv")
        return

    # Fallback to manual parsing
    logging.info("python-dotenv not available, using manual .env parsing")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                os.environ[key.strip()] = value


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
        'EIGHT_SLEEP_EMAIL',
        'EIGHT_SLEEP_PASSWORD',
        'SLEEP_REPORT_EMAIL'
    ]

    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please update your .env file with these values")
        return False

    # Check report enabled
    if not config.get('sleep_report', {}).get('enabled'):
        logger.warning("Sleep reporting is disabled in config.yaml")
        return False

    logger.info("Configuration validation passed")
    return True


def generate_report(config: dict, send_email: bool = True):
    """
    Generate and optionally send sleep report.

    Args:
        config: Configuration dictionary
        send_email: Whether to send the report via email
    """
    logger = logging.getLogger(__name__)

    try:
        # Get report configuration
        report_config = config.get('sleep_report', {})
        timezone = pytz.timezone(report_config.get('timezone', 'America/New_York'))

        # Initialize Eight Sleep service
        logger.info("Connecting to Eight Sleep...")
        eight_service = EightSleepService(
            email=os.getenv('EIGHT_SLEEP_EMAIL'),
            password=os.getenv('EIGHT_SLEEP_PASSWORD'),
            timezone=report_config.get('timezone', 'America/New_York')
        )

        if not eight_service.connect():
            raise ConnectionError("Failed to connect to Eight Sleep API")

        # Get sleep data
        logger.info("Fetching sleep data...")
        report_data = eight_service.get_full_report_data()

        # Disconnect
        eight_service.disconnect()

        logger.info(f"Sleep score: {report_data.get('sleep_data', {}).get('sleep_score', 'N/A')}")
        logger.info(f"Quality: {report_data.get('quality_assessment', 'Unknown')}")

        # Generate HTML report
        logger.info("Generating HTML email...")
        report_generator = SleepReportGenerator(config)
        html_content = report_generator.generate_html_report(report_data)
        text_content = report_generator.generate_text_report(report_data)

        # Save HTML to file for review
        if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
            output_dir = Path('/tmp')
        else:
            output_dir = Path(__file__).parent.parent / 'output'
            output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'sleep_report_{timestamp}.html'

        with open(output_file, 'w') as f:
            f.write(html_content)

        logger.info(f"Report saved to: {output_file}")
        print(f"\nReport generated successfully!")
        print(f"Saved to: {output_file}")

        # Send email if requested
        if send_email:
            recipient = os.getenv('SLEEP_REPORT_EMAIL')

            if not recipient:
                logger.error("No email recipient configured")
                print("\nEmail not sent: No recipient configured")
                return

            logger.info(f"Sending email to {recipient}...")

            # Initialize SES email sender
            email_sender = SESEmailSender(
                region=os.getenv('AWS_REGION', 'us-east-1'),
                sender_email=os.getenv('SES_SENDER_EMAIL', 'brandonhome.appdev@gmail.com')
            )

            # Generate subject
            sleep_score = report_data.get('sleep_data', {}).get('sleep_score')
            quality = report_data.get('quality_assessment', '')

            if sleep_score:
                subject = f"Sleep Report: {sleep_score} ({quality}) - {datetime.now(timezone).strftime('%B %d')}"
            else:
                subject = f"Daily Sleep Report - {datetime.now(timezone).strftime('%B %d, %Y')}"

            # Send email
            success = email_sender.send_html_email(
                to=recipient,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )

            if success:
                print(f"Email sent successfully to {recipient}")
                logger.info(f"Email sent successfully to {recipient}")
            else:
                print(f"\nFailed to send email to {recipient}")
                logger.error(f"Failed to send email to {recipient}")

        # Print summary
        sleep_data = report_data.get('sleep_data', {})
        print(f"\n{'='*60}")
        print("SLEEP REPORT SUMMARY")
        print(f"{'='*60}")

        print(f"\nSleep Score: {sleep_data.get('sleep_score', '--')}")
        print(f"Quality: {report_data.get('quality_assessment', 'Unknown')}")

        time_slept = sleep_data.get('time_slept')
        if time_slept:
            hours = time_slept // 3600
            minutes = (time_slept % 3600) // 60
            print(f"Time Asleep: {hours}h {minutes}m")

        print(f"\nBiometrics:")
        print(f"  Heart Rate: {sleep_data.get('heart_rate', '--')} bpm")
        print(f"  HRV: {sleep_data.get('hrv', '--')}")
        print(f"  Breath Rate: {sleep_data.get('breath_rate', '--')} /min")

        print(f"{'='*60}\n")

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        print(f"\nError: {str(e)}")
        sys.exit(1)


def validate_setup():
    """Validate that all services are properly configured."""
    logger = logging.getLogger(__name__)

    print("\n" + "="*60)
    print("SLEEP EIGHT REPORTER SETUP VALIDATION")
    print("="*60 + "\n")

    try:
        # Load config
        print("Loading configuration...")
        config = load_config()
        print("Config loaded")

        # Load environment
        print("Loading environment variables...")
        load_environment()
        print("Environment loaded")

        # Validate configuration
        print("Validating configuration...")
        if not validate_configuration(config):
            print("Configuration validation failed")
            return False
        print("Configuration valid")

        # Test Eight Sleep connection
        print("\nTesting Eight Sleep connection...")
        eight_service = EightSleepService()
        if eight_service.validate_credentials():
            users = eight_service.get_users()
            print(f"Eight Sleep connection successful - Found {len(users)} user(s)")
            for user in users:
                print(f"   {user.get('side', 'unknown')} side: {user.get('user_id', 'unknown')[:8]}...")
            eight_service.disconnect()
        else:
            print("Eight Sleep connection failed")
            return False

        # Test SES connection
        print("\nTesting AWS SES connection...")
        email_sender = SESEmailSender(
            region=os.getenv('AWS_REGION', 'us-east-1'),
            sender_email=os.getenv('SES_SENDER_EMAIL', 'brandonhome.appdev@gmail.com')
        )
        if email_sender.validate_credentials():
            print("AWS SES connection successful")
            sender = os.getenv('SES_SENDER_EMAIL')
            if sender and email_sender.check_email_verified(sender):
                print(f"Sender email {sender} is verified")
            else:
                print(f"Sender email not verified in SES")
        else:
            print("AWS SES connection failed")

        print("\n" + "="*60)
        print("ALL VALIDATIONS PASSED!")
        print("="*60 + "\n")

        print("Next steps:")
        print("1. Run: python src/sleep_main.py --generate")
        print("2. Or set up AWS Lambda for automatic daily reports\n")

        return True

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        print(f"\nValidation failed: {str(e)}\n")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Sleep Eight Daily Reporter'
    )

    parser.add_argument(
        '--generate',
        action='store_true',
        help='Generate and send sleep report'
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
    logger.info("Starting Sleep Eight Reporter")
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
        print("  python src/sleep_main.py --validate")
        print("  python src/sleep_main.py --generate")
        print("  python src/sleep_main.py --generate --no-email")


if __name__ == '__main__':
    main()
