#!/bin/bash
# Deploy script for Todoist Inbox Manager Lambda function

set -e

echo "======================================"
echo "Todoist Inbox Manager - Lambda Deploy"
echo "======================================"
echo ""

# Configuration
FUNCTION_NAME="todoist-inbox-manager"
RUNTIME="python3.9"
HANDLER="lambda_handler.inbox_manager_handler"
TIMEOUT=60
MEMORY=256
REGION="us-east-1"

# Cleanup previous builds
echo "Cleaning previous builds..."
rm -rf lambda_package
rm -f todoist-inbox-manager-lambda.zip

# Create package directory
echo "Creating package directory..."
mkdir -p lambda_package

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt -t lambda_package/ --quiet

# Copy application code
echo "Copying application code..."
cp -r src/* lambda_package/
cp lambda_handler.py lambda_package/

# Create ZIP package
echo "Creating ZIP package..."
cd lambda_package
zip -r ../todoist-inbox-manager-lambda.zip . -q
cd ..

# Get package size
PACKAGE_SIZE=$(du -h todoist-inbox-manager-lambda.zip | cut -f1)
echo "Package created: todoist-inbox-manager-lambda.zip ($PACKAGE_SIZE)"

# Check if function exists
echo ""
echo "Checking if Lambda function exists..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &> /dev/null; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://todoist-inbox-manager-lambda.zip \
        --region $REGION \
        --no-cli-pager

    echo "Lambda function updated successfully!"
else
    echo "Lambda function does not exist. Creating..."

    # Reuse an existing Lambda execution role
    ROLE_ARN=$(aws iam get-role --role-name TodoistRemindersLambdaRole --query 'Role.Arn' --output text 2>/dev/null || echo "")

    if [ -z "$ROLE_ARN" ]; then
        ROLE_ARN=$(aws iam get-role --role-name LambdaBasicExecutionRole --query 'Role.Arn' --output text 2>/dev/null || echo "")
    fi

    if [ -z "$ROLE_ARN" ]; then
        ROLE_ARN=$(aws iam get-role --role-name BudgetReportLambdaRole --query 'Role.Arn' --output text 2>/dev/null || echo "")
    fi

    if [ -z "$ROLE_ARN" ]; then
        echo "Error: No suitable Lambda execution role found."
        echo ""
        echo "Please create a role with the following trust policy:"
        echo '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
        echo ""
        echo "And attach these policies:"
        echo "  - AWSLambdaBasicExecutionRole"
        echo "  - AmazonSSMReadOnlyAccess"
        exit 1
    fi

    echo "Using role: $ROLE_ARN"

    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --role "$ROLE_ARN" \
        --handler $HANDLER \
        --zip-file fileb://todoist-inbox-manager-lambda.zip \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --region $REGION \
        --environment "Variables={}" \
        --description "Daily Todoist Inbox manager — keeps Inbox under 250 tasks via overflow projects" \
        --no-cli-pager

    echo "Lambda function created successfully!"
fi

# Cleanup
echo ""
echo "Cleaning up..."
rm -rf lambda_package

echo ""
echo "======================================"
echo "Deployment complete!"
echo "======================================"
echo ""
echo "Package: todoist-inbox-manager-lambda.zip ($PACKAGE_SIZE)"
echo ""
echo "Next steps:"
echo "  1. Store the API token in Parameter Store:"
echo "     aws ssm put-parameter \\"
echo "       --name \"/todoist-inbox-manager/api-token\" \\"
echo "       --value \"<TODOIST_API_TOKEN>\" \\"
echo "       --type SecureString"
echo ""
echo "  2. Create an EventBridge rule (daily at 4 AM EST / 9 AM UTC):"
echo "     aws events put-rule \\"
echo "       --name todoist-inbox-manager-daily \\"
echo "       --schedule-expression \"cron(0 9 * * ? *)\" \\"
echo "       --state ENABLED \\"
echo "       --region $REGION"
echo ""
