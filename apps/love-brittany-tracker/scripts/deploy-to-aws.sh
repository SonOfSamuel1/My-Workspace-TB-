#!/bin/bash
# Complete AWS Lambda Deployment Script
# This script automates the entire deployment process

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPO_NAME="love-brittany-automation"
IMAGE_TAG="latest"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Love Brittany AWS Lambda Deployment${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Step 1: Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"
echo ""

# Step 2: Create IAM role
echo -e "${YELLOW}Step 1: Creating IAM role...${NC}"
./scripts/create-iam-role.sh
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}IAM role may already exist, continuing...${NC}"
fi
echo -e "${GREEN}✓ IAM role ready${NC}"
echo ""

# Step 3: Create ECR repository
echo -e "${YELLOW}Step 2: Creating ECR repository...${NC}"
aws ecr create-repository \
    --repository-name $ECR_REPO_NAME \
    --region $AWS_REGION \
    2>/dev/null || echo "Repository already exists"
echo -e "${GREEN}✓ ECR repository ready${NC}"
echo ""

# Step 4: Build Docker image
echo -e "${YELLOW}Step 3: Building Docker image...${NC}"
docker build -t $ECR_REPO_NAME:$IMAGE_TAG -f Dockerfile.lambda .
echo -e "${GREEN}✓ Docker image built${NC}"
echo ""

# Step 5: Login to ECR
echo -e "${YELLOW}Step 4: Logging into ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
echo -e "${GREEN}✓ Logged into ECR${NC}"
echo ""

# Step 6: Tag and push image
echo -e "${YELLOW}Step 5: Pushing image to ECR...${NC}"
docker tag $ECR_REPO_NAME:$IMAGE_TAG \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG
echo -e "${GREEN}✓ Image pushed to ECR${NC}"
echo ""

# Step 7: Create Lambda function
echo -e "${YELLOW}Step 6: Creating Lambda function...${NC}"
./scripts/create-lambda-function.sh
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Lambda function may already exist, updating instead...${NC}"
    ./scripts/update-lambda-function.sh
fi
echo -e "${GREEN}✓ Lambda function ready${NC}"
echo ""

# Step 8: Setup EventBridge schedule
echo -e "${YELLOW}Step 7: Setting up EventBridge schedule...${NC}"
./scripts/setup-eventbridge.sh
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ EventBridge setup failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ EventBridge schedule configured${NC}"
echo ""

# Summary
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "Lambda Function:"
echo "  - love-brittany-weekly-report (runs Sundays at 4:00 AM EST)"
echo ""
echo "⚠️  IMPORTANT: Before the automation will work, you must:"
echo ""
echo "  1. Upload credentials to AWS Parameter Store:"
echo "     ./scripts/setup-parameters.sh"
echo ""
echo "     This uploads:"
echo "     - /love-brittany/calendar-credentials"
echo "     - /love-brittany/calendar-token"
echo "     - /love-brittany/gmail-credentials"
echo "     - /love-brittany/gmail-token"
echo "     - /love-brittany/toggl-api-token"
echo "     - /love-brittany/toggl-workspace-id"
echo ""
echo "     💰 Cost: FREE (Parameter Store standard tier)"
echo ""
echo "Next Steps:"
echo "  1. Monitor CloudWatch Logs:"
echo "     aws logs tail /aws/lambda/love-brittany-weekly-report --follow"
echo ""
echo "  2. Test manually:"
echo "     aws lambda invoke --function-name love-brittany-weekly-report response.json"
echo ""
echo "  3. View schedule:"
echo "     aws events describe-rule --name love-brittany-weekly-report"
echo ""
