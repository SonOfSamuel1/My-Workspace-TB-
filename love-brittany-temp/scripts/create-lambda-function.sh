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
ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/LoveBrittanyLambdaRole"

echo -e "${YELLOW}Creating Lambda function...${NC}"

# Load environment variables
if [ -f ".env" ]; then
    source .env
fi

# Create Weekly Report Lambda
echo ""
echo "Creating Weekly Relationship Report Lambda function..."

aws lambda create-function \
    --function-name love-brittany-weekly-report \
    --package-type Image \
    --code ImageUri=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/love-brittany-automation:latest \
    --role $ROLE_ARN \
    --timeout 900 \
    --memory-size 512 \
    --environment "Variables={
        RECIPIENT_EMAIL=${RECIPIENT_EMAIL:-terrance@goodportion.org}
    }" \
    --description "Weekly relationship tracking report - sends comprehensive email every Sunday at 4 AM EST" \
    --region $AWS_REGION \
    2>&1 | grep -v "FunctionArn" && echo -e "${GREEN}✓ Weekly report function created${NC}" || {
        echo -e "${YELLOW}Function may already exist${NC}"
    }

echo ""
echo -e "${GREEN}✓ Lambda function created${NC}"
echo ""
echo "Function:"
echo "  - love-brittany-weekly-report"
echo ""
