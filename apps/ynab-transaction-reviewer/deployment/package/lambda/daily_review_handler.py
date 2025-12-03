"""
AWS Lambda handler for daily transaction review

This handler is triggered by EventBridge on schedule to run the daily
transaction review and send emails.
"""

import os
import sys
import json
import logging
import boto3
from pathlib import Path

# Add src to path
sys.path.insert(0, '/opt/python')  # Lambda layer path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from reviewer_main import TransactionReviewer

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
ssm = boto3.client('ssm')
s3 = boto3.client('s3')

# S3 bucket for credentials
CREDENTIALS_BUCKET = 'ynab-reviewer-credentials-718881314209'


def get_parameter(name: str, decrypt: bool = True) -> str:
    """Get parameter from AWS Parameter Store"""
    try:
        response = ssm.get_parameter(Name=name, WithDecryption=decrypt)
        return response['Parameter']['Value']
    except Exception as e:
        logger.error(f"Failed to get parameter {name}: {e}")
        raise


def download_gmail_credentials():
    """Download Gmail credentials from S3 to /tmp"""
    credentials_dir = Path('/tmp/credentials')
    credentials_dir.mkdir(parents=True, exist_ok=True)

    # Download credentials.json
    credentials_path = credentials_dir / 'gmail_credentials.json'
    try:
        s3.download_file(
            CREDENTIALS_BUCKET,
            'gmail_credentials.json',
            str(credentials_path)
        )
        logger.info(f"Downloaded gmail_credentials.json to {credentials_path}")
    except Exception as e:
        logger.error(f"Failed to download gmail_credentials.json: {e}")
        raise

    # Download token.pickle
    token_path = credentials_dir / 'gmail_token.pickle'
    try:
        s3.download_file(
            CREDENTIALS_BUCKET,
            'gmail_token.pickle',
            str(token_path)
        )
        logger.info(f"Downloaded gmail_token.pickle to {token_path}")
    except Exception as e:
        logger.error(f"Failed to download gmail_token.pickle: {e}")
        raise

    return str(credentials_dir)


def lambda_handler(event, context):
    """
    Lambda handler for daily review

    Args:
        event: EventBridge event or manual trigger
        context: Lambda context

    Returns:
        Response dictionary
    """
    logger.info(f"Lambda triggered with event: {json.dumps(event)}")

    try:
        # Load parameters from Parameter Store
        os.environ['YNAB_API_KEY'] = get_parameter('/ynab-reviewer/ynab-api-key')
        os.environ['RECIPIENT_EMAIL'] = get_parameter('/ynab-reviewer/recipient-email')

        # Optional parameters
        try:
            os.environ['YNAB_BUDGET_ID'] = get_parameter('/ynab-reviewer/ynab-budget-id')
        except:
            pass  # Use default (first budget)

        # Download Gmail credentials from S3
        credentials_dir = download_gmail_credentials()
        os.environ['GMAIL_CREDENTIALS_PATH'] = f"{credentials_dir}/gmail_credentials.json"
        os.environ['GMAIL_TOKEN_PATH'] = f"{credentials_dir}/gmail_token.pickle"

        # Create reviewer instance
        reviewer = TransactionReviewer()

        # Check if this is a force run
        force_run = event.get('force', False)
        dry_run = event.get('dry_run', False)

        # Run the review
        reviewer.run_review(force=force_run, dry_run=dry_run)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Transaction review completed successfully',
                'forced': force_run,
                'dry_run': dry_run
            })
        }

    except Exception as e:
        logger.error(f"Error in lambda handler: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }


def lambda_handler_action(event, context):
    """
    Lambda handler for processing action links from emails

    Args:
        event: API Gateway event with query parameters
        context: Lambda context

    Returns:
        HTTP response with redirect
    """
    logger.info(f"Action handler triggered: {json.dumps(event)}")

    try:
        # Parse query parameters
        params = event.get('queryStringParameters', {})
        action = params.get('action')
        transaction_id = params.get('txn')
        category_id = params.get('cat')
        token = params.get('token')

        if not all([action, transaction_id, token]):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required parameters'})
            }

        # TODO: Validate token (check signature and expiry)
        # For now, we'll skip token validation in this example

        # Load YNAB credentials
        os.environ['YNAB_API_KEY'] = get_parameter('/ynab-reviewer/ynab-api-key')

        # Import services
        from ynab_service import YNABService

        # Initialize YNAB service
        ynab = YNABService()

        # Process action
        success = False
        message = ""

        if action == 'categorize' and category_id:
            # Categorize transaction
            success = ynab.categorize_transaction(transaction_id, category_id)
            message = "Transaction categorized successfully!" if success else "Failed to categorize"

        elif action == 'split':
            # TODO: Implement split transaction handling
            # This would require storing split suggestions somewhere accessible
            message = "Split functionality not yet implemented"

        else:
            message = f"Unknown action: {action}"

        # Return HTML response with redirect
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta http-equiv="refresh" content="3;url=https://app.ynab.com">
            <title>YNAB Transaction Review</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 8px;
                    text-align: center;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .success {{ color: #4CAF50; }}
                .error {{ color: #f44336; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="{'success' if success else 'error'}">{message}</h1>
                <p>Redirecting to YNAB...</p>
            </div>
        </body>
        </html>
        """

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/html',
            },
            'body': html
        }

    except Exception as e:
        logger.error(f"Error in action handler: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }