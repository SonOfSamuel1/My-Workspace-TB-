#!/bin/bash
# Deploy JT Teaching Newsletter to AWS Lambda
#
# Usage: ./deploy_lambda.sh [--create | --update]
#   --create   Create the Lambda function for the first time
#   --update   Update an existing Lambda function (default)
#
# Prerequisites:
#   - AWS CLI configured with appropriate IAM permissions
#   - Lambda execution role with S3, SES, SSM Parameter Store access
#   - Parameter Store values set (see below)
#
# Parameter Store setup (run once):
#   aws ssm put-parameter --name /jt-newsletter/anthropic-api-key --value "sk-ant-..." --type SecureString
#   aws ssm put-parameter --name /jt-newsletter/email-recipient --value "you@email.com" --type SecureString
#   aws ssm put-parameter --name /jt-newsletter/ses-sender-email --value "sender@email.com" --type SecureString
#   aws ssm put-parameter --name /jt-newsletter/s3-bucket --value "jt-teachings-notes" --type String

set -e

FUNCTION_NAME="jt-teaching-newsletter"
REGION="${AWS_REGION:-us-east-1}"
RUNTIME="python3.12"
TIMEOUT=60
MEMORY=256
HANDLER="lambda_handler.handler"
PACKAGE_FILE="lambda_package.zip"
MODE="${1:---update}"

# IAM role ARN — update this after creating the role
ROLE_ARN="${LAMBDA_ROLE_ARN:-arn:aws:iam::YOUR_ACCOUNT_ID:role/jt-teaching-newsletter-role}"

echo "=================================================="
echo "JT Teaching Newsletter — Lambda Deploy"
echo "=================================================="
echo "Function: $FUNCTION_NAME"
echo "Region:   $REGION"
echo "Mode:     $MODE"
echo ""

# Build deployment package
echo "Building deployment package..."
rm -f "$PACKAGE_FILE"
rm -rf lambda_build/

mkdir -p lambda_build

# Install dependencies into build directory
pip3 install \
    --target lambda_build/ \
    --quiet \
    anthropic \
    boto3 \
    python-dotenv \
    PyYAML

# Copy source files
cp -r src/ lambda_build/src/
cp lambda_handler.py lambda_build/
cp config.yaml lambda_build/

# Create zip
cd lambda_build
zip -r "../$PACKAGE_FILE" . -q
cd ..

echo "Package built: $PACKAGE_FILE ($(du -sh "$PACKAGE_FILE" | cut -f1))"

if [ "$MODE" = "--create" ]; then
    echo ""
    echo "Creating Lambda function..."
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime "$RUNTIME" \
        --role "$ROLE_ARN" \
        --handler "$HANDLER" \
        --zip-file "fileb://$PACKAGE_FILE" \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --region "$REGION" \
        --description "Daily JT Teaching Newsletter — sends 2 Jesus' teachings each morning"

    echo ""
    echo "Creating EventBridge schedule (7:00 AM EST daily)..."
    # Create rule
    aws events put-rule \
        --name "${FUNCTION_NAME}-daily" \
        --schedule-expression "cron(0 12 * * ? *)" \
        --state ENABLED \
        --region "$REGION"

    # Get Lambda ARN
    LAMBDA_ARN=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" --query 'Configuration.FunctionArn' --output text)

    # Add permission for EventBridge to invoke Lambda
    aws lambda add-permission \
        --function-name "$FUNCTION_NAME" \
        --statement-id "EventBridgeDailyTrigger" \
        --action "lambda:InvokeFunction" \
        --principal "events.amazonaws.com" \
        --source-arn "$(aws events describe-rule --name "${FUNCTION_NAME}-daily" --region "$REGION" --query 'Arn' --output text)" \
        --region "$REGION"

    # Add Lambda as EventBridge target
    aws events put-targets \
        --rule "${FUNCTION_NAME}-daily" \
        --targets "Id=1,Arn=$LAMBDA_ARN" \
        --region "$REGION"

    echo "EventBridge schedule created."
    echo ""
    echo "Lambda function created successfully!"
    echo "Test with: aws lambda invoke --function-name $FUNCTION_NAME --region $REGION /tmp/response.json && cat /tmp/response.json"

else
    echo ""
    echo "Updating Lambda function code..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$PACKAGE_FILE" \
        --region "$REGION"

    echo "Lambda function updated successfully!"
fi

# Cleanup
rm -rf lambda_build/

echo ""
echo "Deploy complete!"
