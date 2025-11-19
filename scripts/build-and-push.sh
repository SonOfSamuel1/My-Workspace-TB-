#!/bin/bash
# Build Docker image and push to ECR

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="email-assistant-automation"
IMAGE_TAG=${IMAGE_TAG:-latest}

echo -e "${YELLOW}Building and pushing Email Assistant Docker image...${NC}"

# Create ECR repository if it doesn't exist
echo "Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION 2>/dev/null || {
    echo "Creating ECR repository: $ECR_REPOSITORY"
    aws ecr create-repository \
        --repository-name $ECR_REPOSITORY \
        --region $AWS_REGION \
        --image-scanning-configuration scanOnPush=true
    echo -e "${GREEN}✓ ECR repository created${NC}"
}

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
echo -e "${GREEN}✓ Logged in to ECR${NC}"

# Build Docker image for Lambda ARM64
# Disable provenance and SBOM for Lambda compatibility
echo "Building Docker image for ARM64 (Lambda architecture)..."
docker build --platform linux/arm64 --provenance=false --sbom=false -f Dockerfile.lambda -t $ECR_REPOSITORY:$IMAGE_TAG .
echo -e "${GREEN}✓ Docker image built${NC}"

# Tag image for ECR
echo "Tagging image for ECR..."
docker tag $ECR_REPOSITORY:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG
echo -e "${GREEN}✓ Image tagged${NC}"

# Push to ECR
echo "Pushing image to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG
echo -e "${GREEN}✓ Image pushed to ECR${NC}"

echo ""
echo -e "${GREEN}✓ Build and push complete${NC}"
echo ""
echo "Image URI: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"
echo ""
