"""AWS Lambda handler for Weekly Net Worth & Run Rate Report."""

import json
import logging
import os
import sys

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from networth_main import (  # noqa: E402
    generate_report,
    load_config,
    setup_logging,
    validate_configuration,
)


def get_parameter(parameter_name, region=None):
    """Retrieve parameter from AWS SSM Parameter Store."""
    try:
        import boto3
        from botocore.exceptions import ClientError

        if region is None:
            region = os.environ.get("AWS_REGION", "us-east-1")
        client = boto3.session.Session().client("ssm", region_name=region)
        try:
            response = client.get_parameter(Name=parameter_name, WithDecryption=True)
            return response["Parameter"]["Value"]
        except ClientError as e:
            logger.error(f"Failed to retrieve parameter {parameter_name}: {e}")
            return None
    except ImportError:
        logger.warning("boto3 not available")
        return None
    except Exception as e:
        logger.error(f"Error retrieving parameter {parameter_name}: {e}")
        return None


def load_api_keys_from_parameters():
    """Load API keys from Parameter Store into env vars."""
    ynab_key = get_parameter("/networth-report/ynab-api-key")
    if ynab_key:
        os.environ["YNAB_API_KEY"] = ynab_key
        logger.info("Loaded YNAB_API_KEY from Parameter Store")

    budget_id = get_parameter("/networth-report/budget-id")
    if budget_id:
        os.environ["YNAB_BUDGET_ID"] = budget_id
        logger.info("Loaded YNAB_BUDGET_ID from Parameter Store")

    email = get_parameter("/networth-report/email-recipient")
    if email:
        os.environ["NETWORTH_REPORT_EMAIL"] = email
        logger.info("Loaded NETWORTH_REPORT_EMAIL from Parameter Store")

    ses_sender = get_parameter("/networth-report/ses-sender-email")
    if ses_sender:
        os.environ["SES_SENDER_EMAIL"] = ses_sender
        logger.info("Loaded SES_SENDER_EMAIL from Parameter Store")

    # Load Simplifi token
    simplifi_token = get_parameter("/networth-report/simplifi-token")
    if simplifi_token:
        os.environ["SIMPLIFI_TOKEN"] = simplifi_token
        logger.info("Loaded SIMPLIFI_TOKEN from Parameter Store")

    if not ynab_key:
        logger.info("Using API keys from environment variables")


def networth_report_handler(event, context):
    """Lambda handler for weekly net worth report.

    Triggered by EventBridge on Fridays at 6 PM EST.
    """
    logger.info("=" * 60)
    logger.info("WEEKLY NET WORTH REPORT LAMBDA - Starting execution")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 60)

    try:
        load_api_keys_from_parameters()

        config = load_config()
        if "logging" not in config:
            config["logging"] = {}
        config["logging"]["file"] = "/tmp/networth_report.log"

        setup_logging(config)

        if not validate_configuration(config):
            raise ValueError("Configuration validation failed")

        generate_report(config, send_email=True)

        logger.info("Net worth report sent successfully")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Net worth report sent successfully"}),
        }

    except Exception as e:
        logger.error(f"Net worth report failed: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Net worth report failed: {str(e)}"}),
        }


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Testing Net Worth Report Handler")
    print("=" * 60)
    result = networth_report_handler({}, None)
    print(f"Result: {result}")
