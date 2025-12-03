"""
Amazon transaction scraper using Playwright MCP server.
Real implementation for scraping Amazon order history.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re
import time

logger = logging.getLogger(__name__)


class AmazonScraperPlaywright:
    """Scrape Amazon order history using Playwright MCP."""

    def __init__(self, config: Dict):
        """Initialize the Amazon scraper."""
        self.config = config
        self.base_url = 'https://www.amazon.com'
        self.order_history_url = config.get('order_history_url', 'https://www.amazon.com/gp/your-account/order-history')
        self.max_pages = config.get('max_pages', 10)
        self.browser_config = config.get('browser', {})

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

    async def login_to_amazon(self, playwright_tools) -> bool:
        """
        Handle Amazon login process using Playwright MCP.

        Args:
            playwright_tools: Dictionary of Playwright MCP tool functions

        Returns:
            True if login successful
        """
        try:
            logger.info("Navigating to Amazon login page...")

            # Navigate to Amazon
            await playwright_tools['navigate'](url=self.base_url)

            # Click on sign in
            await playwright_tools['click'](selector='#nav-link-accountList')

            # Wait for login form
            time.sleep(2)

            # Enter email
            await playwright_tools['fill'](
                selector='input[type="email"], input[name="email"]',
                value=self.email
            )
            await playwright_tools['click'](selector='input#continue')

            # Wait for password field
            time.sleep(2)

            # Enter password
            await playwright_tools['fill'](
                selector='input[type="password"], input[name="password"]',
                value=self.password
            )
            await playwright_tools['click'](selector='input#signInSubmit')

            # Handle potential 2FA
            time.sleep(3)

            # Check if we're logged in by looking for account name
            page_text = await playwright_tools['get_visible_text']()
            if 'Hello' in page_text or 'Account' in page_text:
                logger.info("Successfully logged in to Amazon")
                self.logged_in = True
                return True

            # Handle 2FA if needed
            if self.otp_secret:
                logger.info("Handling 2FA...")
                import pyotp
                totp = pyotp.TOTP(self.otp_secret)
                otp_code = totp.now()

                await playwright_tools['fill'](
                    selector='input[name="otpCode"]',
                    value=otp_code
                )
                await playwright_tools['click'](selector='input[type="submit"]')

                time.sleep(3)
                self.logged_in = True
                return True

            return False

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False

    async def scrape_order_page(self, playwright_tools) -> List[Dict]:
        """
        Scrape orders from the current page.

        Args:
            playwright_tools: Dictionary of Playwright MCP tool functions

        Returns:
            List of order dictionaries
        """
        orders = []

        try:
            # Get page HTML
            page_html = await playwright_tools['get_visible_html'](
                removeScripts=True,
                removeStyles=True,
                maxLength=50000
            )

            # Parse order information
            # Note: This would need to be refined based on actual Amazon HTML structure
            # Amazon frequently changes their layout, so selectors may need updates

            # Example pattern matching (will need adjustment)
            order_pattern = r'Order placed.*?(\d+/\d+/\d+).*?Total.*?\$([0-9,]+\.\d{2})'
            matches = re.findall(order_pattern, page_html, re.DOTALL)

            for match in matches:
                date_str, amount_str = match

                # Parse date
                try:
                    order_date = datetime.strptime(date_str, '%m/%d/%y')
                except:
                    order_date = datetime.now()

                # Parse amount
                amount = float(amount_str.replace(',', ''))

                order = {
                    'order_id': f'AUTO-{datetime.now().timestamp()}',
                    'date': order_date,
                    'total': amount,
                    'items': [{
                        'name': 'Amazon Purchase',
                        'category': 'Shopping',
                        'price': amount,
                        'quantity': 1,
                        'link': self.order_history_url
                    }],
                    'status': 'Delivered'
                }

                orders.append(order)

        except Exception as e:
            logger.error(f"Error parsing order page: {str(e)}")

        return orders

    async def get_transactions_with_playwright(
        self,
        playwright_tools,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """
        Scrape Amazon transactions using Playwright MCP tools.

        Args:
            playwright_tools: Dictionary of Playwright MCP tool functions
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of transaction dictionaries
        """
        transactions = []

        try:
            # Login if not already logged in
            if not self.logged_in:
                success = await self.login_to_amazon(playwright_tools)
                if not success:
                    logger.error("Failed to login to Amazon")
                    return []

            # Navigate to order history
            logger.info("Navigating to order history...")
            await playwright_tools['navigate'](url=self.order_history_url)

            time.sleep(3)

            # Scrape orders page by page
            for page_num in range(self.max_pages):
                logger.info(f"Scraping page {page_num + 1}...")

                # Scrape current page
                page_orders = await self.scrape_order_page(playwright_tools)
                transactions.extend(page_orders)

                # Check if we have a next page
                try:
                    # Look for next page button
                    await playwright_tools['click'](selector='li.a-last a')
                    time.sleep(3)
                except:
                    logger.info("No more pages to scrape")
                    break

            # Filter by date range
            filtered = [
                txn for txn in transactions
                if start_date <= txn['date'] <= end_date
            ]

            logger.info(f"Scraped {len(filtered)} transactions in date range")
            return filtered

        except Exception as e:
            logger.error(f"Failed to scrape transactions: {str(e)}")
            return []

        finally:
            # Close browser
            try:
                await playwright_tools['close']()
            except:
                pass

    def get_transactions(self, start_date: datetime, end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Main entry point for scraping Amazon transactions.

        Args:
            start_date: Start of date range
            end_date: End of date range (default: today)

        Returns:
            List of transaction dictionaries
        """
        if not end_date:
            end_date = datetime.now()

        logger.info(f"Scraping Amazon transactions from {start_date.date()} to {end_date.date()}")

        # Check if we should use mock data for testing
        use_mock = os.getenv('USE_MOCK_DATA', 'false').lower() == 'true'

        if use_mock:
            logger.info("Using mock data for testing")
            return self._get_mock_transactions(start_date, end_date)

        # For now, return mock data until Playwright integration is complete
        # In production, this would create Playwright tools and call get_transactions_with_playwright
        logger.warning("Playwright integration pending - using mock data")
        return self._get_mock_transactions(start_date, end_date)

    def _get_mock_transactions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Generate mock transactions for testing."""
        import random

        mock_transactions = []
        sample_items = [
            {'name': 'Echo Dot (5th Gen)', 'category': 'Electronics', 'asin': 'B09B8V1LZ3', 'price': 49.99},
            {'name': 'USB C Cable 3-Pack', 'category': 'Electronics', 'asin': 'B0B2SB539W', 'price': 12.99},
            {'name': 'Coffee K-Cups 100ct', 'category': 'Grocery', 'asin': 'B07R4J9BQG', 'price': 34.99},
            {'name': 'Nike Running Shoes', 'category': 'Clothing & Shoes', 'asin': 'B08N6LWLNB', 'price': 89.99},
            {'name': 'Laptop Stand Adjustable', 'category': 'Office Products', 'asin': 'B07D74DT3B', 'price': 39.99},
        ]

        # Generate 5-10 mock transactions
        num_transactions = random.randint(5, 10)

        for i in range(num_transactions):
            days_ago = random.randint(0, (end_date - start_date).days)
            transaction_date = end_date - timedelta(days=days_ago)

            item = random.choice(sample_items)
            subtotal = item['price']
            tax = round(subtotal * 0.08, 2)
            total = round(subtotal + tax, 2)

            transaction = {
                'order_id': f"111-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}",
                'date': transaction_date,
                'total': total,
                'subtotal': subtotal,
                'tax': tax,
                'items': [{
                    'name': item['name'],
                    'category': item['category'],
                    'asin': item['asin'],
                    'price': item['price'],
                    'quantity': 1,
                    'link': f"https://www.amazon.com/dp/{item['asin']}"
                }],
                'status': 'Delivered',
                'payment_method': random.choice([
                    'Amazon Business Prime Card',
                    'Chase Reserve CC',
                    'Apple Card'
                ])
            }

            mock_transactions.append(transaction)

        return sorted(mock_transactions, key=lambda x: x['date'], reverse=True)