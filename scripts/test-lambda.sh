#!/bin/bash
# Test Lambda function

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWS_REGION=${AWS_REGION:-us-east-1}
FUNCTION_NAME="love-brittany-weekly-report"

echo -e "${YELLOW}Testing Lambda function...${NC}"
echo ""

# Invoke Lambda function
echo "Invoking $FUNCTION_NAME..."
aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --region $AWS_REGION \
    --log-type Tail \
    --query 'LogResult' \
    --output text response.json | base64 --decode

echo ""
echo -e "${GREEN}Response saved to response.json${NC}"
echo ""

# Show response
echo "Response:"
cat response.json | python3 -m json.tool 2>/dev/null || cat response.json
echo ""

# Clean up
rm response.json

echo -e "${GREEN}✓ Test complete${NC}"
echo ""
echo "View full logs:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
