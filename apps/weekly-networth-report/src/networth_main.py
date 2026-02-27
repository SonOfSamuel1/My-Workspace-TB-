#!/usr/bin/env python3
"""
Main entry point for Weekly Net Worth & Run Rate Report

This script orchestrates the net worth reporting system,
generating comprehensive reports on account balances and
financial run rate from YNAB transaction history.
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

# Add project root to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use python-dotenv for proper .env loading
try:
    from dotenv import load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

from networth_analyzer import NetWorthAnalyzer  # noqa: E402
from networth_report import NetWorthReportGenerator  # noqa: E402
from ynab_service import YNABService  # noqa: E402

# Import Simplifi service (for net worth from Quicken Simplifi)
try:
    from simplifi_service import SimplifiService

    HAS_SIMPLIFI = True
except ImportError:
    SimplifiService = None
    HAS_SIMPLIFI = False

# Import SES email sender (preferred for automated emails)
try:
    from ses_email_sender import SESEmailSender

    HAS_SES = True
except ImportError:
    SESEmailSender = None
    HAS_SES = False
    logging.warning("SESEmailSender not available - SES email functionality disabled")


def setup_logging(config: dict):
    """Setup logging configuration."""
    log_config = config.get("logging", {})

    log_level = getattr(logging, log_config.get("level", "INFO"))
    log_format = log_config.get(
        "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log_file = log_config.get("file", "logs/networth_report.log")

    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )


def load_config() -> dict:
    """Load configuration from config.yaml."""
    config_path = Path("config.yaml")

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
    env_path = Path(".env")

    if not env_path.exists():
        logging.warning(
            "Environment file '.env' not found. " "Using environment variables only."
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
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
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
    required_env_vars = ["YNAB_API_KEY", "NETWORTH_REPORT_EMAIL"]

    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
        logger.error("Please update your .env file with these values")
        return False

    # Check net worth reporting enabled
    if not config.get("networth_report", {}).get("enabled"):
        logger.warning("Net worth reporting is disabled in config.yaml")
        return False

    logger.info("Configuration validation passed")
    return True


def generate_report(config: dict, send_email: bool = True):
    """
    Generate and optionally send the net worth & run rate report.

    Args:
        config: Configuration dictionary
        send_email: Whether to send the report via email
    """
    logger = logging.getLogger(__name__)

    try:
        report_config = config["networth_report"]
        use_simplifi = (
            report_config.get("simplifi", {}).get("enabled", False) and HAS_SIMPLIFI
        )

        # --- Net Worth: Simplifi (preferred) or YNAB fallback ---
        simplifi_data = None
        if use_simplifi:
            logger.info("Fetching net worth from Simplifi...")
            try:
                simplifi = SimplifiService()
                simplifi_data = simplifi.get_net_worth_data()
                logger.info(
                    f"Simplifi net worth: ${simplifi_data['net_worth']:,.2f} "
                    f"({len(simplifi_data['asset_accounts'])} assets, "
                    f"{len(simplifi_data['liability_accounts'])} liabilities)"
                )
            except Exception as e:
                logger.warning(f"Simplifi fetch failed, falling back to YNAB: {e}")
                simplifi_data = None

        # --- Run Rate: always from YNAB (transaction history) ---
        logger.info("Initializing YNAB service...")
        ynab_service = YNABService()

        budget_id = os.getenv("YNAB_BUDGET_ID") or report_config.get("budget_id")
        if not budget_id:
            logger.info("No budget ID specified, fetching first budget...")
            budgets = ynab_service.get_budgets()
            if not budgets:
                raise ValueError("No budgets found in YNAB account")
            budget_id = budgets[0]["id"]
            budget_name = budgets[0]["name"]
            logger.info(f"Using budget: {budget_name} ({budget_id})")

        run_rate_months = report_config.get("report", {}).get("run_rate_months", 3)
        since_date = (datetime.now() - timedelta(days=run_rate_months * 31)).strftime(
            "%Y-%m-%d"
        )
        logger.info(
            f"Fetching transactions since {since_date} ({run_rate_months} months for run rate)"
        )

        transactions = ynab_service.get_transactions(budget_id, since_date=since_date)
        logger.info(f"Fetched {len(transactions)} transactions from YNAB")

        # --- Compile report data ---
        analyzer = NetWorthAnalyzer(config)

        if simplifi_data:
            # Use Simplifi for net worth, YNAB for run rate
            logger.info("Using Simplifi for net worth, YNAB for run rate...")
            run_rate_data = analyzer.calculate_run_rate(transactions)
            report_data = {
                **simplifi_data,
                **run_rate_data,
                "data_sources": {"net_worth": "Simplifi", "run_rate": "YNAB"},
                "generated_at": datetime.now().isoformat(),
            }
        else:
            # YNAB for everything
            logger.info("Using YNAB for both net worth and run rate...")
            accounts = ynab_service.get_accounts(budget_id)
            logger.info(f"Fetched {len(accounts)} accounts from YNAB")
            report_data = analyzer.compile_report_data(accounts, transactions)
            report_data["data_sources"] = {"net_worth": "YNAB", "run_rate": "YNAB"}

        # Generate HTML report
        logger.info("Generating HTML report...")
        report_generator = NetWorthReportGenerator(config)
        html_content = report_generator.generate_html_report(report_data)

        # Save HTML to file for review
        if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            output_dir = Path("/tmp")
        else:
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"networth_report_{timestamp}.html"

        with open(output_file, "w") as f:
            f.write(html_content)

        logger.info(f"Report saved to: {output_file}")
        print("\nReport generated successfully!")
        print(f"Saved to: {output_file}")

        # Send email if requested
        if send_email:
            if not HAS_SES:
                logger.error("SESEmailSender not available - cannot send email")
                print("\nEmail functionality not available")
                return

            recipient = os.getenv(
                "NETWORTH_REPORT_EMAIL", report_config.get("email", {}).get("recipient")
            )

            if not recipient:
                logger.error("No email recipient configured")
                print("\nEmail not sent: No recipient configured")
                return

            logger.info(f"Sending email to {recipient}...")

            ses_config = report_config.get("ses", {})
            email_sender = SESEmailSender(
                region=os.getenv("AWS_REGION", ses_config.get("region", "us-east-1")),
                sender_email=os.getenv(
                    "SES_SENDER_EMAIL",
                    ses_config.get("sender_email", "brandonhome.appdev@gmail.com"),
                ),
            )

            # Generate subject
            subject_template = report_config.get("email", {}).get(
                "subject_template", "Net Worth & Run Rate Report - {date}"
            )
            subject = subject_template.format(date=datetime.now().strftime("%B %d, %Y"))

            # Send email
            success = email_sender.send_html_email(
                to=recipient, subject=subject, html_content=html_content
            )

            if success:
                print(f"Email sent successfully to {recipient}")
                logger.info(f"Email sent successfully to {recipient}")
            else:
                print(f"\nFailed to send email to {recipient}")
                logger.error(f"Failed to send email to {recipient}")

        # Print summary
        sources = report_data.get("data_sources", {})
        print(f"\n{'='*60}")
        print("NET WORTH & RUN RATE REPORT SUMMARY")
        print(f"{'='*60}")

        print(
            f"\nNet Worth: ${report_data.get('net_worth', 0):,.2f}  (source: {sources.get('net_worth', 'unknown')})"
        )
        print(f"  Assets: ${report_data.get('total_assets', 0):,.2f}")
        print(f"  Liabilities: ${report_data.get('total_liabilities', 0):,.2f}")
        print(
            f"\nMonthly Run Rate: ${report_data.get('avg_monthly_net', 0):,.2f}  (source: {sources.get('run_rate', 'unknown')})"  # noqa: E501
        )
        print(f"Annual Run Rate: ${report_data.get('annual_run_rate', 0):,.2f}")
        print(f"Asset Accounts: {len(report_data.get('asset_accounts', []))}")
        print(f"Liability Accounts: {len(report_data.get('liability_accounts', []))}")
        print(f"Run Rate Period: {run_rate_months} months")

        print(f"{'='*60}\n")

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        print(f"\nError: {str(e)}")
        sys.exit(1)


def validate_setup():
    """Validate that all services are properly configured."""
    logger = logging.getLogger(__name__)

    print("\n" + "=" * 60)
    print("WEEKLY NET WORTH REPORT SETUP VALIDATION")
    print("=" * 60 + "\n")

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

        # Test YNAB service
        print("\nTesting YNAB connection...")
        ynab_service = YNABService()
        if ynab_service.validate_credentials():
            budgets = ynab_service.get_budgets()
            print(f"YNAB connection successful - Found {len(budgets)} budget(s)")
            for budget in budgets:
                print(f"   - {budget['name']} ({budget['id']})")
        else:
            print("YNAB connection failed")
            return False

        # Test Simplifi connection
        simplifi_enabled = (
            config.get("networth_report", {}).get("simplifi", {}).get("enabled", False)
        )
        if simplifi_enabled and HAS_SIMPLIFI:
            print("\nTesting Simplifi connection...")
            try:
                simplifi = SimplifiService()
                if simplifi.validate_credentials():
                    data = simplifi.get_net_worth_data()
                    print(
                        f"Simplifi connection successful - Net worth: ${data['net_worth']:,.2f}"
                    )
                    print(
                        f"   {len(data['asset_accounts'])} asset accounts, "
                        f"{len(data['liability_accounts'])} liability accounts"
                    )
                else:
                    print("Simplifi credential validation failed")
            except Exception as e:
                print(f"Simplifi connection failed: {e}")
        elif simplifi_enabled:
            print("\nSimplifi enabled in config but simplifiapi not installed")
        else:
            print("\nSimplifi not enabled (net worth from YNAB)")

        # Test SES connection
        if HAS_SES:
            print("\nTesting AWS SES connection...")
            ses_config = config.get("networth_report", {}).get("ses", {})
            email_sender = SESEmailSender(
                region=os.getenv("AWS_REGION", ses_config.get("region", "us-east-1")),
                sender_email=os.getenv(
                    "SES_SENDER_EMAIL",
                    ses_config.get("sender_email", "brandonhome.appdev@gmail.com"),
                ),
            )
            if email_sender.validate_credentials():
                print("AWS SES connection successful")
                sender = os.getenv(
                    "SES_SENDER_EMAIL", ses_config.get("sender_email", "")
                )
                if sender and email_sender.check_email_verified(sender):
                    print(f"Sender email {sender} is verified")
                else:
                    print(f"Sender email {sender} not verified in SES")
            else:
                print("AWS SES connection failed")
        else:
            print("\nSES email sender not available - email disabled")

        print("\n" + "=" * 60)
        print("ALL VALIDATIONS PASSED!")
        print("=" * 60 + "\n")

        print("Next steps:")
        print("1. Update .env with your YNAB API key and email")
        print("2. Run: python src/networth_main.py --generate")
        print("3. Or set up AWS Lambda for automatic weekly reports\n")

        return True

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        print(f"\nValidation failed: {str(e)}\n")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Weekly Net Worth & Run Rate Report Generator"
    )

    parser.add_argument(
        "--generate", action="store_true", help="Generate and send net worth report"
    )

    parser.add_argument(
        "--no-email", action="store_true", help="Generate report but do not send email"
    )

    parser.add_argument(
        "--validate", action="store_true", help="Validate setup and configuration"
    )

    args = parser.parse_args()

    # Load config
    config = load_config()

    # Setup logging
    setup_logging(config)

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Starting Weekly Net Worth & Run Rate Report")
    logger.info("=" * 60)

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
        print("  python src/networth_main.py --validate")
        print("  python src/networth_main.py --generate")
        print("  python src/networth_main.py --generate --no-email")


if __name__ == "__main__":
    main()
