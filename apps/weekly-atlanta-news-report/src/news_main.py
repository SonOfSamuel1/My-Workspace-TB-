#!/usr/bin/env python3
"""
Main entry point for Weekly Atlanta News Report

This script orchestrates the news reporting system,
fetching Atlanta news from RSS feeds and generating
weekly email digests.
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

# Use python-dotenv for proper .env loading
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

from news_fetcher import NewsFetcher
from news_analyzer import NewsAnalyzer
from news_report import NewsReportGenerator

# Import SES email sender (preferred for automated emails)
try:
    from ses_email_sender import SESEmailSender
    HAS_SES = True
except ImportError:
    SESEmailSender = None
    HAS_SES = False


def setup_logging(config: dict):
    """Setup logging configuration."""
    log_config = config.get('logging', {})

    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = log_config.get('file', 'logs/atlanta_news.log')

    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

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
    # Try multiple locations
    config_paths = [
        Path('config.yaml'),
        Path(__file__).parent.parent / 'config.yaml',
    ]

    for config_path in config_paths:
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)

    raise FileNotFoundError(
        "Configuration file 'config.yaml' not found. "
        "Please create it from the template."
    )


def load_environment():
    """Load environment variables from .env file."""
    env_paths = [
        Path('.env'),
        Path(__file__).parent.parent / '.env',
    ]

    for env_path in env_paths:
        if env_path.exists():
            if HAS_DOTENV:
                load_dotenv(env_path)
                logging.info(f"Environment loaded from {env_path}")
                return
            else:
                # Manual parsing fallback
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            value = value.strip().strip('"\'')
                            os.environ[key.strip()] = value
                logging.info(f"Environment loaded manually from {env_path}")
                return

    logging.warning("No .env file found. Using environment variables only.")


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
    required_env_vars = ['ATLANTA_NEWS_EMAIL']
    missing_vars = []

    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please update your .env file with these values")
        return False

    # Check news report enabled
    if not config.get('atlanta_news_report', {}).get('enabled'):
        logger.warning("Atlanta news reporting is disabled in config.yaml")
        return False

    # Check feeds configured
    feeds = config.get('atlanta_news_report', {}).get('feeds', [])
    if not feeds:
        logger.error("No RSS feeds configured in config.yaml")
        return False

    logger.info("Configuration validation passed")
    return True


def generate_report(config: dict, send_email: bool = True):
    """
    Generate and optionally send news report.

    Args:
        config: Configuration dictionary
        send_email: Whether to send the report via email
    """
    logger = logging.getLogger(__name__)

    try:
        news_config = config['atlanta_news_report']
        timezone = pytz.timezone(news_config.get('timezone', 'America/New_York'))

        # Step 1: Fetch news from RSS feeds
        logger.info("Fetching news from RSS feeds...")
        fetcher = NewsFetcher(
            feeds_config=news_config['feeds'],
            timezone=news_config.get('timezone', 'America/New_York')
        )
        articles = fetcher.fetch_all_feeds()
        logger.info(f"Fetched {len(articles)} articles from {len(news_config['feeds'])} feeds")

        if not articles:
            logger.warning("No articles fetched. Check RSS feed configuration.")
            print("\n[WARNING] No articles fetched from RSS feeds.")
            return

        # Step 2: Analyze and process articles
        logger.info("Processing articles...")
        analyzer = NewsAnalyzer(news_config)
        processed_news = analyzer.process_articles(articles)

        # Step 3: Generate HTML report
        logger.info("Generating HTML report...")
        report_generator = NewsReportGenerator(news_config)
        html_content = report_generator.generate_html_report(processed_news)

        # Step 4: Save HTML to file for review
        if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
            output_dir = Path('/tmp')
        else:
            output_dir = Path(__file__).parent.parent / 'output'
            output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'atlanta_news_{timestamp}.html'

        with open(output_file, 'w') as f:
            f.write(html_content)

        logger.info(f"Report saved to: {output_file}")
        print(f"\n[OK] Report generated successfully!")
        print(f"[FILE] Saved to: {output_file}")

        # Step 5: Send email if requested
        if send_email:
            if not HAS_SES:
                logger.error("SES email sender not available")
                print("\n[ERROR] Email functionality not available")
                return

            recipient = os.getenv('ATLANTA_NEWS_EMAIL')
            if not recipient:
                logger.error("No email recipient configured (ATLANTA_NEWS_EMAIL)")
                print("\n[WARNING] Email not sent: No recipient configured")
                return

            logger.info(f"Sending email to {recipient}...")

            email_sender = SESEmailSender(
                region=os.getenv('AWS_REGION', 'us-east-1'),
                sender_email=os.getenv('SES_SENDER_EMAIL', 'brandonhome.appdev@gmail.com')
            )

            subject = report_generator.generate_subject(processed_news)
            plain_text = report_generator.generate_plain_text(processed_news)

            success = email_sender.send_html_email(
                to=recipient,
                subject=subject,
                html_content=html_content,
                text_content=plain_text
            )

            if success:
                print(f"[EMAIL] Email sent successfully to {recipient}")
                logger.info(f"Email sent successfully to {recipient}")
            else:
                print(f"\n[ERROR] Failed to send email to {recipient}")
                logger.error(f"Failed to send email to {recipient}")

        # Print summary
        print(f"\n{'='*60}")
        print("ATLANTA NEWS REPORT SUMMARY")
        print(f"{'='*60}")

        stats = analyzer.get_statistics(processed_news)

        print(f"\n[STATS] Article Statistics:")
        print(f"   Total Articles: {stats['total_articles']}")
        print(f"   Top Stories: {stats['top_stories']}")
        print(f"   General News: {stats['general_news']}")
        print(f"   Business News: {stats['business_news']}")
        print(f"   Duplicates Removed: {stats['duplicates_removed']}")

        print(f"\n[SOURCES] By Source:")
        for source, count in stats['sources'].items():
            print(f"   {source}: {count} articles")

        print(f"\n[PERIOD] Report Period:")
        print(f"   {stats['period']['start']} to {stats['period']['end']} ({stats['period']['days']} days)")

        print(f"{'='*60}\n")

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        print(f"\n[ERROR] {str(e)}")
        sys.exit(1)


def test_feeds(config: dict):
    """Test connectivity to all configured RSS feeds."""
    logger = logging.getLogger(__name__)

    print("\n" + "="*60)
    print("TESTING RSS FEEDS")
    print("="*60 + "\n")

    news_config = config['atlanta_news_report']
    fetcher = NewsFetcher(
        feeds_config=news_config['feeds'],
        timezone=news_config.get('timezone', 'America/New_York')
    )

    results = fetcher.test_feeds()

    success_count = 0
    fail_count = 0

    for name, result in results.items():
        if result['status'] == 'ok':
            print(f"[OK] {name}: {result['entries']} entries")
            success_count += 1
        else:
            print(f"[FAIL] {name}: {result['error']}")
            fail_count += 1

    print("\n" + "="*60)
    print(f"Results: {success_count} OK, {fail_count} Failed")
    print("="*60 + "\n")

    return fail_count == 0


def validate_setup():
    """Validate that all services are properly configured."""
    logger = logging.getLogger(__name__)

    print("\n" + "="*60)
    print("ATLANTA NEWS REPORT SETUP VALIDATION")
    print("="*60 + "\n")

    try:
        # Load config
        print("[CHECK] Loading configuration...")
        config = load_config()
        print("[OK] Config loaded")

        # Load environment
        print("[CHECK] Loading environment variables...")
        load_environment()
        print("[OK] Environment loaded")

        # Validate configuration
        print("[CHECK] Validating configuration...")
        if not validate_configuration(config):
            print("[FAIL] Configuration validation failed")
            return False
        print("[OK] Configuration valid")

        # Test RSS feeds
        print("\n[CHECK] Testing RSS feeds...")
        news_config = config['atlanta_news_report']
        fetcher = NewsFetcher(
            feeds_config=news_config['feeds'],
            timezone=news_config.get('timezone', 'America/New_York')
        )

        results = fetcher.test_feeds()
        working_feeds = sum(1 for r in results.values() if r['status'] == 'ok')
        total_feeds = len(results)
        print(f"[OK] RSS feeds: {working_feeds}/{total_feeds} working")

        if working_feeds == 0:
            print("[WARNING] No RSS feeds are working!")
            return False

        # Test SES (if available)
        if HAS_SES:
            print("\n[CHECK] Testing AWS SES connection...")
            email_sender = SESEmailSender(
                region=os.getenv('AWS_REGION', 'us-east-1'),
                sender_email=os.getenv('SES_SENDER_EMAIL', 'brandonhome.appdev@gmail.com')
            )
            if email_sender.validate_credentials():
                print("[OK] AWS SES connection successful")
            else:
                print("[WARNING] AWS SES connection failed")
        else:
            print("\n[WARNING] SES email sender not available - email disabled")

        print("\n" + "="*60)
        print("[OK] ALL VALIDATIONS PASSED!")
        print("="*60 + "\n")

        print("Next steps:")
        print("1. Update .env with ATLANTA_NEWS_EMAIL")
        print("2. Run: python src/news_main.py --generate")
        print("3. Or set up AWS Lambda for automatic weekly reports\n")

        return True

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        print(f"\n[FAIL] Validation failed: {str(e)}\n")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Weekly Atlanta News Report Generator'
    )

    parser.add_argument(
        '--generate',
        action='store_true',
        help='Generate and send news report'
    )

    parser.add_argument(
        '--no-email',
        action='store_true',
        help='Generate report but do not send email'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate setup and configuration'
    )

    parser.add_argument(
        '--test-feeds',
        action='store_true',
        help='Test RSS feed connectivity only'
    )

    args = parser.parse_args()

    # Load config
    config = load_config()

    # Setup logging
    setup_logging(config)

    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("Starting Atlanta News Report")
    logger.info("="*60)

    # Load environment
    load_environment()

    if args.validate:
        # Run validation
        sys.exit(0 if validate_setup() else 1)

    elif args.test_feeds:
        # Test feeds only
        sys.exit(0 if test_feeds(config) else 1)

    elif args.generate:
        # Validate first
        if not validate_configuration(config):
            sys.exit(1)

        # Generate report
        send_email = not args.no_email
        generate_report(config, send_email=send_email)

    else:
        # Default: show help
        parser.print_help()
        print("\nExamples:")
        print("  python src/news_main.py --validate")
        print("  python src/news_main.py --test-feeds")
        print("  python src/news_main.py --generate")
        print("  python src/news_main.py --generate --no-email")


if __name__ == '__main__':
    main()
