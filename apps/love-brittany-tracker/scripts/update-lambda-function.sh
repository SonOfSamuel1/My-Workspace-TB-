#!/bin/bash
# Update Lambda function with new code

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO_NAME="love-brittany-automation"
IMAGE_TAG="latest"

echo -e "${YELLOW}Updating Lambda function...${NC}"
echo ""

# Build new Docker image
echo "Building Docker image..."
docker build -t $ECR_REPO_NAME:$IMAGE_TAG -f Dockerfile.lambda .
echo -e "${GREEN}✓ Docker image built${NC}"
echo ""

# Login to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
echo -e "${GREEN}✓ Logged into ECR${NC}"
echo ""

# Tag and push image
echo "Pushing image to ECR..."
docker tag $ECR_REPO_NAME:$IMAGE_TAG \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG
echo -e "${GREEN}✓ Image pushed to ECR${NC}"
echo ""

# Update Lambda function
echo "Updating Lambda function code..."
aws lambda update-function-code \
    --function-name love-brittany-weekly-report \
    --image-uri $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG \
    --region $AWS_REGION \
    > /dev/null 2>&1
echo -e "${GREEN}✓ Lambda function updated${NC}"
echo ""

echo -e "${GREEN}✓ Update complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Test the function:"
echo "     ./scripts/test-lambda.sh"
echo ""
echo "  2. Monitor logs:"
echo "     aws logs tail /aws/lambda/love-brittany-weekly-report --follow"
echo ""
