#!/usr/bin/env python3
"""
AWS Lambda Handler for Homeschool Events Gwinnett

Triggered by EventBridge on Monday at 9:00 AM EST.
Searches for homeschool events and sends weekly email digest.
"""

import json
import logging
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Default configuration
DEFAULT_REGION = "us-east-1"
DEFAULT_SENDER = "brandonhome.appdev@gmail.com"


def get_parameter(parameter_name: str, region: str = None) -> str:
    """Retrieve a parameter from AWS Systems Manager Parameter Store."""
    region = region or os.getenv("AWS_REGION", DEFAULT_REGION)
    ssm = boto3.client("ssm", region_name=region)

    try:
        response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
        return response["Parameter"]["Value"]
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ParameterNotFound":
            logger.warning(f"Parameter not found: {parameter_name}")
            return None
        else:
            logger.error(f"Error retrieving parameter {parameter_name}: {e}")
            raise


def load_config_from_parameters():
    """Load configuration from AWS Parameter Store."""
    logger.info("Loading configuration from Parameter Store...")

    param_mappings = {
        "/homeschool-events/openrouter-api-key": "OPENROUTER_API_KEY",
        "/homeschool-events/email-recipient": "EVENTS_EMAIL_RECIPIENT",
        "/homeschool-events/ses-sender-email": "SES_SENDER_EMAIL",
    }

    for param_name, env_var in param_mappings.items():
        value = get_parameter(param_name)
        if value:
            os.environ[env_var] = value
            logger.info(f"Loaded {env_var} from Parameter Store")
        else:
            logger.warning(f"Parameter {param_name} not found")

    if not os.getenv("AWS_REGION"):
        os.environ["AWS_REGION"] = DEFAULT_REGION

    os.environ["IS_LAMBDA"] = "true"


def homeschool_events_handler(event: dict, context) -> dict:
    """
    Lambda handler for weekly homeschool events digest.

    Triggered by EventBridge on schedule:
    cron(0 14 ? * MON *) = Monday 2:00pm UTC = 9:00am EST
    """
    logger.info("=" * 60)
    logger.info("Homeschool Events Gwinnett Lambda Handler Started")
    logger.info("=" * 60)

    try:
        # Load configuration from Parameter Store
        load_config_from_parameters()

        # Import after path setup
        from events_main import generate_events_email, load_config

        # Load config.yaml
        config = load_config()

        # Validate required configuration
        # OPENROUTER_API_KEY is only required if Perplexity source is enabled
        if not os.getenv("EVENTS_EMAIL_RECIPIENT"):
            raise ValueError("EVENTS_EMAIL_RECIPIENT not configured")

        # Generate and send email
        result = generate_events_email(config, send_email=True, dry_run=False)

        if result["email_sent"]:
            logger.info("Email sent successfully!")
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "Homeschool events digest sent successfully",
                        "events_found": result["events_found"],
                        "subject": result["subject"],
                        "date_range": result["date_range"],
                    }
                ),
            }
        else:
            logger.error("Failed to send email")
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "message": "Failed to send email",
                        "events_found": result["events_found"],
                    }
                ),
            }

    except Exception as e:
        logger.error(f"Error in Lambda handler: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "message": "Error generating homeschool events digest",
                    "error": str(e),
                }
            ),
        }


# For local testing
if __name__ == "__main__":
    result = homeschool_events_handler({}, None)
    print(json.dumps(result, indent=2))
