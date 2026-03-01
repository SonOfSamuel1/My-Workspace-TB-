#!/bin/bash
# Deploy Todoist Inbox Digest Lambda function using ZIP package

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWS_REGION=${AWS_REGION:-us-east-1}
FUNCTION_NAME="todoist-inbox-digest"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ZIP_FILE="$PROJECT_DIR/todoist-inbox-digest-lambda.zip"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Todoist Inbox Digest - Lambda Deployment${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Create deployment package
echo -e "${YELLOW}Step 1: Creating deployment package...${NC}"

BUILD_DIR=$(mktemp -d)
echo "Build directory: $BUILD_DIR"

# Install dependencies (Linux x86_64 binaries for Lambda)
echo "Installing dependencies..."
pip3 install \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    -r "$PROJECT_DIR/requirements.txt" \
    -t "$BUILD_DIR" \
    --quiet 2>/dev/null || true

# Copy application code (src/ contents go to root for Lambda imports)
echo "Copying application code..."
cp "$PROJECT_DIR"/src/*.py "$BUILD_DIR/"
cp "$PROJECT_DIR/lambda_handler.py" "$BUILD_DIR/" 2>/dev/null || true

# Create ZIP file
cd "$BUILD_DIR"
echo "Creating ZIP archive..."
zip -r9q "$ZIP_FILE" .
cd "$PROJECT_DIR"

# Clean up
rm -rf "$BUILD_DIR"

echo -e "${GREEN}✓ Deployment package created: $(basename "$ZIP_FILE")${NC}"
ZIP_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo "Package size: $ZIP_SIZE"
echo ""

# Update Lambda function code
echo -e "${YELLOW}Step 2: Updating Lambda function code...${NC}"
aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --zip-file "fileb://$ZIP_FILE" \
    --region $AWS_REGION \
    > /dev/null

echo -e "${GREEN}✓ Lambda function code updated${NC}"
echo ""

# Wait for update to complete
echo -e "${YELLOW}Step 3: Waiting for update to complete...${NC}"
aws lambda wait function-updated \
    --function-name $FUNCTION_NAME \
    --region $AWS_REGION

echo -e "${GREEN}✓ Function update complete${NC}"
echo ""

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "Function: $FUNCTION_NAME"
echo "Package:  $(basename "$ZIP_FILE") ($ZIP_SIZE)"
echo ""
echo "Test web dashboard:"
echo "  Open: <function-url>?action=web&token=<action-token>"
echo ""
echo "Test daily digest (manual trigger):"
echo "  aws lambda invoke --function-name $FUNCTION_NAME --payload '{\"mode\":\"daily_digest\"}' /dev/stdout"
echo ""
echo "View logs:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
