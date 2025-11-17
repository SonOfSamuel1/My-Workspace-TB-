#!/bin/bash
#
# Deploy Toggl Daily Report to AWS Lambda using ZIP package
#
# This script creates a Lambda deployment package and uploads it to AWS Lambda.
# It includes all dependencies and source code in a single ZIP file.
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LAMBDA_FUNCTION_NAME="toggl-daily-report"
PACKAGE_DIR="$PROJECT_DIR/lambda-package"
ZIP_FILE="$PROJECT_DIR/lambda-deployment.zip"

echo "=================================="
echo "Toggl Daily Report - Lambda Deploy"
echo "=================================="
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed"
    echo "Install it with: pip install awscli"
    exit 1
fi

# Clean up previous builds
echo "1. Cleaning up previous builds..."
rm -rf "$PACKAGE_DIR"
rm -f "$ZIP_FILE"

# Create package directory
echo "2. Creating package directory..."
mkdir -p "$PACKAGE_DIR"

# Install dependencies
echo "3. Installing Python dependencies..."
pip install -r "$PROJECT_DIR/requirements.txt" -t "$PACKAGE_DIR" --upgrade

# Copy source code
echo "4. Copying source code..."
cp -r "$PROJECT_DIR/src/"* "$PACKAGE_DIR/"
cp "$PROJECT_DIR/lambda_handler.py" "$PACKAGE_DIR/"
cp "$PROJECT_DIR/config.yaml" "$PACKAGE_DIR/"

# Create ZIP package
echo "5. Creating ZIP package..."
cd "$PACKAGE_DIR"
zip -r "$ZIP_FILE" . -x "*.pyc" -x "__pycache__/*" -x "*.git/*"
cd "$PROJECT_DIR"

# Get package size
PACKAGE_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo "   Package size: $PACKAGE_SIZE"

# Upload to Lambda
echo "6. Uploading to AWS Lambda..."
aws lambda update-function-code \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_FILE" \
    --region us-east-1

echo ""
echo "=================================="
echo "✓ Deployment complete!"
echo "=================================="
echo ""
echo "Function: $LAMBDA_FUNCTION_NAME"
echo "Package: $ZIP_FILE ($PACKAGE_SIZE)"
echo ""
echo "Next steps:"
echo "1. Verify deployment: aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME"
echo "2. Test function: aws lambda invoke --function-name $LAMBDA_FUNCTION_NAME output.json"
echo "3. Check logs: aws logs tail /aws/lambda/$LAMBDA_FUNCTION_NAME --follow"
echo ""
