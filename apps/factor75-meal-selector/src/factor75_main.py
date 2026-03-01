#!/usr/bin/env python3
"""
Factor 75 Meal Selector - Main Entry Point

Automates weekly Factor 75 meal selection with email-based interaction:
1. Scrapes available meals from Factor 75 website
2. Sends email with meal options for user selection
3. Processes email replies to capture selections
4. Submits selections to Factor 75 website

Usage:
    python factor75_main.py --validate         # Validate configuration
    python factor75_main.py --scrape           # Scrape meals and send selection email
    python factor75_main.py --check-replies    # Check for and process email replies
    python factor75_main.py --submit           # Submit pending selections
    python factor75_main.py --test-email       # Send test email with mock data
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

import pytz
import yaml
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from factor75_scraper import (  # noqa: E402
    Factor75Scraper,
    MealOption,
    create_mock_meals_for_testing,
)
from gmail_service import GmailService  # noqa: E402
from meal_report_generator import MealReportGenerator  # noqa: E402
from reply_parser import ReplyParser, SelectionResult  # noqa: E402
from selection_submitter import SelectionSubmitter  # noqa: E402
from ses_email_sender import SESEmailSender  # noqa: E402

logger = logging.getLogger(__name__)


class Factor75MealSelector:
    """Main orchestrator for Factor 75 meal selection automation."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the meal selector.

        Args:
            config_path: Path to config.yaml file
        """
        # Load environment variables
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(env_path)

        # Load config
        self.config = self._load_config(config_path)

        # Initialize timezone
        self.timezone = pytz.timezone("America/New_York")

        # Initialize components
        self.scraper = Factor75Scraper(self.config)
        self.report_generator = MealReportGenerator(
            self.config,
            template_dir=str(Path(__file__).parent / "templates"),
        )
        self.reply_parser = ReplyParser(
            expected_count=self.config.get("factor75", {}).get("meal_count", 10)
        )
        self.submitter = SelectionSubmitter(self.config)

        # State storage path
        self.state_dir = Path(__file__).parent.parent / ".state"
        self.state_dir.mkdir(exist_ok=True)
        self.state_file = self.state_dir / "selector_state.json"

    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """Load configuration from yaml file."""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"

        if Path(config_path).exists():
            with open(config_path) as f:
                return yaml.safe_load(f) or {}

        # Return defaults
        return {
            "factor75": {
                "meal_count": 10,
            },
            "email": {
                "subject_template": "Factor 75 Meal Selection - Week of {date}",
            },
        }

    def _load_state(self) -> Dict:
        """Load selector state from file."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {}

    def _save_state(self, state: Dict):
        """Save selector state to file."""
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def validate(self) -> bool:
        """
        Validate configuration and credentials.

        Returns:
            True if all validation passes
        """
        print("\n=== Factor 75 Meal Selector - Validation ===\n")
        all_valid = True

        # Check environment variables
        print("Checking environment variables...")
        required_vars = ["FACTOR75_EMAIL", "FACTOR75_PASSWORD", "USER_EMAIL"]
        for var in required_vars:
            value = os.getenv(var)
            if value:
                masked = value[:3] + "***" if len(value) > 3 else "***"
                print(f"  {var}: {masked}")
            else:
                print(f"  {var}: MISSING")
                all_valid = False

        # Check SES configuration
        print("\nChecking AWS SES configuration...")
        ses_sender = os.getenv("SES_SENDER_EMAIL")
        if ses_sender:
            print(f"  SES_SENDER_EMAIL: {ses_sender}")
            try:
                ses = SESEmailSender()
                if ses.validate_credentials():
                    print("  SES credentials: Valid")
                else:
                    print("  SES credentials: Invalid")
                    all_valid = False
            except Exception as e:
                print(f"  SES error: {e}")
                all_valid = False
        else:
            print("  SES_SENDER_EMAIL: MISSING")
            all_valid = False

        # Check Gmail configuration
        print("\nChecking Gmail API configuration...")
        try:
            gmail = GmailService()
            if gmail.test_connection():
                email = gmail.get_user_email()
                print(f"  Gmail authenticated: {email}")
            else:
                print("  Gmail: Not authenticated")
                all_valid = False
        except FileNotFoundError:
            print("  Gmail credentials: Not found")
            print("  Run with --setup-gmail to configure")
            all_valid = False
        except Exception as e:
            print(f"  Gmail error: {e}")
            all_valid = False

        # Check config
        print("\nChecking configuration...")
        meal_count = self.config.get("factor75", {}).get("meal_count", 10)
        print(f"  Meal count: {meal_count}")

        print("\n" + "=" * 50)
        if all_valid:
            print("All validation checks passed!")
        else:
            print("Some validation checks failed. Please fix the issues above.")
        print("=" * 50 + "\n")

        return all_valid

    def scrape_and_send_email(
        self,
        no_email: bool = False,
        use_mock_data: bool = False,
    ) -> bool:
        """
        Scrape meals from Factor 75 and send selection email.

        This is designed to be called from Claude Code with Playwright MCP.
        The actual scraping will be performed by the caller using Playwright.

        Args:
            no_email: If True, skip sending email (for testing)
            use_mock_data: If True, use mock meal data instead of scraping

        Returns:
            True if successful
        """
        print("\n=== Scraping Meals and Sending Email ===\n")

        if use_mock_data:
            print("Using mock meal data for testing...")
            meals = create_mock_meals_for_testing()
            deadline = datetime.now(self.timezone) + timedelta(days=2)
            week_of = (datetime.now(self.timezone) + timedelta(days=5)).strftime(
                "%B %d"
            )
        else:
            print("To scrape Factor 75, use Playwright MCP from Claude Code:")
            print("1. Navigate to https://www.factor75.com/login")
            print("2. Fill email and password fields")
            print("3. Click login button")
            print("4. Navigate to https://www.factor75.com/menu")
            print("5. Extract page HTML")
            print("6. Pass HTML to scraper.parse_menu_html()")
            print("\nFor now, using mock data...")
            meals = create_mock_meals_for_testing()
            deadline = datetime.now(self.timezone) + timedelta(days=2)
            week_of = (datetime.now(self.timezone) + timedelta(days=5)).strftime(
                "%B %d"
            )

        print(f"\nFound {len(meals)} meals")
        print(f"Deadline: {deadline}")
        print(f"Week of: {week_of}")

        # Generate email HTML
        print("\nGenerating email...")
        html_content = self.report_generator.generate_selection_email(
            meals=meals,
            deadline=deadline,
            week_of=week_of,
        )

        subject = self.report_generator.get_subject_line(week_of)
        print(f"Subject: {subject}")

        if no_email:
            print("\n--no-email flag set, skipping email send")
            # Save HTML for review
            output_path = self.state_dir / "last_email.html"
            with open(output_path, "w") as f:
                f.write(html_content)
            print(f"Email HTML saved to: {output_path}")
            return True

        # Send email via SES
        user_email = os.getenv("USER_EMAIL")
        print(f"\nSending email to: {user_email}")

        try:
            ses = SESEmailSender()
            success = ses.send_html_email(
                to=user_email,
                subject=subject,
                html_content=html_content,
            )

            if success:
                print("Email sent successfully!")

                # Save state
                state = self._load_state()
                state["last_email_sent"] = datetime.now(self.timezone).isoformat()
                state["last_deadline"] = deadline.isoformat()
                state["week_of"] = week_of
                state["meals"] = [m.to_dict() for m in meals]
                state["selections_submitted"] = False
                self._save_state(state)

                return True
            else:
                print("Failed to send email")
                return False

        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    def check_replies(self, dry_run: bool = False) -> Optional[SelectionResult]:
        """
        Check for email replies and parse selections.

        Args:
            dry_run: If True, don't update state

        Returns:
            SelectionResult if valid reply found, None otherwise
        """
        print("\n=== Checking for Email Replies ===\n")

        state = self._load_state()

        if not state.get("last_email_sent"):
            print("No selection email has been sent yet.")
            print("Run with --scrape first to send the selection email.")
            return None

        # Check if already submitted
        if state.get("selections_submitted"):
            print("Selections have already been submitted for this week.")
            return None

        # Check deadline
        deadline_str = state.get("last_deadline")
        if deadline_str:
            deadline = datetime.fromisoformat(deadline_str)
            if datetime.now(self.timezone) > deadline:
                print("Selection deadline has passed!")
                return None

        # Search for replies
        print("Searching for reply emails...")
        try:
            gmail = GmailService()
            last_sent = datetime.fromisoformat(state["last_email_sent"])

            # Get original message ID if stored
            original_message_id = state.get("last_message_id", "")

            reply = gmail.check_for_selection_reply(
                original_message_id=original_message_id,
                since=last_sent - timedelta(hours=1),
            )

            if not reply:
                print("No reply found yet.")
                return None

            print(f"Found reply from: {reply['from']}")
            print(f"Received at: {reply['date']}")
            print(f"Content preview: {reply['snippet'][:100]}...")

            # Parse the reply
            meals = [MealOption.from_dict(m) for m in state.get("meals", [])]
            result = self.reply_parser.parse(reply["body"], meals)

            print(f"\nParsed {result.total_count} meal selections")
            print(f"Meal numbers: {result.meal_numbers}")

            if result.is_valid:
                print("\nSelections are valid!")

                if not dry_run:
                    # Store pending selections
                    state["pending_selections"] = {
                        "meal_numbers": result.meal_numbers,
                        "quantities": result.quantities,
                        "reply_received_at": datetime.now(self.timezone).isoformat(),
                    }
                    self._save_state(state)

                return result
            else:
                print("\nSelection validation failed:")
                for error in result.validation_errors:
                    print(f"  - {error}")

                # TODO: Send clarification email
                return None

        except Exception as e:
            print(f"Error checking replies: {e}")
            return None

    def submit_selections(self, dry_run: bool = False) -> bool:
        """
        Submit pending selections to Factor 75.

        This generates instructions for Playwright MCP to perform the submission.

        Args:
            dry_run: If True, don't actually submit

        Returns:
            True if successful
        """
        print("\n=== Submitting Selections ===\n")

        state = self._load_state()
        pending = state.get("pending_selections")

        if not pending:
            print("No pending selections to submit.")
            print("Run --check-replies first to process a reply.")
            return False

        meal_numbers = pending["meal_numbers"]
        quantities = pending["quantities"]

        print(f"Pending selections: {meal_numbers}")
        print(f"Quantities: {quantities}")

        if dry_run:
            print("\n--dry-run flag set, not submitting")
            return True

        # Get submission instructions for Playwright
        instructions = self.submitter.get_submission_instructions(
            meal_numbers=meal_numbers,
            quantities=quantities,
        )

        print("\nTo submit selections, use Playwright MCP from Claude Code:")
        print("1. Navigate to Factor 75 menu page")
        print("2. Authenticate if needed")
        print(f"3. Select meals: {meal_numbers}")
        print("4. Click confirm/save button")
        print("\nInstructions JSON:")
        print(json.dumps(instructions, indent=2))

        # For now, mark as submitted (in production, verify with Playwright)
        state["selections_submitted"] = True
        state["submitted_at"] = datetime.now(self.timezone).isoformat()
        self._save_state(state)

        # Send confirmation email
        meals = [MealOption.from_dict(m) for m in state.get("meals", [])]
        selected_meals = []
        for num, qty in quantities.items():
            if 1 <= int(num) <= len(meals):
                selected_meals.extend([meals[int(num) - 1]] * qty)

        html = self.report_generator.generate_confirmation_email(
            selected_meals=selected_meals,
            week_of=state.get("week_of"),
        )

        user_email = os.getenv("USER_EMAIL")
        ses = SESEmailSender()
        ses.send_html_email(
            to=user_email,
            subject=f"Factor 75 Meals Confirmed - {state.get('week_of', 'This Week')}",
            html_content=html,
        )

        print("\nSelections submitted and confirmation email sent!")
        return True

    def send_test_email(self) -> bool:
        """
        Send a test email with mock data.

        Returns:
            True if successful
        """
        print("\n=== Sending Test Email ===\n")

        meals = create_mock_meals_for_testing()
        deadline = datetime.now(self.timezone) + timedelta(days=2)
        week_of = (datetime.now(self.timezone) + timedelta(days=5)).strftime("%B %d")

        html = self.report_generator.generate_selection_email(
            meals=meals,
            deadline=deadline,
            week_of=week_of,
        )

        user_email = os.getenv("USER_EMAIL")
        subject = f"[TEST] {self.report_generator.get_subject_line(week_of)}"

        print(f"Sending test email to: {user_email}")

        try:
            ses = SESEmailSender()
            success = ses.send_html_email(
                to=user_email,
                subject=subject,
                html_content=html,
            )

            if success:
                print("Test email sent successfully!")
                print("Check your inbox and try replying with meal numbers.")
                return True
            else:
                print("Failed to send test email")
                return False

        except Exception as e:
            print(f"Error: {e}")
            return False


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Factor 75 Meal Selector - Automate meal selection with email",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python factor75_main.py --validate           # Check configuration
  python factor75_main.py --scrape             # Scrape meals and send email
  python factor75_main.py --scrape --no-email  # Scrape without sending
  python factor75_main.py --check-replies      # Process email replies
  python factor75_main.py --submit             # Submit selections
  python factor75_main.py --test-email         # Send test email
        """,
    )

    parser.add_argument(
        "--validate", action="store_true", help="Validate configuration and credentials"
    )
    parser.add_argument(
        "--scrape", action="store_true", help="Scrape meals and send selection email"
    )
    parser.add_argument(
        "--check-replies",
        action="store_true",
        help="Check for and process email replies",
    )
    parser.add_argument(
        "--submit", action="store_true", help="Submit pending selections to Factor 75"
    )
    parser.add_argument(
        "--test-email", action="store_true", help="Send test email with mock data"
    )
    parser.add_argument(
        "--no-email", action="store_true", help="Skip email sending (for testing)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Do not make actual changes"
    )
    parser.add_argument(
        "--mock-data",
        action="store_true",
        help="Use mock meal data instead of scraping",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--config", type=str, default=None, help="Path to config.yaml file"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # If no action specified, show help
    if not any(
        [args.validate, args.scrape, args.check_replies, args.submit, args.test_email]
    ):
        parser.print_help()
        return 1

    # Initialize selector
    selector = Factor75MealSelector(config_path=args.config)

    # Execute requested action(s)
    if args.validate:
        success = selector.validate()
        return 0 if success else 1

    if args.test_email:
        success = selector.send_test_email()
        return 0 if success else 1

    if args.scrape:
        success = selector.scrape_and_send_email(
            no_email=args.no_email,
            use_mock_data=args.mock_data,
        )
        return 0 if success else 1

    if args.check_replies:
        result = selector.check_replies(dry_run=args.dry_run)
        return 0 if result and result.is_valid else 1

    if args.submit:
        success = selector.submit_selections(dry_run=args.dry_run)
        return 0 if success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
