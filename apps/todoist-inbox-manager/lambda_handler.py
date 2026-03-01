"""AWS Lambda handler for Todoist Inbox Manager automation.

Triggered by EventBridge daily at 4:00 AM EST.
Keeps the Inbox under 250 tasks by moving the oldest tasks to overflow
projects and maintaining a navigator task with live overflow counts.
"""

import json
import logging
import os
import sys

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from inbox_main import DEFAULT_TIMEZONE, manage_inbox, setup_logging  # noqa: E402


def get_parameter(parameter_name: str, region: str = None) -> str:
    """Retrieve a parameter from AWS Systems Manager Parameter Store.

    Args:
        parameter_name: Name of the parameter in Parameter Store
        region: AWS region (defaults to environment variable or us-east-1)

    Returns:
        Parameter value as string, or None if retrieval fails
    """
    try:
        import boto3
        from botocore.exceptions import ClientError

        if region is None:
            region = os.environ.get("AWS_REGION", "us-east-1")

        session = boto3.session.Session()
        client = session.client(service_name="ssm", region_name=region)

        try:
            response = client.get_parameter(
                Name=parameter_name,
                WithDecryption=True,
            )
            return response["Parameter"]["Value"]
        except ClientError as e:
            logger.error(f"Failed to retrieve parameter {parameter_name}: {e}")
            return None
    except ImportError:
        logger.warning("boto3 not available, skipping Parameter Store integration")
        return None
    except Exception as e:
        logger.error(f"Error retrieving parameter {parameter_name}: {e}")
        return None


def load_api_key_from_parameters() -> None:
    """Load Todoist API key from Parameter Store into the environment."""
    api_key = get_parameter("/todoist-inbox-manager/api-token")
    if api_key:
        os.environ["TODOIST_API_TOKEN"] = api_key
        logger.info("Loaded TODOIST_API_TOKEN from Parameter Store")
    else:
        logger.info("Using TODOIST_API_TOKEN from environment variables")

    timezone = get_parameter("/todoist-inbox-manager/timezone")
    if timezone:
        os.environ["TODOIST_TIMEZONE"] = timezone
        logger.info(f"Loaded TODOIST_TIMEZONE from Parameter Store: {timezone}")


def inbox_manager_handler(event: dict, context) -> dict:
    """Lambda handler for the Todoist Inbox Manager.

    Triggered by EventBridge daily at 4:00 AM EST.

    Args:
        event: Lambda event object from EventBridge
        context: Lambda context object

    Returns:
        Dict with statusCode and body
    """
    logger.info("=" * 60)
    logger.info("TODOIST INBOX MANAGER LAMBDA - Starting execution")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 60)

    try:
        # Load secrets from Parameter Store
        logger.info("Loading API key from Parameter Store...")
        load_api_key_from_parameters()

        # Get API token
        api_token = os.environ.get("TODOIST_API_TOKEN")
        if not api_token:
            raise ValueError("TODOIST_API_TOKEN not configured")

        timezone_str = os.environ.get("TODOIST_TIMEZONE", DEFAULT_TIMEZONE)

        logger.info("Configuration:")
        logger.info(f"  Timezone: {timezone_str}")

        setup_logging()

        logger.info("Running inbox manager...")
        results = manage_inbox(api_token=api_token, timezone_str=timezone_str)

        logger.info("=" * 60)
        logger.info("Inbox manager completed successfully")
        logger.info(f"  Tasks moved:       {results['tasks_moved']}")
        logger.info(f"  Inbox before:      {results['inbox_count_before']}")
        logger.info(f"  Inbox after:       {results['inbox_count_after']}")
        logger.info(f"  Navigator action:  {results['navigator_action']}")
        logger.info(f"  Overflow projects: {len(results['overflow_projects'])}")
        if results["errors"]:
            logger.warning(f"  Errors: {results['errors']}")
        logger.info("=" * 60)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Inbox manager completed successfully",
                    "tasks_moved": results["tasks_moved"],
                    "inbox_count_before": results["inbox_count_before"],
                    "inbox_count_after": results["inbox_count_after"],
                    "navigator_action": results["navigator_action"],
                    "overflow_projects": results["overflow_projects"],
                    "errors": results["errors"],
                }
            ),
        }

    except Exception as e:
        logger.error(f"Inbox manager failed: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Inbox manager failed: {str(e)}"}),
        }


# For local testing
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Testing Inbox Manager Handler")
    print("=" * 60)
    result = inbox_manager_handler({}, None)
    print(f"Result: {json.dumps(json.loads(result['body']), indent=2)}")
