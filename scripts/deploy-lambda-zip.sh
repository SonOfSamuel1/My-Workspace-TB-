#!/bin/bash
# Deploy Lambda function using ZIP package instead of container

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWS_REGION=${AWS_REGION:-us-east-1}
FUNCTION_NAME="love-brittany-weekly-report"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Lambda ZIP Deployment${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Create deployment package
echo -e "${YELLOW}Step 1: Creating deployment package...${NC}"

# Create a temporary directory
BUILD_DIR=$(mktemp -d)
echo "Build directory: $BUILD_DIR"

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt -t "$BUILD_DIR" --quiet

# Copy application code
echo "Copying application code..."
cp -r src "$BUILD_DIR/"
cp lambda_handler.py "$BUILD_DIR/"
cp config.yaml "$BUILD_DIR/"

# Create ZIP file
cd "$BUILD_DIR"
echo "Creating ZIP archive..."
zip -r9q ../lambda-deployment.zip .
cd -
mv "$BUILD_DIR/../lambda-deployment.zip" ./lambda-deployment.zip

# Clean up
rm -rf "$BUILD_DIR"

echo -e "${GREEN}✓ Deployment package created: lambda-deployment.zip${NC}"
ZIP_SIZE=$(du -h lambda-deployment.zip | cut -f1)
echo "Package size: $ZIP_SIZE"
echo ""

# Delete old container-based function if it exists
echo -e "${YELLOW}Step 2: Removing old container-based function...${NC}"
aws lambda delete-function --function-name $FUNCTION_NAME --region $AWS_REGION 2>/dev/null && echo -e "${GREEN}✓ Old function deleted${NC}" || echo -e "${YELLOW}No existing function found${NC}"
echo ""

# Wait a moment for deletion to complete
sleep 3

# Create new ZIP-based Lambda function
echo -e "${YELLOW}Step 3: Creating Lambda function...${NC}"

ROLE_ARN=$(aws iam get-role --role-name LoveBrittanyLambdaRole --query 'Role.Arn' --output text)

aws lambda create-function \
    --function-name $FUNCTION_NAME \
    --runtime python3.9 \
    --role $ROLE_ARN \
    --handler lambda_handler.weekly_report_handler \
    --zip-file fileb://lambda-deployment.zip \
    --timeout 900 \
    --memory-size 512 \
    --environment "Variables={RECIPIENT_EMAIL=terrance@goodportion.org}" \
    --description "Weekly relationship tracking report - sends comprehensive email every Sunday at 4 AM EST" \
    --region $AWS_REGION \
    > /dev/null

echo -e "${GREEN}✓ Lambda function created${NC}"
echo ""

# Re-add EventBridge permission
echo -e "${YELLOW}Step 4: Adding EventBridge permission...${NC}"
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id AllowEventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:$AWS_REGION:$(aws sts get-caller-identity --query Account --output text):rule/$FUNCTION_NAME" \
    --region $AWS_REGION \
    > /dev/null 2>&1

echo -e "${GREEN}✓ EventBridge permission added${NC}"
echo ""

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "Function: $FUNCTION_NAME"
echo "Runtime: Python 3.9 (ZIP package)"
echo "Schedule: Sundays at 4:00 AM EST"
echo ""
echo "Test the function:"
echo "  ./scripts/test-lambda.sh"
echo ""
echo "View logs:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
