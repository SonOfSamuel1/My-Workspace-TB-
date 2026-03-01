#!/bin/bash
# Deploy script for Todoist CC Task Mover Lambda function

set -e

echo "======================================"
echo "Todoist CC Task Mover - Lambda Deploy"
echo "======================================"
echo ""

# Configuration
FUNCTION_NAME="todoist-cc-task-mover"
RUNTIME="python3.9"
HANDLER="lambda_handler.cc_task_mover_handler"
TIMEOUT=60
MEMORY=256
REGION="us-east-1"

# Cleanup previous builds
echo "Cleaning previous builds..."
rm -rf lambda_package
rm -f todoist-cc-task-mover-lambda.zip

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

# Create ZIP package
echo "Creating ZIP package..."
cd lambda_package
zip -r ../todoist-cc-task-mover-lambda.zip . -q
cd ..

# Get package size
PACKAGE_SIZE=$(du -h todoist-cc-task-mover-lambda.zip | cut -f1)
echo "Package created: todoist-cc-task-mover-lambda.zip ($PACKAGE_SIZE)"

# Check if function exists
echo ""
echo "Checking if Lambda function exists..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION &> /dev/null; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://todoist-cc-task-mover-lambda.zip \
        --region $REGION

    echo "Lambda function updated successfully!"
else
    echo "Lambda function does not exist. Creating..."

    # Reuse an existing Lambda execution role
    ROLE_ARN=$(aws iam get-role --role-name TodoistRemindersLambdaRole --query 'Role.Arn' --output text 2>/dev/null || echo "")

    if [ -z "$ROLE_ARN" ]; then
        ROLE_ARN=$(aws iam get-role --role-name LambdaBasicExecutionRole --query 'Role.Arn' --output text 2>/dev/null || echo "")
    fi

    if [ -z "$ROLE_ARN" ]; then
        ROLE_ARN=$(aws iam get-role --role-name BudgetReportLambdaRole --query 'Role.Arn' --output text 2>/dev/null || echo "")
    fi

    if [ -z "$ROLE_ARN" ]; then
        echo "Error: No suitable Lambda execution role found."
        echo ""
        echo "Please create a role with the following trust policy:"
        echo '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
        echo ""
        echo "And attach these policies:"
        echo "  - AWSLambdaBasicExecutionRole"
        echo "  - AmazonSSMReadOnlyAccess"
        exit 1
    fi

    echo "Using role: $ROLE_ARN"

    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --role "$ROLE_ARN" \
        --handler $HANDLER \
        --zip-file fileb://todoist-cc-task-mover-lambda.zip \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --region $REGION \
        --environment "Variables={}" \
        --description "Daily mover of cc- prefixed tasks from Inbox to Claude Code project" \

    echo "Lambda function created successfully!"
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
echo "Package: todoist-cc-task-mover-lambda.zip ($PACKAGE_SIZE)"
echo ""
echo "Next steps:"
echo "  1. Store the API token in Parameter Store:"
echo "     aws ssm put-parameter \\"
echo "       --name \"/todoist-cc-task-mover/api-token\" \\"
echo "       --value \"<TODOIST_API_TOKEN>\" \\"
echo "       --type SecureString"
echo ""
echo "  2. Create an EventBridge rule (daily at 4 AM EST / 9 AM UTC):"
echo "     aws events put-rule \\"
echo "       --name todoist-cc-task-mover-daily \\"
echo "       --schedule-expression \"cron(0 9 * * ? *)\" \\"
echo "       --state ENABLED \\"
echo "       --region $REGION"
echo ""
echo "  3. Add Lambda as target for the rule:"
echo "     FUNCTION_ARN=\$(aws lambda get-function --function-name $FUNCTION_NAME --query 'Configuration.FunctionArn' --output text)"
echo "     aws events put-targets \\"
echo "       --rule todoist-cc-task-mover-daily \\"
echo "       --targets \"Id=1,Arn=\$FUNCTION_ARN\""
echo ""
echo "  4. Grant EventBridge permission to invoke Lambda:"
echo "     aws lambda add-permission \\"
echo "       --function-name $FUNCTION_NAME \\"
echo "       --statement-id todoist-cc-task-mover-eventbridge \\"
echo "       --action lambda:InvokeFunction \\"
echo "       --principal events.amazonaws.com \\"
echo "       --source-arn \$(aws events describe-rule --name todoist-cc-task-mover-daily --query 'Arn' --output text)"
echo ""
