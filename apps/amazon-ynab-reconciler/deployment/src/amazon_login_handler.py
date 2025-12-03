#!/usr/bin/env python3
"""
Amazon login handler that uses browser profiles for persistent sessions.
This handles cookies properly to maintain login state.
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from browser_profile_manager import AmazonSessionManager


class AmazonLoginHandler:
    """Handle Amazon login with persistent sessions."""

    def __init__(self):
        """Initialize the login handler."""
        self.session_manager = AmazonSessionManager()
        self.email = os.getenv('AMAZON_EMAIL')
        self.password = os.getenv('AMAZON_PASSWORD')

    async def login_to_amazon(self):
        """
        Perform Amazon login using Playwright MCP with session persistence.
        """
        logger.info("Starting Amazon login process...")

        # We'll use the actual Playwright MCP tools here
        # First, try to navigate directly to order history
        try:
            # Navigate to order history page
            # If we have valid cookies, this should work without login
            from mcp_playwright import playwright_navigate, playwright_get_visible_text

            await playwright_navigate(
                url='https://www.amazon.com/gp/your-account/order-history',
                headless=False
            )

            # Wait for page to load
            time.sleep(3)

            # Check if we're on the order history page
            page_text = await playwright_get_visible_text()

            if 'Order' in page_text and 'Details' in page_text:
                logger.info("Successfully accessed order history!")
                return True

            # If not, we need to log in
            logger.info("Login required, proceeding with authentication...")

            # The session manager will handle the login
            playwright_tools = {
                'navigate': playwright_navigate,
                'get_visible_text': playwright_get_visible_text,
                # Add other tools as needed
            }

            success = await self.session_manager.login_with_profile(
                playwright_tools,
                self.email,
                self.password
            )

            if success:
                logger.info("Login successful with profile manager!")
                return True
            else:
                logger.error("Login failed")
                return False

        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False


async def test_login():
    """Test the Amazon login with profile management."""
    handler = AmazonLoginHandler()

    print("\n" + "="*60)
    print("AMAZON LOGIN TEST WITH BROWSER PROFILE")
    print("="*60)

    success = await handler.login_to_amazon()

    if success:
        print("\n✅ Login successful!")
        print("Session has been saved for future use.")
    else:
        print("\n❌ Login failed.")
        print("You may need to set up manual session (see instructions).")

    print("="*60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_login())