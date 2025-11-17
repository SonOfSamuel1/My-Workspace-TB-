"""AWS Lambda handler for Toggl Daily Report automation.

This module provides Lambda function handler for:
- Daily Toggl Track performance reports (triggered by EventBridge at 6:00 PM EST)
"""
import json
import logging
import os
import sys
import base64
from typing import Dict, Any, Optional

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from toggl_daily import TogglDailyReport


def get_parameter(parameter_name: str, region: str = None) -> Optional[str]:
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


def load_credentials_from_parameters():
    """Load credential files from Parameter Store to /tmp directory.

    Lambda ephemeral storage at /tmp can hold credential files.
    """
    # Create credentials directory in /tmp
    os.makedirs('/tmp/credentials', exist_ok=True)

    cred_mapping = {
        '/toggl-daily-report/credentials': '/tmp/credentials/credentials.json',
        '/toggl-daily-report/token': '/tmp/credentials/token.pickle'
    }

    for param_name, file_path in cred_mapping.items():
        param_value = get_parameter(param_name)
        if param_value and file_path:
            try:
                # Decode base64 for pickle file, write as-is for JSON
                if file_path.endswith('.pickle'):
                    decoded_value = base64.b64decode(param_value)
                    with open(file_path, 'wb') as f:
                        f.write(decoded_value)
                else:
                    with open(file_path, 'w') as f:
                        f.write(param_value)
                logger.info(f"Loaded {param_name} to {file_path}")
            except Exception as e:
                logger.warning(f"Failed to write {param_name} to {file_path}: {e}")


def load_api_keys_from_parameters():
    """Load API keys from Parameter Store and set environment variables."""
    # Load Toggl API token
    toggl_token = get_parameter('/toggl-daily-report/toggl-api-token')
    if toggl_token:
        os.environ['TOGGL_API_TOKEN'] = toggl_token
        logger.info("Loaded TOGGL_API_TOKEN from Parameter Store")

    # Load Toggl workspace ID
    workspace_id = get_parameter('/toggl-daily-report/toggl-workspace-id')
    if workspace_id:
        os.environ['TOGGL_WORKSPACE_ID'] = workspace_id
        logger.info("Loaded TOGGL_WORKSPACE_ID from Parameter Store")

    # Load recipient email
    recipient_email = get_parameter('/toggl-daily-report/recipient-email')
    if recipient_email:
        os.environ['REPORT_RECIPIENT_EMAIL'] = recipient_email
        logger.info("Loaded REPORT_RECIPIENT_EMAIL from Parameter Store")

    if not toggl_token or not workspace_id:
        logger.warning("Missing required API keys from Parameter Store")


def daily_report_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for daily Toggl Track performance report.

    Triggered by EventBridge daily at 6:00 PM EST.

    Args:
        event: Lambda event object from EventBridge
        context: Lambda context object

    Returns:
        Dict with status code and body
    """
    logger.info("=" * 60)
    logger.info("TOGGL DAILY REPORT LAMBDA - Starting execution")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 60)

    try:
        # Load credentials and API keys from Parameter Store
        logger.info("Loading credentials from Parameter Store...")
        load_credentials_from_parameters()
        load_api_keys_from_parameters()

        # Set credential paths for Lambda environment
        os.environ['GOOGLE_CREDENTIALS_FILE'] = '/tmp/credentials/credentials.json'
        os.environ['GOOGLE_TOKEN_FILE'] = '/tmp/credentials/token.pickle'

        # Create .env file in /tmp for TogglService
        env_path = '/tmp/.env'
        with open(env_path, 'w') as f:
            f.write(f"TOGGL_API_TOKEN={os.environ.get('TOGGL_API_TOKEN', '')}\n")
            f.write(f"TOGGL_WORKSPACE_ID={os.environ.get('TOGGL_WORKSPACE_ID', '')}\n")
            f.write(f"REPORT_RECIPIENT_EMAIL={os.environ.get('REPORT_RECIPIENT_EMAIL', '')}\n")

        # Initialize Toggl Daily Report system
        logger.info("Initializing Toggl Daily Report system...")
        system = TogglDailyReport(config_path='config.yaml', env_path=env_path)

        # Generate and send report
        logger.info("Generating and sending daily report...")
        success = system.generate_report()

        if success:
            logger.info("=" * 60)
            logger.info("✓ Daily Toggl report sent successfully")
            logger.info("=" * 60)

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Daily Toggl report sent successfully'
                })
            }
        else:
            logger.error("Failed to generate or send report")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'message': 'Failed to generate or send report'
                })
            }

    except Exception as e:
        logger.error(f"Daily report failed: {str(e)}", exc_info=True)

        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Daily report failed: {str(e)}'
            })
        }


# Main Lambda handler (entry point)
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler entry point.

    Routes to appropriate handler based on event source.

    Args:
        event: Lambda event object
        context: Lambda context object

    Returns:
        Dict with status code and body
    """
    # Default to daily report handler
    return daily_report_handler(event, context)


# For local testing
if __name__ == '__main__':
    print("\n" + "="*60)
    print("Testing Daily Report Handler")
    print("="*60)
    result = daily_report_handler({}, None)
    print(f"Result: {result}")
