"""
News Main - Main orchestration module for the Daily AI News Report.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

import yaml
from dotenv import load_dotenv

from .email_report import EmailReportGenerator
from .news_processor import NewsProcessor
from .rss_fetcher import Article, RSSFetcher
from .ses_email_sender import SESEmailSender

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default RSS feeds for AI news
DEFAULT_FEEDS = [
    {
        'name': 'MIT Technology Review - AI',
        'url': 'https://www.technologyreview.com/topic/artificial-intelligence/feed',
        'category': 'research'
    },
    {
        'name': 'VentureBeat AI',
        'url': 'https://venturebeat.com/category/ai/feed/',
        'category': 'industry'
    },
    {
        'name': 'The Verge - AI',
        'url': 'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml',
        'category': 'tech'
    },
    {
        'name': 'Ars Technica - AI',
        'url': 'https://feeds.arstechnica.com/arstechnica/technology-lab',
        'category': 'tech'
    },
    {
        'name': 'Wired - AI',
        'url': 'https://www.wired.com/feed/tag/ai/latest/rss',
        'category': 'tech'
    },
]


class DailyAINewsReport:
    """Main class for generating and sending daily AI news reports."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        env_path: Optional[str] = None
    ):
        """
        Initialize the daily news report.

        Args:
            config_path: Path to config.yaml file
            env_path: Path to .env file
        """
        # Load environment variables
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()

        # Load configuration
        self.config = self._load_config(config_path)

        # Initialize components
        self.feeds = self.config.get('feeds', DEFAULT_FEEDS)
        self.rss_fetcher = RSSFetcher(self.feeds)
        self.processor = NewsProcessor(
            max_articles=self.config.get('processing', {}).get('max_articles', 10),
            min_relevance_score=self.config.get('processing', {}).get('min_relevance_score', 0.3),
            dedup_window_days=self.config.get('processing', {}).get('dedup_window_days', 7)
        )

        # Template directory
        template_dir = self.config.get('email', {}).get('template_dir')
        if not template_dir:
            # Default to templates directory relative to this file
            template_dir = str(Path(__file__).parent.parent / 'templates')

        self.report_generator = EmailReportGenerator(
            template_dir=template_dir if Path(template_dir).exists() else None,
            subject_prefix=self.config.get('email', {}).get('subject_prefix', '[AI News]')
        )

        # Email sender (initialized lazily)
        self._email_sender = None

        # State file for deduplication
        self.state_file = self.config.get('state_file', 'logs/seen_articles.json')

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from YAML file."""
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")

        # Try default location
        default_config = Path(__file__).parent.parent / 'config' / 'config.yaml'
        if default_config.exists():
            try:
                with open(default_config, 'r') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Failed to load default config: {e}")

        return {}

    @property
    def email_sender(self) -> SESEmailSender:
        """Lazy initialization of email sender."""
        if self._email_sender is None:
            self._email_sender = SESEmailSender(
                sender_email=os.environ.get('SENDER_EMAIL'),
                region=os.environ.get('AWS_REGION', 'us-east-1')
            )
        return self._email_sender

    def run(self, send_email: bool = True) -> dict:
        """
        Run the daily news report generation.

        Args:
            send_email: Whether to send the email (False for testing)

        Returns:
            Dict with report details and status
        """
        logger.info("Starting Daily AI News Report generation")
        start_time = datetime.now()

        try:
            # Load previously seen articles
            seen_hashes = self._load_seen_hashes()

            # Fetch articles from RSS feeds
            logger.info(f"Fetching articles from {len(self.feeds)} feeds")
            articles = self.rss_fetcher.fetch_all()
            logger.info(f"Fetched {len(articles)} total articles")

            # Process articles
            processed_articles = self.processor.process(articles, seen_hashes)
            logger.info(f"Selected {len(processed_articles)} articles for report")

            # Generate report
            report = self.report_generator.generate(
                processed_articles,
                title="Daily AI News Digest"
            )

            # Send email if enabled
            email_result = None
            if send_email and processed_articles:
                recipients = self._get_recipients()
                if recipients:
                    email_result = self.email_sender.send_email(
                        recipients=recipients,
                        subject=report['subject'],
                        html_body=report['html'],
                        text_body=report['text']
                    )
                    logger.info(f"Email sent to {len(recipients)} recipients")

            # Save seen hashes
            self._save_seen_hashes(self.processor.get_seen_hashes())

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Report generation completed in {elapsed:.2f}s")

            return {
                'status': 'success',
                'articles_fetched': len(articles),
                'articles_selected': len(processed_articles),
                'email_sent': email_result is not None,
                'elapsed_seconds': elapsed,
                'report': report,
            }

        except Exception as e:
            logger.error(f"Report generation failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
            }

    def _get_recipients(self) -> List[str]:
        """Get recipient email addresses."""
        # Try environment variable first
        recipients_env = os.environ.get('RECIPIENT_EMAIL', '')
        if recipients_env:
            return [r.strip() for r in recipients_env.split(',') if r.strip()]

        # Try config file
        return self.config.get('email', {}).get('recipients', [])

    def _load_seen_hashes(self) -> Set[str]:
        """Load previously seen article hashes from state file."""
        state_path = Path(self.state_file)
        if state_path.exists():
            try:
                with open(state_path, 'r') as f:
                    data = json.load(f)
                    return set(data.get('seen_hashes', []))
            except Exception as e:
                logger.warning(f"Failed to load state file: {e}")
        return set()

    def _save_seen_hashes(self, hashes: Set[str]) -> None:
        """Save seen article hashes to state file."""
        state_path = Path(self.state_file)
        state_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Keep only the most recent 1000 hashes
            hash_list = list(hashes)[-1000:]
            with open(state_path, 'w') as f:
                json.dump({
                    'seen_hashes': hash_list,
                    'updated_at': datetime.now().isoformat(),
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save state file: {e}")


def main():
    """Main entry point for local execution."""
    import argparse

    parser = argparse.ArgumentParser(description='Daily AI News Report')
    parser.add_argument('--config', '-c', help='Path to config.yaml')
    parser.add_argument('--env', '-e', help='Path to .env file')
    parser.add_argument('--dry-run', '-d', action='store_true',
                       help='Generate report without sending email')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    report = DailyAINewsReport(
        config_path=args.config,
        env_path=args.env
    )

    result = report.run(send_email=not args.dry_run)

    if result['status'] == 'success':
        print(f"\n{'='*50}")
        print(f"Report generated successfully!")
        print(f"Articles fetched: {result['articles_fetched']}")
        print(f"Articles selected: {result['articles_selected']}")
        print(f"Email sent: {result['email_sent']}")
        print(f"Time elapsed: {result['elapsed_seconds']:.2f}s")
        print(f"{'='*50}\n")

        if args.dry_run:
            print("Subject:", result['report']['subject'])
            print("\nPlain text preview:")
            print(result['report']['text'][:500])

        return 0
    else:
        print(f"\nError: {result.get('error', 'Unknown error')}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
