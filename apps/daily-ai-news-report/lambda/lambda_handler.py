"""
AWS Lambda Handler for Daily AI News Report.

This handler is invoked by AWS EventBridge on a daily schedule.
"""

import json
import logging
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.news_main import DailyAINewsReport

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_secrets(secret_name: str, region: str = None) -> dict:
    """
    Retrieve secrets from AWS Secrets Manager.

    Args:
        secret_name: Name of the secret in Secrets Manager
        region: AWS region

    Returns:
        Dict of secret key-value pairs
    """
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
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            logger.error(f"Secret {secret_name} not found")
        elif error_code == 'InvalidRequestException':
            logger.error(f"Invalid request for secret {secret_name}")
        elif error_code == 'InvalidParameterException':
            logger.error(f"Invalid parameter for secret {secret_name}")
        else:
            logger.error(f"Error retrieving secret: {e}")
        raise


def load_secrets_to_env(secret_name: str) -> None:
    """
    Load secrets from Secrets Manager into environment variables.

    Args:
        secret_name: Name of the secret
    """
    try:
        secrets = get_secrets(secret_name)
        for key, value in secrets.items():
            if key not in os.environ:  # Don't override existing env vars
                os.environ[key] = str(value)
        logger.info(f"Loaded {len(secrets)} secrets from {secret_name}")
    except Exception as e:
        logger.warning(f"Failed to load secrets from {secret_name}: {e}")


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
        # Load secrets from Secrets Manager if configured
        secret_name = os.environ.get('SECRETS_NAME', 'daily-ai-news/credentials')
        if not os.environ.get('SENDER_EMAIL'):
            load_secrets_to_env(secret_name)

        # Determine if this is a scheduled event or manual trigger
        is_scheduled = event.get('source') == 'aws.events'
        is_dry_run = event.get('dry_run', False)

        logger.info(f"Running report (scheduled={is_scheduled}, dry_run={is_dry_run})")

        # Initialize and run the report
        report = DailyAINewsReport()
        result = report.run(send_email=not is_dry_run)

        if result['status'] == 'success':
            response = {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Report generated successfully',
                    'articles_fetched': result['articles_fetched'],
                    'articles_selected': result['articles_selected'],
                    'email_sent': result['email_sent'],
                    'elapsed_seconds': result['elapsed_seconds'],
                })
            }
            logger.info(f"Success: {response['body']}")
        else:
            response = {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Report generation failed',
                    'error': result.get('error', 'Unknown error'),
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
    # Simulate Lambda invocation
    test_event = {
        'source': 'local-test',
        'dry_run': True,
    }

    class MockContext:
        function_name = 'daily-ai-news-report'
        memory_limit_in_mb = 256
        invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789:function:daily-ai-news-report'
        aws_request_id = 'test-request-id'

    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
