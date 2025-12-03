#!/bin/bash
# Deploy Sleep Eight Reporter to AWS Lambda
# ==========================================
#
# This script packages the application and deploys it to AWS Lambda.
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - Lambda function already created in AWS Console
#
# Usage: ./scripts/deploy-lambda-zip.sh

set -e

# Configuration
FUNCTION_NAME="sleep-eight-reporter"
RUNTIME="python3.9"
HANDLER="lambda_handler.daily_sleep_report_handler"
TIMEOUT=120
MEMORY=512
REGION="${AWS_REGION:-us-east-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Sleep Eight Reporter - Lambda Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Clean up any existing package
echo -e "\n${YELLOW}Cleaning up previous build...${NC}"
rm -rf lambda_package
rm -f sleep-eight-reporter-lambda.zip

# Create package directory
echo -e "${YELLOW}Creating package directory...${NC}"
mkdir -p lambda_package

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt -t lambda_package/ --quiet --upgrade

# Copy application code
echo -e "${YELLOW}Copying application code...${NC}"
cp -r src/* lambda_package/
cp lambda_handler.py lambda_package/
cp config.yaml lambda_package/

# Create ZIP file
echo -e "${YELLOW}Creating deployment package...${NC}"
cd lambda_package
zip -r ../sleep-eight-reporter-lambda.zip . -q
cd ..

# Get package size
PACKAGE_SIZE=$(du -h sleep-eight-reporter-lambda.zip | cut -f1)
echo -e "${GREEN}Package created: sleep-eight-reporter-lambda.zip (${PACKAGE_SIZE})${NC}"

# Check if function exists
echo -e "\n${YELLOW}Checking Lambda function...${NC}"
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" &> /dev/null; then
    echo -e "${GREEN}Function exists. Updating code...${NC}"

    # Update function code
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://sleep-eight-reporter-lambda.zip" \
        --region "$REGION" \
        --output text > /dev/null

    echo -e "${GREEN}Function code updated successfully!${NC}"

    # Wait for update to complete
    echo -e "${YELLOW}Waiting for update to complete...${NC}"
    aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"

    # Update function configuration
    echo -e "${YELLOW}Updating function configuration...${NC}"
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --timeout "$TIMEOUT" \
        --memory-size "$MEMORY" \
        --runtime "$RUNTIME" \
        --handler "$HANDLER" \
        --region "$REGION" \
        --output text > /dev/null

    echo -e "${GREEN}Function configuration updated!${NC}"

else
    echo -e "${RED}Function '$FUNCTION_NAME' does not exist.${NC}"
    echo -e "${YELLOW}Please create the Lambda function first using AWS Console or CLI.${NC}"
    echo ""
    echo "To create the function, run:"
    echo ""
    echo "  aws lambda create-function \\"
    echo "    --function-name $FUNCTION_NAME \\"
    echo "    --runtime $RUNTIME \\"
    echo "    --handler $HANDLER \\"
    echo "    --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-sleep-eight-role \\"
    echo "    --timeout $TIMEOUT \\"
    echo "    --memory-size $MEMORY \\"
    echo "    --zip-file fileb://sleep-eight-reporter-lambda.zip \\"
    echo "    --region $REGION"
    echo ""
    exit 1
fi

# Clean up
echo -e "\n${YELLOW}Cleaning up...${NC}"
rm -rf lambda_package

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\nNext steps:"
echo "1. Set up Parameter Store keys (see setup-parameters.sh)"
echo "2. Create EventBridge rule for daily trigger"
echo "3. Test the function: aws lambda invoke --function-name $FUNCTION_NAME response.json"
