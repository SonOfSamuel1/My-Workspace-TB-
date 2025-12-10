"""
Amazon transaction scraper with multiple data source support.
Handles Dual-Email (primary), Downloads folder, CSV import, and Playwright web scraping.

Priority Order (configurable):
1. DUAL EMAIL - Multi-account email reconciliation (Gmail + IMAP)
2. DOWNLOADS - Amazon CSV exports from Downloads folder
3. SINGLE EMAIL - Legacy single Gmail account mode
4. CSV - Manual CSV import from data/ directory
5. BROWSERBASE - Cloud browser automation
6. PLAYWRIGHT - Local browser automation (fallback)

Playwright dependencies are loaded lazily to reduce Lambda memory usage
when using email or CSV modes.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import base64

logger = logging.getLogger(__name__)

# Lazy import for pyotp - only needed for 2FA login
_pyotp = None

def _get_pyotp():
    """Lazy load pyotp module only when needed."""
    global _pyotp
    if _pyotp is None:
        import pyotp
        _pyotp = pyotp
    return _pyotp


class AmazonScraper:
    """Scrape Amazon order history using Playwright."""

    def __init__(self, config: Dict):
        """Initialize the Amazon scraper."""
        self.config = config
        self.base_url = config.get('order_history_url', 'https://www.amazon.com/gp/your-account/order-history')
        self.max_pages = config.get('max_pages', 10)
        self.browser_config = config.get('browser', {})
        self.selectors = config.get('selectors', {})

        # Get credentials from environment
        self.email = os.getenv('AMAZON_EMAIL')
        self.password = os.getenv('AMAZON_PASSWORD')
        self.otp_secret = os.getenv('AMAZON_OTP_SECRET')

        # Track session state
        self.logged_in = False
        self.transactions = []

    def validate_credentials(self) -> bool:
        """Validate that Amazon credentials are available."""
        if not self.email or not self.password:
            logger.error("Amazon email and password not configured")
            return False
        return True

    def get_transactions(self, start_date: datetime, end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Scrape Amazon transactions within the date range.

        Args:
            start_date: Start of date range
            end_date: End of date range (default: today)

        Returns:
            List of transaction dictionaries
        """
        if not end_date:
            end_date = datetime.now()

        # Validate date range - end_date should not be more than 30 days in future
        max_future = datetime.now() + timedelta(days=30)
        if end_date > max_future:
            logger.warning(f"End date {end_date.date()} is more than 30 days in future, using current date")
            end_date = datetime.now()

        # Validate start_date is before end_date
        if start_date > end_date:
            logger.error(f"Start date {start_date.date()} is after end date {end_date.date()}")
            raise ValueError("Start date cannot be after end date")

        logger.info(f"Getting Amazon transactions from {start_date.date()} to {end_date.date()}")

        # =====================================================================
        # PRIORITY 1: DUAL EMAIL MODE (Primary - searches both Gmail + IMAP)
        # =====================================================================
        use_dual_email = os.getenv('USE_DUAL_EMAIL', 'false').lower() == 'true'
        if use_dual_email:
            logger.info("Using DUAL EMAIL mode (primary) - searching multiple email accounts")
            transactions = self._fetch_from_dual_email(start_date, end_date)
            if transactions is not None:  # None means fallback, empty list means no transactions
                return transactions
            logger.info("Dual email mode returned no results, trying fallback sources...")

        # =====================================================================
        # PRIORITY 2: DOWNLOADS MODE
        # =====================================================================
        use_downloads = os.getenv('USE_DOWNLOADS', 'false').lower() == 'true'
        if use_downloads:
            logger.info("Using downloads mode to fetch Amazon transactions from Downloads folder")
            from amazon_csv_importer import AmazonCSVImporter

            try:
                importer = AmazonCSVImporter()
                transactions, csv_path = importer.import_from_downloads(since=start_date)

                if transactions:
                    # Use enhanced parsing if available
                    if csv_path:
                        enhanced_transactions = importer.parse_enhanced_csv(csv_path)
                        if enhanced_transactions:
                            transactions = enhanced_transactions

                    # Filter by date range
                    filtered = [
                        txn for txn in transactions
                        if start_date <= txn['date'] <= end_date
                    ]

                    logger.info(f"Imported {len(filtered)} transactions from Downloads folder")

                    # Archive the CSV if configured
                    if csv_path and self.config.get('archive_downloads', True):
                        importer.archive_csv(csv_path)

                    return filtered
                else:
                    logger.info("No unprocessed Amazon CSV files found in Downloads folder")
                    # Fall through to email mode
            except Exception as e:
                logger.error(f"Downloads mode failed: {e}")
                logger.info("Falling back to email mode if available")
                # Fall through to email mode

        # Check if we should use Browserbase mode (second priority after downloads)
        use_browserbase = os.getenv('USE_BROWSERBASE', 'false').lower() == 'true'
        if use_browserbase:
            logger.info("Using Browserbase mode to fetch Amazon transactions")
            from amazon_browserbase_scraper import AmazonBrowserbaseScraper
            from exceptions import BrowserbaseAuthRequiredError, BrowserbaseError

            try:
                browserbase_config = self.config.get('browserbase', {})
                scraper = AmazonBrowserbaseScraper(browserbase_config)
                transactions = scraper.get_transactions(start_date, end_date)

                if transactions:
                    logger.info(f"Scraped {len(transactions)} transactions via Browserbase")
                    return transactions
                else:
                    logger.info("No transactions found via Browserbase, falling back to email")
                    # Fall through to email mode

            except BrowserbaseAuthRequiredError as e:
                logger.warning(f"Browserbase session expired: {e}")
                logger.info("Manual re-authentication required. Falling back to email mode.")
                # Send notification about expired session
                self._notify_browserbase_session_expired(str(e))
                # Fall through to email mode

            except BrowserbaseError as e:
                logger.error(f"Browserbase mode failed: {e}")
                logger.info("Falling back to email mode if available")
                # Fall through to email mode

            except Exception as e:
                logger.error(f"Unexpected Browserbase error: {e}")
                logger.info("Falling back to email mode if available")
                # Fall through to email mode

        # Check if we should use email mode (third priority)
        use_email = os.getenv('USE_EMAIL', 'false').lower() == 'true'
        if use_email:
            logger.info("Using email mode to fetch Amazon transactions")
            from amazon_email_parser import AmazonEmailParser
            from gmail_service import get_gmail_service

            try:
                gmail_service = get_gmail_service()
                parser = AmazonEmailParser(gmail_service)
                transactions = parser.get_transactions(start_date, end_date)
                logger.info(f"Parsed {len(transactions)} transactions from emails")
                return transactions
            except Exception as e:
                logger.error(f"Email mode failed: {e}")
                logger.info("Falling back to CSV mode if available")
                # Fall through to CSV mode

        # Check if we should use CSV import (third priority)
        use_csv = os.getenv('USE_CSV', 'false').lower() == 'true'
        if use_csv:
            from amazon_csv_importer import AmazonCSVImporter
            importer = AmazonCSVImporter()
            transactions = importer.import_orders_csv()

            # Filter by date range
            filtered = [
                txn for txn in transactions
                if start_date <= txn['date'] <= end_date
            ]

            logger.info(f"Imported {len(filtered)} transactions from CSV in date range")
            return filtered

        # Check if we should use sample data
        use_sample = os.getenv('USE_SAMPLE', 'false').lower() == 'true'
        if use_sample:
            from amazon_csv_importer import AmazonCSVImporter
            importer = AmazonCSVImporter()
            transactions = importer.import_orders_json('data/amazon_orders_sample.json')

            # Filter by date range
            filtered = [
                txn for txn in transactions
                if start_date <= txn['date'] <= end_date
            ]

            logger.info(f"Using {len(filtered)} sample transactions in date range")
            return filtered

        try:
            # Note: In production, this would use the Playwright MCP server
            # For now, returning mock data for development
            transactions = self._scrape_with_playwright(start_date, end_date)

            # Filter by date range
            filtered = [
                txn for txn in transactions
                if start_date <= txn['date'] <= end_date
            ]

            logger.info(f"Scraped {len(filtered)} transactions in date range")
            return filtered

        except Exception as e:
            logger.error(f"Failed to scrape Amazon transactions: {str(e)}")
            raise

    def _scrape_with_playwright(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Use Playwright to scrape Amazon order history.
        In production, this would interact with the Playwright MCP server.
        """
        # This is a placeholder for the actual Playwright implementation
        # In production, we would:
        # 1. Use playwright_navigate to go to Amazon
        # 2. Handle login if needed
        # 3. Navigate through order history pages
        # 4. Extract transaction details
        # 5. Return structured data

        # For development, return mock data
        mock_transactions = []

        # Generate some mock transactions for testing
        current_date = end_date
        order_id = 100000000

        sample_items = [
            {'name': 'Echo Dot (5th Gen)', 'category': 'Electronics', 'asin': 'B09B8V1LZ3', 'price': 49.99},
            {'name': 'Anker USB C Charger', 'category': 'Electronics', 'asin': 'B0B2SB539W', 'price': 19.99},
            {'name': 'Organic Coffee Beans', 'category': 'Grocery', 'asin': 'B07R4J9BQG', 'price': 14.99},
            {'name': 'Running Shoes', 'category': 'Clothing & Shoes', 'asin': 'B08N6LWLNB', 'price': 89.99},
            {'name': 'Office Supplies Bundle', 'category': 'Office Products', 'asin': 'B07P8Y8L2F', 'price': 45.99},
            {'name': 'Wireless Mouse', 'category': 'Electronics', 'asin': 'B07DHNQMXK', 'price': 29.99},
            {'name': 'Laptop Stand', 'category': 'Office Products', 'asin': 'B07D74DT3B', 'price': 39.99},
            {'name': 'Bluetooth Headphones', 'category': 'Electronics', 'asin': 'B08C1KN5J2', 'price': 129.99},
            {'name': 'Dog Food - 30lb Bag', 'category': 'Pet Supplies', 'asin': 'B01EINBA76', 'price': 54.99},
            {'name': 'Instant Pot Duo', 'category': 'Home & Kitchen', 'asin': 'B00FLYWNYQ', 'price': 79.99},
            {'name': 'Yoga Mat', 'category': 'Sports & Outdoors', 'asin': 'B07P6Y8L2F', 'price': 24.99},
            {'name': 'Book: Atomic Habits', 'category': 'Books', 'asin': '0735211299', 'price': 16.99}
        ]

        # Generate transactions going back from end_date
        import random
        num_transactions = 15

        for i in range(num_transactions):
            # Random date within range
            days_ago = random.randint(0, (end_date - start_date).days)
            transaction_date = end_date - timedelta(days=days_ago)

            # Random item(s)
            num_items = random.randint(1, 3)
            items = random.sample(sample_items, min(num_items, len(sample_items)))

            # Calculate total
            subtotal = sum(item['price'] for item in items)
            tax = round(subtotal * 0.08, 2)  # 8% tax
            total = round(subtotal + tax, 2)

            transaction = {
                'order_id': f"{order_id + i}-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}",
                'date': transaction_date,
                'total': total,
                'subtotal': subtotal,
                'tax': tax,
                'items': [
                    {
                        'name': item['name'],
                        'category': item['category'],
                        'asin': item['asin'],
                        'price': item['price'],
                        'quantity': 1,
                        'link': f"https://www.amazon.com/dp/{item['asin']}"
                    }
                    for item in items
                ],
                'status': 'Delivered',
                'payment_method': random.choice([
                    'Amazon Business Prime Card',
                    'Chase Reserve CC',
                    'SimplyCash® Plus Card',
                    'Apple Card'
                ])
            }

            mock_transactions.append(transaction)

        # Sort by date descending
        mock_transactions.sort(key=lambda x: x['date'], reverse=True)

        return mock_transactions

    def _login_to_amazon(self) -> bool:
        """
        Handle Amazon login process.
        Returns True if successful.
        """
        # Placeholder for actual login implementation
        # Would use Playwright to:
        # 1. Navigate to login page
        # 2. Fill email/password
        # 3. Handle 2FA if needed
        # 4. Verify login success

        logger.info("Logging in to Amazon...")

        if self.otp_secret:
            # Generate OTP if 2FA is configured (lazy load pyotp)
            pyotp = _get_pyotp()
            totp = pyotp.TOTP(self.otp_secret)
            otp_code = totp.now()
            logger.info(f"Generated OTP code for 2FA")

        # Simulate login success
        self.logged_in = True
        return True

    def _extract_order_details(self, order_element: Dict) -> Dict:
        """
        Extract details from an order element.

        Args:
            order_element: Raw order data from page

        Returns:
            Structured transaction dictionary
        """
        # This would parse the actual HTML/DOM elements
        # For now, it's a placeholder
        return {
            'order_id': order_element.get('id'),
            'date': datetime.now(),
            'total': 0.0,
            'items': [],
            'status': 'Unknown'
        }

    def _navigate_to_date_range(self, start_date: datetime) -> bool:
        """
        Navigate to the correct date range in order history.
        Amazon allows filtering by year and specific time periods.
        """
        # Placeholder for navigation logic
        year = start_date.year
        logger.info(f"Navigating to orders from {year}")
        return True

    def close(self):
        """Clean up browser resources."""
        logger.info("Closing Amazon scraper")
        # Would close Playwright browser here

    def _fetch_from_dual_email(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[List[Dict]]:
        """
        Fetch Amazon transactions from multiple email accounts.

        Uses the MultiAccountEmailService to search both Gmail and IMAP accounts,
        then parses the emails into transaction data.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of transactions, or None if should fallback to other sources
        """
        try:
            from multi_account_email_service import MultiAccountEmailService
            from amazon_email_parser import AmazonEmailParser

            # Calculate days to look back
            days_back = (end_date - start_date).days + 1

            # Initialize multi-account service (loads from config.yaml)
            config_path = os.path.join(
                os.path.dirname(__file__), '..', 'config.yaml'
            )
            email_service = MultiAccountEmailService(config_path=config_path)

            # Check if we have any accounts configured
            if not email_service.clients:
                logger.warning("No email accounts configured for dual email mode")
                return None  # Fallback to other sources

            # Test connections
            connection_results = email_service.test_all_connections()
            connected_accounts = sum(1 for success in connection_results.values() if success)

            if connected_accounts == 0:
                logger.error("No email accounts could connect")
                return None  # Fallback to other sources

            logger.info(f"Connected to {connected_accounts}/{len(email_service.clients)} email accounts")

            # Search all accounts for Amazon emails
            logger.info(f"Searching for Amazon emails (last {days_back} days)...")
            email_messages = email_service.search_all_accounts(
                days_back=days_back,
                deduplicate=True,
                parallel=True
            )

            if not email_messages:
                logger.info("No Amazon emails found in any account")
                return []  # Return empty list (don't fallback - this is intentional)

            logger.info(f"Found {len(email_messages)} unique Amazon emails")

            # Parse emails into transactions
            parser = AmazonEmailParser()
            transactions = parser.parse_email_messages(
                messages=email_messages,
                start_date=start_date,
                end_date=end_date
            )

            # Close email connections
            email_service.close_all()

            logger.info(f"Parsed {len(transactions)} transactions from dual email sources")
            return transactions

        except ImportError as e:
            logger.warning(f"Multi-account email dependencies not available: {e}")
            return None  # Fallback to other sources
        except Exception as e:
            logger.error(f"Dual email mode failed: {e}")
            import traceback
            traceback.print_exc()
            return None  # Fallback to other sources

    def _notify_browserbase_session_expired(self, error_details: str):
        """
        Send notification when Browserbase Amazon session expires.

        Uses SNS if configured, otherwise just logs.

        Args:
            error_details: Error message with details
        """
        topic_arn = os.getenv('NOTIFICATION_TOPIC_ARN') or \
                    self.config.get('browserbase', {}).get('notification_topic_arn')

        message = f"""
Your Amazon Browserbase session has expired.

Error: {error_details}

To restore automated scraping:
1. Run locally: python src/browserbase_setup.py --login
2. Complete Amazon login in the browser window
3. Session will be automatically saved to Parameter Store

The system has fallen back to email parsing mode for this run.
        """.strip()

        if topic_arn:
            try:
                import boto3
                sns = boto3.client('sns', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
                sns.publish(
                    TopicArn=topic_arn,
                    Subject='[Amazon-YNAB] Browserbase Session Expired - Action Required',
                    Message=message
                )
                logger.info("Session expiry notification sent via SNS")
            except Exception as e:
                logger.warning(f"Failed to send SNS notification: {e}")
        else:
            logger.warning("No notification topic configured for session expiry alerts")


# Utility functions for date parsing
def parse_amazon_date(date_str: str) -> datetime:
    """Parse Amazon's date format."""
    # Amazon uses various formats like "December 4, 2024"
    try:
        return datetime.strptime(date_str, "%B %d, %Y")
    except:
        # Try other formats
        return datetime.now()


def extract_asin_from_link(link: str) -> Optional[str]:
    """Extract ASIN from Amazon product link."""
    import re
    match = re.search(r'/dp/([A-Z0-9]{10})', link)
    if match:
        return match.group(1)
    return None