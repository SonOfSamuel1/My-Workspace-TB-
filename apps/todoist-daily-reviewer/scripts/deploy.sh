#!/bin/bash
# Deploy todoist-daily-reviewer Lambda function

set -e

AWS_REGION=${AWS_REGION:-us-east-1}
FUNCTION_NAME="todoist-daily-reviewer"

echo "========================================"
echo "Deploying todoist-daily-reviewer Lambda"
echo "========================================"

# Create deployment package
echo "Creating deployment package..."
BUILD_DIR=$(mktemp -d)

# Copy source files
cp -r src "$BUILD_DIR/"
cp -r config "$BUILD_DIR/" 2>/dev/null || true
cp package.json "$BUILD_DIR/"

# Install production dependencies
cd "$BUILD_DIR"
npm install --production --quiet

# Create ZIP
echo "Creating ZIP archive..."
zip -r9q ../lambda.zip .
cd -
mv "$BUILD_DIR/../lambda.zip" ./lambda.zip

# Clean up
rm -rf "$BUILD_DIR"

ZIP_SIZE=$(du -h lambda.zip | cut -f1)
echo "Package size: $ZIP_SIZE"

# Update Lambda function
echo "Updating Lambda function..."
aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --zip-file fileb://lambda.zip \
    --region $AWS_REGION \
    --output text --query 'FunctionArn'

echo ""
echo "========================================"
echo "Deployment complete!"
echo "========================================"
