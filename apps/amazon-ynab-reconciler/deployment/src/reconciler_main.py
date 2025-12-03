"""
Main orchestrator for Amazon-YNAB transaction reconciliation.
Coordinates scraping, matching, and updating processes.
"""

import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import argparse
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

from amazon_scraper import AmazonScraper
from ynab_service import YNABService
from transaction_matcher import TransactionMatcher
from reconciliation_engine import ReconciliationEngine
from report_generator import ReportGenerator

# Set up logging
# Check if running in Lambda
if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    # Lambda environment - use console logging only
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
else:
    # Local environment - use file and console logging
    log_path = Path(__file__).parent.parent / 'logs'
    log_path.mkdir(exist_ok=True)
    log_file = log_path / 'reconciler.log'

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(str(log_file)),
            logging.StreamHandler()
        ]
    )
logger = logging.getLogger(__name__)


class AmazonYNABReconciler:
    """Main reconciliation orchestrator."""

    def __init__(self, config_path: str = None, dry_run: bool = False):
        """Initialize the reconciler with configuration."""
        self.config = self._load_config(config_path)
        self.dry_run = dry_run

        # Initialize services
        self.amazon_scraper = AmazonScraper(self.config.get('amazon', {}))
        self.ynab_service = YNABService(self.config.get('ynab', {}))
        self.matcher = TransactionMatcher(self.config.get('reconciliation', {}))
        self.reconciliation_engine = ReconciliationEngine(
            self.ynab_service,
            self.config.get('reconciliation', {}),
            dry_run=dry_run
        )
        self.report_generator = ReportGenerator(self.config.get('email', {}))

        logger.info(f"Reconciler initialized. Dry run mode: {dry_run}")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        # Default to config.yaml in parent directory
        if not config_path:
            config_path = Path(__file__).parent.parent / 'config.yaml'

        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            # Return default config
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Return default configuration."""
        return {
            'reconciliation': {
                'lookback_days': 30,
                'match_threshold': 80,
                'date_tolerance_days': 2,
                'amount_tolerance_cents': 50
            },
            'amazon': {
                'order_history_url': 'https://www.amazon.com/gp/your-account/order-history',
                'max_pages': 10
            },
            'ynab': {
                'budget_name': 'Main Budget',
                'account_names': ['Chase Credit Card', 'Amex']
            },
            'email': {
                'enabled': True,
                'recipient': None
            }
        }

    def run(self, lookback_days: Optional[int] = None) -> Dict:
        """
        Run the complete reconciliation process.

        Args:
            lookback_days: Override config lookback period

        Returns:
            Summary of reconciliation results
        """
        start_time = datetime.now()
        logger.info("Starting Amazon-YNAB reconciliation process")

        # Use provided lookback or fall back to config
        lookback = lookback_days or self.config['reconciliation']['lookback_days']
        start_date = datetime.now() - timedelta(days=lookback)

        results = {
            'start_time': start_time,
            'lookback_days': lookback,
            'amazon_transactions': [],
            'ynab_transactions': [],
            'matches': [],
            'unmatched_amazon': [],
            'unmatched_ynab': [],
            'updates_applied': 0,
            'errors': []
        }

        try:
            # Step 1: Scrape Amazon transactions
            logger.info(f"Scraping Amazon transactions from {start_date.date()}")
            results['amazon_transactions'] = self.amazon_scraper.get_transactions(
                start_date=start_date
            )
            logger.info(f"Found {len(results['amazon_transactions'])} Amazon transactions")

            # Step 2: Fetch YNAB transactions
            logger.info("Fetching YNAB transactions")
            results['ynab_transactions'] = self.ynab_service.get_transactions(
                since_date=start_date,
                account_names=self.config['ynab']['account_names']
            )
            logger.info(f"Found {len(results['ynab_transactions'])} YNAB transactions")

            # Step 3: Match transactions
            logger.info("Matching transactions")
            logger.debug(f"Passing {len(results['amazon_transactions'])} Amazon and {len(results['ynab_transactions'])} YNAB to matcher")
            matches, unmatched_amazon, unmatched_ynab = self.matcher.match_transactions(
                amazon_transactions=results['amazon_transactions'],
                ynab_transactions=results['ynab_transactions']
            )

            results['matches'] = matches
            results['unmatched_amazon'] = unmatched_amazon
            results['unmatched_ynab'] = unmatched_ynab

            logger.info(f"Matched {len(matches)} transactions")
            logger.info(f"Unmatched Amazon: {len(unmatched_amazon)}")
            logger.info(f"Unmatched YNAB: {len(unmatched_ynab)}")

            # Step 4: Apply updates to YNAB
            if matches and not self.dry_run:
                logger.info("Applying updates to YNAB")
                results['updates_applied'] = self.reconciliation_engine.apply_updates(matches)
                logger.info(f"Applied {results['updates_applied']} updates")
            elif self.dry_run:
                logger.info("DRY RUN: Skipping YNAB updates")

            # Step 5: Generate and send report
            if self.config['email'].get('enabled'):
                logger.info("Generating reconciliation report")
                self.report_generator.send_report(results)

        except Exception as e:
            logger.error(f"Reconciliation failed: {str(e)}", exc_info=True)
            results['errors'].append(str(e))

        results['end_time'] = datetime.now()
        results['duration'] = (results['end_time'] - start_time).total_seconds()

        logger.info(f"Reconciliation complete in {results['duration']:.2f} seconds")
        return results

    def validate_setup(self) -> bool:
        """Validate that all services are properly configured."""
        logger.info("Validating setup...")

        validations = [
            ('Amazon credentials', self.amazon_scraper.validate_credentials()),
            ('YNAB connection', self.ynab_service.validate_connection()),
            ('Email configuration', self.report_generator.validate_config())
        ]

        all_valid = True
        for name, is_valid in validations:
            if is_valid:
                logger.info(f"✓ {name}: Valid")
            else:
                logger.error(f"✗ {name}: Invalid")
                all_valid = False

        return all_valid


def main():
    """Main entry point for the reconciler."""
    parser = argparse.ArgumentParser(
        description='Amazon-YNAB Transaction Reconciliation'
    )
    parser.add_argument(
        '--days',
        type=int,
        help='Number of days to look back for transactions'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without applying updates to YNAB'
    )
    parser.add_argument(
        '--use-email',
        action='store_true',
        help='Use Gmail to parse Amazon order confirmation emails'
    )
    parser.add_argument(
        '--use-csv',
        action='store_true',
        help='Import Amazon orders from CSV file instead of web scraping'
    )
    parser.add_argument(
        '--use-sample',
        action='store_true',
        help='Use sample Amazon data for testing'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate configuration and exit'
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to configuration file'
    )

    args = parser.parse_args()

    # Set environment variable for email mode if requested
    if args.use_email:
        os.environ['USE_EMAIL'] = 'true'
        logger.info("Email mode enabled - will parse Amazon emails from Gmail")

    # Set environment variable for CSV mode if requested
    if args.use_csv:
        os.environ['USE_CSV'] = 'true'

    # Set environment variable for sample mode if requested
    if args.use_sample:
        os.environ['USE_SAMPLE'] = 'true'

    # Initialize reconciler
    reconciler = AmazonYNABReconciler(
        config_path=args.config,
        dry_run=args.dry_run
    )

    # Validate only
    if args.validate:
        if reconciler.validate_setup():
            print("✓ All validations passed")
            sys.exit(0)
        else:
            print("✗ Validation failed")
            sys.exit(1)

    # Run reconciliation
    results = reconciler.run(lookback_days=args.days)

    # Print summary
    print("\n" + "="*50)
    print("RECONCILIATION SUMMARY")
    print("="*50)
    print(f"Duration: {results['duration']:.2f} seconds")
    print(f"Amazon transactions: {len(results['amazon_transactions'])}")
    print(f"YNAB transactions: {len(results['ynab_transactions'])}")
    print(f"Matched: {len(results['matches'])}")
    print(f"Updates applied: {results['updates_applied']}")

    if results['errors']:
        print(f"\nErrors: {len(results['errors'])}")
        for error in results['errors']:
            print(f"  - {error}")

    print("="*50)


if __name__ == "__main__":
    main()