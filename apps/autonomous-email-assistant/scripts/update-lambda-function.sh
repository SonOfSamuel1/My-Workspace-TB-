#!/bin/bash
# Update existing Lambda function

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
FUNCTION_NAME="email-assistant-processor"

echo -e "${YELLOW}Updating Lambda function...${NC}"

# Load environment variables
if [ -f ".env" ]; then
    source .env
fi

# Update function code
echo "Updating function code..."
aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --image-uri $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/email-assistant-automation:latest \
    --region $AWS_REGION \
    > /dev/null && echo -e "${GREEN}✓ Function code updated${NC}"

# Wait for update to complete
echo "Waiting for update to complete..."
aws lambda wait function-updated --function-name $FUNCTION_NAME --region $AWS_REGION

# Update environment variables if provided
if [ -n "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    echo "Updating environment variables..."
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --environment "Variables={
            CLAUDE_CODE_OAUTH_TOKEN=${CLAUDE_CODE_OAUTH_TOKEN},
            GMAIL_OAUTH_CREDENTIALS=${GMAIL_OAUTH_CREDENTIALS},
            GMAIL_CREDENTIALS=${GMAIL_CREDENTIALS},
            ESCALATION_PHONE=${ESCALATION_PHONE:-+14077448449},
            TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID:-},
            TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN:-},
            TWILIO_FROM_NUMBER=${TWILIO_FROM_NUMBER:-},
            TEST_MODE=${TEST_MODE:-false}
        }" \
        --region $AWS_REGION \
        > /dev/null && echo -e "${GREEN}✓ Environment variables updated${NC}"
fi

echo ""
echo -e "${GREEN}✓ Lambda function updated successfully${NC}"
echo ""
