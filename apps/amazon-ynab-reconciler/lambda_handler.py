"""
AWS Lambda handler for Amazon-YNAB reconciliation.
Optimized for ZIP deployment with smaller memory footprint.

Memory Optimization:
- Uses email mode by default (no Playwright/browser dependencies)
- Playwright dependencies are loaded lazily only when needed
- Recommended Lambda memory: 512MB for email/CSV modes, 3GB for web scraping
"""

import os
import sys
import json
import logging
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Initialize AWS clients
ssm = boto3.client('ssm')
s3 = boto3.client('s3')
ses = boto3.client('ses', region_name='us-east-1')  # SES typically in us-east-1


def get_parameter(param_name: str, decrypt: bool = True) -> str:
    """Get parameter from AWS Parameter Store."""
    try:
        response = ssm.get_parameter(
            Name=param_name,
            WithDecryption=decrypt
        )
        return response['Parameter']['Value']
    except Exception as e:
        logger.error(f"Failed to get parameter {param_name}: {str(e)}")
        raise


def load_credentials_from_parameters():
    """Load all credentials from Parameter Store."""
    logger.info("Loading credentials from Parameter Store")

    # Load YNAB API key
    ynab_api_key = get_parameter('/amazon-reconciler/ynab-api-key')
    os.environ['YNAB_API_KEY'] = ynab_api_key

    # Load Gmail credentials (stored as base64 JSON)
    try:
        import base64
        gmail_creds_b64 = get_parameter('/amazon-reconciler/gmail-credentials')
        gmail_creds = base64.b64decode(gmail_creds_b64).decode('utf-8')

        # Save to temporary file for Gmail API
        creds_path = '/tmp/gmail_credentials.json'
        with open(creds_path, 'w') as f:
            f.write(gmail_creds)
        os.environ['GMAIL_CREDENTIALS_PATH'] = creds_path
    except Exception as e:
        logger.warning(f"Could not load Gmail credentials: {e}")

    # Load Gmail token if exists
    try:
        import pickle
        gmail_token_b64 = get_parameter('/amazon-reconciler/gmail-token')
        gmail_token = base64.b64decode(gmail_token_b64)

        # Save to temporary file
        token_path = '/tmp/gmail_token.pickle'
        with open(token_path, 'wb') as f:
            f.write(gmail_token)
        os.environ['GMAIL_TOKEN_PATH'] = token_path
    except:
        logger.info("Gmail token not found, will need to authenticate")

    # Load Amazon credentials (for CSV fallback)
    try:
        amazon_email = get_parameter('/amazon-reconciler/amazon-email', decrypt=False)
        os.environ['AMAZON_EMAIL'] = amazon_email
    except:
        logger.info("Amazon email not configured")

    # Load Browserbase credentials
    try:
        browserbase_api_key = get_parameter('/amazon-reconciler/browserbase-api-key')
        os.environ['BROWSERBASE_API_KEY'] = browserbase_api_key
        logger.info("Browserbase API key loaded")
    except:
        logger.info("Browserbase API key not configured")

    # Load Browserbase session ID (enables Browserbase mode if present)
    try:
        browserbase_session = get_parameter('/amazon-reconciler/browserbase-session-id')
        # Parse the JSON to get just the session_id
        import json as json_module
        session_data = json_module.loads(browserbase_session)
        os.environ['BROWSERBASE_SESSION_ID'] = session_data.get('session_id', browserbase_session)
        os.environ['USE_BROWSERBASE'] = 'true'
        logger.info("Browserbase session loaded - will use cloud browser automation")
    except:
        logger.info("Browserbase session not configured, will use email mode")


def load_state_from_s3(bucket: str = None) -> Dict:
    """Load reconciliation state from S3."""
    if not bucket:
        bucket = os.environ.get('STATE_BUCKET', 'amazon-ynab-reconciler')

    key = 'state/reconciliation_state.json'

    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        state = json.loads(response['Body'].read())
        logger.info(f"Loaded state from S3: {bucket}/{key}")
        return state
    except s3.exceptions.NoSuchKey:
        logger.info("No existing state found in S3")
        return {'matched_pairs': [], 'last_run': None}
    except Exception as e:
        logger.error(f"Error loading state from S3: {e}")
        return {'matched_pairs': [], 'last_run': None}


def save_state_to_s3(state: Dict, bucket: str = None):
    """Save reconciliation state to S3."""
    if not bucket:
        bucket = os.environ.get('STATE_BUCKET', 'amazon-ynab-reconciler')

    key = 'state/reconciliation_state.json'

    try:
        state['last_run'] = datetime.now().isoformat()
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(state, indent=2, default=str),
            ContentType='application/json'
        )
        logger.info(f"Saved state to S3: {bucket}/{key}")
    except Exception as e:
        logger.error(f"Error saving state to S3: {e}")


def send_email_report(report: Dict, recipient: str = None):
    """Send email report via SES."""
    if not recipient:
        recipient = os.environ.get('REPORT_EMAIL', 'terrancebrandon@me.com')

    subject = f"Amazon-YNAB Reconciliation Report - {datetime.now().strftime('%Y-%m-%d')}"

    # Create HTML body
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ background-color: #f0f0f0; padding: 20px; }}
            .stats {{ margin: 20px 0; }}
            .stat-item {{ padding: 10px; border-bottom: 1px solid #ddd; }}
            .success {{ color: green; }}
            .warning {{ color: orange; }}
            .error {{ color: red; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Amazon-YNAB Reconciliation Report</h2>
            <p>Run Date: {report.get('timestamp', datetime.now().isoformat())}</p>
        </div>

        <div class="stats">
            <div class="stat-item">
                <strong>Amazon Transactions Found:</strong> {report.get('amazon_count', 0)}
            </div>
            <div class="stat-item">
                <strong>YNAB Transactions Found:</strong> {report.get('ynab_count', 0)}
            </div>
            <div class="stat-item">
                <strong>Matches Found:</strong> {report.get('matches_count', 0)}
            </div>
            <div class="stat-item">
                <strong>Updates Applied:</strong> {report.get('updates_applied', 0)}
            </div>
        </div>

        <h3>Match Details</h3>
        <ul>
            <li>High Confidence (90%+): {report.get('high_confidence', 0)}</li>
            <li>Medium Confidence (70-90%): {report.get('medium_confidence', 0)}</li>
            <li>Low Confidence (<70%): {report.get('low_confidence', 0)}</li>
        </ul>

        <p>View logs in CloudWatch for detailed information.</p>
    </body>
    </html>
    """

    try:
        ses.send_email(
            Source=recipient,  # Use same email as sender
            Destination={'ToAddresses': [recipient]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Html': {'Data': html_body}}
            }
        )
        logger.info(f"Email report sent to {recipient}")
    except Exception as e:
        logger.error(f"Failed to send email report: {e}")


def lambda_handler(event, context):
    """
    Main Lambda handler function.

    Args:
        event: Lambda event dict
        context: Lambda context object

    Returns:
        Response dict with statusCode and body
    """
    logger.info("Starting Amazon-YNAB reconciliation Lambda")
    logger.info(f"Event: {json.dumps(event)}")

    try:
        # Load credentials from Parameter Store
        load_credentials_from_parameters()

        # Set data source priority for Lambda
        # Browserbase takes priority if session is configured (set in load_credentials_from_parameters)
        # Otherwise, fall back to email mode
        if not os.environ.get('USE_BROWSERBASE'):
            os.environ['USE_EMAIL'] = 'true'
            logger.info("Using email mode for Lambda (no Browserbase session)")

        # Load state from S3
        state_bucket = os.environ.get('STATE_BUCKET')
        if state_bucket:
            existing_state = load_state_from_s3(state_bucket)
            # Save state to temp file for the reconciler
            with open('/tmp/reconciliation_state.json', 'w') as f:
                json.dump(existing_state, f)

        # Import and run reconciler
        from reconciler_main import AmazonYNABReconciler

        # Get lookback days from event or use default
        lookback_days = event.get('lookback_days', 30)

        # Override config path for Lambda
        config = {
            'reconciliation': {
                'lookback_days': lookback_days,
                'match_threshold': 80,
                'date_tolerance_days': 2,
                'amount_tolerance_cents': 50,
                'enable_state_tracking': True,
                'state_file': '/tmp/reconciliation_state.json'
            },
            'ynab': {
                'budget_name': "Terrance Brandon's Plan",
                'account_names': [
                    'Amazon Business Prime Card – 3008',
                    'Amazon Business Prime Card – 1010',
                    'Chase Reserve CC – 1516',
                    'SimplyCash® Plus Card – 4008',
                    'Apple Card'
                ],
                'only_uncleared': True,
                'memo_format': '[Amazon: {category}] | {item_name} | {item_link}',
                'preserve_existing_memo': True
            },
            'email': {
                'enabled': True,
                'recipient': os.environ.get('REPORT_EMAIL'),
                'include_details': True,
                'only_on_activity': False
            }
        }

        # Initialize reconciler with Lambda config
        reconciler = AmazonYNABReconciler(config_path=None, dry_run=False)
        reconciler.config = config  # Override with Lambda config

        # Run reconciliation
        results = reconciler.run(lookback_days=lookback_days)

        # Prepare summary report
        report = {
            'timestamp': datetime.now().isoformat(),
            'amazon_count': len(results.get('amazon_transactions', [])),
            'ynab_count': len(results.get('ynab_transactions', [])),
            'matches_count': len(results.get('matches', [])),
            'updates_applied': results.get('updates_applied', 0),
            'high_confidence': 0,
            'medium_confidence': 0,
            'low_confidence': 0
        }

        # Count confidence levels
        for match in results.get('matches', []):
            confidence = match.get('confidence', 0)
            if confidence >= 90:
                report['high_confidence'] += 1
            elif confidence >= 70:
                report['medium_confidence'] += 1
            else:
                report['low_confidence'] += 1

        # Save updated state to S3
        if state_bucket and os.path.exists('/tmp/reconciliation_state.json'):
            with open('/tmp/reconciliation_state.json', 'r') as f:
                updated_state = json.load(f)
            save_state_to_s3(updated_state, state_bucket)

        # Send email report
        if report['matches_count'] > 0 or event.get('force_email'):
            send_email_report(report)

        # Log summary
        logger.info(f"Reconciliation complete: {report['matches_count']} matches, "
                    f"{report['updates_applied']} updates applied")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Reconciliation completed successfully',
                'report': report
            })
        }

    except Exception as e:
        logger.error(f"Reconciliation failed: {str(e)}", exc_info=True)

        # Send error notification
        try:
            error_report = {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'amazon_count': 0,
                'ynab_count': 0,
                'matches_count': 0,
                'updates_applied': 0
            }
            send_email_report(error_report)
        except:
            pass

        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Reconciliation failed',
                'error': str(e)
            })
        }


if __name__ == "__main__":
    # Test locally
    test_event = {
        'lookback_days': 7,
        'force_email': True
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))