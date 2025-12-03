#!/usr/bin/env python3
"""Deploy script for Todoist Daily Reminders Lambda function using boto3."""

import os
import sys
import shutil
import subprocess
import zipfile
import boto3
from botocore.exceptions import ClientError

# Configuration
FUNCTION_NAME = "todoist-daily-reminders"
RUNTIME = "python3.9"
HANDLER = "lambda_handler.daily_reminders_handler"
TIMEOUT = 60
MEMORY = 256
REGION = "us-east-1"
DESCRIPTION = "Daily reminders for Todoist tasks with @commit label"

# EventBridge configuration
RULE_NAME = "todoist-daily-reminders-schedule"
# Run at 6am EST (11am UTC) daily
SCHEDULE_EXPRESSION = "cron(0 11 * * ? *)"


def create_deployment_package():
    """Create the Lambda deployment ZIP package."""
    print("=" * 50)
    print("Creating deployment package...")
    print("=" * 50)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    package_dir = os.path.join(script_dir, "lambda_package")
    zip_path = os.path.join(script_dir, "todoist-reminders-lambda.zip")

    # Cleanup
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
    if os.path.exists(zip_path):
        os.remove(zip_path)

    os.makedirs(package_dir)

    # Install dependencies
    print("Installing dependencies...")
    requirements_path = os.path.join(script_dir, "requirements.txt")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", requirements_path,
         "-t", package_dir, "--quiet"],
        check=True
    )

    # Copy source files
    print("Copying source files...")
    src_dir = os.path.join(script_dir, "src")
    for item in os.listdir(src_dir):
        src_path = os.path.join(src_dir, item)
        dst_path = os.path.join(package_dir, item)
        if os.path.isfile(src_path):
            shutil.copy2(src_path, dst_path)

    # Copy lambda handler
    shutil.copy2(
        os.path.join(script_dir, "lambda_handler.py"),
        os.path.join(package_dir, "lambda_handler.py")
    )

    # Create ZIP
    print("Creating ZIP package...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, package_dir)
                zipf.write(file_path, arcname)

    # Cleanup package directory
    shutil.rmtree(package_dir)

    # Get package size
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"Package created: {zip_path} ({size_mb:.1f} MB)")

    return zip_path


def get_or_create_lambda_role(iam_client):
    """Get existing Lambda role or create a new one."""
    role_name = "TodoistRemindersLambdaRole"

    try:
        response = iam_client.get_role(RoleName=role_name)
        print(f"Using existing role: {role_name}")
        return response['Role']['Arn']
    except ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchEntity':
            raise

    print(f"Creating new role: {role_name}...")

    # Trust policy for Lambda
    trust_policy = """{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }"""

    # Create the role
    response = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=trust_policy,
        Description="Execution role for Todoist Daily Reminders Lambda"
    )
    role_arn = response['Role']['Arn']

    # Attach required policies
    policies = [
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
    ]

    for policy_arn in policies:
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn
        )
        print(f"  Attached policy: {policy_arn.split('/')[-1]}")

    # Wait for role to propagate
    print("Waiting for role to propagate...")
    import time
    time.sleep(10)

    return role_arn


def deploy_lambda(zip_path, role_arn):
    """Deploy or update the Lambda function."""
    print("=" * 50)
    print("Deploying Lambda function...")
    print("=" * 50)

    lambda_client = boto3.client('lambda', region_name=REGION)

    with open(zip_path, 'rb') as f:
        zip_content = f.read()

    try:
        # Try to update existing function
        lambda_client.get_function(FunctionName=FUNCTION_NAME)
        print(f"Updating existing function: {FUNCTION_NAME}")

        lambda_client.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=zip_content
        )
        print("Function code updated successfully!")

    except ClientError as e:
        if e.response['Error']['Code'] != 'ResourceNotFoundException':
            raise

        # Create new function
        print(f"Creating new function: {FUNCTION_NAME}")

        lambda_client.create_function(
            FunctionName=FUNCTION_NAME,
            Runtime=RUNTIME,
            Role=role_arn,
            Handler=HANDLER,
            Code={'ZipFile': zip_content},
            Description=DESCRIPTION,
            Timeout=TIMEOUT,
            MemorySize=MEMORY,
            Environment={
                'Variables': {
                    'AWS_REGION_NAME': REGION
                }
            }
        )
        print("Function created successfully!")

    # Get function ARN
    response = lambda_client.get_function(FunctionName=FUNCTION_NAME)
    return response['Configuration']['FunctionArn']


def create_eventbridge_schedule(function_arn):
    """Create EventBridge rule to trigger Lambda daily."""
    print("=" * 50)
    print("Creating EventBridge schedule...")
    print("=" * 50)

    events_client = boto3.client('events', region_name=REGION)
    lambda_client = boto3.client('lambda', region_name=REGION)

    # Create or update the rule
    try:
        events_client.put_rule(
            Name=RULE_NAME,
            ScheduleExpression=SCHEDULE_EXPRESSION,
            State='ENABLED',
            Description="Trigger Todoist daily reminders at 6am EST"
        )
        print(f"Rule created/updated: {RULE_NAME}")
        print(f"Schedule: {SCHEDULE_EXPRESSION} (6am EST / 11am UTC)")
    except ClientError as e:
        print(f"Error creating rule: {e}")
        raise

    # Add Lambda as target
    try:
        events_client.put_targets(
            Rule=RULE_NAME,
            Targets=[{
                'Id': 'todoist-reminders-target',
                'Arn': function_arn
            }]
        )
        print("Lambda target added to rule")
    except ClientError as e:
        print(f"Error adding target: {e}")
        raise

    # Add permission for EventBridge to invoke Lambda
    try:
        lambda_client.add_permission(
            FunctionName=FUNCTION_NAME,
            StatementId='eventbridge-daily-trigger',
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com',
            SourceArn=f"arn:aws:events:{REGION}:{boto3.client('sts').get_caller_identity()['Account']}:rule/{RULE_NAME}"
        )
        print("Lambda permission added for EventBridge")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            print("Lambda permission already exists")
        else:
            raise

    print("EventBridge schedule configured successfully!")


def setup_parameter_store():
    """Check and prompt for Parameter Store setup."""
    print("=" * 50)
    print("Checking Parameter Store...")
    print("=" * 50)

    ssm_client = boto3.client('ssm', region_name=REGION)

    param_name = '/todoist-reminders/api-token'

    try:
        ssm_client.get_parameter(Name=param_name, WithDecryption=True)
        print(f"Parameter exists: {param_name}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ParameterNotFound':
            print(f"Parameter NOT found: {param_name}")
            print("")
            print("Please create it with:")
            print(f"  aws ssm put-parameter --name \"{param_name}\" \\")
            print("    --type SecureString --value \"YOUR_TODOIST_API_TOKEN\"")
            print("")
            print("Or via boto3:")
            print("  ssm.put_parameter(")
            print(f"    Name='{param_name}',")
            print("    Value='YOUR_API_TOKEN',")
            print("    Type='SecureString'")
            print("  )")
            return False
        raise

    return True


def test_lambda():
    """Test the Lambda function with a test invocation."""
    print("=" * 50)
    print("Testing Lambda function...")
    print("=" * 50)

    lambda_client = boto3.client('lambda', region_name=REGION)

    try:
        response = lambda_client.invoke(
            FunctionName=FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=b'{}'
        )

        payload = response['Payload'].read().decode('utf-8')
        print(f"Response: {payload}")

        if response.get('FunctionError'):
            print(f"Function error: {response['FunctionError']}")
            return False

        print("Test completed successfully!")
        return True

    except ClientError as e:
        print(f"Error invoking function: {e}")
        return False


def main():
    """Main deployment function."""
    print("")
    print("=" * 50)
    print("TODOIST DAILY REMINDERS - DEPLOYMENT")
    print("=" * 50)
    print("")

    # Create deployment package
    zip_path = create_deployment_package()

    # Get or create IAM role
    print("")
    iam_client = boto3.client('iam')
    role_arn = get_or_create_lambda_role(iam_client)

    # Deploy Lambda
    print("")
    function_arn = deploy_lambda(zip_path, role_arn)

    # Create EventBridge schedule
    print("")
    create_eventbridge_schedule(function_arn)

    # Check Parameter Store
    print("")
    param_exists = setup_parameter_store()

    # Test if parameter exists
    if param_exists:
        print("")
        test_lambda()

    print("")
    print("=" * 50)
    print("DEPLOYMENT COMPLETE!")
    print("=" * 50)
    print("")
    print(f"Function: {FUNCTION_NAME}")
    print(f"Schedule: Daily at 6:00 AM EST")
    print(f"Region: {REGION}")
    print("")

    if not param_exists:
        print("ACTION REQUIRED: Set up the Todoist API token in Parameter Store")
        print("")


if __name__ == "__main__":
    main()
