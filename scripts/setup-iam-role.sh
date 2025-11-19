#!/bin/bash
# Setup IAM role for Email Assistant Lambda

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWS_REGION=${AWS_REGION:-us-east-1}
ROLE_NAME="EmailAssistantLambdaRole"

echo -e "${YELLOW}Setting up IAM role for Email Assistant Lambda...${NC}"

# Create trust policy for Lambda
cat > /tmp/lambda-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create IAM role
echo "Creating IAM role: $ROLE_NAME"
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
    --description "Execution role for Email Assistant Lambda function" \
    --region $AWS_REGION \
    2>&1 | grep -v "Arn" && echo -e "${GREEN}✓ Role created${NC}" || {
        echo -e "${YELLOW}Role may already exist${NC}"
    }

# Attach basic Lambda execution policy
echo "Attaching Lambda basic execution policy..."
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
    --region $AWS_REGION \
    && echo -e "${GREEN}✓ Basic execution policy attached${NC}"

# Create and attach custom policy for email assistant
cat > /tmp/email-assistant-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "*"
    }
  ]
}
EOF

echo "Creating custom Email Assistant policy..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
POLICY_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:policy/EmailAssistantLambdaPolicy"

aws iam create-policy \
    --policy-name EmailAssistantLambdaPolicy \
    --policy-document file:///tmp/email-assistant-policy.json \
    --description "Custom policy for Email Assistant Lambda function" \
    --region $AWS_REGION \
    2>&1 | grep -v "Arn" && echo -e "${GREEN}✓ Custom policy created${NC}" || {
        echo -e "${YELLOW}Policy may already exist${NC}"
    }

echo "Attaching custom policy to role..."
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $POLICY_ARN \
    --region $AWS_REGION \
    && echo -e "${GREEN}✓ Custom policy attached${NC}"

# Wait for role to be available
echo "Waiting for IAM role to propagate..."
sleep 10

echo ""
echo -e "${GREEN}✓ IAM role setup complete${NC}"
echo ""
echo "Role ARN: arn:aws:iam::$AWS_ACCOUNT_ID:role/$ROLE_NAME"
echo ""

# Cleanup temp files
rm -f /tmp/lambda-trust-policy.json /tmp/email-assistant-policy.json
