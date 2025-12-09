#!/bin/bash
# Deploy script for Weekly Atlanta News Report Lambda function
#
# Prerequisites:
# - AWS CLI configured with appropriate credentials
# - Lambda execution role with SES, SSM, and CloudWatch permissions
#
# Usage:
#   ./deploy_lambda.sh [--create]
#
# Options:
#   --create    Create the Lambda function (first time only)

set -e

# Configuration
FUNCTION_NAME="weekly-atlanta-news-report"
RUNTIME="python3.9"
HANDLER="lambda_handler.atlanta_news_handler"
TIMEOUT=300  # 5 minutes
MEMORY=512   # MB
REGION="${AWS_REGION:-us-east-1}"
ROLE_NAME="lambda-atlanta-news-role"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Weekly Atlanta News Report - Deploy${NC}"
echo -e "${GREEN}============================================${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Parse arguments
CREATE_FUNCTION=false
if [[ "$1" == "--create" ]]; then
    CREATE_FUNCTION=true
fi

# Step 1: Clean previous builds
echo -e "\n${YELLOW}[1/6] Cleaning previous builds...${NC}"
rm -rf package/
rm -f lambda_package.zip
mkdir -p package

# Step 2: Install dependencies
echo -e "\n${YELLOW}[2/6] Installing dependencies...${NC}"
pip install -r requirements.txt -t package/ --quiet --upgrade

# Remove unnecessary files to reduce package size
rm -rf package/*.dist-info
rm -rf package/__pycache__
rm -rf package/boto3*  # boto3 is included in Lambda runtime
rm -rf package/botocore*  # botocore is included in Lambda runtime
rm -rf package/s3transfer*
rm -rf package/urllib3*
find package/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find package/ -type f -name "*.pyc" -delete 2>/dev/null || true

# Step 3: Copy source code
echo -e "\n${YELLOW}[3/6] Copying source code...${NC}"
cp -r src/* package/
cp lambda_handler.py package/
cp config.yaml package/

# Step 4: Create ZIP archive
echo -e "\n${YELLOW}[4/6] Creating ZIP archive...${NC}"
cd package
zip -r ../lambda_package.zip . -x "*.pyc" -x "__pycache__/*" -x "*.dist-info/*" --quiet
cd ..

# Get package size
PACKAGE_SIZE=$(ls -lh lambda_package.zip | awk '{print $5}')
echo -e "   Package size: ${PACKAGE_SIZE}"

# Step 5: Deploy to Lambda
echo -e "\n${YELLOW}[5/6] Deploying to AWS Lambda...${NC}"

# Check if function exists
FUNCTION_EXISTS=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null && echo "true" || echo "false")

if [[ "$FUNCTION_EXISTS" == "true" ]]; then
    echo -e "   Updating existing function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda_package.zip \
        --region $REGION \
        --output text > /dev/null

    # Wait for update to complete
    aws lambda wait function-updated --function-name $FUNCTION_NAME --region $REGION

    # Update configuration
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --region $REGION \
        --output text > /dev/null

    echo -e "   ${GREEN}Function updated successfully!${NC}"

elif [[ "$CREATE_FUNCTION" == "true" ]]; then
    echo -e "   Creating new function..."

    # Get role ARN
    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null || echo "")

    if [[ -z "$ROLE_ARN" ]]; then
        echo -e "${RED}   Error: IAM role '$ROLE_NAME' not found.${NC}"
        echo -e "   Please create the role with the following permissions:"
        echo -e "   - AWSLambdaBasicExecutionRole"
        echo -e "   - AmazonSESFullAccess (or custom SES policy)"
        echo -e "   - AmazonSSMReadOnlyAccess"
        exit 1
    fi

    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --handler $HANDLER \
        --role $ROLE_ARN \
        --zip-file fileb://lambda_package.zip \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --region $REGION \
        --output text > /dev/null

    echo -e "   ${GREEN}Function created successfully!${NC}"
else
    echo -e "${YELLOW}   Function does not exist. Use --create flag to create it.${NC}"
    echo -e "   Example: ./deploy_lambda.sh --create"
    exit 0
fi

# Step 6: Set up EventBridge schedule
echo -e "\n${YELLOW}[6/6] Configuring EventBridge schedule...${NC}"

RULE_NAME="atlanta-news-weekly-schedule"
# Friday at 11:30pm UTC = 6:30pm EST
SCHEDULE="cron(30 23 ? * FRI *)"

# Check if rule exists
RULE_EXISTS=$(aws events describe-rule --name $RULE_NAME --region $REGION 2>/dev/null && echo "true" || echo "false")

if [[ "$RULE_EXISTS" == "false" ]]; then
    echo -e "   Creating EventBridge rule..."
    aws events put-rule \
        --name $RULE_NAME \
        --schedule-expression "$SCHEDULE" \
        --state ENABLED \
        --description "Trigger Atlanta news report every Friday at 6:30pm EST" \
        --region $REGION \
        --output text > /dev/null

    # Get Lambda ARN
    LAMBDA_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --query 'Configuration.FunctionArn' --output text)

    # Add permission for EventBridge to invoke Lambda
    aws lambda add-permission \
        --function-name $FUNCTION_NAME \
        --statement-id "atlanta-news-eventbridge" \
        --action "lambda:InvokeFunction" \
        --principal events.amazonaws.com \
        --source-arn "arn:aws:events:${REGION}:$(aws sts get-caller-identity --query Account --output text):rule/${RULE_NAME}" \
        --region $REGION \
        --output text > /dev/null 2>&1 || true

    # Add Lambda as target
    aws events put-targets \
        --rule $RULE_NAME \
        --targets "Id"="1","Arn"="$LAMBDA_ARN" \
        --region $REGION \
        --output text > /dev/null

    echo -e "   ${GREEN}EventBridge rule created!${NC}"
else
    echo -e "   EventBridge rule already exists."
fi

# Cleanup
echo -e "\n${YELLOW}Cleaning up...${NC}"
rm -rf package/

# Summary
echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo -e ""
echo -e "Function: ${FUNCTION_NAME}"
echo -e "Runtime:  ${RUNTIME}"
echo -e "Handler:  ${HANDLER}"
echo -e "Timeout:  ${TIMEOUT}s"
echo -e "Memory:   ${MEMORY}MB"
echo -e "Schedule: Friday 6:30pm EST"
echo -e ""
echo -e "To test manually:"
echo -e "  aws lambda invoke --function-name $FUNCTION_NAME --region $REGION output.json"
echo -e ""
echo -e "To view logs:"
echo -e "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $REGION"
echo -e ""
