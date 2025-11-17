#!/bin/bash
# Setup EventBridge schedule for Lambda function

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo -e "${YELLOW}Setting up EventBridge schedule...${NC}"

# Create rule for weekly report (Sunday at 4 AM EST = 9 AM UTC)
echo ""
echo "Creating weekly report schedule (Sunday 4:00 AM EST)..."
aws events put-rule \
    --name love-brittany-weekly-report \
    --schedule-expression "cron(0 9 ? * SUN *)" \
    --description "Trigger weekly relationship report on Sundays at 4 AM EST" \
    --state ENABLED \
    --region $AWS_REGION \
    > /dev/null 2>&1 && echo -e "${GREEN}✓ Weekly report rule created${NC}"

# Add Lambda as target
echo "Adding Lambda function as target..."
aws events put-targets \
    --rule love-brittany-weekly-report \
    --targets "Id"="1","Arn"="arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT_ID:function:love-brittany-weekly-report" \
    --region $AWS_REGION \
    > /dev/null 2>&1 && echo -e "${GREEN}✓ Target added${NC}"

# Grant EventBridge permission to invoke Lambda
echo "Granting EventBridge permission..."
aws lambda add-permission \
    --function-name love-brittany-weekly-report \
    --statement-id AllowEventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:$AWS_REGION:$AWS_ACCOUNT_ID:rule/love-brittany-weekly-report \
    --region $AWS_REGION \
    2>/dev/null && echo -e "${GREEN}✓ Permission granted${NC}" || echo -e "${YELLOW}Permission may already exist${NC}"

echo ""
echo -e "${GREEN}✓ EventBridge schedule configured successfully${NC}"
echo ""
echo "Schedule:"
echo "  - love-brittany-weekly-report: Runs every Sunday at 4:00 AM EST (9:00 AM UTC)"
echo ""
echo "View schedule:"
echo "  aws events list-rules --region $AWS_REGION | grep love-brittany"
echo ""
