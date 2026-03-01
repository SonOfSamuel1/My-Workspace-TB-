"""
AWS Lambda Handler for Toggl Daily Productivity Report.

Invoked by AWS EventBridge on a daily schedule.
"""

import json
import logging
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent))

from src.productivity_service import ProductivityService
from src.report_generator import ReportGenerator
from src.ses_email_sender import SESEmailSender

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_secrets(secret_name: str, region: str = None) -> dict:
    """Retrieve secrets from AWS Secrets Manager."""
    region = region or os.environ.get('AWS_REGION', 'us-east-1')
    client = boto3.client('secretsmanager', region_name=region)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        if 'SecretString' in response:
            return json.loads(response['SecretString'])
        else:
            logger.error("Secret is binary, expected string")
            return {}
    except ClientError as e:
        logger.error(f"Error retrieving secret: {e}")
        raise


def load_secrets_to_env(secret_name: str) -> None:
    """Load secrets from Secrets Manager into environment variables."""
    try:
        secrets = get_secrets(secret_name)
        for key, value in secrets.items():
            if key not in os.environ:
                os.environ[key] = str(value)
        logger.info(f"Loaded {len(secrets)} secrets from {secret_name}")
    except Exception as e:
        logger.warning(f"Failed to load secrets from {secret_name}: {e}")


def load_config() -> dict:
    """Load configuration from config.yaml."""
    import yaml
    config_path = Path(__file__).parent / 'config' / 'config.yaml'

    if not config_path.exists():
        logger.warning("Config file not found, using defaults")
        return {'daily_goal_minutes': 360, 'timezone': 'America/New_York'}

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config.get('productivity_report', {})


def lambda_handler(event: dict, context) -> dict:
    """
    AWS Lambda entry point.

    Args:
        event: Lambda event data (from EventBridge, API Gateway, etc.)
        context: Lambda context object

    Returns:
        Response dict with statusCode and body
    """
    logger.info(f"Lambda invoked with event: {json.dumps(event)}")

    try:
        # Load secrets from Secrets Manager
        secret_name = os.environ.get('SECRETS_NAME', 'toggl-productivity/credentials')
        if not os.environ.get('TOGGL_API_TOKEN'):
            load_secrets_to_env(secret_name)

        is_scheduled = event.get('source') == 'aws.events'
        is_dry_run = event.get('dry_run', False)

        logger.info(f"Running report (scheduled={is_scheduled}, dry_run={is_dry_run})")

        # Load config
        config = load_config()

        # Generate report
        productivity = ProductivityService(config)
        generator = ReportGenerator()

        report_data = productivity.get_productivity_report()

        # Determine period
        from datetime import datetime
        hour = datetime.now().hour
        period = "Morning" if hour < 12 else "Evening"

        html_content = generator.generate_html_report(report_data, period)
        text_content = generator.generate_text_report(report_data, period)

        # Format subject
        subject = f"Daily Productivity Report - {datetime.now().strftime('%Y-%m-%d')} {period}"

        logger.info(f"Report generated: {report_data['yesterday_total']} mins yesterday ({report_data['yesterday_percent']}%)")

        if is_dry_run:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Dry run complete',
                    'yesterday_total': report_data['yesterday_total'],
                    'yesterday_percent': report_data['yesterday_percent'],
                    'week_avg': report_data['week_avg'],
                    'month_avg': report_data['month_avg'],
                })
            }

        # Send email
        email_config = config.get('email', {})
        ses_config = config.get('ses', {})

        recipient = os.getenv('REPORT_RECIPIENT', email_config.get('recipient', ''))
        sender = os.getenv('SES_SENDER_EMAIL', ses_config.get('sender_email', ''))
        region = os.getenv('AWS_REGION', ses_config.get('region', 'us-east-1'))

        if not recipient:
            raise ValueError("No recipient email configured")

        email_sender = SESEmailSender(sender_email=sender, region=region)
        success = email_sender.send_html_email(
            to=recipient,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

        if success:
            response = {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Report sent successfully',
                    'yesterday_total': report_data['yesterday_total'],
                    'yesterday_percent': report_data['yesterday_percent'],
                    'email_sent': True,
                })
            }
            logger.info(f"Success: {response['body']}")
        else:
            response = {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Failed to send email',
                    'email_sent': False,
                })
            }
            logger.error(f"Failed: {response['body']}")

        return response

    except Exception as e:
        logger.error(f"Lambda execution failed: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Lambda execution failed',
                'error': str(e),
            })
        }


# For local testing
if __name__ == '__main__':
    test_event = {
        'source': 'local-test',
        'dry_run': True,
    }

    class MockContext:
        function_name = 'toggl-daily-productivity'
        memory_limit_in_mb = 256
        invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789:function:toggl-daily-productivity'
        aws_request_id = 'test-request-id'

    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
