#!/bin/bash
# Delete Lambda function and associated resources

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWS_REGION=${AWS_REGION:-us-east-1}
FUNCTION_NAME="email-assistant-processor"
RULE_NAME="email-assistant-hourly-schedule"

echo -e "${YELLOW}Deleting Email Assistant Lambda resources...${NC}"
echo ""
read -p "Are you sure you want to delete the Lambda function and schedule? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Remove EventBridge targets
echo "Removing EventBridge targets..."
aws events remove-targets \
    --rule $RULE_NAME \
    --ids 1 \
    --region $AWS_REGION \
    2>/dev/null && echo -e "${GREEN}✓ Targets removed${NC}" || echo -e "${YELLOW}No targets found${NC}"

# Delete EventBridge rule
echo "Deleting EventBridge rule..."
aws events delete-rule \
    --name $RULE_NAME \
    --region $AWS_REGION \
    2>/dev/null && echo -e "${GREEN}✓ Rule deleted${NC}" || echo -e "${YELLOW}No rule found${NC}"

# Delete Lambda function
echo "Deleting Lambda function..."
aws lambda delete-function \
    --function-name $FUNCTION_NAME \
    --region $AWS_REGION \
    2>/dev/null && echo -e "${GREEN}✓ Function deleted${NC}" || echo -e "${YELLOW}No function found${NC}"

echo ""
echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""
echo "Note: ECR repository and IAM role were not deleted."
echo "To delete these manually:"
echo "  aws ecr delete-repository --repository-name email-assistant-automation --force --region $AWS_REGION"
echo "  aws iam delete-role --role-name EmailAssistantLambdaRole"
echo ""
