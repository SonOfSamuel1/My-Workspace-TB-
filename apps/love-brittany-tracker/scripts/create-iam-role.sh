#!/bin/bash
# Create IAM role for Lambda functions

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWS_REGION=${AWS_REGION:-us-east-1}
ROLE_NAME="LoveBrittanyLambdaRole"

echo -e "${YELLOW}Creating IAM role for Lambda...${NC}"

# Create trust policy
cat > /tmp/lambda-trust-policy.json << 'EOF'
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

# Create the role
echo "Creating role: $ROLE_NAME"
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
    --description "Execution role for Love Brittany Lambda functions" \
    2>/dev/null && echo -e "${GREEN}✓ Role created${NC}" || {
        echo -e "${YELLOW}Role already exists${NC}"
    }

# Attach basic execution policy
echo "Attaching basic execution policy..."
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
    2>/dev/null && echo -e "${GREEN}✓ Basic execution policy attached${NC}" || {
        echo -e "${YELLOW}Policy already attached${NC}"
    }

# Create custom policy for Parameter Store access
cat > /tmp/parameter-store-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/love-brittany/*"
    }
  ]
}
EOF

# Attach Parameter Store policy
echo "Attaching Parameter Store policy..."
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name ParameterStoreAccess \
    --policy-document file:///tmp/parameter-store-policy.json \
    2>/dev/null && echo -e "${GREEN}✓ Parameter Store policy attached${NC}" || {
        echo -e "${YELLOW}Policy already attached${NC}"
    }

# Create CloudWatch Logs policy
cat > /tmp/cloudwatch-policy.json << 'EOF'
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
    }
  ]
}
EOF

echo "Attaching CloudWatch Logs policy..."
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name CloudWatchLogsAccess \
    --policy-document file:///tmp/cloudwatch-policy.json \
    2>/dev/null && echo -e "${GREEN}✓ CloudWatch Logs policy attached${NC}" || {
        echo -e "${YELLOW}Policy already attached${NC}"
    }

# Clean up temp files
rm /tmp/lambda-trust-policy.json
rm /tmp/parameter-store-policy.json
rm /tmp/cloudwatch-policy.json

# Wait for role to be ready
echo "Waiting for IAM role to propagate..."
sleep 10

echo -e "${GREEN}✓ IAM role setup complete${NC}"
echo "Role ARN: arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/$ROLE_NAME"
