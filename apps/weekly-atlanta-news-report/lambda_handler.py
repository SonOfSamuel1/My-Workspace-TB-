#!/usr/bin/env python3
"""
AWS Lambda Handler for Weekly Atlanta News Report

Triggered by EventBridge on Friday at 6:30 PM EST.
Fetches Atlanta news from RSS feeds and sends weekly email digest.
"""
import os
import sys
import json
import logging
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Default configuration
DEFAULT_REGION = 'us-east-1'
DEFAULT_SENDER = 'brandonhome.appdev@gmail.com'


def get_parameter(parameter_name: str, region: str = None) -> str:
    """
    Retrieve a parameter from AWS Systems Manager Parameter Store.

    Args:
        parameter_name: Name of the parameter (e.g., '/atlanta-news/email-recipient')
        region: AWS region (defaults to DEFAULT_REGION)

    Returns:
        Parameter value as string

    Raises:
        Exception if parameter cannot be retrieved
    """
    region = region or os.getenv('AWS_REGION', DEFAULT_REGION)

    ssm = boto3.client('ssm', region_name=region)

    try:
        response = ssm.get_parameter(
            Name=parameter_name,
            WithDecryption=True  # Handles SecureString parameters
        )
        return response['Parameter']['Value']

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ParameterNotFound':
            logger.warning(f"Parameter not found: {parameter_name}")
            return None
        else:
            logger.error(f"Error retrieving parameter {parameter_name}: {e}")
            raise


def load_config_from_parameters():
    """
    Load configuration from AWS Parameter Store.

    Sets environment variables from Parameter Store values.
    """
    logger.info("Loading configuration from Parameter Store...")

    # Map of Parameter Store keys to environment variables
    param_mappings = {
        '/atlanta-news/email-recipient': 'ATLANTA_NEWS_EMAIL',
        '/atlanta-news/ses-sender-email': 'SES_SENDER_EMAIL',
    }

    for param_name, env_var in param_mappings.items():
        value = get_parameter(param_name)
        if value:
            os.environ[env_var] = value
            logger.info(f"Loaded {env_var} from Parameter Store")
        else:
            logger.warning(f"Parameter {param_name} not found")

    # Ensure AWS region is set
    if not os.getenv('AWS_REGION'):
        os.environ['AWS_REGION'] = DEFAULT_REGION


def atlanta_news_handler(event: dict, context) -> dict:
    """
    Lambda handler for weekly Atlanta news report.

    Triggered by EventBridge on schedule:
    cron(30 23 ? * FRI *)  = Friday 11:30pm UTC = 6:30pm EST

    Args:
        event: Lambda event data (usually empty for scheduled events)
        context: Lambda context object

    Returns:
        Response dict with statusCode and body
    """
    logger.info("="*60)
    logger.info("Atlanta News Report Lambda Handler Started")
    logger.info("="*60)

    try:
        # Load configuration from Parameter Store
        load_config_from_parameters()

        # Import after path setup
        import yaml
        from news_fetcher import NewsFetcher
        from news_analyzer import NewsAnalyzer
        from news_report import NewsReportGenerator
        from ses_email_sender import SESEmailSender

        # Load config.yaml
        config_path = Path(__file__).parent / 'config.yaml'
        with open(config_path) as f:
            config = yaml.safe_load(f)

        news_config = config['atlanta_news_report']

        # Validate required configuration
        recipient = os.getenv('ATLANTA_NEWS_EMAIL')
        if not recipient:
            raise ValueError("ATLANTA_NEWS_EMAIL not configured")

        # Step 1: Fetch news from RSS feeds
        logger.info("Fetching news from RSS feeds...")
        fetcher = NewsFetcher(
            feeds_config=news_config['feeds'],
            timezone=news_config.get('timezone', 'America/New_York')
        )
        articles = fetcher.fetch_all_feeds()
        logger.info(f"Fetched {len(articles)} articles")

        if not articles:
            logger.warning("No articles fetched from RSS feeds")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No articles found',
                    'articles_fetched': 0
                })
            }

        # Step 2: Process articles
        logger.info("Processing articles...")
        analyzer = NewsAnalyzer(news_config)
        processed_news = analyzer.process_articles(articles)

        # Step 3: Generate HTML report
        logger.info("Generating HTML report...")
        report_generator = NewsReportGenerator(news_config)
        html_content = report_generator.generate_html_report(processed_news)
        plain_text = report_generator.generate_plain_text(processed_news)
        subject = report_generator.generate_subject(processed_news)

        # Save to /tmp for debugging (Lambda ephemeral storage)
        output_file = Path('/tmp/atlanta_news_report.html')
        with open(output_file, 'w') as f:
            f.write(html_content)
        logger.info(f"Report saved to {output_file}")

        # Step 4: Send email
        logger.info(f"Sending email to {recipient}...")
        email_sender = SESEmailSender(
            region=os.getenv('AWS_REGION', DEFAULT_REGION),
            sender_email=os.getenv('SES_SENDER_EMAIL', DEFAULT_SENDER)
        )

        success = email_sender.send_html_email(
            to=recipient,
            subject=subject,
            html_content=html_content,
            text_content=plain_text
        )

        if success:
            logger.info("Email sent successfully!")
            stats = analyzer.get_statistics(processed_news)

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Atlanta news report sent successfully',
                    'recipient': recipient,
                    'articles_fetched': len(articles),
                    'articles_in_report': processed_news.total_count,
                    'top_stories': len(processed_news.top_stories),
                    'general_news': len(processed_news.general_news),
                    'business_news': len(processed_news.business_news),
                    'duplicates_removed': processed_news.duplicates_removed,
                    'sources': stats['sources']
                })
            }
        else:
            logger.error("Failed to send email")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Failed to send email',
                    'error': 'SES send_html_email returned False'
                })
            }

    except Exception as e:
        logger.error(f"Error in Lambda handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error generating Atlanta news report',
                'error': str(e)
            })
        }


# For local testing
if __name__ == '__main__':
    # Simulate Lambda invocation
    result = atlanta_news_handler({}, None)
    print(json.dumps(result, indent=2))
