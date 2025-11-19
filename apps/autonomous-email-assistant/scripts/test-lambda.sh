#!/bin/bash
# Test Lambda function

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWS_REGION=${AWS_REGION:-us-east-1}
FUNCTION_NAME="email-assistant-processor"

echo -e "${YELLOW}Testing Lambda function...${NC}"

# Create test event
cat > /tmp/test-event.json <<EOF
{
  "test": true,
  "time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "Invoking Lambda function: $FUNCTION_NAME"
echo ""

# Invoke function
aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --payload file:///tmp/test-event.json \
    --region $AWS_REGION \
    /tmp/lambda-response.json

echo ""
echo -e "${GREEN}Function Response:${NC}"
cat /tmp/lambda-response.json | jq '.'

echo ""
echo -e "${YELLOW}Recent logs:${NC}"
aws logs tail /aws/lambda/$FUNCTION_NAME --follow --since 1m --region $AWS_REGION

# Cleanup
rm -f /tmp/test-event.json /tmp/lambda-response.json
