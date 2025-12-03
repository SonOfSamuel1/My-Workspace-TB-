#!/bin/bash
# Deploy script for Todoist Daily Reminders Lambda function

set -e

echo "======================================"
echo "Todoist Daily Reminders - Lambda Deploy"
echo "======================================"
echo ""

# Configuration
FUNCTION_NAME="todoist-daily-reminders"
RUNTIME="python3.9"
HANDLER="lambda_handler.daily_reminders_handler"
TIMEOUT=60
MEMORY=256
REGION="us-east-1"

# Cleanup previous builds
echo "Cleaning previous builds..."
rm -rf lambda_package
rm -f todoist-reminders-lambda.zip

# Create package directory
echo "Creating package directory..."
mkdir -p lambda_package

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -t lambda_package/ --quiet

# Copy application code
echo "Copying application code..."
cp -r src/* lambda_package/
cp lambda_handler.py lambda_package/

# Create ZIP package
echo "Creating ZIP package..."
cd lambda_package
zip -r ../todoist-reminders-lambda.zip . -q
cd ..

# Get package size
PACKAGE_SIZE=$(du -h todoist-reminders-lambda.zip | cut -f1)
echo "Package created: todoist-reminders-lambda.zip ($PACKAGE_SIZE)"

# Check if function exists
echo ""
echo "Checking if Lambda function exists..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &> /dev/null; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://todoist-reminders-lambda.zip \
        --region $REGION \
        --no-cli-pager

    echo "Lambda function updated successfully!"
else
    echo "Lambda function does not exist. Creating..."

    # Get the existing Lambda role (reuse from other functions)
    ROLE_ARN=$(aws iam get-role --role-name LambdaBasicExecutionRole --query 'Role.Arn' --output text 2>/dev/null || echo "")

    if [ -z "$ROLE_ARN" ]; then
        # Try alternative role names
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
        --zip-file fileb://todoist-reminders-lambda.zip \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --region $REGION \
        --environment "Variables={AWS_REGION=$REGION}" \
        --description "Daily reminders for Todoist tasks with @commit label" \
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
echo "Package: todoist-reminders-lambda.zip ($PACKAGE_SIZE)"
echo ""
