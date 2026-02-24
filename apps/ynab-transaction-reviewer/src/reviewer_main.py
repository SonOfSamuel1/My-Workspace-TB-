#!/usr/bin/env python3
"""
YNAB Transaction Reviewer - Main Orchestrator

Daily email system that pushes uncategorized YNAB transactions for review
with smart suggestions and one-click categorization.

REFACTORED: Now uses batch-first architecture with BudgetDataContext.
API calls reduced from 100+ to 4-5 total, eliminating rate limit issues.
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
from batch_fetcher import BatchDataFetcher
from data_context import BudgetDataContext, Transaction
from suggestion_engine import SuggestionEngine
from split_analyzer import SplitAnalyzer
from email_generator import EmailGenerator

# Note: TransactionScanner removed - using batch-first architecture now

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
        self.data_context = None  # Pre-fetched budget data (batch-first architecture)
        self.suggestion_engine = None
        self.split_analyzer = None
        self.email_generator = None
        self.email_service = None

    def _load_config(self, config_path: str = None) -> Dict:
        """Load configuration from YAML file"""
        if not config_path:
            # Check if running in Lambda (flat structure) or locally
            local_config = Path(__file__).parent / 'config' / 'config.yaml'
            parent_config = Path(__file__).parent.parent / 'config' / 'config.yaml'
            if local_config.exists():
                config_path = local_config
            elif parent_config.exists():
                config_path = parent_config
            else:
                # Fallback to Lambda task directory
                config_path = Path('/var/task/config/config.yaml')

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

        # BATCH-FIRST ARCHITECTURE: Fetch all data upfront (4 API calls total)
        # This replaces 100+ per-transaction API calls that caused rate limiting
        logger.info("Fetching complete budget context (batch-first architecture)...")
        fetcher = BatchDataFetcher(self.ynab)
        lookback_days = self.config['scanning'].get('lookback_days', 30)

        # Fetch with longer history for better suggestion patterns
        history_days = max(lookback_days, self.config.get('merchant_intelligence', {}).get('lookback_days', 365))
        self.data_context = fetcher.fetch_complete_context(days_back=history_days)
        logger.info(f"Context fetched: {self.data_context.transaction_count} transactions, "
                   f"{len(self.data_context.uncategorized_transactions)} uncategorized, "
                   f"{len(self.data_context.unapproved_transactions)} unapproved")

        # Determine data directory (use /tmp on Lambda)
        is_lambda = os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None
        data_dir = '/tmp/data' if is_lambda else 'data'

        # Initialize suggestion engine with context (no more per-transaction API calls)
        if self.config['suggestions']['enabled']:
            self.suggestion_engine = SuggestionEngine(
                data_context=self.data_context,
                merchant_db_file=f'{data_dir}/merchants.json'
            )

        # Initialize split analyzer with context (no more per-transaction API calls)
        if self.config['split_detection']['enabled']:
            self.split_analyzer = SplitAnalyzer(
                data_context=self.data_context
            )

        # Initialize email service (SES or Gmail based on environment)
        use_ses = os.getenv('USE_SES', 'false').lower() == 'true'
        if use_ses:
            from ses_service import SESEmailService
            sender_email = os.getenv('SES_SENDER_EMAIL', 'TERRANCE@GOODPORTION.ORG')
            self.email_service = SESEmailService(sender_email=sender_email)
            logger.info(f"Using AWS SES for email (sender: {sender_email})")
        else:
            from gmail_service import GmailService
            self.email_service = GmailService()
            logger.info("Using Gmail for email")

        # Initialize email generator
        self.email_generator = EmailGenerator(
            email_service=self.email_service,
            action_base_url=self.config['actions'].get('api_gateway_url'),
            budget_id=self.ynab.budget_id
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
            # Use pre-fetched transactions from context (no additional API calls)
            logger.info("Using pre-fetched transactions from context...")

            # Get transactions from context (already filtered)
            transactions = self.data_context.uncategorized_transactions
            unapproved_transactions = self.data_context.unapproved_transactions

            logger.info(f"Found {len(transactions)} uncategorized transactions")
            logger.info(f"Found {len(unapproved_transactions)} unapproved transactions")

            # Check if we have any transactions to review
            if not transactions and not unapproved_transactions:
                if not self.config['notifications']['empty_report']:
                    logger.info("No transactions found needing review, skipping email")
                    return

            # Generate suggestions for uncategorized transactions
            suggestions = {}
            split_suggestions = {}

            if transactions:
                logger.info(f"Generating suggestions for {len(transactions)} uncategorized transactions...")

                for txn in transactions:
                    try:
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
                    except Exception as e:
                        # Continue with other transactions even if one fails
                        logger.warning(f"Error processing transaction {txn.payee_name}: {e}")

            # Generate suggestions for unapproved transactions
            unapproved_suggestions = {}
            unapproved_splits = {}

            if unapproved_transactions:
                logger.info(f"Generating suggestions for {len(unapproved_transactions)} unapproved transactions...")

                for txn in unapproved_transactions:
                    try:
                        # Generate category suggestions
                        if self.suggestion_engine:
                            category_suggestions = self.suggestion_engine.suggest_category(txn)
                            if category_suggestions:
                                unapproved_suggestions[txn.id] = category_suggestions

                        # Check for split suggestions
                        if self.split_analyzer:
                            split_suggestion = self.split_analyzer.analyze_for_split(txn)
                            if split_suggestion:
                                unapproved_splits[txn.id] = split_suggestion
                    except Exception as e:
                        # Continue with other transactions even if one fails
                        logger.warning(f"Error processing unapproved transaction {txn.payee_name}: {e}")

            # Get recipient email
            recipient_email = self.config['notifications']['recipient_email']
            if not recipient_email:
                recipient_email = os.getenv('RECIPIENT_EMAIL', 'terrancebrandon@me.com')

            if dry_run or self.config['development']['dry_run']:
                logger.info("[DRY RUN] Would send email to: " + recipient_email)
                logger.info(f"Uncategorized transactions: {len(transactions)}")
                logger.info(f"Unapproved transactions: {len(unapproved_transactions)}")
                logger.info(f"Suggestions generated: {len(suggestions)}")
                logger.info(f"Split suggestions: {len(split_suggestions)}")

                # Log sample uncategorized transaction details
                if transactions:
                    sample = transactions[0]
                    logger.info(f"\nSample uncategorized transaction:")
                    logger.info(f"  Payee: {sample.payee_name}")
                    logger.info(f"  Amount: ${abs(sample.amount):.2f}")
                    logger.info(f"  Date: {sample.date}")
                    logger.info(f"  Account: {sample.account_name}")

                    if sample.id in suggestions:
                        logger.info(f"  Top suggestion: {suggestions[sample.id][0].category_name} "
                                  f"({suggestions[sample.id][0].confidence:.0f}%)")

                # Log sample unapproved transaction details
                if unapproved_transactions:
                    sample = unapproved_transactions[0]
                    logger.info(f"\nSample unapproved transaction:")
                    logger.info(f"  Payee: {sample.payee_name}")
                    logger.info(f"  Amount: ${abs(sample.amount):.2f}")
                    logger.info(f"  Date: {sample.date}")
                    logger.info(f"  Account: {sample.account_name}")
                    logger.info(f"  Category: {sample.category_name or 'None'}")
            else:
                # Trash previous digest emails before sending new one
                from gmail_service import GmailService as GmailSvc
                if isinstance(self.email_service, GmailSvc):
                    try:
                        trashed = self.email_service.trash_previous_digests()
                        logger.info(f"Trashed {trashed} previous YNAB digest(s)")
                    except Exception as e:
                        logger.warning(f"Could not trash previous digests: {e}")

                # Send the email
                logger.info(f"Sending review email to {recipient_email}...")

                if transactions or unapproved_transactions:
                    success = self.email_generator.generate_and_send_review_email(
                        to_email=recipient_email,
                        transactions=transactions,
                        suggestions=suggestions,
                        split_suggestions=split_suggestions,
                        unapproved_transactions=unapproved_transactions,
                        unapproved_suggestions=unapproved_suggestions,
                        unapproved_splits=unapproved_splits,
                        is_sunday=self.is_sunday()
                    )
                else:
                    # Send "all caught up" email
                    success = self.email_generator.send_no_transactions_email(recipient_email)

                if success:
                    logger.info("Email sent successfully!")
                else:
                    logger.error("Failed to send email")

            # Log statistics from data context
            logger.info("\n--- Review Statistics ---")
            logger.info(f"Total transactions: {self.data_context.transaction_count}")
            logger.info(f"Uncategorized: {len(self.data_context.uncategorized_transactions)}")
            logger.info(f"Unapproved: {len(self.data_context.unapproved_transactions)}")

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

        # Test email service connection
        try:
            if self.email_service.test_connection():
                logger.info("✓ Email service connected")
            else:
                issues.append("Email service connection failed")
        except Exception as e:
            issues.append(f"Email service connection error: {e}")

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
        if not self.data_context:
            self.initialize_services()

        print("\n" + "=" * 50)
        print("YNAB Transaction Reviewer - Statistics")
        print("=" * 50)
        print(f"\nTransaction State:")
        print(f"  Total transactions: {self.data_context.transaction_count}")
        print(f"  Uncategorized: {len(self.data_context.uncategorized_transactions)}")
        print(f"  Unapproved: {len(self.data_context.unapproved_transactions)}")
        print(f"  Categories tracked: {len(self.data_context.categories)}")
        print(f"  Payees with history: {len(self.data_context.payee_category_histogram)}")

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