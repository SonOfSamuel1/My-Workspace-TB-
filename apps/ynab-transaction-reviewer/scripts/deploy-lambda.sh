#!/bin/bash

# YNAB Transaction Reviewer - AWS Lambda Deployment Script
# This script packages and deploys the application to AWS Lambda

set -e  # Exit on error

echo "========================================="
echo "YNAB Transaction Reviewer - Lambda Deploy"
echo "========================================="

# Configuration
FUNCTION_NAME="ynab-transaction-reviewer"
REGION="${AWS_REGION:-us-east-1}"
RUNTIME="python3.9"
TIMEOUT="300"  # 5 minutes
MEMORY="512"   # MB
HANDLER="lambda.daily_review_handler.lambda_handler"

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_DIR="$PROJECT_DIR/deployment"
PACKAGE_DIR="$DEPLOYMENT_DIR/package"

echo ""
echo "📦 Step 1: Preparing deployment package..."
echo "----------------------------------------"

# Clean up old deployment
rm -rf "$DEPLOYMENT_DIR"
mkdir -p "$PACKAGE_DIR"

# Copy source code
echo "Copying source code..."
cp -r "$PROJECT_DIR/src" "$PACKAGE_DIR/"
cp -r "$PROJECT_DIR/lambda" "$PACKAGE_DIR/"
cp -r "$PROJECT_DIR/config" "$PACKAGE_DIR/"

# Copy credentials (but not into the package - we'll use Parameter Store)
mkdir -p "$PACKAGE_DIR/credentials"
echo "Note: Gmail credentials will be handled via Lambda layers or S3"

# Install dependencies
echo "Installing dependencies..."
cd "$PACKAGE_DIR"
if [ -f "$PROJECT_DIR/requirements-lambda.txt" ]; then
    python3 -m pip install -t . -r "$PROJECT_DIR/requirements-lambda.txt" --upgrade --quiet
else
    python3 -m pip install -t . -r "$PROJECT_DIR/requirements.txt" --upgrade --quiet
fi

# Remove unnecessary files
echo "Cleaning up package..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
rm -rf boto3* botocore*  # These are provided by Lambda

# Create deployment zip
echo ""
echo "📦 Step 2: Creating deployment ZIP..."
echo "------------------------------------"
cd "$PACKAGE_DIR"
zip -r9q "$DEPLOYMENT_DIR/lambda-package.zip" .
PACKAGE_SIZE=$(du -h "$DEPLOYMENT_DIR/lambda-package.zip" | cut -f1)
echo "Package size: $PACKAGE_SIZE"

# Check if function exists
echo ""
echo "☁️ Step 3: Checking Lambda function..."
echo "-------------------------------------"

if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null; then
    echo "Function exists. Updating code..."

    # Update function code
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$DEPLOYMENT_DIR/lambda-package.zip" \
        --region "$REGION" \
        --output json > /dev/null

    echo "✅ Function code updated!"

    # Update function configuration
    echo "Updating function configuration..."
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --runtime "$RUNTIME" \
        --timeout "$TIMEOUT" \
        --memory-size "$MEMORY" \
        --region "$REGION" \
        --output json > /dev/null

else
    echo "Function does not exist. Creating new function..."
    echo ""
    echo "⚠️  First, you need to create an IAM role for Lambda."
    echo ""
    echo "Run this command to create the role:"
    echo ""
    echo "aws iam create-role --role-name ynab-reviewer-lambda-role \\"
    echo "  --assume-role-policy-document '{"
    echo '    "Version": "2012-10-17",'
    echo '    "Statement": [{'
    echo '      "Effect": "Allow",'
    echo '      "Principal": {"Service": "lambda.amazonaws.com"},'
    echo '      "Action": "sts:AssumeRole"'
    echo '    }]'
    echo "  }'"
    echo ""
    echo "Then attach policies:"
    echo "aws iam attach-role-policy --role-name ynab-reviewer-lambda-role \\"
    echo "  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    echo ""
    echo "aws iam attach-role-policy --role-name ynab-reviewer-lambda-role \\"
    echo "  --policy-arn arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
    echo ""
    echo "After creating the role, run:"
    echo ""
    echo "aws lambda create-function \\"
    echo "  --function-name $FUNCTION_NAME \\"
    echo "  --runtime $RUNTIME \\"
    echo "  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/ynab-reviewer-lambda-role \\"
    echo "  --handler $HANDLER \\"
    echo "  --timeout $TIMEOUT \\"
    echo "  --memory-size $MEMORY \\"
    echo "  --zip-file fileb://$DEPLOYMENT_DIR/lambda-package.zip \\"
    echo "  --region $REGION"
    echo ""
    exit 1
fi

# Store secrets in Parameter Store
echo ""
echo "🔐 Step 4: Storing secrets in Parameter Store..."
echo "-----------------------------------------------"

# Check if parameters exist
if aws ssm get-parameter --name "/ynab-reviewer/ynab-api-key" --region "$REGION" 2>/dev/null; then
    echo "YNAB API key already stored in Parameter Store"
else
    echo "Storing YNAB API key..."
    # Read from .env file
    if [ -f "$PROJECT_DIR/.env" ]; then
        YNAB_KEY=$(grep "YNAB_API_KEY=" "$PROJECT_DIR/.env" | cut -d'=' -f2)
        if [ -n "$YNAB_KEY" ]; then
            aws ssm put-parameter \
                --name "/ynab-reviewer/ynab-api-key" \
                --value "$YNAB_KEY" \
                --type "SecureString" \
                --region "$REGION" \
                --overwrite \
                --output json > /dev/null
            echo "✅ YNAB API key stored"
        fi
    fi
fi

if aws ssm get-parameter --name "/ynab-reviewer/recipient-email" --region "$REGION" 2>/dev/null; then
    echo "Recipient email already stored in Parameter Store"
else
    echo "Storing recipient email..."
    if [ -f "$PROJECT_DIR/.env" ]; then
        EMAIL=$(grep "RECIPIENT_EMAIL=" "$PROJECT_DIR/.env" | cut -d'=' -f2)
        if [ -n "$EMAIL" ]; then
            aws ssm put-parameter \
                --name "/ynab-reviewer/recipient-email" \
                --value "$EMAIL" \
                --type "String" \
                --region "$REGION" \
                --overwrite \
                --output json > /dev/null
            echo "✅ Recipient email stored"
        fi
    fi
fi

# Create or update EventBridge rule
echo ""
echo "⏰ Step 5: Setting up EventBridge schedule..."
echo "--------------------------------------------"

RULE_NAME="ynab-daily-review-5pm"
# Schedule for 5 PM ET daily, excluding Saturday
# Note: EventBridge uses UTC, so 5 PM ET = 9 PM UTC (during EST) or 10 PM UTC (during EDT)
SCHEDULE_EXPRESSION="cron(0 21 ? * SUN,MON,TUE,WED,THU,FRI *)"

# Create or update the rule
aws events put-rule \
    --name "$RULE_NAME" \
    --schedule-expression "$SCHEDULE_EXPRESSION" \
    --description "Daily YNAB transaction review at 5 PM ET (skip Saturday)" \
    --region "$REGION" \
    --output json > /dev/null

echo "✅ EventBridge rule created/updated"

# Add Lambda permission for EventBridge
aws lambda add-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id "AllowEventBridgeInvoke" \
    --action "lambda:InvokeFunction" \
    --principal "events.amazonaws.com" \
    --source-arn "arn:aws:events:$REGION:*:rule/$RULE_NAME" \
    --region "$REGION" 2>/dev/null || true

# Add target to the rule
aws events put-targets \
    --rule "$RULE_NAME" \
    --targets "[{\"Id\":\"1\",\"Arn\":\"arn:aws:lambda:$REGION:$(aws sts get-caller-identity --query Account --output text):function:$FUNCTION_NAME\"}]" \
    --region "$REGION" \
    --output json > /dev/null

echo "✅ EventBridge target configured"

# Clean up
echo ""
echo "🧹 Step 6: Cleaning up..."
echo "------------------------"
rm -rf "$DEPLOYMENT_DIR"

echo ""
echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""
echo "Function: $FUNCTION_NAME"
echo "Region: $REGION"
echo "Schedule: Daily at 5 PM ET (except Saturday)"
echo ""
echo "📝 Next Steps:"
echo "1. Upload Gmail credentials to S3 (secure bucket)"
echo "2. Test the function: aws lambda invoke --function-name $FUNCTION_NAME response.json"
echo "3. Check CloudWatch logs for execution details"
echo ""
echo "To manually trigger:"
echo "  aws lambda invoke --function-name $FUNCTION_NAME response.json --region $REGION"
echo ""
echo "To view logs:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $REGION"
echo ""