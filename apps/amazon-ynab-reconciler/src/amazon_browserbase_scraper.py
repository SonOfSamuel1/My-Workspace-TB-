"""
Amazon transaction scraper using Browserbase MCP.

Uses Browserbase's cloud-based browser automation with Stagehand tools
for navigating Amazon and extracting order data. Supports persistent
sessions to avoid repeated login.
"""

import os
import re
import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from browserbase_session_manager import BrowserbaseSessionManager
from exceptions import (
    BrowserbaseError,
    BrowserbaseSessionError,
    BrowserbaseAuthRequiredError,
    BrowserbaseNavigationError,
    BrowserbaseExtractionError
)

logger = logging.getLogger(__name__)


class AmazonBrowserbaseScraper:
    """
    Scrape Amazon orders using Browserbase MCP.

    This scraper uses Browserbase's cloud-based browser instances
    with Stagehand tools for intelligent web automation.
    """

    AMAZON_ORDER_HISTORY_URL = 'https://www.amazon.com/gp/your-account/order-history'
    AMAZON_BASE_URL = 'https://www.amazon.com'

    def __init__(self, config: Dict = None):
        """
        Initialize the Browserbase scraper.

        Args:
            config: Configuration dict with browserbase settings
        """
        self.config = config or {}
        self.session_manager = BrowserbaseSessionManager(self.config)

        # Browserbase settings from config
        self.order_history_pages = self.config.get('order_history_pages', 5)
        self.extraction_timeout = self.config.get('extraction_timeout', 30000)
        self.wait_between_pages = self.config.get('wait_between_pages', 2000)
        self.max_retries = self.config.get('max_retries', 3)

        # Track current session
        self._session_id = None
        self._browserbase_api = None

    def get_transactions(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get Amazon transactions using Browserbase.

        This is the main entry point that:
        1. Loads/creates Browserbase session
        2. Validates Amazon login state
        3. Extracts order data
        4. Returns formatted transactions

        Args:
            start_date: Start of date range
            end_date: End of date range (default: now)

        Returns:
            List of transaction dicts matching existing format

        Raises:
            BrowserbaseAuthRequiredError: When Amazon session expired
            BrowserbaseExtractionError: When extraction fails
        """
        if not end_date:
            end_date = datetime.now()

        logger.info(f"Browserbase: Getting Amazon transactions from {start_date.date()} to {end_date.date()}")

        # Initialize Browserbase session
        self._initialize_session()

        # Navigate to Amazon and check login state
        if not self._validate_amazon_login():
            raise BrowserbaseAuthRequiredError(
                "Amazon session expired. Manual re-authentication required. "
                "Run: python src/browserbase_setup.py --login"
            )

        # Extract orders from Amazon
        try:
            orders = self._extract_order_pages(start_date, end_date)

            # Update session last_used timestamp on success
            self.session_manager.update_last_used()

            logger.info(f"Browserbase: Extracted {len(orders)} orders")
            return orders

        except Exception as e:
            logger.error(f"Browserbase extraction failed: {e}")
            raise BrowserbaseExtractionError(f"Failed to extract orders: {e}") from e

    def _initialize_session(self):
        """
        Initialize or reuse Browserbase session.

        Loads existing session ID from storage, or creates new one.
        """
        # Check for existing session
        existing_session = self.session_manager.get_session_id()

        if existing_session:
            is_valid, reason = self.session_manager.is_session_likely_valid()
            logger.info(f"Found existing session: {existing_session[:20]}... ({reason})")

            if is_valid:
                self._session_id = existing_session
                self._create_or_reuse_browserbase_session(existing_session)
                return

            logger.warning(f"Session may be invalid: {reason}")

        # Create new session
        logger.info("Creating new Browserbase session")
        self._session_id = self._create_or_reuse_browserbase_session()
        self.session_manager.save_session_id(self._session_id, {
            'created_via': 'auto_creation',
            'amazon_logged_in': False  # Will be verified
        })

    def _create_or_reuse_browserbase_session(self, session_id: str = None) -> str:
        """
        Call Browserbase to create or reuse a session.

        This method interfaces with the Browserbase MCP tools.
        In Claude Code context, MCP tools are called directly.
        In Lambda/standalone context, uses HTTP API.

        Args:
            session_id: Optional existing session ID to reuse

        Returns:
            Active session ID
        """
        # Check if we're in an MCP context (Claude Code)
        # or need to use HTTP API (Lambda)
        if os.environ.get('BROWSERBASE_API_KEY'):
            return self._create_session_via_api(session_id)
        else:
            # In MCP context, session creation is handled by the MCP server
            # Return the session ID for tracking
            return session_id or 'mcp-managed-session'

    def _create_session_via_api(self, session_id: str = None) -> str:
        """
        Create/reuse Browserbase session via HTTP API.

        Used when running outside of MCP context (e.g., Lambda).
        """
        import httpx

        api_key = os.environ.get('BROWSERBASE_API_KEY')
        if not api_key:
            raise BrowserbaseError("BROWSERBASE_API_KEY not configured")

        # Browserbase API endpoint
        api_url = "https://www.browserbase.com/v1/sessions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        if session_id:
            # Try to reuse existing session
            try:
                response = httpx.get(
                    f"{api_url}/{session_id}",
                    headers=headers,
                    timeout=30.0
                )
                if response.status_code == 200:
                    logger.info(f"Reusing existing session: {session_id[:20]}...")
                    return session_id
            except Exception as e:
                logger.warning(f"Could not reuse session: {e}")

        # Create new session
        response = httpx.post(
            api_url,
            headers=headers,
            json={"projectId": os.environ.get('BROWSERBASE_PROJECT_ID')},
            timeout=30.0
        )

        if response.status_code not in (200, 201):
            raise BrowserbaseSessionError(
                f"Failed to create session: {response.status_code} {response.text}"
            )

        data = response.json()
        new_session_id = data.get('id')
        logger.info(f"Created new Browserbase session: {new_session_id[:20]}...")
        return new_session_id

    def _validate_amazon_login(self) -> bool:
        """
        Check if we're logged in to Amazon.

        Navigates to Amazon and checks for signs of authentication.

        Returns:
            True if logged in, False if login required
        """
        logger.info("Validating Amazon login state...")

        # Navigate to Amazon order history
        self._navigate(self.AMAZON_ORDER_HISTORY_URL)

        # Extract login state indicators
        extraction = self._extract(
            "Check if the user is logged in to Amazon. "
            "Look for: 'Hello, [Name]' text in header, 'Sign in' button, "
            "or 'Your Orders' heading. "
            "Return JSON: {logged_in: boolean, user_name: string or null, indicators: [strings]}"
        )

        try:
            result = self._parse_extraction_json(extraction)

            if result.get('logged_in'):
                user_name = result.get('user_name', 'Unknown')
                logger.info(f"Amazon login validated: {user_name}")
                return True
            else:
                indicators = result.get('indicators', [])
                logger.warning(f"Not logged in. Indicators: {indicators}")
                return False

        except Exception as e:
            logger.warning(f"Could not parse login state: {e}")
            # If we can't determine, assume not logged in
            return False

    def _extract_order_pages(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """
        Extract orders from multiple pages of Amazon order history.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of order dicts
        """
        all_orders = []

        # Navigate to order history filtered by year
        year = start_date.year
        url = f"{self.AMAZON_ORDER_HISTORY_URL}?orderFilter=year-{year}"
        self._navigate(url)

        for page_num in range(self.order_history_pages):
            logger.info(f"Extracting page {page_num + 1}...")

            # Extract orders from current page
            extraction = self._extract(
                "Extract all visible orders from this Amazon order history page. "
                "For each order, extract:\n"
                "- order_id: The order number (format like 112-1234567-1234567)\n"
                "- date: Order date (format: YYYY-MM-DD)\n"
                "- total: Total amount as number (e.g., 29.99)\n"
                "- status: Delivery status (Delivered, Shipped, etc.)\n"
                "- items: Array of item names\n"
                "\n"
                "Return as JSON array: [{order_id, date, total, status, items}, ...]"
            )

            # Parse extraction result
            page_orders = self._parse_orders_extraction(extraction)

            if page_orders:
                all_orders.extend(page_orders)
                logger.info(f"Page {page_num + 1}: Found {len(page_orders)} orders")
            else:
                logger.info(f"Page {page_num + 1}: No orders found")

            # Check for and click next page
            has_next = self._check_and_click_next_page()
            if not has_next:
                logger.info("No more pages available")
                break

            # Wait between pages to avoid rate limiting
            time.sleep(self.wait_between_pages / 1000)

        # Filter by date range
        filtered_orders = self._filter_by_date_range(all_orders, start_date, end_date)

        logger.info(f"Total orders after date filter: {len(filtered_orders)}")
        return filtered_orders

    def _parse_orders_extraction(self, extraction: str) -> List[Dict]:
        """
        Parse the Stagehand extraction result into order dicts.

        Args:
            extraction: Raw extraction result from Stagehand

        Returns:
            List of parsed order dicts
        """
        try:
            orders_data = self._parse_extraction_json(extraction)

            if not isinstance(orders_data, list):
                orders_data = [orders_data] if orders_data else []

            parsed_orders = []
            for order in orders_data:
                try:
                    parsed = self._normalize_order(order)
                    if parsed:
                        parsed_orders.append(parsed)
                except Exception as e:
                    logger.warning(f"Failed to parse order: {e}")
                    continue

            return parsed_orders

        except Exception as e:
            logger.error(f"Failed to parse orders extraction: {e}")
            return []

    def _normalize_order(self, order: Dict) -> Optional[Dict]:
        """
        Normalize an extracted order to standard format.

        Args:
            order: Raw order dict from extraction

        Returns:
            Normalized order dict matching existing format
        """
        if not order:
            return None

        # Parse date
        date_str = order.get('date', '')
        try:
            if isinstance(date_str, str):
                # Try various date formats
                for fmt in ['%Y-%m-%d', '%B %d, %Y', '%m/%d/%Y', '%d %B %Y']:
                    try:
                        order_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    order_date = datetime.now()
            else:
                order_date = datetime.now()
        except Exception:
            order_date = datetime.now()

        # Parse total amount
        total = order.get('total', 0)
        if isinstance(total, str):
            # Remove currency symbols and parse
            total = re.sub(r'[^\d.]', '', total)
            try:
                total = float(total)
            except ValueError:
                total = 0.0

        # Parse items
        items = order.get('items', [])
        if isinstance(items, str):
            items = [items]

        # Build normalized order
        normalized = {
            'order_id': order.get('order_id', 'UNKNOWN'),
            'date': order_date,
            'total': float(total),
            'subtotal': float(total),  # Approximate
            'tax': 0.0,  # Not always available
            'items': [
                {
                    'name': item if isinstance(item, str) else item.get('name', 'Unknown'),
                    'category': 'Unknown',  # Not extracted
                    'asin': None,
                    'price': None,
                    'quantity': 1,
                    'link': None
                }
                for item in items
            ],
            'status': order.get('status', 'Unknown'),
            'payment_method': None,  # Not extracted
            'source': 'browserbase'
        }

        return normalized

    def _filter_by_date_range(
        self,
        orders: List[Dict],
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """
        Filter orders to only those within date range.

        Args:
            orders: List of order dicts
            start_date: Start of range
            end_date: End of range

        Returns:
            Filtered list of orders
        """
        filtered = []
        for order in orders:
            order_date = order.get('date')
            if isinstance(order_date, datetime):
                if start_date <= order_date <= end_date:
                    filtered.append(order)
        return filtered

    def _check_and_click_next_page(self) -> bool:
        """
        Check if there's a next page and click it.

        Returns:
            True if next page was clicked, False if no more pages
        """
        try:
            # Observe for next page button
            observation = self._observe(
                "Find the 'Next' pagination button or link to go to the next page of orders. "
                "Look for text like 'Next', '>' arrow, or pagination controls."
            )

            if not observation or 'not found' in str(observation).lower():
                return False

            # Click next page
            self._act("Click the 'Next' button or link to go to the next page of orders")
            return True

        except Exception as e:
            logger.debug(f"No next page: {e}")
            return False

    # --- Browserbase MCP Tool Wrappers ---

    def _navigate(self, url: str):
        """
        Navigate to a URL using Browserbase.

        In MCP context, this calls mcp__browserbase__browserbase_stagehand_navigate.
        Outside MCP, uses HTTP API or raises error.
        """
        logger.debug(f"Navigating to: {url}")

        # This is a placeholder - actual implementation depends on execution context
        # In Claude Code: MCP tool is called directly
        # In Lambda: Would use Browserbase Connect API with Playwright

        # For now, we rely on the caller (Claude Code) to make the actual MCP call
        # and this serves as documentation of the interface

        pass  # MCP call: browserbase_stagehand_navigate(url=url)

    def _extract(self, instruction: str) -> str:
        """
        Extract data using Browserbase Stagehand.

        In MCP context, this calls mcp__browserbase__browserbase_stagehand_extract.

        Args:
            instruction: Extraction instruction for Stagehand

        Returns:
            Extraction result as string
        """
        logger.debug(f"Extracting: {instruction[:50]}...")

        # Placeholder for MCP call
        pass  # MCP call: browserbase_stagehand_extract(instruction=instruction)

        return ""  # Would return actual extraction result

    def _act(self, action: str):
        """
        Perform an action using Browserbase Stagehand.

        In MCP context, this calls mcp__browserbase__browserbase_stagehand_act.

        Args:
            action: Action to perform
        """
        logger.debug(f"Acting: {action[:50]}...")

        # Placeholder for MCP call
        pass  # MCP call: browserbase_stagehand_act(action=action)

    def _observe(self, instruction: str) -> Optional[Dict]:
        """
        Observe elements using Browserbase Stagehand.

        In MCP context, this calls mcp__browserbase__browserbase_stagehand_observe.

        Args:
            instruction: Observation instruction

        Returns:
            Observation result or None
        """
        logger.debug(f"Observing: {instruction[:50]}...")

        # Placeholder for MCP call
        pass  # MCP call: browserbase_stagehand_observe(instruction=instruction)

        return None  # Would return actual observation result

    def _parse_extraction_json(self, extraction: str) -> Dict:
        """
        Parse JSON from extraction result.

        Handles various formats and cleans up the response.

        Args:
            extraction: Raw extraction string

        Returns:
            Parsed dict or list
        """
        if not extraction:
            return {}

        # Try direct JSON parse
        try:
            return json.loads(extraction)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in the string
        json_match = re.search(r'[\[{].*[\]}]', extraction, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Return empty if parsing fails
        return {}

    def close(self):
        """Close the Browserbase session (optional cleanup)."""
        # Session can be kept open for reuse
        logger.info("Browserbase scraper closed")
