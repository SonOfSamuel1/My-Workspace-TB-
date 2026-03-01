#!/bin/bash
# Deploy Eight Sleep -> Toggl Sync to AWS Lambda

set -e

FUNCTION_NAME="${LAMBDA_FUNCTION_NAME:-eight-sleep-toggl-sync}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$APP_DIR/deployment"
ZIP_FILE="$BUILD_DIR/lambda_package.zip"

echo "==================================="
echo "Deploying Eight Sleep Toggl Sync"
echo "==================================="
echo "Function: $FUNCTION_NAME"
echo "Region: $AWS_REGION"
echo ""

mkdir -p "$BUILD_DIR"
rm -rf "$BUILD_DIR/package"
mkdir -p "$BUILD_DIR/package"

echo "Installing dependencies..."
pip3 install -r "$APP_DIR/requirements.txt" \
    --target "$BUILD_DIR/package" \
    --platform manylinux2014_x86_64 \
    --only-binary=:all: \
    --upgrade \
    --quiet

echo "Copying source files..."
cp -r "$APP_DIR/src" "$BUILD_DIR/package/"
cp "$APP_DIR/lambda_handler.py" "$BUILD_DIR/package/"

echo "Creating deployment package..."
cd "$BUILD_DIR/package"
zip -r "$ZIP_FILE" . -x "*.pyc" -x "__pycache__/*" -x "*.egg-info/*" > /dev/null

PACKAGE_SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo "Package size: $PACKAGE_SIZE"

if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$ZIP_FILE" \
        --region "$AWS_REGION" \
        --output text
else
    echo "Lambda function '$FUNCTION_NAME' does not exist."
    echo "Create it first with:"
    echo "  aws lambda create-function \\"
    echo "    --function-name $FUNCTION_NAME \\"
    echo "    --runtime python3.12 \\"
    echo "    --handler lambda_handler.handler \\"
    echo "    --role arn:aws:iam::ACCOUNT_ID:role/YOUR_LAMBDA_ROLE \\"
    echo "    --timeout 60 \\"
    echo "    --memory-size 128 \\"
    echo "    --zip-file fileb://$ZIP_FILE \\"
    echo "    --region $AWS_REGION"
    exit 1
fi

echo ""
echo "==================================="
echo "Deployment complete!"
echo "==================================="
echo ""
echo "Test with:"
echo "  aws lambda invoke --function-name $FUNCTION_NAME --payload '{}' response.json && cat response.json"
echo ""
echo "Setup daily schedule (10am ET):"
echo "  aws events put-rule --name eight-sleep-toggl-daily --schedule-expression 'cron(0 15 ? * * *)' --region $AWS_REGION"
echo ""
