#!/bin/bash
# Deploy Toggl Daily Productivity Report to AWS Lambda

set -e

# Configuration
FUNCTION_NAME="${LAMBDA_FUNCTION_NAME:-toggl-daily-productivity}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$APP_DIR/deployment"
ZIP_FILE="$BUILD_DIR/lambda_package.zip"

echo "==================================="
echo "Deploying Toggl Daily Productivity"
echo "==================================="
echo "Function: $FUNCTION_NAME"
echo "Region: $AWS_REGION"
echo ""

# Create build directory
mkdir -p "$BUILD_DIR"
rm -rf "$BUILD_DIR/package"
mkdir -p "$BUILD_DIR/package"

echo "Installing dependencies..."
pip3 install -r "$APP_DIR/lambda/requirements.txt" \
    --target "$BUILD_DIR/package" \
    --upgrade \
    --quiet

echo "Copying source files..."
cp -r "$APP_DIR/src" "$BUILD_DIR/package/"
cp "$APP_DIR/lambda/lambda_handler.py" "$BUILD_DIR/package/"
cp -r "$APP_DIR/config.yaml" "$BUILD_DIR/package/config/" 2>/dev/null || true

# Create config directory and copy config
mkdir -p "$BUILD_DIR/package/config"
cp "$APP_DIR/config.yaml" "$BUILD_DIR/package/config/config.yaml"

# Create logs directory
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
    echo "Create it first with:"
    echo "  aws lambda create-function \\"
    echo "    --function-name $FUNCTION_NAME \\"
    echo "    --runtime python3.12 \\"
    echo "    --handler lambda_handler.lambda_handler \\"
    echo "    --role arn:aws:iam::ACCOUNT_ID:role/YOUR_LAMBDA_ROLE \\"
    echo "    --timeout 120 \\"
    echo "    --memory-size 256 \\"
    echo "    --zip-file fileb://$ZIP_FILE \\"
    echo "    --region $AWS_REGION"
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
echo "Setup EventBridge schedule with:"
echo "  aws events put-rule --name toggl-productivity-morning --schedule-expression 'cron(0 11 ? * MON-FRI,SUN *)' --region $AWS_REGION"
echo "  aws events put-rule --name toggl-productivity-evening --schedule-expression 'cron(0 0 ? * * *)' --region $AWS_REGION"
echo ""
