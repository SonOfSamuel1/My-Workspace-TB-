#!/bin/bash

# Deploy Amazon-YNAB Reconciler to AWS Lambda using ZIP package
# This script creates a minimal deployment package for Lambda

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Lambda configuration
FUNCTION_NAME="amazon-ynab-reconciler"
RUNTIME="python3.9"
HANDLER="lambda_handler.lambda_handler"
MEMORY_SIZE=512  # Reduced from 3008MB for container
TIMEOUT=300
ROLE_ARN="arn:aws:iam::$(aws sts get-caller-identity --query 'Account' --output text):role/lambda-execution-role"
REGION="${AWS_REGION:-us-east-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Lambda ZIP deployment for Amazon-YNAB Reconciler${NC}"

# Create deployment directory
DEPLOY_DIR="$PROJECT_DIR/deployment"
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

echo -e "${YELLOW}Creating deployment package...${NC}"

# Copy Lambda handler
cp "$PROJECT_DIR/lambda_handler.py" "$DEPLOY_DIR/"

# Copy source code
cp -r "$PROJECT_DIR/src" "$DEPLOY_DIR/"

# Copy config (if exists)
if [ -f "$PROJECT_DIR/config.yaml" ]; then
    cp "$PROJECT_DIR/config.yaml" "$DEPLOY_DIR/"
fi

# Install dependencies to deployment directory
echo -e "${YELLOW}Installing dependencies...${NC}"
pip3 install -q -r "$PROJECT_DIR/requirements.txt" -t "$DEPLOY_DIR/"

# Remove unnecessary files to reduce package size
echo -e "${YELLOW}Optimizing package size...${NC}"
find "$DEPLOY_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$DEPLOY_DIR" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find "$DEPLOY_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find "$DEPLOY_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$DEPLOY_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true

# Create ZIP file
ZIP_FILE="$PROJECT_DIR/lambda-deployment.zip"
cd "$DEPLOY_DIR"
zip -q -r "$ZIP_FILE" .
cd "$PROJECT_DIR"

# Get ZIP file size
ZIP_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo -e "${GREEN}Created deployment package: $ZIP_FILE (${ZIP_SIZE})${NC}"

# Check if Lambda function exists
echo -e "${YELLOW}Checking if Lambda function exists...${NC}"
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &>/dev/null; then
    echo -e "${GREEN}Function exists. Updating code...${NC}"

    # Update function code
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$ZIP_FILE" \
        --region "$REGION" \
        --output json > /dev/null

    # Update function configuration
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --runtime "$RUNTIME" \
        --handler "$HANDLER" \
        --memory-size "$MEMORY_SIZE" \
        --timeout "$TIMEOUT" \
        --environment "Variables={
            USE_EMAIL=true,
            STATE_BUCKET=amazon-ynab-reconciler,
            REPORT_EMAIL=terrancebrandon@me.com
        }" \
        --region "$REGION" \
        --output json > /dev/null

else
    echo -e "${YELLOW}Function doesn't exist. Creating...${NC}"

    # Check if IAM role exists
    if ! aws iam get-role --role-name lambda-execution-role &>/dev/null; then
        echo -e "${YELLOW}Creating IAM role...${NC}"

        # Create trust policy
        cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

        # Create role
        aws iam create-role \
            --role-name lambda-execution-role \
            --assume-role-policy-document file:///tmp/trust-policy.json \
            --output json > /dev/null

        # Attach basic execution policy
        aws iam attach-role-policy \
            --role-name lambda-execution-role \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

        # Create and attach custom policy for SSM, S3, and SES
        cat > /tmp/lambda-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter",
                "ssm:GetParameters"
            ],
            "Resource": "arn:aws:ssm:*:*:parameter/amazon-reconciler/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::amazon-ynab-reconciler/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ses:SendEmail"
            ],
            "Resource": "*"
        }
    ]
}
EOF

        aws iam put-role-policy \
            --role-name lambda-execution-role \
            --policy-name lambda-reconciler-policy \
            --policy-document file:///tmp/lambda-policy.json

        echo -e "${GREEN}IAM role created${NC}"

        # Wait for role to propagate
        sleep 10
    fi

    # Create Lambda function
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime "$RUNTIME" \
        --role "$ROLE_ARN" \
        --handler "$HANDLER" \
        --memory-size "$MEMORY_SIZE" \
        --timeout "$TIMEOUT" \
        --environment "Variables={
            USE_EMAIL=true,
            STATE_BUCKET=amazon-ynab-reconciler,
            REPORT_EMAIL=terrancebrandon@me.com
        }" \
        --zip-file "fileb://$ZIP_FILE" \
        --region "$REGION" \
        --output json > /dev/null
fi

echo -e "${GREEN}Lambda function deployed successfully!${NC}"

# Create S3 bucket for state management if it doesn't exist
echo -e "${YELLOW}Setting up S3 bucket for state management...${NC}"
BUCKET_NAME="amazon-ynab-reconciler"

if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb "s3://$BUCKET_NAME" --region "$REGION"
    echo -e "${GREEN}Created S3 bucket: $BUCKET_NAME${NC}"
else
    echo -e "${GREEN}S3 bucket already exists: $BUCKET_NAME${NC}"
fi

# Set up EventBridge rule for scheduled execution
echo -e "${YELLOW}Setting up EventBridge schedule...${NC}"
RULE_NAME="amazon-ynab-reconciler-daily"

# Create rule (daily at 2 AM ET / 7 AM UTC)
aws events put-rule \
    --name "$RULE_NAME" \
    --schedule-expression "cron(0 7 * * ? *)" \
    --description "Daily Amazon-YNAB reconciliation" \
    --region "$REGION" \
    --output json > /dev/null

# Add Lambda permission for EventBridge
aws lambda add-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id "EventBridgeInvoke" \
    --action "lambda:InvokeFunction" \
    --principal "events.amazonaws.com" \
    --source-arn "arn:aws:events:$REGION:$(aws sts get-caller-identity --query 'Account' --output text):rule/$RULE_NAME" \
    --region "$REGION" 2>/dev/null || true

# Add Lambda as target for the rule
aws events put-targets \
    --rule "$RULE_NAME" \
    --targets "Id"="1","Arn"="arn:aws:lambda:$REGION:$(aws sts get-caller-identity --query 'Account' --output text):function:$FUNCTION_NAME" \
    --region "$REGION" \
    --output json > /dev/null

echo -e "${GREEN}EventBridge schedule configured${NC}"

# Clean up deployment directory
rm -rf "$DEPLOY_DIR"

echo -e "${GREEN}✓ Deployment complete!${NC}"
echo ""
echo "Function Name: $FUNCTION_NAME"
echo "Region: $REGION"
echo "Memory: ${MEMORY_SIZE}MB"
echo "Timeout: ${TIMEOUT}s"
echo "Schedule: Daily at 2 AM ET"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Run setup-parameters.sh to configure AWS Parameter Store"
echo "2. Test the function: aws lambda invoke --function-name $FUNCTION_NAME output.json"
echo "3. Check CloudWatch Logs for execution details"