#!/bin/bash
# Deploy script for GoFundMe Widow Digest Lambda function
#
# Prerequisites:
# - AWS CLI configured with appropriate credentials
# - Lambda execution role with SSM and CloudWatch permissions
#
# Usage:
#   ./scripts/deploy-lambda-zip.sh [--create]

set -e

FUNCTION_NAME="gofundme-widow-digest"
RUNTIME="python3.11"
HANDLER="lambda_handler.lambda_handler"
TIMEOUT=120
MEMORY=256
REGION="${AWS_REGION:-us-east-1}"
ROLE_NAME="lambda-execution-role"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  GoFundMe Widow Digest - Deploy${NC}"
echo -e "${GREEN}============================================${NC}"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$APP_DIR"

CREATE_FUNCTION=false
if [[ "$1" == "--create" ]]; then
    CREATE_FUNCTION=true
fi

# Step 1: Clean
echo -e "\n${YELLOW}[1/6] Cleaning previous builds...${NC}"
rm -rf package/
rm -f lambda_package.zip
mkdir -p package

# Step 2: Install dependencies
echo -e "\n${YELLOW}[2/6] Installing dependencies...${NC}"
pip3 install -r requirements.txt -t package/ --quiet --upgrade \
    --platform manylinux2014_x86_64 --only-binary=:all: 2>/dev/null || \
    pip3 install -r requirements.txt -t package/ --quiet --upgrade

rm -rf package/*.dist-info package/__pycache__
rm -rf package/boto3* package/botocore* package/s3transfer* package/urllib3*
find package/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find package/ -type f -name "*.pyc" -delete 2>/dev/null || true

# Step 3: Copy source code
echo -e "\n${YELLOW}[3/6] Copying source code...${NC}"
cp -r src/* package/
cp lambda_handler.py package/
cp config.yaml package/

# Step 4: Create ZIP
echo -e "\n${YELLOW}[4/6] Creating ZIP archive...${NC}"
cd package
zip -r ../lambda_package.zip . -x "*.pyc" -x "__pycache__/*" -x "*.dist-info/*" --quiet
cd ..
PACKAGE_SIZE=$(ls -lh lambda_package.zip | awk '{print $5}')
echo -e "   Package size: ${PACKAGE_SIZE}"

# Step 5: Deploy
echo -e "\n${YELLOW}[5/6] Deploying to AWS Lambda...${NC}"
FUNCTION_EXISTS=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION >/dev/null 2>&1 && echo "true" || echo "false")

if [[ "$FUNCTION_EXISTS" == "true" ]]; then
    echo -e "   Updating existing function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda_package.zip \
        --region $REGION \
        --output text > /dev/null
    aws lambda wait function-updated --function-name $FUNCTION_NAME --region $REGION
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --region $REGION \
        --output text > /dev/null
    echo -e "   ${GREEN}Function updated successfully!${NC}"

elif [[ "$CREATE_FUNCTION" == "true" ]]; then
    echo -e "   Creating new function..."
    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null || echo "")
    if [[ -z "$ROLE_ARN" ]]; then
        echo -e "${RED}   Error: IAM role '$ROLE_NAME' not found.${NC}"
        echo -e "   Create it with: AWSLambdaBasicExecutionRole + AmazonSSMReadOnlyAccess"
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
    exit 0
fi

# Step 6: EventBridge schedule (weekly Saturday 10am EST = 3pm UTC)
echo -e "\n${YELLOW}[6/6] Configuring EventBridge schedule...${NC}"
RULE_NAME="gofundme-widow-digest-weekly"
SCHEDULE="cron(0 15 ? * SAT *)"

RULE_EXISTS=$(aws events describe-rule --name $RULE_NAME --region $REGION 2>/dev/null && echo "true" || echo "false")

if [[ "$RULE_EXISTS" == "false" ]]; then
    echo -e "   Creating EventBridge rule..."
    aws events put-rule \
        --name $RULE_NAME \
        --schedule-expression "$SCHEDULE" \
        --state ENABLED \
        --description "Weekly GoFundMe widow digest - Saturday 10am EST" \
        --region $REGION \
        --output text > /dev/null

    LAMBDA_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --query 'Configuration.FunctionArn' --output text)

    aws lambda add-permission \
        --function-name $FUNCTION_NAME \
        --statement-id "gofundme-digest-eventbridge" \
        --action "lambda:InvokeFunction" \
        --principal events.amazonaws.com \
        --source-arn "arn:aws:events:${REGION}:$(aws sts get-caller-identity --query Account --output text):rule/${RULE_NAME}" \
        --region $REGION \
        --output text > /dev/null 2>&1 || true

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
rm -rf package/

echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo -e ""
echo -e "Function: ${FUNCTION_NAME}"
echo -e "Runtime:  ${RUNTIME}"
echo -e "Handler:  ${HANDLER}"
echo -e "Schedule: Saturday 10am EST (weekly)"
echo -e ""
echo -e "To test manually:"
echo -e "  aws lambda invoke --function-name $FUNCTION_NAME --region $REGION output.json"
echo -e ""
echo -e "To view logs:"
echo -e "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $REGION"
