#!/bin/bash
# Deploy Daily AI News Report to AWS Lambda

set -e

# Configuration
FUNCTION_NAME="${LAMBDA_FUNCTION_NAME:-daily-ai-news-report}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$APP_DIR/deployment"
ZIP_FILE="$BUILD_DIR/lambda_package.zip"

echo "==================================="
echo "Deploying Daily AI News Report"
echo "==================================="
echo "Function: $FUNCTION_NAME"
echo "Region: $AWS_REGION"
echo ""

# Create build directory
mkdir -p "$BUILD_DIR"
rm -rf "$BUILD_DIR/package"
mkdir -p "$BUILD_DIR/package"

echo "Installing dependencies..."
pip install -r "$APP_DIR/lambda/requirements.txt" \
    --target "$BUILD_DIR/package" \
    --upgrade \
    --quiet

echo "Copying source files..."
cp -r "$APP_DIR/src" "$BUILD_DIR/package/"
cp "$APP_DIR/lambda/lambda_handler.py" "$BUILD_DIR/package/"
cp -r "$APP_DIR/config" "$BUILD_DIR/package/"
cp -r "$APP_DIR/templates" "$BUILD_DIR/package/" 2>/dev/null || true

# Create logs directory in package
mkdir -p "$BUILD_DIR/package/logs"

echo "Creating deployment package..."
cd "$BUILD_DIR/package"
zip -r "$ZIP_FILE" . -x "*.pyc" -x "__pycache__/*" -x "*.egg-info/*" > /dev/null

PACKAGE_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo "Package size: $PACKAGE_SIZE"

# Check if Lambda function exists
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$ZIP_FILE" \
        --region "$AWS_REGION" \
        --output text
else
    echo "Lambda function '$FUNCTION_NAME' does not exist."
    echo "Please create it first using create-lambda-function.sh"
    exit 1
fi

echo ""
echo "==================================="
echo "Deployment complete!"
echo "==================================="
echo ""
echo "Test the function with:"
echo "  aws lambda invoke --function-name $FUNCTION_NAME --payload '{\"dry_run\": true}' response.json"
echo ""
