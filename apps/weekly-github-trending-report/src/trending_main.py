#!/usr/bin/env python3
"""
Main entry point for Weekly GitHub Trending Report

This script orchestrates the trending report system,
fetching trending GitHub repos and generating weekly
email digests.
"""
import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Use python-dotenv for proper .env loading
try:
    from dotenv import load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

from github_fetcher import GitHubFetcher  # noqa: E402
from trending_analyzer import TrendingAnalyzer  # noqa: E402
from trending_report import (  # noqa: E402
    generate_html_report,
    generate_plain_text,
    generate_subject,
)

# Import SES email sender (preferred for automated emails)
try:
    from ses_email_sender import SESEmailSender

    HAS_SES = True
except ImportError:
    SESEmailSender = None
    HAS_SES = False


def setup_logging(config: dict):
    """Setup logging configuration."""
    log_config = config.get("logging", {})

    log_level = getattr(logging, log_config.get("level", "INFO"))
    log_format = log_config.get(
        "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log_file = log_config.get("file", "logs/github_trending.log")

    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )


def load_config() -> dict:
    """Load configuration from config.yaml."""
    config_paths = [
        Path("config.yaml"),
        Path(__file__).parent.parent / "config.yaml",
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
        Path(".env"),
        Path(__file__).parent.parent / ".env",
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
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            value = value.strip().strip("\"'")
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
    required_env_vars = ["GITHUB_TRENDING_EMAIL"]
    missing_vars = []

    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
        logger.error("Please update your .env file with these values")
        return False

    # Check report enabled
    if not config.get("github_trending_report", {}).get("enabled"):
        logger.warning("GitHub trending reporting is disabled in config.yaml")
        return False

    # Check queries configured
    queries = config.get("github_trending_report", {}).get("api", {}).get("queries", [])
    if not queries:
        logger.error("No API queries configured in config.yaml")
        return False

    logger.info("Configuration validation passed")
    return True


def generate_report(config: dict, send_email: bool = True):
    """
    Generate and optionally send trending report.

    Args:
        config: Configuration dictionary
        send_email: Whether to send the report via email
    """
    logger = logging.getLogger(__name__)

    try:
        trending_config = config["github_trending_report"]

        # Step 1: Fetch trending repos from GitHub
        logger.info("Fetching trending repos from GitHub...")
        fetcher = GitHubFetcher(
            queries_config=trending_config["api"]["queries"],
            timeout=trending_config["api"].get("timeout", 30),
            timezone=trending_config.get("timezone", "America/New_York"),
        )

        lookback_days = trending_config.get("report", {}).get("lookback_days", 7)
        repos = fetcher.fetch_trending_repos(lookback_days=lookback_days)
        logger.info(f"Fetched {len(repos)} unique repos")

        if not repos:
            logger.warning("No repos fetched. Check GitHub API connectivity.")
            print("\n[WARNING] No repos fetched from GitHub API.")
            return

        # Step 2: Analyze and rank repos (with rotation tracking)
        logger.info("Analyzing repos...")
        analyzer = TrendingAnalyzer(trending_config)

        # Load seen-repos for rotation
        if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            seen_path = Path("/tmp") / "seen_repos.json"
        else:
            seen_path = Path(__file__).parent.parent / trending_config.get(
                "rotation", {}
            ).get("seen_repos_file", "seen_repos.json")
        analyzer.set_seen_repos_path(seen_path)

        processed = analyzer.process_repos(repos)

        # Save selected repos to seen-list for future rotation
        analyzer.save_seen_repos(processed.trending_repos)

        # Step 3: Generate HTML report
        logger.info("Generating HTML report...")
        html_content = generate_html_report(processed)

        # Step 4: Save HTML to file for review
        if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            output_dir = Path("/tmp")
        else:
            output_dir = Path(__file__).parent.parent / "output"
            output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"github_trending_{timestamp}.html"

        with open(output_file, "w") as f:
            f.write(html_content)

        logger.info(f"Report saved to: {output_file}")
        print("\n[OK] Report generated successfully!")
        print(f"[FILE] Saved to: {output_file}")

        # Step 5: Send email if requested
        if send_email:
            if not HAS_SES:
                logger.error("SES email sender not available")
                print("\n[ERROR] Email functionality not available")
                return

            recipient = os.getenv("GITHUB_TRENDING_EMAIL")
            if not recipient:
                logger.error("No email recipient configured (GITHUB_TRENDING_EMAIL)")
                print("\n[WARNING] Email not sent: No recipient configured")
                return

            logger.info(f"Sending email to {recipient}...")

            email_sender = SESEmailSender(
                region=os.getenv("AWS_REGION", "us-east-1"),
                sender_email=os.getenv(
                    "SES_SENDER_EMAIL", "brandonhome.appdev@gmail.com"
                ),
            )

            subject = generate_subject(processed)
            plain_text = generate_plain_text(processed)

            success = email_sender.send_html_email(
                to=recipient,
                subject=subject,
                html_content=html_content,
                text_content=plain_text,
            )

            if success:
                print(f"[EMAIL] Email sent successfully to {recipient}")
                logger.info(f"Email sent successfully to {recipient}")
            else:
                print(f"\n[ERROR] Failed to send email to {recipient}")
                logger.error(f"Failed to send email to {recipient}")

        # Print summary
        print(f"\n{'='*60}")
        print("GITHUB TRENDING REPORT SUMMARY")
        print(f"{'='*60}")

        stats = analyzer.get_statistics(processed)

        print("\n[STATS] Repository Statistics:")
        print(f"   Total Fetched: {stats['total_fetched']}")
        print(f"   Top Repos: {stats['top_repos']}")
        print(f"   Avg Stars: {stats['avg_stars']}")
        print(f"   Avg Forks: {stats['avg_forks']}")
        print(f"   Avg Growth: ~{stats['avg_growth_rate']} stars/day")

        print("\n[LANGUAGES] Breakdown:")
        for lang, count in stats["languages"].items():
            print(f"   {lang}: {count}")

        print("\n[PERIOD] Report Period:")
        print(
            f"   {stats['period']['start']} to {stats['period']['end']} "
            f"({stats['period']['days']} days)"
        )

        print(f"{'='*60}\n")

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        print(f"\n[ERROR] {str(e)}")
        sys.exit(1)


def validate_setup():
    """Validate that all services are properly configured."""
    logger = logging.getLogger(__name__)

    print("\n" + "=" * 60)
    print("GITHUB TRENDING REPORT SETUP VALIDATION")
    print("=" * 60 + "\n")

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

        # Test GitHub API
        print("\n[CHECK] Testing GitHub API...")
        trending_config = config["github_trending_report"]
        fetcher = GitHubFetcher(
            queries_config=trending_config["api"]["queries"],
            timeout=trending_config["api"].get("timeout", 30),
            timezone=trending_config.get("timezone", "America/New_York"),
        )

        api_result = fetcher.test_api()
        if api_result["status"] == "ok":
            auth_status = (
                "authenticated" if api_result["authenticated"] else "unauthenticated"
            )
            print(
                f"[OK] GitHub API: {auth_status}, "
                f"search rate limit: {api_result['search_remaining']}/"
                f"{api_result['search_limit']}"
            )
        else:
            print(
                f"[WARNING] GitHub API test failed: {api_result.get('error', 'unknown')}"
            )

        # Test SES (if available)
        if HAS_SES:
            print("\n[CHECK] Testing AWS SES connection...")
            email_sender = SESEmailSender(
                region=os.getenv("AWS_REGION", "us-east-1"),
                sender_email=os.getenv(
                    "SES_SENDER_EMAIL", "brandonhome.appdev@gmail.com"
                ),
            )
            if email_sender.validate_credentials():
                print("[OK] AWS SES connection successful")
            else:
                print("[WARNING] AWS SES connection failed")
        else:
            print("\n[WARNING] SES email sender not available - email disabled")

        print("\n" + "=" * 60)
        print("[OK] ALL VALIDATIONS PASSED!")
        print("=" * 60 + "\n")

        print("Next steps:")
        print("1. Update .env with GITHUB_TRENDING_EMAIL")
        print("2. Run: python src/trending_main.py --generate")
        print("3. Or set up AWS Lambda for automatic weekly reports\n")

        return True

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        print(f"\n[FAIL] Validation failed: {str(e)}\n")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Weekly GitHub Trending Report Generator"
    )

    parser.add_argument(
        "--generate", action="store_true", help="Generate and send trending report"
    )

    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Generate report but do not send email",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate setup and configuration",
    )

    args = parser.parse_args()

    # Load config
    config = load_config()

    # Setup logging
    setup_logging(config)

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Starting GitHub Trending Report")
    logger.info("=" * 60)

    # Load environment
    load_environment()

    if args.validate:
        sys.exit(0 if validate_setup() else 1)

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
        print("  python src/trending_main.py --validate")
        print("  python src/trending_main.py --generate")
        print("  python src/trending_main.py --generate --no-email")


if __name__ == "__main__":
    main()
