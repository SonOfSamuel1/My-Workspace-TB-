"""AWS Lambda handler for Sleep Eight Daily Reporter.

This module provides Lambda function handler for daily sleep reports,
triggered by EventBridge on a schedule (e.g., 7 AM daily).
"""
import json
import logging
import os
import sys

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sleep_main import (
    setup_logging,
    load_config,
    load_environment,
    generate_report,
    validate_configuration
)


def get_parameter(parameter_name: str, region: str = None) -> str:
    """Retrieve parameter from AWS Systems Manager Parameter Store.

    Args:
        parameter_name: Name of the parameter in Parameter Store
        region: AWS region (defaults to environment variable or us-east-1)

    Returns:
        Parameter value as string, or None if error
    """
    try:
        import boto3
        from botocore.exceptions import ClientError

        if region is None:
            region = os.environ.get('AWS_REGION', 'us-east-1')

        session = boto3.session.Session()
        client = session.client(
            service_name='ssm',
            region_name=region
        )

        try:
            response = client.get_parameter(
                Name=parameter_name,
                WithDecryption=True  # Decrypt SecureString parameters
            )
            return response['Parameter']['Value']
        except ClientError as e:
            logger.error(f"Failed to retrieve parameter {parameter_name}: {e}")
            return None
    except ImportError:
        logger.warning("boto3 not available, skipping Parameter Store integration")
        return None
    except Exception as e:
        logger.error(f"Error retrieving parameter {parameter_name}: {e}")
        return None


def load_api_keys_from_parameters():
    """Load API keys from Parameter Store and set environment variables."""
    # Load Eight Sleep credentials
    eight_email = get_parameter('/sleep-eight-reporter/eight-sleep-email')
    if eight_email:
        os.environ['EIGHT_SLEEP_EMAIL'] = eight_email
        logger.info("Loaded EIGHT_SLEEP_EMAIL from Parameter Store")

    eight_password = get_parameter('/sleep-eight-reporter/eight-sleep-password')
    if eight_password:
        os.environ['EIGHT_SLEEP_PASSWORD'] = eight_password
        logger.info("Loaded EIGHT_SLEEP_PASSWORD from Parameter Store")

    # Load email recipient
    email = get_parameter('/sleep-eight-reporter/email-recipient')
    if email:
        os.environ['SLEEP_REPORT_EMAIL'] = email
        logger.info("Loaded SLEEP_REPORT_EMAIL from Parameter Store")

    # Load SES sender email
    ses_sender = get_parameter('/sleep-eight-reporter/ses-sender-email')
    if ses_sender:
        os.environ['SES_SENDER_EMAIL'] = ses_sender
        logger.info("Loaded SES_SENDER_EMAIL from Parameter Store")

    if not eight_email or not eight_password:
        logger.info("Using credentials from environment variables")


def daily_sleep_report_handler(event: dict, context) -> dict:
    """Lambda handler for daily sleep report.

    Triggered by EventBridge on schedule (e.g., daily at 7 AM EST).

    Args:
        event: Lambda event object from EventBridge
        context: Lambda context object

    Returns:
        Dict with status code and body
    """
    logger.info("=" * 60)
    logger.info("SLEEP EIGHT DAILY REPORT - Starting execution")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 60)

    try:
        # Load API keys from Parameter Store
        logger.info("Loading credentials from Parameter Store...")
        load_api_keys_from_parameters()

        # Load configuration
        logger.info("Loading configuration...")
        config = load_config()

        # Override log paths for Lambda (only /tmp is writable)
        if 'logging' not in config:
            config['logging'] = {}
        config['logging']['file'] = '/tmp/sleep_report.log'

        # Setup logging
        setup_logging(config)

        # Validate configuration
        logger.info("Validating configuration...")
        if not validate_configuration(config):
            raise ValueError("Configuration validation failed")

        # Generate and send report
        logger.info("Generating sleep report...")
        generate_report(config, send_email=True)

        logger.info("=" * 60)
        logger.info("Daily sleep report sent successfully")
        logger.info("=" * 60)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Daily sleep report sent successfully'
            })
        }

    except Exception as e:
        logger.error(f"Daily sleep report failed: {str(e)}", exc_info=True)

        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Daily sleep report failed: {str(e)}'
            })
        }


# For local testing
if __name__ == '__main__':
    print("\n" + "="*60)
    print("Testing Sleep Eight Daily Report Handler")
    print("="*60)
    result = daily_sleep_report_handler({}, None)
    print(f"Result: {result}")
