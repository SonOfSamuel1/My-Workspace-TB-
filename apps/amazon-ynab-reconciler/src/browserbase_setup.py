#!/usr/bin/env python3
"""
Browserbase session setup utility for Amazon-YNAB Reconciler.

This CLI tool helps manage Browserbase sessions for automated Amazon scraping.
Run this locally to authenticate with Amazon and create a persistent session
that can be reused by Lambda or automated runs.

Usage:
    python browserbase_setup.py --login     # Set up a new session with Amazon login
    python browserbase_setup.py --check     # Check current session status
    python browserbase_setup.py --clear     # Clear stored session
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from browserbase_session_manager import BrowserbaseSessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_status(label: str, value: str, success: bool = True):
    """Print a status line with checkmark or X."""
    symbol = "✓" if success else "✗"
    print(f"  {symbol} {label}: {value}")


def setup_session_interactive():
    """
    Interactive session setup.

    This guides the user through creating a Browserbase session
    and logging in to Amazon for persistent automation.
    """
    print_header("BROWSERBASE SESSION SETUP FOR AMAZON")

    manager = BrowserbaseSessionManager()

    # Check for existing session
    existing = manager.get_session_id()
    if existing:
        is_valid, reason = manager.is_session_likely_valid()
        print(f"\nExisting session found: {existing[:20]}...")
        print(f"Status: {'Valid' if is_valid else 'May need re-authentication'}")
        print(f"Reason: {reason}")

        response = input("\nUse existing session? (y/n): ").strip().lower()
        if response == 'y':
            print("\nUsing existing session. Run --check to verify it's working.")
            return

    print("\n" + "-" * 60)
    print("SETUP INSTRUCTIONS")
    print("-" * 60)
    print("""
This tool helps you create a persistent Browserbase session for Amazon.

Since Amazon has strong anti-bot detection and often requires 2FA,
the recommended workflow is:

1. Create a Browserbase session in headed (visible) mode
2. Manually log in to Amazon through the browser
3. Save the session ID for automated reuse

The session typically stays valid for 7-14 days before needing re-authentication.
    """)

    input("Press Enter to continue...")

    print("\n" + "-" * 60)
    print("STEP 1: CREATE BROWSERBASE SESSION")
    print("-" * 60)

    # Check for Browserbase API key
    api_key = os.environ.get('BROWSERBASE_API_KEY')
    if not api_key:
        print("\n⚠️  BROWSERBASE_API_KEY not found in environment.")
        print("    Set it in your .env file or export it:")
        print("    export BROWSERBASE_API_KEY='your-api-key'")
        print("\n    Get your API key from: https://www.browserbase.com/settings/api-keys")

        api_key = input("\nEnter your Browserbase API key (or press Enter to skip): ").strip()
        if api_key:
            os.environ['BROWSERBASE_API_KEY'] = api_key

    if api_key:
        print("\nAttempting to create Browserbase session...")

        # Try to create session via API
        try:
            import httpx

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            # Create a headed session
            response = httpx.post(
                "https://www.browserbase.com/v1/sessions",
                headers=headers,
                json={
                    "projectId": os.environ.get('BROWSERBASE_PROJECT_ID'),
                    "browserSettings": {
                        "headless": False  # Headed mode for manual login
                    }
                },
                timeout=30.0
            )

            if response.status_code in (200, 201):
                data = response.json()
                session_id = data.get('id')
                connect_url = data.get('connectUrl')

                print(f"\n✓ Session created: {session_id[:20]}...")

                if connect_url:
                    print(f"\nConnect URL: {connect_url}")
                    print("\nOpen this URL in your browser or use Playwright to connect.")

                print("\n" + "-" * 60)
                print("STEP 2: LOG IN TO AMAZON")
                print("-" * 60)
                print("""
In the Browserbase session:
1. Navigate to: https://www.amazon.com
2. Click 'Sign In'
3. Enter your Amazon credentials
4. Complete any 2FA challenges
5. Verify you see 'Hello, [Your Name]' in the header
                """)

                input("Press Enter after you've logged in to Amazon...")

                # Save the session
                manager.save_session_id(session_id, {
                    'created_via': 'setup_cli',
                    'amazon_logged_in': True,
                    'created_at': datetime.now().isoformat()
                })

                print(f"\n✓ Session saved successfully!")
                print(f"\nYou can now use --use-browserbase flag with the reconciler:")
                print("  python src/reconciler_main.py --use-browserbase --dry-run --days 7")

                return

            else:
                print(f"\n✗ Failed to create session: {response.status_code}")
                print(f"  {response.text}")

        except ImportError:
            print("\n⚠️  httpx not installed. Install with: pip install httpx")
        except Exception as e:
            print(f"\n✗ Error creating session: {e}")

    # Manual fallback
    print("\n" + "-" * 60)
    print("MANUAL SESSION SETUP")
    print("-" * 60)
    print("""
If automatic session creation didn't work, you can set up manually:

1. Go to Browserbase dashboard: https://www.browserbase.com
2. Create a new session (select 'Headed' mode)
3. Navigate to Amazon and log in
4. Copy the session ID from the dashboard
    """)

    session_id = input("\nEnter the Browserbase session ID: ").strip()

    if session_id:
        manager.save_session_id(session_id, {
            'created_via': 'manual_entry',
            'amazon_logged_in': True,
            'created_at': datetime.now().isoformat()
        })
        print(f"\n✓ Session saved successfully!")
        print(f"Session ID: {session_id[:20]}...")
    else:
        print("\nNo session ID provided. Setup cancelled.")


def check_session():
    """Check and display current session status."""
    print_header("BROWSERBASE SESSION STATUS")

    manager = BrowserbaseSessionManager()

    session_id = manager.get_session_id()
    if not session_id:
        print("\n✗ No Browserbase session configured.")
        print("\nRun with --login to set up a session.")
        return

    print(f"\nSession ID: {session_id[:20]}...")

    metadata = manager.get_session_metadata()
    if metadata:
        print(f"\nMetadata:")
        print(f"  Created: {metadata.get('created_at', 'Unknown')}")
        print(f"  Last Used: {metadata.get('last_used', 'Unknown')}")
        print(f"  Use Count: {metadata.get('use_count', 0)}")
        print(f"  Created Via: {metadata.get('created_via', 'Unknown')}")
        print(f"  Amazon Logged In: {metadata.get('amazon_logged_in', 'Unknown')}")

    is_valid, reason = manager.is_session_likely_valid()
    print(f"\nValidity Check:")
    print_status("Status", "VALID" if is_valid else "MAY NEED RE-AUTH", is_valid)
    print(f"  Reason: {reason}")

    if not is_valid:
        print("\n💡 Tip: Run with --login to create a new session.")


def clear_session():
    """Clear the stored session after confirmation."""
    print_header("CLEAR BROWSERBASE SESSION")

    manager = BrowserbaseSessionManager()

    session_id = manager.get_session_id()
    if not session_id:
        print("\nNo session to clear.")
        return

    print(f"\nCurrent session: {session_id[:20]}...")

    response = input("\nAre you sure you want to clear this session? (yes/no): ").strip().lower()
    if response == 'yes':
        if manager.clear_session():
            print("\n✓ Session cleared successfully.")
        else:
            print("\n✗ Failed to clear session.")
    else:
        print("\nCancelled.")


def upload_to_parameter_store():
    """Upload current session to AWS Parameter Store."""
    print_header("UPLOAD SESSION TO AWS PARAMETER STORE")

    manager = BrowserbaseSessionManager()

    session_id = manager.get_session_id()
    if not session_id:
        print("\nNo local session found. Run --login first.")
        return

    metadata = manager.get_session_metadata()

    print(f"\nSession to upload: {session_id[:20]}...")

    response = input("\nUpload to Parameter Store? (yes/no): ").strip().lower()
    if response != 'yes':
        print("Cancelled.")
        return

    try:
        import boto3
        import json

        ssm = boto3.client('ssm', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

        data = {
            'session_id': session_id,
            **(metadata or {}),
            'uploaded_at': datetime.now().isoformat()
        }

        ssm.put_parameter(
            Name='/amazon-reconciler/browserbase-session-id',
            Value=json.dumps(data),
            Type='SecureString',
            Overwrite=True
        )

        print("\n✓ Session uploaded to Parameter Store!")
        print("  The Lambda function will now use this session.")

    except Exception as e:
        print(f"\n✗ Failed to upload: {e}")
        print("\n  Make sure you have AWS credentials configured.")


def main():
    parser = argparse.ArgumentParser(
        description='Browserbase session management for Amazon-YNAB Reconciler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --login       Set up a new Browserbase session with Amazon login
  %(prog)s --check       Check current session status
  %(prog)s --clear       Clear the stored session
  %(prog)s --upload      Upload local session to AWS Parameter Store

For automated Lambda runs, the session is stored in Parameter Store.
For local runs, it's stored in data/browserbase_session.json.
        """
    )

    parser.add_argument(
        '--login', '-l',
        action='store_true',
        help='Set up a new Browserbase session with Amazon login'
    )
    parser.add_argument(
        '--check', '-c',
        action='store_true',
        help='Check current session status'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear the stored session'
    )
    parser.add_argument(
        '--upload', '-u',
        action='store_true',
        help='Upload local session to AWS Parameter Store'
    )

    args = parser.parse_args()

    if args.login:
        setup_session_interactive()
    elif args.check:
        check_session()
    elif args.clear:
        clear_session()
    elif args.upload:
        upload_to_parameter_store()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
