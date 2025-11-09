#!/bin/bash
set -e

# Update EventBridge Schedule to Run Every 5 Minutes
# This replaces the hourly schedule with a 5-minute interval

echo "========================================="
echo "Updating Schedule to Every 5 Minutes"
echo "========================================="
echo ""

AWS_REGION="${1:-us-east-1}"
FUNCTION_NAME="email-assistant-processor"
RULE_NAME="email-assistant-schedule"

echo "Region: $AWS_REGION"
echo "Function: $FUNCTION_NAME"
echo "Rule: $RULE_NAME"
echo ""

# Check if rule exists
if aws events describe-rule --name "$RULE_NAME" --region "$AWS_REGION" &> /dev/null; then
    echo "✓ Found existing rule: $RULE_NAME"

    # Update the rule to run every 5 minutes
    echo "Updating schedule to every 5 minutes..."
    aws events put-rule \
        --name "$RULE_NAME" \
        --schedule-expression "rate(5 minutes)" \
        --state ENABLED \
        --description "Email Assistant - Runs every 5 minutes" \
        --region "$AWS_REGION"

    echo "✓ Schedule updated successfully!"
    echo ""
    echo "New schedule: Every 5 minutes (24/7)"
    echo ""
else
    echo "Creating new EventBridge rule..."

    # Create the rule
    aws events put-rule \
        --name "$RULE_NAME" \
        --schedule-expression "rate(5 minutes)" \
        --state ENABLED \
        --description "Email Assistant - Runs every 5 minutes" \
        --region "$AWS_REGION"

    # Get Lambda function ARN
    FUNCTION_ARN=$(aws lambda get-function \
        --function-name "$FUNCTION_NAME" \
        --region "$AWS_REGION" \
        --query 'Configuration.FunctionArn' \
        --output text)

    # Add Lambda permission for EventBridge
    aws lambda add-permission \
        --function-name "$FUNCTION_NAME" \
        --statement-id "AllowEventBridgeInvoke" \
        --action "lambda:InvokeFunction" \
        --principal events.amazonaws.com \
        --source-arn "arn:aws:events:${AWS_REGION}:$(aws sts get-caller-identity --query Account --output text):rule/${RULE_NAME}" \
        --region "$AWS_REGION" 2>/dev/null || echo "Permission already exists"

    # Add Lambda as target
    aws events put-targets \
        --rule "$RULE_NAME" \
        --targets "Id=1,Arn=$FUNCTION_ARN" \
        --region "$AWS_REGION"

    echo "✓ EventBridge rule created and configured!"
    echo ""
fi

echo "========================================="
echo "Schedule Configuration Complete"
echo "========================================="
echo ""
echo "The email assistant will now run every 5 minutes."
echo ""
echo "To monitor executions:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $AWS_REGION"
echo ""
echo "To check next execution:"
echo "  aws events list-rules --name-prefix $RULE_NAME --region $AWS_REGION"
echo ""
echo "WARNING: Running every 5 minutes will process emails very frequently."
echo "This may result in:"
echo "  - Higher AWS Lambda costs (~$10-20/month vs $2-5/month hourly)"
echo "  - More Claude API usage"
echo "  - Faster inbox processing"
echo ""
