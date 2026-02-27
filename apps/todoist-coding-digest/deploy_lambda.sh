#!/bin/bash
# Deploy script for Todoist Coding Digest Lambda function

set -e

echo "======================================"
echo "Todoist Coding Digest - Lambda Deploy"
echo "======================================"
echo ""

# Configuration
FUNCTION_NAME="todoist-coding-digest"
RUNTIME="python3.9"
HANDLER="lambda_handler.lambda_handler"
TIMEOUT=60
MEMORY=256
REGION="us-east-1"

# Cleanup previous builds
echo "Cleaning previous builds..."
rm -rf lambda_package
rm -f coding-digest-lambda.zip

# Create package directory
echo "Creating package directory..."
mkdir -p lambda_package

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt -t lambda_package/ --quiet

# Copy application code
echo "Copying application code..."
cp -r src/* lambda_package/
cp lambda_handler.py lambda_package/
cp config.yaml lambda_package/

# Create ZIP package
echo "Creating ZIP package..."
cd lambda_package
zip -r ../coding-digest-lambda.zip . -q
cd ..

# Get package size
PACKAGE_SIZE=$(du -h coding-digest-lambda.zip | cut -f1)
echo "Package created: coding-digest-lambda.zip ($PACKAGE_SIZE)"

# Check if function exists
echo ""
echo "Checking if Lambda function exists..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &> /dev/null; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://coding-digest-lambda.zip \
        --region $REGION \
        --no-cli-pager

    echo "Lambda function updated successfully!"
else
    echo "Lambda function does not exist. Creating..."

    # Get the existing Lambda role
    ROLE_ARN=$(aws iam get-role --role-name LambdaBasicExecutionRole --query 'Role.Arn' --output text 2>/dev/null || echo "")

    if [ -z "$ROLE_ARN" ]; then
        ROLE_ARN=$(aws iam get-role --role-name BudgetReportLambdaRole --query 'Role.Arn' --output text 2>/dev/null || echo "")
    fi

    if [ -z "$ROLE_ARN" ]; then
        echo "Error: No suitable Lambda execution role found."
        echo "Please create a role with AWSLambdaBasicExecutionRole + AmazonSSMReadOnlyAccess + AmazonSESFullAccess"
        exit 1
    fi

    echo "Using role: $ROLE_ARN"

    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --role "$ROLE_ARN" \
        --handler $HANDLER \
        --zip-file fileb://coding-digest-lambda.zip \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --region $REGION \
        --environment "Variables={AWS_REGION=$REGION}" \
        --description "Daily coding task digest from Todoist Claude project" \
        --no-cli-pager

    echo "Lambda function created successfully!"

    # Enable Function URL
    echo ""
    echo "Creating Function URL..."
    aws lambda create-function-url-config \
        --function-name $FUNCTION_NAME \
        --auth-type NONE \
        --region $REGION \
        --no-cli-pager || echo "Function URL may already exist"

    # Add permission for public access to Function URL
    aws lambda add-permission \
        --function-name $FUNCTION_NAME \
        --statement-id FunctionURLPublicAccess \
        --action lambda:InvokeFunctionUrl \
        --principal "*" \
        --function-url-auth-type NONE \
        --region $REGION \
        --no-cli-pager 2>/dev/null || echo "Permission may already exist"

    # Get and display the Function URL
    FUNC_URL=$(aws lambda get-function-url-config \
        --function-name $FUNCTION_NAME \
        --region $REGION \
        --query 'FunctionUrl' --output text 2>/dev/null || echo "")

    if [ -n "$FUNC_URL" ]; then
        echo ""
        echo "Function URL: $FUNC_URL"
        echo ""
        echo "Store this URL in Parameter Store:"
        echo "  aws ssm put-parameter --name /coding-digest/function-url --value '$FUNC_URL' --type String"
    fi
fi

# Cleanup
echo ""
echo "Cleaning up..."
rm -rf lambda_package

echo ""
echo "======================================"
echo "Deployment complete!"
echo "======================================"
echo ""
echo "Package: coding-digest-lambda.zip ($PACKAGE_SIZE)"
echo ""
echo "Next steps:"
echo "1. Store parameters in SSM Parameter Store:"
echo "   aws ssm put-parameter --name /coding-digest/todoist-api-token --value 'YOUR_TOKEN' --type SecureString"
echo "   aws ssm put-parameter --name /coding-digest/email-recipient --value 'you@example.com' --type String"
echo "   aws ssm put-parameter --name /coding-digest/ses-sender-email --value 'sender@example.com' --type String"
echo ""
echo "2. Create EventBridge schedule for daily 5pm EST:"
echo "   aws scheduler create-schedule \\"
echo "     --name todoist-coding-digest-daily \\"
echo "     --schedule-expression 'cron(0 17 * * ? *)' \\"
echo "     --schedule-expression-timezone 'America/New_York' \\"
echo "     --target '{\"Arn\":\"arn:aws:lambda:us-east-1:YOUR_ACCOUNT:function:todoist-coding-digest\",\"RoleArn\":\"arn:aws:iam::YOUR_ACCOUNT:role/EventBridgeSchedulerRole\",\"Input\":\"{\\\"mode\\\":\\\"digest\\\"}\"}' \\"
echo "     --flexible-time-window '{\"Mode\":\"OFF\"}'"
echo ""
