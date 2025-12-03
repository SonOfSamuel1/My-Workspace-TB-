"""AWS Lambda handler for Todoist Daily Reminders automation.

This module provides Lambda function handler for:
- Daily reminder creation (triggered by EventBridge daily at 6:00 AM EST)

Creates reminders at 8am, 11am, 4pm, and 7pm for tasks due today
with the @commit label.
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

from reminder_main import (
    setup_logging,
    process_tasks_and_create_reminders,
    DEFAULT_LABEL,
    DEFAULT_TIMEZONE,
    DEFAULT_REMINDER_TIMES
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


def load_api_key_from_parameters():
    """Load Todoist API key from Parameter Store and set environment variable."""
    # Load Todoist API key
    api_key = get_parameter('/todoist-reminders/api-token')
    if api_key:
        os.environ['TODOIST_API_TOKEN'] = api_key
        logger.info("Loaded TODOIST_API_TOKEN from Parameter Store")
    else:
        logger.info("Using TODOIST_API_TOKEN from environment variables")

    # Load optional label override
    label = get_parameter('/todoist-reminders/label')
    if label:
        os.environ['TODOIST_LABEL'] = label
        logger.info(f"Loaded TODOIST_LABEL from Parameter Store: {label}")

    # Load optional timezone override
    timezone = get_parameter('/todoist-reminders/timezone')
    if timezone:
        os.environ['TODOIST_TIMEZONE'] = timezone
        logger.info(f"Loaded TODOIST_TIMEZONE from Parameter Store: {timezone}")


def daily_reminders_handler(event: dict, context) -> dict:
    """Lambda handler for daily reminders creation.

    Triggered by EventBridge daily at 6:00 AM EST.

    Args:
        event: Lambda event object from EventBridge
        context: Lambda context object

    Returns:
        Dict with status code and body
    """
    logger.info("=" * 60)
    logger.info("TODOIST DAILY REMINDERS LAMBDA - Starting execution")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 60)

    try:
        # Load API key from Parameter Store
        logger.info("Loading API key from Parameter Store...")
        load_api_key_from_parameters()

        # Get API token
        api_token = os.environ.get('TODOIST_API_TOKEN')
        if not api_token:
            raise ValueError("TODOIST_API_TOKEN not configured")

        # Get optional configuration
        label_name = os.environ.get('TODOIST_LABEL', DEFAULT_LABEL)
        timezone_str = os.environ.get('TODOIST_TIMEZONE', DEFAULT_TIMEZONE)

        logger.info(f"Configuration:")
        logger.info(f"  Label: @{label_name}")
        logger.info(f"  Timezone: {timezone_str}")
        logger.info(f"  Reminder times: 8am, 11am, 4pm, 7pm")

        # Setup logging
        setup_logging()

        # Process tasks and create reminders
        logger.info("Processing tasks and creating reminders...")
        results = process_tasks_and_create_reminders(
            api_token=api_token,
            label_name=label_name,
            timezone_str=timezone_str,
            reminder_times=DEFAULT_REMINDER_TIMES
        )

        logger.info("=" * 60)
        logger.info("Daily reminders created successfully")
        logger.info("=" * 60)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Daily reminders created successfully',
                'tasks_found': results['tasks_found'],
                'reminders_created': results['reminders_created'],
                'reminders_deleted': results['reminders_deleted'],
                'errors': results['errors']
            })
        }

    except Exception as e:
        logger.error(f"Daily reminders failed: {str(e)}", exc_info=True)

        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Daily reminders failed: {str(e)}'
            })
        }


# For local testing
if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Testing Daily Reminders Handler")
    print("=" * 60)
    result = daily_reminders_handler({}, None)
    print(f"Result: {result}")
