#!/bin/bash
# Deploy script for Weekly YNAB Budget Report Lambda function

set -e

echo "======================================"
echo "Weekly Budget Report - Lambda Deploy"
echo "======================================"
echo ""

# Configuration
FUNCTION_NAME="weekly-budget-report"
RUNTIME="python3.9"
HANDLER="lambda_handler.weekly_report_handler"
TIMEOUT=300
MEMORY=512
REGION="us-east-1"

# Cleanup previous builds
echo "📦 Cleaning previous builds..."
rm -rf lambda_package
rm -f budget-report-lambda.zip

# Create package directory
echo "📁 Creating package directory..."
mkdir -p lambda_package

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt -t lambda_package/ --quiet

# Copy application code
echo "📋 Copying application code..."
cp -r src/* lambda_package/
cp lambda_handler.py lambda_package/
cp config.yaml lambda_package/

# Copy email sender from Love Brittany tracker
echo "📧 Copying email sender..."
if [ -f "../love-brittany-tracker/src/email_sender.py" ]; then
    cp ../love-brittany-tracker/src/email_sender.py lambda_package/
else
    echo "⚠️  Warning: email_sender.py not found, email functionality may not work"
fi

# Create ZIP package
echo "🗜️  Creating ZIP package..."
cd lambda_package
zip -r ../budget-report-lambda.zip . -q
cd ..

# Get package size
PACKAGE_SIZE=$(du -h budget-report-lambda.zip | cut -f1)
echo "✅ Package created: budget-report-lambda.zip ($PACKAGE_SIZE)"

# Check if function exists
echo ""
echo "🔍 Checking if Lambda function exists..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &> /dev/null; then
    echo "📤 Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://budget-report-lambda.zip \
        --region $REGION \
        --no-cli-pager

    echo "✅ Lambda function updated successfully!"
else
    echo "⚠️  Lambda function does not exist."
    echo ""
    echo "To create the function, run:"
    echo ""
    echo "aws lambda create-function \\"
    echo "  --function-name $FUNCTION_NAME \\"
    echo "  --runtime $RUNTIME \\"
    echo "  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/BudgetReportLambdaRole \\"
    echo "  --handler $HANDLER \\"
    echo "  --zip-file fileb://budget-report-lambda.zip \\"
    echo "  --timeout $TIMEOUT \\"
    echo "  --memory-size $MEMORY \\"
    echo "  --region $REGION \\"
    echo "  --environment Variables=\"{AWS_REGION=$REGION}\" \\"
    echo "  --description \"Weekly YNAB budget report generator\""
    echo ""
    echo "See docs/AWS_DEPLOYMENT.md for full setup instructions."
fi

# Cleanup
echo ""
echo "🧹 Cleaning up..."
rm -rf lambda_package

echo ""
echo "======================================"
echo "✅ Deployment package ready!"
echo "======================================"
echo ""
echo "Package: budget-report-lambda.zip ($PACKAGE_SIZE)"
echo ""
echo "Next steps:"
echo "1. Upload to AWS Lambda (or create function if needed)"
echo "2. Configure Parameter Store credentials"
echo "3. Set up EventBridge schedule"
echo ""
echo "See docs/AWS_DEPLOYMENT.md for detailed instructions."
echo ""
