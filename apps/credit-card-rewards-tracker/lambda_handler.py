#!/usr/bin/env python3
"""
AWS Lambda Handler for Credit Card Rewards Tracker

This handler is invoked by AWS Lambda to generate and send weekly rewards reports.
Triggered by AWS EventBridge on a schedule.
"""

import os
import sys
import json
import logging
import boto3
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data_manager import DataManager
from card_service import CardService
from rewards_analyzer import RewardsAnalyzer
from rewards_report import RewardsReportGenerator

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_parameter(parameter_name: str, region: str = None) -> str:
    """
    Retrieve a parameter from AWS Parameter Store.

    Args:
        parameter_name: Name of the parameter
        region: AWS region (default: us-east-1)

    Returns:
        Parameter value as string
    """
    region = region or os.environ.get('AWS_REGION', 'us-east-1')
    ssm = boto3.client('ssm', region_name=region)

    try:
        response = ssm.get_parameter(
            Name=parameter_name,
            WithDecryption=True
        )
        return response['Parameter']['Value']
    except Exception as e:
        logger.error(f"Failed to retrieve parameter {parameter_name}: {e}")
        raise


def load_config_from_ssm(prefix: str = '/rewards-tracker/') -> dict:
    """
    Load configuration from Parameter Store.

    Args:
        prefix: Parameter Store prefix

    Returns:
        Configuration dictionary
    """
    config = {
        'rewards_tracker': {
            'enabled': True,
            'email': {
                'recipient': get_parameter(f"{prefix}email-recipient"),
                'sender_email': get_parameter(f"{prefix}sender-email"),
                'subject_template': 'Weekly Rewards Report - {date}'
            },
            'point_valuations': {
                'chase_ultimate_rewards': 1.5,
                'amex_membership_rewards': 1.0,
                'capital_one_miles': 1.0,
                'cash_back': 1.0
            },
            'alerts': {
                'annual_fee_warning_days': 60,
                'min_acceptable_roi': 100,
                'expiring_points_days': 90
            }
        }
    }

    return config


def send_ses_email(to_email: str, subject: str, html_body: str, sender_email: str, region: str = None) -> bool:
    """
    Send email via AWS SES.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML email body
        sender_email: Sender email address
        region: AWS region

    Returns:
        True if successful, False otherwise
    """
    region = region or os.environ.get('AWS_REGION', 'us-east-1')
    ses = boto3.client('ses', region_name=region)

    try:
        response = ses.send_email(
            Source=sender_email,
            Destination={
                'ToAddresses': [to_email]
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Html': {
                        'Data': html_body,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        logger.info(f"Email sent successfully. Message ID: {response['MessageId']}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def lambda_handler(event, context):
    """
    AWS Lambda entry point.

    Args:
        event: Lambda event data
        context: Lambda context

    Returns:
        Response dictionary
    """
    logger.info("Starting Credit Card Rewards Tracker Lambda")
    logger.info(f"Event: {json.dumps(event)}")

    try:
        # Load configuration from Parameter Store
        prefix = os.environ.get('PARAM_PREFIX', '/rewards-tracker/')
        config = load_config_from_ssm(prefix)

        # Initialize services
        # Note: In Lambda, data would typically come from S3 or DynamoDB
        # For now, we'll use the local data manager with /tmp
        data_dir = '/tmp/data'
        os.makedirs(data_dir, exist_ok=True)

        # Copy data from S3 if configured
        s3_bucket = os.environ.get('DATA_S3_BUCKET')
        if s3_bucket:
            s3 = boto3.client('s3')
            data_files = ['cards.json', 'rewards_balances.json', 'transactions.json',
                         'redemptions.json', 'annual_summary.json']

            for filename in data_files:
                try:
                    s3_key = f"rewards-tracker/data/{filename}"
                    local_path = f"{data_dir}/{filename}"
                    s3.download_file(s3_bucket, s3_key, local_path)
                    logger.info(f"Downloaded {filename} from S3")
                except Exception as e:
                    logger.warning(f"Could not download {filename}: {e}")

        data_manager = DataManager(data_dir=data_dir)
        card_service = CardService(data_manager, config)
        analyzer = RewardsAnalyzer(data_manager, card_service, config)

        # Generate summary
        logger.info("Generating weekly summary...")
        summary = analyzer.generate_weekly_summary()

        # Generate HTML report
        logger.info("Generating HTML report...")
        report_generator = RewardsReportGenerator(config)
        html_content = report_generator.generate_html_report(summary)

        # Save report to /tmp
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = f'/tmp/rewards_report_{timestamp}.html'
        with open(report_path, 'w') as f:
            f.write(html_content)
        logger.info(f"Report saved to {report_path}")

        # Optionally upload report to S3
        if s3_bucket:
            s3_key = f"rewards-tracker/reports/rewards_report_{timestamp}.html"
            s3.upload_file(report_path, s3_bucket, s3_key)
            logger.info(f"Report uploaded to s3://{s3_bucket}/{s3_key}")

        # Send email
        email_config = config['rewards_tracker']['email']
        recipient = email_config['recipient']
        sender = email_config['sender_email']
        subject = email_config['subject_template'].format(
            date=datetime.now().strftime('%B %d, %Y')
        )

        email_success = send_ses_email(
            to_email=recipient,
            subject=subject,
            html_body=html_content,
            sender_email=sender
        )

        # Prepare response
        total_value = summary.get('total_value', {})
        response_body = {
            'message': 'Weekly rewards report generated successfully',
            'email_sent': email_success,
            'email_recipient': recipient,
            'total_value_cents': total_value.get('combined_cents', 0),
            'report_path': report_path,
            'timestamp': timestamp
        }

        logger.info(f"Lambda completed successfully: {json.dumps(response_body)}")

        return {
            'statusCode': 200,
            'body': json.dumps(response_body)
        }

    except Exception as e:
        logger.error(f"Lambda failed: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to generate rewards report'
            })
        }


# For local testing
if __name__ == '__main__':
    # Simulate Lambda event
    test_event = {
        'source': 'local-test',
        'detail-type': 'Scheduled Event'
    }

    # Mock context
    class MockContext:
        function_name = 'credit-card-rewards-tracker'
        memory_limit_in_mb = 256
        invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789:function:test'

    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
