"""AWS Lambda handler for Todoist CC Task Mover.

Triggered by EventBridge daily at 4:00 AM EST.
Moves tasks prefixed with 'cc-' or 'cc' from Inbox/Inbox 2 to the Claude Code project.
"""

import json
import logging
import os
import sys

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from cc_mover_main import move_cc_tasks, setup_logging  # noqa: E402


def get_parameter(parameter_name: str, region: str = None) -> str:
    """Retrieve a parameter from AWS Systems Manager Parameter Store."""
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
    api_key = get_parameter("/todoist-cc-task-mover/api-token")
    if api_key:
        os.environ["TODOIST_API_TOKEN"] = api_key
        logger.info("Loaded TODOIST_API_TOKEN from Parameter Store")
    else:
        logger.info("Using TODOIST_API_TOKEN from environment variables")


def cc_task_mover_handler(event: dict, context) -> dict:
    """Lambda handler for the Todoist CC Task Mover.

    Args:
        event: Lambda event object from EventBridge
        context: Lambda context object

    Returns:
        Dict with statusCode and body
    """
    logger.info("=" * 60)
    logger.info("TODOIST CC TASK MOVER - Starting execution")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 60)

    try:
        logger.info("Loading API key from Parameter Store...")
        load_api_key_from_parameters()

        api_token = os.environ.get("TODOIST_API_TOKEN")
        if not api_token:
            raise ValueError("TODOIST_API_TOKEN not configured")

        setup_logging()

        logger.info("Running CC task mover...")
        results = move_cc_tasks(api_token=api_token)

        logger.info("=" * 60)
        logger.info("CC task mover completed successfully")
        logger.info(f"  Tasks scanned: {results['tasks_scanned']}")
        logger.info(f"  Tasks moved:   {results['tasks_moved']}")
        logger.info(f"  Sources:       {list(results['source_breakdown'].keys())}")
        if results["errors"]:
            logger.warning(f"  Errors: {results['errors']}")
        logger.info("=" * 60)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "CC task mover completed successfully",
                    "tasks_moved": results["tasks_moved"],
                    "tasks_scanned": results["tasks_scanned"],
                    "source_breakdown": results["source_breakdown"],
                    "errors": results["errors"],
                }
            ),
        }

    except Exception as e:
        logger.error(f"CC task mover failed: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"CC task mover failed: {str(e)}"}),
        }


# For local testing
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Testing CC Task Mover Handler")
    print("=" * 60)
    result = cc_task_mover_handler({}, None)
    print(f"Result: {json.dumps(json.loads(result['body']), indent=2)}")
