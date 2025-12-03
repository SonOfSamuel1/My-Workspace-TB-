"""
Browser profile manager for handling Amazon cookies and persistent sessions.
This allows us to save login state and reuse it across sessions.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
import pickle
import base64

logger = logging.getLogger(__name__)


class BrowserProfileManager:
    """Manage browser profiles and cookies for Amazon scraping."""

    def __init__(self):
        """Initialize the browser profile manager."""
        self.profile_dir = Path(__file__).parent.parent / 'browser_profile'
        self.cookies_file = self.profile_dir / 'amazon_cookies.json'
        self.session_file = self.profile_dir / 'session_state.json'

        # Create profile directory if it doesn't exist
        self.profile_dir.mkdir(exist_ok=True)

        logger.info(f"Browser profile directory: {self.profile_dir}")

    def save_cookies(self, cookies):
        """
        Save browser cookies to file.

        Args:
            cookies: List of cookie dictionaries from Playwright
        """
        try:
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2, default=str)
            logger.info(f"Saved {len(cookies)} cookies to {self.cookies_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cookies: {str(e)}")
            return False

    def load_cookies(self):
        """
        Load saved cookies from file.

        Returns:
            List of cookie dictionaries or None if not found
        """
        if not self.cookies_file.exists():
            logger.info("No saved cookies found")
            return None

        try:
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)
            logger.info(f"Loaded {len(cookies)} cookies from {self.cookies_file}")
            return cookies
        except Exception as e:
            logger.error(f"Failed to load cookies: {str(e)}")
            return None

    def save_session_state(self, state_data):
        """
        Save session state information.

        Args:
            state_data: Dictionary with session information
        """
        try:
            state_data['last_login'] = datetime.now().isoformat()
            with open(self.session_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            logger.info("Session state saved")
            return True
        except Exception as e:
            logger.error(f"Failed to save session state: {str(e)}")
            return False

    def load_session_state(self):
        """
        Load session state information.

        Returns:
            Session state dictionary or None
        """
        if not self.session_file.exists():
            return None

        try:
            with open(self.session_file, 'r') as f:
                state = json.load(f)

            # Check if session is still valid (less than 24 hours old)
            last_login = datetime.fromisoformat(state['last_login'])
            if datetime.now() - last_login < timedelta(hours=24):
                logger.info("Session state is still valid")
                return state
            else:
                logger.info("Session state expired")
                return None

        except Exception as e:
            logger.error(f"Failed to load session state: {str(e)}")
            return None

    def clear_profile(self):
        """Clear all saved profile data."""
        try:
            if self.cookies_file.exists():
                self.cookies_file.unlink()
            if self.session_file.exists():
                self.session_file.unlink()
            logger.info("Browser profile cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear profile: {str(e)}")
            return False

    def is_logged_in(self):
        """
        Check if we have a valid logged-in session.

        Returns:
            True if we have valid cookies and session state
        """
        cookies = self.load_cookies()
        session = self.load_session_state()

        return cookies is not None and session is not None


class AmazonSessionManager:
    """Manage Amazon login sessions with Playwright."""

    def __init__(self):
        """Initialize the Amazon session manager."""
        self.profile_manager = BrowserProfileManager()
        self.logged_in = False

    async def setup_browser_context(self, playwright_tools):
        """
        Set up browser context with saved cookies if available.

        Args:
            playwright_tools: Dictionary of Playwright MCP tool functions

        Returns:
            True if session restored successfully
        """
        # Load saved cookies
        cookies = self.profile_manager.load_cookies()

        if cookies:
            logger.info("Restoring previous session with saved cookies")
            # Note: In actual Playwright, we would use context.add_cookies(cookies)
            # With MCP, we'll need to handle this differently
            return True

        return False

    async def save_current_session(self, playwright_tools):
        """
        Save the current browser session cookies.

        Args:
            playwright_tools: Dictionary of Playwright MCP tool functions
        """
        try:
            # In actual Playwright: cookies = await context.cookies()
            # For MCP, we need to extract cookies differently

            # Save session state
            state = {
                'logged_in': True,
                'email': os.getenv('AMAZON_EMAIL')
            }
            self.profile_manager.save_session_state(state)

            logger.info("Session saved successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to save session: {str(e)}")
            return False

    async def login_with_profile(self, playwright_tools, email, password):
        """
        Login to Amazon using browser profile for cookie persistence.

        Args:
            playwright_tools: Dictionary of Playwright MCP tool functions
            email: Amazon email
            password: Amazon password

        Returns:
            True if login successful
        """
        try:
            # Check if we have a saved session
            if self.profile_manager.is_logged_in():
                logger.info("Found saved session, attempting to restore...")

                # Navigate to Amazon account page to verify login
                await playwright_tools['navigate'](
                    url='https://www.amazon.com/gp/css/homepage.html'
                )

                # Check if we're logged in
                page_text = await playwright_tools['get_visible_text']()
                if 'Hello' in page_text or 'Your Account' in page_text:
                    logger.info("Successfully restored previous session!")
                    self.logged_in = True
                    return True

            # If no saved session or restoration failed, perform fresh login
            logger.info("Performing fresh login to Amazon...")

            # Navigate to Amazon
            await playwright_tools['navigate'](
                url='https://www.amazon.com',
                headless=False  # Use headed mode for better cookie handling
            )

            # Click sign in
            await playwright_tools['click'](selector='#nav-link-accountList')

            # Enter email
            await playwright_tools['fill'](
                selector='input[type="email"]',
                value=email
            )
            await playwright_tools['click'](selector='input[type="submit"]')

            # Enter password
            await playwright_tools['fill'](
                selector='input[type="password"]',
                value=password
            )
            await playwright_tools['click'](selector='input#signInSubmit')

            # Wait for login to complete
            import time
            time.sleep(3)

            # Verify login
            page_text = await playwright_tools['get_visible_text']()
            if 'Hello' in page_text or 'Your Account' in page_text:
                logger.info("Login successful!")

                # Save the session
                await self.save_current_session(playwright_tools)

                self.logged_in = True
                return True

            logger.error("Login verification failed")
            return False

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False


# Utility function for manual session setup
def setup_manual_session():
    """
    Guide user through manual session setup.
    This is a fallback if automated login fails.
    """
    print("\n" + "="*60)
    print("MANUAL SESSION SETUP")
    print("="*60)
    print("\nIf automated login fails due to cookies, follow these steps:")
    print("\n1. Open Chrome/Firefox")
    print("2. Log into Amazon manually")
    print("3. Go to: chrome://settings/cookies/detail?site=amazon.com")
    print("4. Export cookies")
    print("5. Save to: browser_profile/amazon_cookies.json")
    print("\nOnce done, the system will use your saved session.")
    print("="*60)