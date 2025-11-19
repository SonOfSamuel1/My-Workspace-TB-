#!/bin/bash
# Deploy Email Assistant to AWS Lambda - Full Deployment

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Email Assistant Lambda Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}ERROR: .env file not found${NC}"
    echo "Please create .env file with your credentials."
    echo "See .env.example for template."
    exit 1
fi

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

echo -e "${YELLOW}Step 1/5: Setting up IAM role...${NC}"
./scripts/setup-iam-role.sh
echo ""

echo -e "${YELLOW}Step 2/5: Building and pushing Docker image...${NC}"
echo "⚠️  This may take 5-10 minutes on first run..."
./scripts/build-and-push.sh
echo ""

echo -e "${YELLOW}Step 3/5: Creating Lambda function...${NC}"
./scripts/create-lambda-function.sh
echo ""

echo -e "${YELLOW}Step 4/5: Setting up EventBridge schedule...${NC}"
./scripts/setup-eventbridge-schedule.sh
echo ""

echo -e "${YELLOW}Step 5/5: Testing Lambda function...${NC}"
./scripts/test-lambda.sh
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Your Email Assistant is now running on AWS Lambda!"
echo ""
echo "Schedule: Every hour from 7 AM - 5 PM EST, Monday-Friday"
echo ""
echo "To view logs:"
echo "  aws logs tail /aws/lambda/email-assistant-processor --follow"
echo ""
echo "To update after changes:"
echo "  ./scripts/build-and-push.sh"
echo "  ./scripts/update-lambda-function.sh"
echo ""
