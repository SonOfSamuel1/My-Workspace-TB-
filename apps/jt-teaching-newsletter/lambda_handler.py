"""AWS Lambda handler for JT Teaching Newsletter.

Triggered by EventBridge at 7:00 AM EST daily (cron: 0 12 * * ? *).
"""

import json
import logging
import os
import sys

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def get_parameter(parameter_name: str, region: str = None) -> str:
    """Retrieve parameter from AWS Systems Manager Parameter Store."""
    try:
        import boto3
        from botocore.exceptions import ClientError

        if region is None:
            region = os.environ.get("AWS_REGION", "us-east-1")

        client = boto3.session.Session().client(service_name="ssm", region_name=region)
        try:
            response = client.get_parameter(Name=parameter_name, WithDecryption=True)
            return response["Parameter"]["Value"]
        except ClientError as e:
            logger.error(f"Failed to retrieve parameter {parameter_name}: {e}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving parameter {parameter_name}: {e}")
        return None


def load_parameters():
    """Load credentials from Parameter Store into environment variables."""
    param_map = {
        "/jt-newsletter/anthropic-api-key": "ANTHROPIC_API_KEY",
        "/jt-newsletter/anthropic-base-url": "ANTHROPIC_BASE_URL",
        "/jt-newsletter/claude-model": "CLAUDE_MODEL",
        "/jt-newsletter/email-recipient": "JT_EMAIL_RECIPIENT",
        "/jt-newsletter/ses-sender-email": "SES_SENDER_EMAIL",
        "/jt-newsletter/s3-bucket": "JT_S3_BUCKET",
    }

    for param_name, env_var in param_map.items():
        value = get_parameter(param_name)
        if value:
            os.environ[env_var] = value
            logger.info(f"Loaded {env_var} from Parameter Store")
        else:
            logger.warning(f"Could not load {param_name}")


def handler(event: dict, context) -> dict:
    """Lambda entry point.

    Args:
        event: EventBridge scheduled event (or {} for manual test)
        context: Lambda context

    Returns:
        Dict with statusCode and body
    """
    logger.info("=" * 60)
    logger.info("JT TEACHING NEWSLETTER LAMBDA — Starting")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 60)

    try:
        # Load secrets from Parameter Store
        logger.info("Loading credentials from Parameter Store...")
        load_parameters()

        # Import after path is set
        from pathlib import Path

        # Load config
        import yaml
        from teaching_main import generate_email, setup_logging

        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Override log file for Lambda (only /tmp is writable)
        if "logging" not in config:
            config["logging"] = {}
        config["logging"]["file"] = "/tmp/jt_newsletter.log"

        setup_logging(config)

        # Generate and send email
        logger.info("Generating daily teachings email...")
        generate_email(config, send_email=True)

        logger.info("=" * 60)
        logger.info("JT Teaching Newsletter sent successfully")
        logger.info("=" * 60)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Daily teachings email sent successfully"}),
        }

    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"message": f"Failed: {str(e)}"})}


# Local testing convenience
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Testing JT Teaching Newsletter Lambda Handler")
    print("=" * 60)
    result = handler({}, None)
    print(f"Result: {result}")
