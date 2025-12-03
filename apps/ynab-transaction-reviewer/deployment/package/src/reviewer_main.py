#!/usr/bin/env python3
"""
YNAB Transaction Reviewer - Main Orchestrator

Daily email system that pushes uncategorized YNAB transactions for review
with smart suggestions and one-click categorization.
"""

import os
import sys
import argparse
import logging
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from ynab_service import YNABService
from transaction_scanner import TransactionScanner
from suggestion_engine import SuggestionEngine
from split_analyzer import SplitAnalyzer
from email_generator import EmailGenerator
from gmail_service import GmailService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TransactionReviewer:
    """Main orchestrator for transaction review system"""

    def __init__(self, config_path: str = None):
        """
        Initialize the transaction reviewer

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)
        self._setup_logging()

        # Initialize services
        self.ynab = None
        self.scanner = None
        self.suggestion_engine = None
        self.split_analyzer = None
        self.email_generator = None
        self.gmail = None

    def _load_config(self, config_path: str = None) -> Dict:
        """Load configuration from YAML file"""
        if not config_path:
            config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Load .env file if it exists
        env_file = Path(__file__).parent.parent / '.env'
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()

        # Override with environment variables if present
        if os.getenv('YNAB_API_KEY'):
            config['ynab_api_key'] = os.getenv('YNAB_API_KEY')
        if os.getenv('RECIPIENT_EMAIL'):
            config['notifications']['recipient_email'] = os.getenv('RECIPIENT_EMAIL')

        return config

    def _setup_logging(self):
        """Setup logging based on configuration"""
        log_level = getattr(logging, self.config['logging']['level'])
        logging.getLogger().setLevel(log_level)

        # Skip file logging on Lambda (uses CloudWatch instead)
        is_lambda = os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None
        if is_lambda:
            return

        # File logging if enabled (local only)
        if self.config['logging'].get('file_enabled'):
            from logging.handlers import RotatingFileHandler

            log_dir = Path(self.config['logging']['file_path']).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            handler = RotatingFileHandler(
                self.config['logging']['file_path'],
                maxBytes=self.config['logging']['file_max_size_mb'] * 1024 * 1024,
                backupCount=self.config['logging']['file_backup_count']
            )
            handler.setFormatter(logging.Formatter(self.config['logging']['format']))
            logging.getLogger().addHandler(handler)

    def initialize_services(self):
        """Initialize all required services"""
        logger.info("Initializing services...")

        # Initialize YNAB service
        self.ynab = YNABService(
            api_key=self.config.get('ynab_api_key'),
            budget_id=self.config.get('ynab_budget_id')
        )

        # Determine data directory (use /tmp on Lambda)
        is_lambda = os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None
        data_dir = '/tmp/data' if is_lambda else 'data'

        # Initialize scanner
        self.scanner = TransactionScanner(
            ynab_service=self.ynab,
            state_file=f'{data_dir}/review_state.json'
        )

        # Initialize suggestion engine
        if self.config['suggestions']['enabled']:
            self.suggestion_engine = SuggestionEngine(
                ynab_service=self.ynab,
                merchant_db_file=f'{data_dir}/merchants.json'
            )

        # Initialize split analyzer
        if self.config['split_detection']['enabled']:
            self.split_analyzer = SplitAnalyzer(
                ynab_service=self.ynab
            )

        # Initialize Gmail service
        self.gmail = GmailService()

        # Initialize email generator
        self.email_generator = EmailGenerator(
            gmail_service=self.gmail,
            action_base_url=self.config['actions'].get('api_gateway_url')
        )

        logger.info("All services initialized successfully")

    def should_run_today(self) -> bool:
        """Check if review should run today based on schedule"""
        today = datetime.now().strftime('%A')

        # Check if today is in skip days
        if today in self.config['schedule']['skip_days']:
            logger.info(f"Skipping review - {today} is in skip days")
            return False

        return True

    def is_sunday(self) -> bool:
        """Check if today is Sunday"""
        return datetime.now().weekday() == 6

    def run_review(self, force: bool = False, dry_run: bool = False):
        """
        Run the transaction review process

        Args:
            force: Force run even on skip days
            dry_run: Don't send emails, just log what would happen
        """
        logger.info("=" * 50)
        logger.info("Starting YNAB Transaction Review")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 50)

        # Check if should run today
        if not force and not self.should_run_today():
            return

        # Initialize services if not already done
        if not self.ynab:
            self.initialize_services()

        try:
            # Scan for uncategorized transactions
            logger.info("Scanning for uncategorized transactions...")

            # Check if we should include Saturday transactions (on Sunday)
            include_saturday = (
                self.is_sunday() and
                self.config['schedule']['saturday_handling'] == 'include_in_sunday'
            )

            if include_saturday:
                logger.info("Including Saturday transactions in Sunday review")
                # Look back 2 days to include Saturday
                transactions = self.scanner.scan_for_uncategorized(days_back=2)
            else:
                transactions = self.scanner.scan_for_uncategorized(
                    days_back=self.config['scanning']['lookback_days']
                )

            # Check if we have transactions to review
            if not transactions and not self.config['notifications']['empty_report']:
                logger.info("No uncategorized transactions found, skipping email")
                return

            # Generate suggestions for each transaction
            suggestions = {}
            split_suggestions = {}

            if transactions:
                logger.info(f"Generating suggestions for {len(transactions)} transactions...")

                for txn in transactions:
                    # Generate category suggestions
                    if self.suggestion_engine:
                        category_suggestions = self.suggestion_engine.suggest_category(txn)
                        if category_suggestions:
                            suggestions[txn.id] = category_suggestions

                    # Check for split suggestions
                    if self.split_analyzer:
                        split_suggestion = self.split_analyzer.analyze_for_split(txn)
                        if split_suggestion:
                            split_suggestions[txn.id] = split_suggestion

            # Get recipient email
            recipient_email = self.config['notifications']['recipient_email']
            if not recipient_email:
                recipient_email = self.gmail.get_user_email()

            if dry_run or self.config['development']['dry_run']:
                logger.info("[DRY RUN] Would send email to: " + recipient_email)
                logger.info(f"Transactions: {len(transactions)}")
                logger.info(f"Suggestions generated: {len(suggestions)}")
                logger.info(f"Split suggestions: {len(split_suggestions)}")

                # Log sample transaction details
                if transactions:
                    sample = transactions[0]
                    logger.info(f"\nSample transaction:")
                    logger.info(f"  Payee: {sample.payee_name}")
                    logger.info(f"  Amount: ${abs(sample.amount):.2f}")
                    logger.info(f"  Date: {sample.date}")
                    logger.info(f"  Account: {sample.account_name}")

                    if sample.id in suggestions:
                        logger.info(f"  Top suggestion: {suggestions[sample.id][0].category_name} "
                                  f"({suggestions[sample.id][0].confidence:.0f}%)")
            else:
                # Send the email
                logger.info(f"Sending review email to {recipient_email}...")

                if transactions:
                    success = self.email_generator.generate_and_send_review_email(
                        to_email=recipient_email,
                        transactions=transactions,
                        suggestions=suggestions,
                        split_suggestions=split_suggestions,
                        is_sunday=self.is_sunday()
                    )
                else:
                    # Send "all caught up" email
                    success = self.email_generator.send_no_transactions_email(recipient_email)

                if success:
                    logger.info("Email sent successfully!")

                    # Mark transactions as reviewed (sent for review)
                    if transactions:
                        txn_ids = [t.id for t in transactions]
                        self.scanner.mark_as_reviewed(txn_ids)
                else:
                    logger.error("Failed to send email")

            # Log statistics
            stats = self.scanner.get_statistics()
            logger.info("\n--- Review Statistics ---")
            logger.info(f"Total reviewed: {stats['total_reviewed']}")
            logger.info(f"Pending review: {stats['pending_review']}")
            logger.info(f"Categorizations recorded: {stats['categorizations_recorded']}")

            if self.suggestion_engine:
                merchant_stats = self.suggestion_engine.get_merchant_stats()
                logger.info(f"Known merchants: {merchant_stats['total_known_merchants']}")

        except Exception as e:
            logger.error(f"Error during review: {e}", exc_info=True)
            raise

        logger.info("\n" + "=" * 50)
        logger.info("Transaction review completed")
        logger.info("=" * 50)

    def validate_setup(self) -> bool:
        """Validate all services and configuration"""
        logger.info("Validating setup...")

        issues = []

        # Check configuration
        if not self.config.get('ynab_api_key') and not os.getenv('YNAB_API_KEY'):
            issues.append("YNAB API key not configured")

        if not self.config['notifications']['recipient_email']:
            logger.warning("Recipient email not configured, will use authenticated Gmail account")

        # Initialize services
        try:
            self.initialize_services()
        except Exception as e:
            issues.append(f"Failed to initialize services: {e}")
            return False

        # Test YNAB connection
        try:
            if self.ynab.validate_connection():
                logger.info("✓ YNAB connection successful")
            else:
                issues.append("YNAB connection failed")
        except Exception as e:
            issues.append(f"YNAB connection error: {e}")

        # Test Gmail connection
        try:
            if self.gmail.test_connection():
                email = self.gmail.get_user_email()
                logger.info(f"✓ Gmail connected: {email}")
            else:
                issues.append("Gmail connection failed")
        except Exception as e:
            issues.append(f"Gmail connection error: {e}")

        # Check data directories
        data_dir = Path(__file__).parent.parent / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Data directory ready: {data_dir}")

        # Report issues
        if issues:
            logger.error("\n❌ Setup validation failed:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False

        logger.info("\n✅ All validations passed!")
        return True

    def show_stats(self):
        """Show current statistics"""
        if not self.scanner:
            self.initialize_services()

        stats = self.scanner.get_statistics()

        print("\n" + "=" * 50)
        print("YNAB Transaction Reviewer - Statistics")
        print("=" * 50)
        print(f"\nReview State:")
        print(f"  Total reviewed: {stats['total_reviewed']}")
        print(f"  Pending review: {stats['pending_review']}")
        print(f"  Last scan: {stats.get('last_scan', 'Never')}")

        if 'oldest_pending_days' in stats:
            print(f"  Oldest pending: {stats['oldest_pending_days']} days")

        if self.suggestion_engine:
            merchant_stats = self.suggestion_engine.get_merchant_stats()
            print(f"\nMerchant Intelligence:")
            print(f"  Known merchants: {merchant_stats['total_known_merchants']}")
            print(f"  Categories tracked: {merchant_stats['categories_tracked']}")
            print(f"  Last updated: {merchant_stats.get('last_updated', 'Never')}")

        print("\nSchedule:")
        print(f"  Daily review time: {self.config['schedule']['daily_review_time']}")
        print(f"  Timezone: {self.config['schedule']['timezone']}")
        print(f"  Skip days: {', '.join(self.config['schedule']['skip_days'])}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='YNAB Transaction Reviewer - Daily email system for transaction categorization'
    )

    parser.add_argument(
        '--run',
        action='store_true',
        help='Run the transaction review now'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate setup and connections'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show current statistics'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without sending emails'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force run even on skip days'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file'
    )

    args = parser.parse_args()

    # Create reviewer instance
    reviewer = TransactionReviewer(config_path=args.config)

    # Handle commands
    if args.validate:
        success = reviewer.validate_setup()
        sys.exit(0 if success else 1)
    elif args.stats:
        reviewer.show_stats()
    elif args.run:
        reviewer.run_review(force=args.force, dry_run=args.dry_run)
    else:
        # Show help if no command specified
        parser.print_help()
        print("\nExamples:")
        print("  python reviewer_main.py --validate    # Validate setup")
        print("  python reviewer_main.py --run         # Run review now")
        print("  python reviewer_main.py --dry-run     # Test without sending")
        print("  python reviewer_main.py --stats       # Show statistics")


if __name__ == "__main__":
    main()