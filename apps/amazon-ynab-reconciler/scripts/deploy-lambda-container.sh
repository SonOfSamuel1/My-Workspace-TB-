#!/bin/bash

# Amazon-YNAB Reconciler Lambda Container Deployment Script
# Deploys the containerized Lambda function to AWS

set -e

# Configuration
FUNCTION_NAME="amazon-ynab-reconciler"
REGION=${AWS_REGION:-"us-east-1"}
ACCOUNT_ID=${AWS_ACCOUNT_ID:-""}
ECR_REPO_NAME="amazon-ynab-reconciler"
IMAGE_TAG="latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Amazon-YNAB Reconciler Lambda Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Get AWS account ID if not provided
if [ -z "$ACCOUNT_ID" ]; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    echo -e "${YELLOW}Using AWS Account ID: $ACCOUNT_ID${NC}"
fi

ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME"

# Step 1: Create ECR repository if it doesn't exist
echo -e "\n${YELLOW}Step 1: Creating ECR repository...${NC}"
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $ECR_REPO_NAME --region $REGION

# Step 2: Login to ECR
echo -e "\n${YELLOW}Step 2: Logging in to ECR...${NC}"
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

# Step 3: Build Docker image
echo -e "\n${YELLOW}Step 3: Building Docker image...${NC}"
cd ../lambda
docker build -t $ECR_REPO_NAME:$IMAGE_TAG .

# Step 4: Tag image for ECR
echo -e "\n${YELLOW}Step 4: Tagging image for ECR...${NC}"
docker tag $ECR_REPO_NAME:$IMAGE_TAG $ECR_URI:$IMAGE_TAG

# Step 5: Push image to ECR
echo -e "\n${YELLOW}Step 5: Pushing image to ECR...${NC}"
docker push $ECR_URI:$IMAGE_TAG

# Step 6: Create or update Lambda function
echo -e "\n${YELLOW}Step 6: Updating Lambda function...${NC}"

# Check if function exists
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null; then
    echo "Updating existing function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --image-uri $ECR_URI:$IMAGE_TAG \
        --region $REGION
else
    echo "Creating new function..."
    echo -e "${YELLOW}Please create the Lambda function manually with:${NC}"
    echo "  - Container image: $ECR_URI:$IMAGE_TAG"
    echo "  - Memory: 3008 MB"
    echo "  - Timeout: 300 seconds"
    echo "  - Handler: lambda_handler.lambda_handler"
fi

# Step 7: Update function configuration
echo -e "\n${YELLOW}Step 7: Updating function configuration...${NC}"
aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --timeout 300 \
    --memory-size 3008 \
    --environment "Variables={AWS_REGION=$REGION}" \
    --region $REGION 2>/dev/null || echo "Function configuration update skipped"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Set up Parameter Store values:"
echo "   - /amazon-reconciler/amazon-email"
echo "   - /amazon-reconciler/amazon-password"
echo "   - /amazon-reconciler/ynab-api-key"
echo "   - /amazon-reconciler/gmail-credentials"
echo "   - /amazon-reconciler/gmail-token"
echo ""
echo "2. Create EventBridge rule for scheduling:"
echo "   aws events put-rule --name amazon-ynab-daily --schedule-expression 'cron(0 7 * * ? *)'"
echo ""
echo "3. Test the function:"
echo "   aws lambda invoke --function-name $FUNCTION_NAME --payload '{\"dry_run\": true}' response.json"