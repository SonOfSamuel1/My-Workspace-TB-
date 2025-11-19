#!/bin/bash
# Setup EventBridge (CloudWatch Events) schedule for hourly execution

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
FUNCTION_NAME="email-assistant-processor"
RULE_NAME="email-assistant-hourly-schedule"

echo -e "${YELLOW}Setting up EventBridge schedule for hourly execution...${NC}"

# Create EventBridge rule for hourly execution (7 AM - 5 PM EST, Monday-Friday)
# Cron: minute hour day-of-month month day-of-week year
# EST is UTC-5, so 7 AM EST = 12:00 UTC, 5 PM EST = 22:00 UTC
# Run every hour from 12:00 to 22:00 UTC (7 AM to 5 PM EST)

echo "Creating EventBridge rule: $RULE_NAME"
aws events put-rule \
    --name $RULE_NAME \
    --schedule-expression "cron(0 12-22 ? * MON-FRI *)" \
    --state ENABLED \
    --description "Triggers email assistant hourly from 7 AM to 5 PM EST, Monday-Friday" \
    --region $AWS_REGION \
    > /dev/null && echo -e "${GREEN}✓ EventBridge rule created${NC}"

# Add permission for EventBridge to invoke Lambda
echo "Adding Lambda permission for EventBridge..."
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id AllowEventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:$AWS_REGION:$AWS_ACCOUNT_ID:rule/$RULE_NAME \
    --region $AWS_REGION \
    2>&1 | grep -v "Statement" && echo -e "${GREEN}✓ Permission added${NC}" || {
        echo -e "${YELLOW}Permission may already exist${NC}"
    }

# Add Lambda as target for the EventBridge rule
echo "Adding Lambda as target for EventBridge rule..."
aws events put-targets \
    --rule $RULE_NAME \
    --targets "Id=1,Arn=arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:$FUNCTION_NAME" \
    --region $AWS_REGION \
    > /dev/null && echo -e "${GREEN}✓ Target configured${NC}"

echo ""
echo -e "${GREEN}✓ EventBridge schedule configured successfully${NC}"
echo ""
echo "Schedule: Every hour from 7 AM to 5 PM EST (12:00-22:00 UTC), Monday-Friday"
echo "Rule: $RULE_NAME"
echo "Target: $FUNCTION_NAME"
echo ""
echo "The email assistant will now run automatically every hour during business hours!"
echo ""
echo "To view scheduled executions:"
echo "  aws events list-rules --name-prefix email-assistant --region $AWS_REGION"
echo ""
echo "To view Lambda logs:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $AWS_REGION"
echo ""
