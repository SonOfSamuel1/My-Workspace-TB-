"""
AWS Lambda handler for Amazon-YNAB reconciliation.
Loads credentials from Parameter Store and executes reconciliation.
"""

import os
import sys
import json
import boto3
import base64
import pickle
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, '/var/task/src')

# Import reconciliation modules
from reconciler_main import AmazonYNABReconciler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()


def load_credentials_from_parameter_store():
    """Load credentials from AWS Parameter Store."""
    ssm = boto3.client('ssm', region_name=os.getenv('AWS_REGION', 'us-east-1'))

    parameters = {
        'AMAZON_EMAIL': '/amazon-reconciler/amazon-email',
        'AMAZON_PASSWORD': '/amazon-reconciler/amazon-password',
        'AMAZON_OTP_SECRET': '/amazon-reconciler/amazon-otp-secret',
        'YNAB_API_KEY': '/amazon-reconciler/ynab-api-key',
        'EMAIL_RECIPIENT': '/amazon-reconciler/email-recipient',
        'GMAIL_CREDENTIALS': '/amazon-reconciler/gmail-credentials',
        'GMAIL_TOKEN': '/amazon-reconciler/gmail-token'
    }

    for env_var, param_name in parameters.items():
        try:
            response = ssm.get_parameter(
                Name=param_name,
                WithDecryption=True
            )
            value = response['Parameter']['Value']

            # Handle JSON credentials
            if env_var == 'GMAIL_CREDENTIALS':
                # Save credentials JSON to file
                creds_path = '/tmp/gmail_credentials.json'
                with open(creds_path, 'w') as f:
                    f.write(value)
                os.environ['GMAIL_CREDENTIALS_PATH'] = creds_path

            # Handle pickled token
            elif env_var == 'GMAIL_TOKEN':
                # Decode and save token pickle
                token_path = '/tmp/gmail_token.pickle'
                token_data = base64.b64decode(value)
                with open(token_path, 'wb') as f:
                    f.write(token_data)
                os.environ['GMAIL_TOKEN_PATH'] = token_path

            else:
                os.environ[env_var] = value

            logger.info(f"Loaded {env_var} from Parameter Store")

        except ssm.exceptions.ParameterNotFound:
            logger.warning(f"Parameter {param_name} not found")
        except Exception as e:
            logger.error(f"Error loading {param_name}: {str(e)}")


def lambda_handler(event, context):
    """
    Main Lambda handler function.

    Args:
        event: Lambda event data
        context: Lambda context

    Returns:
        Response dictionary
    """
    try:
        logger.info("Starting Amazon-YNAB reconciliation Lambda function")

        # Load credentials from Parameter Store
        load_credentials_from_parameter_store()

        # Get configuration from event or use defaults
        config_overrides = event.get('config', {})
        dry_run = event.get('dry_run', False)
        lookback_days = event.get('lookback_days')

        # Initialize reconciler
        reconciler = AmazonYNABReconciler(
            config_path='/var/task/config.yaml',
            dry_run=dry_run
        )

        # Apply any config overrides
        if config_overrides:
            reconciler.config.update(config_overrides)

        # Validate setup
        if not reconciler.validate_setup():
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Configuration validation failed',
                    'message': 'Please check logs for details'
                })
            }

        # Run reconciliation
        results = reconciler.run(lookback_days=lookback_days)

        # Prepare response
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'duration': results['duration'],
                'matches': len(results['matches']),
                'updates_applied': results['updates_applied'],
                'amazon_transactions': len(results['amazon_transactions']),
                'ynab_transactions': len(results['ynab_transactions']),
                'unmatched_amazon': len(results['unmatched_amazon']),
                'unmatched_ynab': len(results['unmatched_ynab']),
                'errors': results['errors']
            }, default=str)
        }

        logger.info(f"Reconciliation completed successfully: {response['body']}")
        return response

    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'message': 'Reconciliation failed. Check CloudWatch logs for details.'
            })
        }


def manual_trigger(event_type='manual'):
    """
    Create a manual trigger event for local testing.

    Args:
        event_type: Type of trigger event

    Returns:
        Event dictionary
    """
    return {
        'trigger': event_type,
        'dry_run': False,
        'lookback_days': 30,
        'config': {
            'email': {
                'enabled': True,
                'only_on_activity': False
            }
        }
    }


if __name__ == "__main__":
    # Local testing
    print("Running locally...")

    # Load local .env file if it exists
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment from {env_path}")

    # Run with manual trigger
    result = lambda_handler(manual_trigger(), None)
    print(json.dumps(result, indent=2))