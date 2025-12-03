#!/usr/bin/env python3
"""
Main entry point for Weekly YNAB Budget Report

This script orchestrates the budget reporting system,
generating comprehensive reports on spending and budget performance,
including Tiller-style annual budget tracking.
"""
import os
import sys
import logging
import yaml
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import pytz

# Add project root to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'love-brittany-tracker' / 'src'))

# Use python-dotenv for proper .env loading
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

from ynab_service import YNABService
from budget_analyzer import BudgetAnalyzer
from budget_report import BudgetReportGenerator

# Import SES email sender (preferred for automated emails)
try:
    from ses_email_sender import SESEmailSender
    HAS_SES = True
except ImportError:
    SESEmailSender = None
    HAS_SES = False
    logging.warning("SESEmailSender not available - SES email functionality disabled")

# Fallback to Gmail sender from Love Brittany tracker shared services
try:
    from email_sender import EmailSender as GmailEmailSender
    HAS_GMAIL = True
except ImportError:
    GmailEmailSender = None
    HAS_GMAIL = False

# Determine which email sender to use
EmailSender = SESEmailSender if HAS_SES else GmailEmailSender
if not EmailSender:
    logging.warning("No email sender available - email functionality disabled")


def setup_logging(config: dict):
    """Setup logging configuration."""
    log_config = config.get('logging', {})

    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = log_config.get('file', 'logs/budget_report.log')

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
    env_path = Path('.env')

    if not env_path.exists():
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
                # Remove quotes if present
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
        'YNAB_API_KEY',
        'BUDGET_REPORT_EMAIL'
    ]

    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please update your .env file with these values")
        return False

    # Check budget tracking enabled
    if not config.get('budget_report', {}).get('enabled'):
        logger.warning("Budget reporting is disabled in config.yaml")
        return False

    logger.info("Configuration validation passed")
    return True


def generate_report(config: dict, send_email: bool = True):
    """
    Generate and optionally send budget report.

    Args:
        config: Configuration dictionary
        send_email: Whether to send the report via email
    """
    logger = logging.getLogger(__name__)

    try:
        # Initialize YNAB service
        logger.info("Initializing YNAB service...")
        ynab_service = YNABService()

        # Get budget configuration
        budget_config = config['budget_report']
        budget_id = os.getenv('YNAB_BUDGET_ID') or budget_config.get('budget_id')

        # If no budget ID specified, use the first budget
        if not budget_id:
            logger.info("No budget ID specified, fetching first budget...")
            budgets = ynab_service.get_budgets()
            if not budgets:
                raise ValueError("No budgets found in YNAB account")
            budget_id = budgets[0]['id']
            budget_name = budgets[0]['name']
            logger.info(f"Using budget: {budget_name} ({budget_id})")

        # Calculate reporting period
        report_config = budget_config.get('report', {})
        lookback_days = report_config.get('lookback_days', 7)

        timezone = pytz.timezone(budget_config.get('timezone', 'America/New_York'))
        end_date = datetime.now(timezone).replace(hour=23, minute=59, second=59, microsecond=0)
        start_date = end_date - timedelta(days=lookback_days)

        logger.info(f"Report period: {start_date.date()} to {end_date.date()}")

        # Fetch data from YNAB
        logger.info("Fetching YNAB data...")
        since_date = (start_date - timedelta(days=30)).strftime('%Y-%m-%d')  # Extra buffer for trends

        transactions = ynab_service.get_transactions(budget_id, since_date=since_date)
        categories = ynab_service.get_categories(budget_id)
        payees = ynab_service.get_payees(budget_id)
        accounts = ynab_service.get_accounts(budget_id)

        logger.info(f"Fetched {len(transactions)} transactions, {len(payees)} payees, "
                   f"{len(accounts)} accounts")

        # Get current month budget data
        current_month = datetime.now(timezone).strftime('%Y-%m-01')
        month_budget = ynab_service.get_month_budget(budget_id, current_month)

        # Analyze transactions
        logger.info("Analyzing budget data...")
        analyzer = BudgetAnalyzer(config)

        analysis = analyzer.analyze_transactions(
            transactions=transactions,
            categories=categories,
            payees=payees,
            accounts=accounts,
            start_date=start_date,
            end_date=end_date
        )

        # Compare to budget
        budget_comparison = analyzer.compare_to_budget(
            analysis['category_breakdown'],
            month_budget
        )

        # Generate alerts
        alerts = analyzer.generate_alerts(budget_comparison, analysis['category_breakdown'])

        # Compile report data
        report_data = {
            'period': analysis['period'],
            'analysis': analysis,
            'budget_comparison': budget_comparison,
            'alerts': alerts
        }

        # Generate HTML report
        logger.info("Generating HTML email...")
        report_generator = BudgetReportGenerator(budget_config)
        html_content = report_generator.generate_html_report(report_data)

        # Save HTML to file for review
        if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
            output_dir = Path('/tmp')
        else:
            output_dir = Path('output')
            output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'budget_report_{timestamp}.html'

        with open(output_file, 'w') as f:
            f.write(html_content)

        logger.info(f"Report saved to: {output_file}")
        print(f"\n✅ Report generated successfully!")
        print(f"📄 Saved to: {output_file}")

        # Send email if requested
        if send_email:
            if not EmailSender:
                logger.error("EmailSender not available - cannot send email")
                print("\n❌ Email functionality not available")
                return

            recipient = os.getenv(
                'BUDGET_REPORT_EMAIL',
                budget_config.get('email', {}).get('recipient')
            )

            if not recipient:
                logger.error("No email recipient configured")
                print("\n⚠️  Email not sent: No recipient configured")
                return

            logger.info(f"Sending email to {recipient}...")

            # Initialize email sender based on available service
            if HAS_SES:
                # Use AWS SES (preferred for automated emails)
                logger.info("Using AWS SES for email delivery")
                email_sender = SESEmailSender(
                    region=os.getenv('AWS_REGION', 'us-east-1'),
                    sender_email=os.getenv('SES_SENDER_EMAIL', 'brandonhome.appdev@gmail.com')
                )
            elif HAS_GMAIL:
                # Fallback to Gmail API
                logger.info("Using Gmail API for email delivery")
                email_sender = GmailEmailSender(
                    credentials_path=os.getenv('GOOGLE_CREDENTIALS_FILE',
                                              '../../shared/credentials/credentials.json'),
                    token_path=os.getenv('GOOGLE_TOKEN_FILE',
                                        '../../shared/credentials/token.pickle')
                )
            else:
                logger.error("No email sender available")
                print("\n❌ No email sender configured")
                return

            # Generate subject
            subject_template = budget_config.get('email', {}).get(
                'subject_template',
                'Weekly Budget Report - {date}'
            )
            subject = subject_template.format(
                date=end_date.strftime('%B %d, %Y')
            )

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
        print("BUDGET REPORT SUMMARY")
        print(f"{'='*60}")

        print(f"\n💰 Spending Summary:")
        print(f"   Total Spent: ${analysis['summary']['total_outflow']:,.2f}")
        print(f"   Total Income: ${analysis['summary']['total_inflow']:,.2f}")
        print(f"   Net: ${analysis['summary']['net']:,.2f}")
        print(f"   Transactions: {analysis['summary']['transaction_count']}")

        if budget_comparison:
            print(f"\n📊 Budget Performance:")
            print(f"   Budget: ${budget_comparison['total_budgeted']:,.2f}")
            print(f"   Spent: ${budget_comparison['total_spent']:,.2f}")
            print(f"   Remaining: ${budget_comparison['total_remaining']:,.2f}")
            print(f"   Usage: {budget_comparison['overall_percentage_used']:.1f}%")

        if alerts:
            print(f"\n🚨 Alerts ({len(alerts)}):")
            for alert in alerts[:5]:
                emoji = "🔴" if alert['level'] == 'critical' else "⚠️"
                print(f"   {emoji} {alert['category']}: {alert['message']}")

        print(f"{'='*60}\n")

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


def validate_setup():
    """Validate that all services are properly configured."""
    logger = logging.getLogger(__name__)

    print("\n" + "="*60)
    print("WEEKLY BUDGET REPORT SETUP VALIDATION")
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

        # Test YNAB service
        print("\n💰 Testing YNAB connection...")
        ynab_service = YNABService()
        if ynab_service.validate_credentials():
            budgets = ynab_service.get_budgets()
            print(f"✅ YNAB connection successful - Found {len(budgets)} budget(s)")
            for budget in budgets:
                print(f"   • {budget['name']} ({budget['id']})")
        else:
            print("❌ YNAB connection failed")
            return False

        # Test Email service (if available)
        if HAS_SES:
            print("📧 Testing AWS SES connection...")
            email_sender = SESEmailSender(
                region=os.getenv('AWS_REGION', 'us-east-1'),
                sender_email=os.getenv('SES_SENDER_EMAIL', 'brandonhome.appdev@gmail.com')
            )
            if email_sender.validate_credentials():
                print("✅ AWS SES connection successful")
                # Check if sender email is verified
                sender = os.getenv('SES_SENDER_EMAIL', 'TERRANCE@GOODPORTION.ORG')
                if email_sender.check_email_verified(sender):
                    print(f"✅ Sender email {sender} is verified")
                else:
                    print(f"⚠️  Sender email {sender} not verified in SES")
            else:
                print("⚠️  AWS SES connection failed")
        elif HAS_GMAIL:
            print("📧 Testing Gmail connection...")
            credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE',
                                        '../../shared/credentials/credentials.json')
            token_file = os.getenv('GOOGLE_TOKEN_FILE',
                                  '../../shared/credentials/token.pickle')

            if os.path.exists(credentials_file):
                email_sender = GmailEmailSender(credentials_file, token_file)
                if email_sender.validate_credentials():
                    print("✅ Gmail connection successful")
                else:
                    print("⚠️  Gmail connection failed")
            else:
                print("⚠️  Gmail credentials not found - email disabled")
        else:
            print("⚠️  No email sender available - email disabled")

        print("\n" + "="*60)
        print("✅ ALL VALIDATIONS PASSED!")
        print("="*60 + "\n")

        print("Next steps:")
        print("1. Update .env with your YNAB API key and email")
        print("2. Run: python src/budget_main.py --generate")
        print("3. Or set up AWS Lambda for automatic weekly reports\n")

        return True

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        print(f"\n❌ Validation failed: {str(e)}\n")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Weekly YNAB Budget Report Generator'
    )

    parser.add_argument(
        '--generate',
        action='store_true',
        help='Generate and send budget report'
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
    logger.info("Starting Weekly Budget Report")
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
        print("  python src/budget_main.py --validate")
        print("  python src/budget_main.py --generate")
        print("  python src/budget_main.py --generate --no-email")


if __name__ == '__main__':
    main()
