"""AWS Lambda handler for Love Brittany relationship tracking automation.

This module provides Lambda function handler for:
- Weekly relationship tracking reports (triggered by EventBridge on Sundays at 4 AM EST)
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

from relationship_main import (
    setup_logging,
    load_config,
    load_environment,
    generate_report,
    validate_configuration
)


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
    import os
    os.makedirs('/tmp/credentials', exist_ok=True)

    cred_mapping = {
        '/love-brittany/credentials': '/tmp/credentials/credentials.json',
        '/love-brittany/token': '/tmp/credentials/token.pickle'
    }

    for param_name, file_path in cred_mapping.items():
        param_value = get_parameter(param_name)
        if param_value and file_path:
            try:
                # Decode base64 for pickle file, write as-is for JSON
                if file_path.endswith('.pickle'):
                    import base64
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
    toggl_token = get_parameter('/love-brittany/toggl-api-token')
    if toggl_token:
        os.environ['TOGGL_API_TOKEN'] = toggl_token
        logger.info("Loaded TOGGL_API_TOKEN from Parameter Store")

    # Load Toggl workspace ID
    workspace_id = get_parameter('/love-brittany/toggl-workspace-id')
    if workspace_id:
        os.environ['TOGGL_WORKSPACE_ID'] = workspace_id
        logger.info("Loaded TOGGL_WORKSPACE_ID from Parameter Store")

    if not toggl_token or not workspace_id:
        logger.info("Using API keys from environment variables")


def weekly_report_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for weekly relationship tracking report.

    Triggered by EventBridge on Sundays at 4:00 AM EST.

    Args:
        event: Lambda event object from EventBridge
        context: Lambda context object

    Returns:
        Dict with status code and body
    """
    logger.info("=" * 60)
    logger.info("LOVE BRITTANY WEEKLY REPORT LAMBDA - Starting execution")
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

        # Load configuration
        logger.info("Loading configuration...")
        config = load_config()

        # Override log paths for Lambda (only /tmp is writable)
        if 'logging' not in config:
            config['logging'] = {}
        config['logging']['file'] = '/tmp/relationship.log'

        # Setup logging
        setup_logging(config)

        # Validate configuration
        logger.info("Validating configuration...")
        if not validate_configuration(config):
            raise ValueError("Configuration validation failed")

        # Generate and send report
        logger.info("Generating relationship tracking report...")
        generate_report(config, send_email=True)

        logger.info("=" * 60)
        logger.info("✓ Weekly relationship report sent successfully")
        logger.info("=" * 60)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Weekly relationship report sent successfully'
            })
        }

    except Exception as e:
        logger.error(f"Weekly report failed: {str(e)}", exc_info=True)

        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Weekly report failed: {str(e)}'
            })
        }


# For local testing
if __name__ == '__main__':
    print("\n" + "="*60)
    print("Testing Weekly Report Handler")
    print("="*60)
    result = weekly_report_handler({}, None)
    print(f"Result: {result}")
