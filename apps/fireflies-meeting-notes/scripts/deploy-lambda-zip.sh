#!/bin/bash
# Deploy script for Fireflies Meeting Notes Lambda function

set -e

echo "======================================"
echo "Fireflies Meeting Notes - Lambda Deploy"
echo "======================================"
echo ""

# Configuration
FUNCTION_NAME="fireflies-meeting-notes"
RUNTIME="python3.9"
HANDLER="lambda_handler.lambda_handler"
TIMEOUT=120
MEMORY=512
REGION="us-east-1"
ZIP_FILE="fireflies-meeting-notes-lambda.zip"

# Navigate to app root (script lives in scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
cd "$APP_DIR"

# Cleanup previous builds
echo "Cleaning previous builds..."
rm -rf lambda_package
rm -f "$ZIP_FILE"

# Create package directory
echo "Creating package directory..."
mkdir -p lambda_package

# Install Lambda-specific dependencies
echo "Installing dependencies..."
pip3 install \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 39 \
  --only-binary=:all: \
  --target lambda_package/ \
  -r requirements-lambda.txt \
  --quiet

# Copy application code
echo "Copying application code..."
cp -r src/* lambda_package/
cp lambda_handler.py lambda_package/

# Create ZIP package
echo "Creating ZIP package..."
cd lambda_package
zip -r "../$ZIP_FILE" . -q
cd ..

PACKAGE_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo "Package created: $ZIP_FILE ($PACKAGE_SIZE)"

# Check if function exists and update or create
echo ""
echo "Checking if Lambda function exists..."
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &>/dev/null; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$ZIP_FILE" \
        --region "$REGION" \
        --no-cli-pager

    echo "Lambda function updated successfully!"
else
    echo "Lambda function does not exist. Creating..."

    # Try to find an existing execution role
    ROLE_ARN=$(aws iam get-role --role-name LambdaBasicExecutionRole \
        --query 'Role.Arn' --output text 2>/dev/null || echo "")

    if [ -z "$ROLE_ARN" ]; then
        ROLE_ARN=$(aws iam get-role --role-name BudgetReportLambdaRole \
            --query 'Role.Arn' --output text 2>/dev/null || echo "")
    fi

    if [ -z "$ROLE_ARN" ]; then
        echo "Error: No suitable Lambda execution role found."
        echo ""
        echo "Create a role with trust policy for lambda.amazonaws.com and attach:"
        echo "  - AWSLambdaBasicExecutionRole"
        echo "  - AmazonSSMReadOnlyAccess"
        echo "  - AmazonS3FullAccess (or scoped to fireflies-meeting-notes bucket)"
        echo "  - AmazonSESFullAccess (or scoped send permission)"
        exit 1
    fi

    echo "Using role: $ROLE_ARN"

    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime "$RUNTIME" \
        --role "$ROLE_ARN" \
        --handler "$HANDLER" \
        --zip-file "fileb://$ZIP_FILE" \
        --timeout "$TIMEOUT" \
        --memory-size "$MEMORY" \
        --region "$REGION" \
        --environment "Variables={AWS_REGION=$REGION}" \
        --description "Fireflies meeting transcript -> email summary + Todoist tasks + Obsidian notes" \
        --no-cli-pager

    echo "Lambda function created successfully!"
fi

# Cleanup build artifacts
echo ""
echo "Cleaning up..."
rm -rf lambda_package

echo ""
echo "======================================"
echo "Deployment complete!"
echo "======================================"
echo ""
echo "Package: $ZIP_FILE ($PACKAGE_SIZE)"
echo ""
echo "Next steps:"
echo "  1. Ensure Parameter Store keys exist under /fireflies-meeting-notes/"
echo "  2. Ensure S3 bucket 'fireflies-meeting-notes' exists"
echo "  3. Verify SES sender email is verified"
echo "  4. Create a Lambda Function URL (auth type NONE)"
echo "  5. Configure Fireflies webhook to POST to the Function URL"
echo "  6. Test: aws lambda invoke --function-name $FUNCTION_NAME"
echo "           --payload '{\"transcript_id\":\"YOUR_ID\"}' /tmp/out.json"
echo ""
