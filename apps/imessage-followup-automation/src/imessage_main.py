#!/usr/bin/env python3
"""
Main entry point for iMessage Follow-up Automation

This script orchestrates the iMessage follow-up system,
analyzing conversations and sending email notifications.
"""

import os
import sys
import logging
import yaml
import argparse
from datetime import datetime
from pathlib import Path
import pytz

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from imessage_service import iMessageService
from message_analyzer import MessageAnalyzer
from action_recommender import ActionRecommender
from state_tracker import StateTracker
from report_generator import ReportGenerator
from email_sender import EmailSender


def setup_logging(config: dict):
    """Setup logging configuration."""
    log_config = config.get('logging', {})

    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = log_config.get('file', 'logs/imessage_followup.log')

    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def load_config() -> dict:
    """Load configuration from config.yaml."""
    config_path = Path('config.yaml')

    if not config_path.exists():
        raise FileNotFoundError(
            "Configuration file 'config.yaml' not found. "
            "Please create it from the template."
        )

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config


def load_environment():
    """Load environment variables from .env file."""
    env_path = Path('.env')

    if not env_path.exists():
        raise FileNotFoundError(
            "Environment file '.env' not found. "
            "Please create it from .env.example"
        )

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()


def validate_configuration(config: dict) -> bool:
    """
    Validate that required configuration is present.

    Args:
        config: Configuration dictionary

    Returns:
        True if valid, False otherwise
    """
    logger = logging.getLogger(__name__)

    # Check required environment variables
    required_env_vars = [
        'ANTHROPIC_API_KEY',
        'IMESSAGE_FOLLOWUP_EMAIL',
        'GOOGLE_CREDENTIALS_FILE'
    ]

    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please update your .env file with these values")
        return False

    # Check if enabled
    if not config.get('imessage_followup', {}).get('enabled'):
        logger.warning("iMessage follow-up is disabled in config.yaml")
        return False

    logger.info("Configuration validation passed")
    return True


def initialize_services(config: dict):
    """
    Initialize all required services.

    Args:
        config: Configuration dictionary

    Returns:
        Tuple of services
    """
    logger = logging.getLogger(__name__)
    followup_config = config['imessage_followup']

    # Initialize iMessage Service
    logger.info("Initializing iMessage Service...")
    db_path = os.getenv(
        'IMESSAGE_DB_PATH',
        followup_config.get('imessage_db_path')
    )
    if db_path:
        db_path = os.path.expanduser(db_path)

    imessage_service = iMessageService(db_path)

    # Initialize Message Analyzer
    logger.info("Initializing Message Analyzer...")
    analyzer = MessageAnalyzer(followup_config)

    # Initialize Action Recommender
    logger.info("Initializing Action Recommender...")
    recommender = ActionRecommender(followup_config)

    # Initialize State Tracker
    logger.info("Initializing State Tracker...")
    state_db_path = followup_config.get('state', {}).get('database_path', 'data/imessage_state.db')
    retention_days = followup_config.get('state', {}).get('retention_days', 30)
    state_tracker = StateTracker(state_db_path, retention_days)

    # Initialize Report Generator
    logger.info("Initializing Report Generator...")
    report_generator = ReportGenerator(followup_config)

    # Initialize Email Sender
    logger.info("Initializing Email Sender...")
    credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials/credentials.json')
    token_file = os.getenv('GOOGLE_TOKEN_FILE', 'credentials/token.pickle')
    email_sender = EmailSender(credentials_file, token_file)

    logger.info("All services initialized successfully")

    return (
        imessage_service,
        analyzer,
        recommender,
        state_tracker,
        report_generator,
        email_sender
    )


def check_and_notify(config: dict, send_email: bool = True, force: bool = False):
    """
    Check for messages needing follow-up and send notifications.

    Args:
        config: Configuration dictionary
        send_email: Whether to send email notification
        force: Force notification even if already notified
    """
    logger = logging.getLogger(__name__)

    try:
        # Initialize services
        (
            imessage_service,
            analyzer,
            recommender,
            state_tracker,
            report_generator,
            email_sender
        ) = initialize_services(config)

        followup_config = config['imessage_followup']

        # Get recent conversations
        logger.info("Fetching recent conversations...")
        lookback_hours = followup_config.get('lookback_hours', 48)
        exclude_group_chats = followup_config.get('exclude_group_chats', False)
        priority_contacts = followup_config.get('priority_contacts', [])

        conversations = imessage_service.get_conversations(
            lookback_hours=lookback_hours,
            exclude_group_chats=exclude_group_chats,
            priority_contacts=priority_contacts
        )

        logger.info(f"Found {len(conversations)} conversations")

        # Analyze conversations
        logger.info("Analyzing conversations...")
        follow_up_items = analyzer.analyze_conversations(conversations)

        logger.info(f"Identified {len(follow_up_items)} conversations needing follow-up")

        # Filter out already-notified items (unless force mode)
        if not force:
            renotify_days = followup_config.get('state', {}).get('renotify_after_days', 3)
            filtered_items = []

            for item in follow_up_items:
                if state_tracker.should_notify(
                    item.conversation.chat_id,
                    item.conversation.last_message.date,
                    renotify_days
                ):
                    filtered_items.append(item)

            logger.info(f"After filtering duplicates: {len(filtered_items)} items")
            follow_up_items = filtered_items

        # If no items, optionally send daily summary
        if not follow_up_items:
            send_daily = followup_config.get('email', {}).get('send_daily_summary', False)

            if not send_daily:
                print("\n✅ No new messages requiring follow-up!")
                logger.info("No follow-up items found")
                return

            print("\n📬 No urgent messages, but sending daily summary...")

        # Generate recommendations for each item
        logger.info("Generating AI recommendations...")
        recommendations_by_item = {}

        for item in follow_up_items:
            recommendations = recommender.generate_recommendations(item)
            recommendations_by_item[item] = recommendations

        # Generate HTML report
        logger.info("Generating email report...")
        html_content = report_generator.generate_html_report(
            follow_up_items,
            recommendations_by_item
        )

        # Save HTML to file for review
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'imessage_followup_{timestamp}.html'

        with open(output_file, 'w') as f:
            f.write(html_content)

        logger.info(f"Report saved to: {output_file}")
        print(f"\n✅ Report generated successfully!")
        print(f"📄 Saved to: {output_file}")

        # Send email if requested
        if send_email:
            recipient = os.getenv(
                'IMESSAGE_FOLLOWUP_EMAIL',
                followup_config.get('email', {}).get('recipient')
            )

            if not recipient:
                logger.error("No email recipient configured")
                print("\n⚠️  Email not sent: No recipient configured")
                return

            logger.info(f"Sending email to {recipient}...")

            # Generate subject
            now = datetime.now(pytz.timezone(followup_config.get('timezone', 'America/New_York')))
            subject_template = followup_config.get('email', {}).get(
                'subject_template',
                'iMessage Follow-up Reminders - {date}'
            )
            subject = subject_template.format(date=now.strftime('%B %d, %Y'))

            # Send email
            success = email_sender.send_html_email(
                to=recipient,
                subject=subject,
                html_content=html_content
            )

            if success:
                print(f"📧 Email sent successfully to {recipient}")
                logger.info(f"Email sent successfully to {recipient}")

                # Record notifications in state tracker
                for item in follow_up_items:
                    state_tracker.record_notification(
                        item.conversation.chat_id,
                        item.contact_name,
                        item.conversation.last_message.date,
                        item.priority,
                        item.reason
                    )

            else:
                print(f"\n❌ Failed to send email to {recipient}")
                logger.error(f"Failed to send email to {recipient}")

        # Print summary
        print(f"\n{'='*60}")
        print("FOLLOW-UP SUMMARY")
        print(f"{'='*60}")

        urgent = [i for i in follow_up_items if i.priority == 'urgent']
        high = [i for i in follow_up_items if i.priority == 'high']
        medium = [i for i in follow_up_items if i.priority == 'medium']
        low = [i for i in follow_up_items if i.priority == 'low']

        print(f"🚨 Urgent: {len(urgent)}")
        print(f"⚠️  High Priority: {len(high)}")
        print(f"📌 Medium Priority: {len(medium)}")
        print(f"💬 Low Priority: {len(low)}")

        if urgent or high:
            print(f"\n⚠️  PRIORITY ITEMS NEED ATTENTION:")
            for item in (urgent + high)[:5]:
                print(f"   • {item.contact_name}: {item.reason}")

        # State tracker stats
        stats = state_tracker.get_stats()
        print(f"\n📊 State Tracker Stats:")
        print(f"   • Unresolved notifications: {stats['unresolved']}")
        print(f"   • Notifications last week: {stats['last_week']}")

        print(f"{'='*60}\n")

        # Cleanup old state records
        state_tracker.cleanup_old_records()

    except Exception as e:
        logger.error(f"Error during follow-up check: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


def validate_setup():
    """Validate that all services are properly configured."""
    logger = logging.getLogger(__name__)

    print("\n" + "="*60)
    print("iMESSAGE FOLLOW-UP AUTOMATION - SETUP VALIDATION")
    print("="*60 + "\n")

    try:
        # Load config
        print("📋 Loading configuration...")
        config = load_config()
        print("✅ Config loaded")

        # Load environment
        print("🔐 Loading environment variables...")
        load_environment()
        print("✅ Environment loaded")

        # Validate configuration
        print("✔️  Validating configuration...")
        if not validate_configuration(config):
            print("❌ Configuration validation failed")
            return False
        print("✅ Configuration valid")

        followup_config = config['imessage_followup']

        # Test iMessage database access
        print("\n📱 Testing iMessage database access...")
        db_path = os.getenv(
            'IMESSAGE_DB_PATH',
            followup_config.get('imessage_db_path')
        )
        if db_path:
            db_path = os.path.expanduser(db_path)

        imessage_service = iMessageService(db_path)

        if imessage_service.validate_database():
            print("✅ iMessage database accessible")
        else:
            print("❌ iMessage database not accessible")
            return False

        # Test Anthropic API
        print("🤖 Testing Anthropic Claude API...")
        if os.getenv('ANTHROPIC_API_KEY'):
            print("✅ Anthropic API key found")
        else:
            print("⚠️  Anthropic API key not found - AI analysis will be disabled")

        # Test Gmail service
        print("📧 Testing Gmail connection...")
        credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials/credentials.json')
        token_file = os.getenv('GOOGLE_TOKEN_FILE', 'credentials/token.pickle')

        email_sender = EmailSender(credentials_file, token_file)

        if email_sender.validate_credentials():
            print("✅ Gmail connection successful")
        else:
            print("❌ Gmail connection failed")
            return False

        # Test state tracker
        print("💾 Testing state tracker...")
        state_db_path = followup_config.get('state', {}).get('database_path', 'data/imessage_state.db')
        state_tracker = StateTracker(state_db_path, 30)
        stats = state_tracker.get_stats()
        print(f"✅ State tracker initialized (total notifications: {stats['total_notifications']})")

        print("\n" + "="*60)
        print("✅ ALL VALIDATIONS PASSED!")
        print("="*60 + "\n")

        print("Next steps:")
        print("1. Run: python src/imessage_main.py --check")
        print("2. Or set up scheduler for automatic checks")
        print("3. Configure cron or AWS EventBridge for periodic execution\n")

        return True

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        print(f"\n❌ Validation failed: {str(e)}\n")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='iMessage Follow-up Automation'
    )

    parser.add_argument(
        '--check',
        action='store_true',
        help='Check for messages needing follow-up and send notification'
    )

    parser.add_argument(
        '--no-email',
        action='store_true',
        help='Generate report but do not send email'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force notification even if already notified recently'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate setup and configuration'
    )

    args = parser.parse_args()

    # Load config
    config = load_config()

    # Setup logging
    setup_logging(config)

    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("Starting iMessage Follow-up Automation")
    logger.info("="*60)

    # Load environment
    load_environment()

    if args.validate:
        # Run validation
        sys.exit(0 if validate_setup() else 1)

    elif args.check:
        # Validate first
        if not validate_configuration(config):
            sys.exit(1)

        # Check and notify
        send_email = not args.no_email
        check_and_notify(config, send_email=send_email, force=args.force)

    else:
        # Default: show help
        parser.print_help()
        print("\nExamples:")
        print("  python src/imessage_main.py --validate")
        print("  python src/imessage_main.py --check")
        print("  python src/imessage_main.py --check --no-email")
        print("  python src/imessage_main.py --check --force")


if __name__ == '__main__':
    main()
