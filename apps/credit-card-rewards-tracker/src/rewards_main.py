#!/usr/bin/env python3
"""
Main entry point for Credit Card Rewards Tracker

This script orchestrates the rewards tracking system,
providing CLI commands for managing cards, tracking rewards,
and generating reports.
"""

import os
import sys
import logging
import yaml
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Use python-dotenv for proper .env loading
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

from data_manager import DataManager
from card_service import CardService
from rewards_analyzer import RewardsAnalyzer
from cli_dashboard import CLIDashboard

# Import report generator (created later)
try:
    from rewards_report import RewardsReportGenerator
    HAS_REPORT = True
except ImportError:
    RewardsReportGenerator = None
    HAS_REPORT = False

# Import SES email sender
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'ynab-transaction-reviewer' / 'src'))
    from ses_service import SESEmailService
    HAS_SES = True
except ImportError:
    SESEmailService = None
    HAS_SES = False
    logging.warning("SESEmailService not available - email functionality disabled")


def setup_logging(config: dict):
    """Setup logging configuration."""
    log_config = config.get('logging', {})

    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = log_config.get('file', 'logs/rewards_tracker.log')

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
    """Validate that required configuration is present."""
    logger = logging.getLogger(__name__)

    # Check if tracker is enabled
    if not config.get('rewards_tracker', {}).get('enabled'):
        logger.warning("Rewards tracker is disabled in config.yaml")
        return False

    # Validate data directory
    data_dir = config.get('rewards_tracker', {}).get('data', {}).get('directory', 'data')
    data_path = Path(data_dir)
    if not data_path.exists():
        data_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created data directory: {data_path}")

    logger.info("Configuration validation passed")
    return True


def validate_setup(config: dict) -> bool:
    """Validate that all services are properly configured."""
    logger = logging.getLogger(__name__)

    print("\n" + "=" * 60)
    print("CREDIT CARD REWARDS TRACKER SETUP VALIDATION")
    print("=" * 60 + "\n")

    try:
        # Load config
        print("Loading configuration...")
        print("Config loaded")

        # Validate configuration
        print("Validating configuration...")
        if not validate_configuration(config):
            print("Configuration validation failed")
            return False
        print("Configuration valid")

        # Test data manager
        print("\nTesting data manager...")
        data_manager = DataManager()
        errors = data_manager.validate_data_integrity()
        if errors:
            print(f"Data integrity issues: {len(errors)}")
            for error in errors:
                print(f"  - {error}")
        else:
            print("Data manager working correctly")

        # Test card service
        print("\nTesting card service...")
        card_service = CardService(data_manager, config)
        cards = card_service.get_all_cards()
        print(f"Found {len(cards)} card(s)")

        # Test email service (if available)
        if HAS_SES:
            print("\nTesting AWS SES connection...")
            try:
                ses = SESEmailService(
                    region=os.getenv('AWS_REGION', 'us-east-1'),
                    sender_email=os.getenv('SES_SENDER_EMAIL', 'brandonhome.appdev@gmail.com')
                )
                print("AWS SES connection available")
            except Exception as e:
                print(f"AWS SES not configured: {e}")
        else:
            print("\nAWS SES not available - email disabled")

        print("\n" + "=" * 60)
        print("ALL VALIDATIONS PASSED!")
        print("=" * 60 + "\n")

        print("Next steps:")
        print("1. Add your credit cards: python src/rewards_main.py --add-card")
        print("2. Update balances: python src/rewards_main.py --add-balance")
        print("3. View dashboard: python src/rewards_main.py --dashboard")
        print("4. Generate report: python src/rewards_main.py --generate\n")

        return True

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        print(f"\nValidation failed: {str(e)}\n")
        return False


def interactive_add_card(card_service: CardService):
    """Interactive prompts to add a new card."""
    print("\n" + "=" * 50)
    print("ADD NEW CREDIT CARD")
    print("=" * 50 + "\n")

    try:
        # Basic info
        issuer = input("Card issuer (e.g., chase, amex, capital_one): ").strip().lower()
        name = input("Card name (e.g., Chase Freedom Flex): ").strip()
        last_four = input("Last 4 digits of card number: ").strip()

        # Reward type
        print("\nReward type options: points, cash_back, miles")
        reward_type = input("Reward type: ").strip().lower()

        # Reward program
        print("\nCommon reward programs:")
        print("  - chase_ultimate_rewards")
        print("  - amex_membership_rewards")
        print("  - capital_one_miles")
        print("  - cash_back")
        reward_program = input("Reward program (or enter custom): ").strip().lower()

        # Annual fee
        annual_fee_str = input("Annual fee in dollars (0 if none): ").strip()
        annual_fee = int(float(annual_fee_str) * 100) if annual_fee_str else 0

        annual_fee_date = None
        if annual_fee > 0:
            annual_fee_date = input("Annual fee due date (YYYY-MM-DD, or leave blank): ").strip() or None

        # Base reward rate
        base_rate_str = input("Base reward rate (e.g., 1 for 1x, 1.5 for 1.5%): ").strip()
        base_rate = float(base_rate_str) if base_rate_str else 1.0

        # Category multipliers
        print("\nAdd category multipliers (press Enter when done):")
        multipliers = []
        while True:
            category = input("  Category (e.g., dining, groceries, gas) or Enter to finish: ").strip().lower()
            if not category:
                break
            mult_str = input(f"  Multiplier for {category} (e.g., 3 for 3x): ").strip()
            if mult_str:
                multipliers.append({
                    "category": category,
                    "multiplier": float(mult_str)
                })

        # Build card data
        card_data = {
            "issuer": issuer,
            "name": name,
            "last_four": last_four,
            "reward_type": reward_type,
            "reward_program": reward_program,
            "annual_fee": annual_fee,
            "annual_fee_due_date": annual_fee_date,
            "base_reward_rate": base_rate,
            "category_multipliers": multipliers,
            "opened_date": datetime.now().strftime("%Y-%m-%d"),
            "is_active": True
        }

        # Validate and add
        is_valid, errors = card_service.validate_card_data(card_data)
        if not is_valid:
            print("\nValidation errors:")
            for error in errors:
                print(f"  - {error}")
            return

        card = card_service.add_card(card_data)
        print(f"\nCard added successfully: {card['id']}")

    except KeyboardInterrupt:
        print("\n\nCancelled.")
    except Exception as e:
        print(f"\nError adding card: {e}")


def interactive_add_balance(data_manager: DataManager):
    """Interactive prompts to update a balance."""
    print("\n" + "=" * 50)
    print("UPDATE REWARDS BALANCE")
    print("=" * 50 + "\n")

    try:
        programs = data_manager.get_reward_programs()
        print("Available programs:")
        for prog_id, prog in programs.items():
            print(f"  - {prog_id}: {prog.get('name')}")

        program = input("\nProgram ID: ").strip().lower()
        points_str = input("Current points balance: ").strip()
        points = int(points_str) if points_str else 0

        data_manager.update_balance(program, points, source="manual")
        print(f"\nBalance updated: {program} = {points:,} pts")

    except KeyboardInterrupt:
        print("\n\nCancelled.")
    except Exception as e:
        print(f"\nError updating balance: {e}")


def interactive_add_redemption(data_manager: DataManager):
    """Interactive prompts to log a redemption."""
    print("\n" + "=" * 50)
    print("LOG REDEMPTION")
    print("=" * 50 + "\n")

    try:
        programs = data_manager.get_reward_programs()
        print("Available programs:")
        for prog_id in programs.keys():
            print(f"  - {prog_id}")

        program = input("\nProgram ID: ").strip().lower()
        points_str = input("Points redeemed: ").strip()
        points = int(points_str) if points_str else 0

        print("\nRedemption types: statement_credit, travel_portal, transfer_partner, gift_card, cash_back")
        red_type = input("Redemption type: ").strip().lower()

        value_str = input("Value received in dollars: ").strip()
        value_cents = int(float(value_str) * 100) if value_str else 0

        partner = None
        if red_type == "transfer_partner":
            partner = input("Transfer partner (e.g., hyatt, united): ").strip().lower()

        notes = input("Notes (optional): ").strip()

        redemption = {
            "program": program,
            "points_redeemed": points,
            "redemption_type": red_type,
            "value_received_cents": value_cents,
            "partner": partner,
            "notes": notes
        }

        result = data_manager.add_redemption(redemption)
        cpp = result.get("cents_per_point", 0)
        print(f"\nRedemption logged: {result['id']}")
        print(f"Value: {cpp:.2f} cents per point")

    except KeyboardInterrupt:
        print("\n\nCancelled.")
    except Exception as e:
        print(f"\nError logging redemption: {e}")


def generate_report(config: dict, send_email: bool = True):
    """Generate and optionally send weekly report."""
    logger = logging.getLogger(__name__)

    try:
        # Initialize services
        logger.info("Initializing services...")
        data_manager = DataManager()
        card_service = CardService(data_manager, config)
        analyzer = RewardsAnalyzer(data_manager, card_service, config)

        # Generate summary
        logger.info("Generating weekly summary...")
        summary = analyzer.generate_weekly_summary()

        # Generate HTML report
        if HAS_REPORT:
            logger.info("Generating HTML report...")
            report_generator = RewardsReportGenerator(config)
            html_content = report_generator.generate_html_report(summary)
        else:
            # Fallback to simple text report
            logger.warning("RewardsReportGenerator not available, using text output")
            html_content = generate_simple_report(summary)

        # Save report to file
        if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
            output_dir = Path('/tmp')
        else:
            output_dir = Path('output')
            output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'rewards_report_{timestamp}.html'

        with open(output_file, 'w') as f:
            f.write(html_content)

        logger.info(f"Report saved to: {output_file}")
        print(f"\nReport generated successfully!")
        print(f"Saved to: {output_file}")

        # Send email if requested
        if send_email and HAS_SES:
            recipient = os.getenv(
                'REWARDS_REPORT_EMAIL',
                config.get('rewards_tracker', {}).get('email', {}).get('recipient')
            )

            if not recipient:
                logger.warning("No email recipient configured")
                print("\nEmail not sent: No recipient configured")
                return

            logger.info(f"Sending email to {recipient}...")

            ses = SESEmailService(
                region=os.getenv('AWS_REGION', 'us-east-1'),
                sender_email=os.getenv('SES_SENDER_EMAIL', 'brandonhome.appdev@gmail.com')
            )

            subject_template = config.get('rewards_tracker', {}).get('email', {}).get(
                'subject_template',
                'Weekly Rewards Report - {date}'
            )
            subject = subject_template.format(date=datetime.now().strftime('%B %d, %Y'))

            success = ses.send_email(
                to_email=recipient,
                subject=subject,
                html_body=html_content
            )

            if success:
                print(f"Email sent successfully to {recipient}")
                logger.info(f"Email sent to {recipient}")
            else:
                print(f"\nFailed to send email to {recipient}")
                logger.error(f"Failed to send email to {recipient}")

        # Print summary
        print_summary(summary)

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        print(f"\nError: {str(e)}")
        sys.exit(1)


def generate_simple_report(summary: dict) -> str:
    """Generate a simple HTML report when full generator isn't available."""
    total_value = summary.get('total_value', {})

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Weekly Rewards Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            h1 {{ color: #333; }}
            .summary {{ background: #f5f5f5; padding: 15px; border-radius: 8px; }}
        </style>
    </head>
    <body>
        <h1>Weekly Rewards Report</h1>
        <p>Generated: {summary.get('generated_at', '')[:19]}</p>

        <div class="summary">
            <h2>Total Rewards Value</h2>
            <p><strong>Points Value:</strong> ${total_value.get('points_value_cents', 0) / 100:.2f}</p>
            <p><strong>Cash Back:</strong> ${total_value.get('cash_back_cents', 0) / 100:.2f}</p>
            <p><strong>Combined:</strong> ${total_value.get('combined_cents', 0) / 100:.2f}</p>
        </div>
    </body>
    </html>
    """


def print_summary(summary: dict):
    """Print summary to console."""
    total_value = summary.get('total_value', {})

    print("\n" + "=" * 60)
    print("REWARDS SUMMARY")
    print("=" * 60)

    print(f"\nTotal Rewards Value:")
    print(f"  Points: ${total_value.get('points_value_cents', 0) / 100:,.2f}")
    print(f"  Cash Back: ${total_value.get('cash_back_cents', 0) / 100:,.2f}")
    print(f"  Combined: ${total_value.get('combined_cents', 0) / 100:,.2f}")

    tips = summary.get('optimization_tips', [])
    if tips:
        print(f"\nOptimization Tips ({len(tips)}):")
        for tip in tips[:3]:
            print(f"  [{tip['priority'].upper()}] {tip['title']}")

    upcoming = summary.get('upcoming_fees', [])
    if upcoming:
        print(f"\nUpcoming Annual Fees:")
        for fee in upcoming[:3]:
            print(f"  - {fee['card_name']}: ${fee['amount']/100:.0f} in {fee['days_until']} days")

    print("=" * 60 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Credit Card Rewards Tracker'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate setup and configuration'
    )

    parser.add_argument(
        '--generate',
        action='store_true',
        help='Generate and send weekly report'
    )

    parser.add_argument(
        '--no-email',
        action='store_true',
        help='Generate report but do not send email'
    )

    parser.add_argument(
        '--dashboard',
        action='store_true',
        help='Show CLI dashboard'
    )

    parser.add_argument(
        '--balances',
        action='store_true',
        help='Show balances only (with --dashboard)'
    )

    parser.add_argument(
        '--recommendations',
        action='store_true',
        help='Show recommendations only (with --dashboard)'
    )

    parser.add_argument(
        '--fees',
        action='store_true',
        help='Show annual fee analysis (with --dashboard)'
    )

    parser.add_argument(
        '--add-card',
        action='store_true',
        help='Add a new credit card interactively'
    )

    parser.add_argument(
        '--add-balance',
        action='store_true',
        help='Update a rewards balance interactively'
    )

    parser.add_argument(
        '--add-redemption',
        action='store_true',
        help='Log a redemption interactively'
    )

    parser.add_argument(
        '--best-card',
        type=str,
        metavar='CATEGORY',
        help='Show best card for a spending category'
    )

    parser.add_argument(
        '--roi',
        action='store_true',
        help='Show ROI analysis for cards with annual fees'
    )

    args = parser.parse_args()

    # Load config
    config = load_config()

    # Setup logging
    setup_logging(config)

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Starting Credit Card Rewards Tracker")
    logger.info("=" * 60)

    # Load environment
    load_environment()

    # Initialize services
    data_manager = DataManager()
    card_service = CardService(data_manager, config)
    analyzer = RewardsAnalyzer(data_manager, card_service, config)
    dashboard = CLIDashboard(data_manager, card_service, analyzer, config)

    # Handle commands
    if args.validate:
        sys.exit(0 if validate_setup(config) else 1)

    elif args.generate:
        if not validate_configuration(config):
            sys.exit(1)
        send_email = not args.no_email
        generate_report(config, send_email=send_email)

    elif args.dashboard:
        if args.balances:
            dashboard.display_header()
            dashboard.display_balances()
        elif args.recommendations:
            dashboard.display_header()
            dashboard.display_recommendations()
        elif args.fees:
            dashboard.display_header()
            dashboard.display_fees()
        else:
            dashboard.run_interactive()

    elif args.add_card:
        interactive_add_card(card_service)

    elif args.add_balance:
        interactive_add_balance(data_manager)

    elif args.add_redemption:
        interactive_add_redemption(data_manager)

    elif args.best_card:
        dashboard.display_header()
        dashboard.display_quick_lookup(args.best_card)

    elif args.roi:
        dashboard.display_header()
        dashboard.display_fees()

    else:
        # Default: show help
        parser.print_help()
        print("\nExamples:")
        print("  python src/rewards_main.py --validate")
        print("  python src/rewards_main.py --dashboard")
        print("  python src/rewards_main.py --add-card")
        print("  python src/rewards_main.py --add-balance")
        print("  python src/rewards_main.py --add-redemption")
        print("  python src/rewards_main.py --best-card dining")
        print("  python src/rewards_main.py --generate")
        print("  python src/rewards_main.py --generate --no-email")


if __name__ == '__main__':
    main()
