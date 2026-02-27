#!/bin/bash
# Deploy script for Weekly Net Worth Report Lambda function

set -e

echo "======================================"
echo "Net Worth Report - Lambda Deploy"
echo "======================================"
echo ""

# Configuration
FUNCTION_NAME="weekly-networth-report"
RUNTIME="python3.9"
HANDLER="lambda_handler.networth_report_handler"
TIMEOUT=300
MEMORY=512
REGION="us-east-1"

# Cleanup previous builds
echo "Cleaning previous builds..."
rm -rf lambda_package
rm -f networth-report-lambda.zip

# Create package directory
echo "Creating package directory..."
mkdir -p lambda_package

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -t lambda_package/ --quiet

# Copy application code
echo "Copying application code..."
cp -r src/* lambda_package/
cp lambda_handler.py lambda_package/
cp config.yaml lambda_package/

# Create ZIP package
echo "Creating ZIP package..."
cd lambda_package
zip -r ../networth-report-lambda.zip . -q
cd ..

# Get package size
PACKAGE_SIZE=$(du -h networth-report-lambda.zip | cut -f1)
echo "Package created: networth-report-lambda.zip ($PACKAGE_SIZE)"

# Check if function exists
echo ""
echo "Checking if Lambda function exists..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &> /dev/null; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://networth-report-lambda.zip \
        --region $REGION \
        --no-cli-pager

    echo "Lambda function updated successfully!"
else
    echo "Lambda function does not exist."
    echo ""
    echo "To create the function, run:"
    echo ""
    echo "aws lambda create-function \\"
    echo "  --function-name $FUNCTION_NAME \\"
    echo "  --runtime $RUNTIME \\"
    echo "  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/NetWorthReportLambdaRole \\"
    echo "  --handler $HANDLER \\"
    echo "  --zip-file fileb://networth-report-lambda.zip \\"
    echo "  --timeout $TIMEOUT \\"
    echo "  --memory-size $MEMORY \\"
    echo "  --region $REGION \\"
    echo "  --environment Variables=\"{AWS_REGION=$REGION}\" \\"
    echo "  --description \"Weekly net worth and run rate report\""
    echo ""
    echo "Then add EventBridge schedule:"
    echo ""
    echo "aws events put-rule \\"
    echo "  --name weekly-networth-report \\"
    echo "  --schedule-expression 'cron(0 23 ? * FRI *)' \\"
    echo "  --region $REGION \\"
    echo "  --description 'Trigger net worth report every Friday 6pm EST'"
fi

# Cleanup
echo ""
echo "Cleaning up..."
rm -rf lambda_package

echo ""
echo "======================================"
echo "Deployment package ready!"
echo "======================================"
echo ""
echo "Package: networth-report-lambda.zip ($PACKAGE_SIZE)"
echo ""
echo "AWS Parameter Store keys needed:"
echo "  /networth-report/ynab-api-key"
echo "  /networth-report/email-recipient"
echo "  /networth-report/ses-sender-email"
echo ""
