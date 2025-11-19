#!/bin/bash
# Create Lambda function

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/EmailAssistantLambdaRole"
FUNCTION_NAME="email-assistant-processor"

echo -e "${YELLOW}Creating Lambda function...${NC}"

# Load environment variables
if [ -f ".env" ]; then
    source .env
fi

# Validate required environment variables
if [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    echo -e "${RED}ERROR: CLAUDE_CODE_OAUTH_TOKEN not set in .env${NC}"
    exit 1
fi

if [ -z "$GMAIL_OAUTH_CREDENTIALS" ]; then
    echo -e "${RED}ERROR: GMAIL_OAUTH_CREDENTIALS not set in .env${NC}"
    exit 1
fi

if [ -z "$GMAIL_CREDENTIALS" ]; then
    echo -e "${RED}ERROR: GMAIL_CREDENTIALS not set in .env${NC}"
    exit 1
fi

# Create Lambda function
echo "Creating Lambda function: $FUNCTION_NAME"

aws lambda create-function \
    --function-name $FUNCTION_NAME \
    --package-type Image \
    --code ImageUri=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/email-assistant-automation:latest \
    --role $ROLE_ARN \
    --timeout 900 \
    --memory-size 1024 \
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
    --description "Autonomous email assistant - processes emails hourly during business hours" \
    --region $AWS_REGION \
    2>&1 | grep -v "FunctionArn" && echo -e "${GREEN}✓ Lambda function created${NC}" || {
        echo -e "${YELLOW}Function may already exist - use update-lambda-function.sh to update${NC}"
        exit 1
    }

echo ""
echo -e "${GREEN}✓ Lambda function created successfully${NC}"
echo ""
echo "Function: $FUNCTION_NAME"
echo "Region: $AWS_REGION"
echo ""
echo "Next steps:"
echo "  1. Run ./scripts/setup-eventbridge-schedule.sh to configure hourly execution"
echo "  2. Test the function: ./scripts/test-lambda.sh"
echo ""
