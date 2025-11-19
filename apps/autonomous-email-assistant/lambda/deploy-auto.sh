#!/bin/bash
set -e

# Automated AWS Lambda Deployment Script
# Uses credentials from environment variables or GitHub secrets

echo "========================================="
echo "Email Assistant - Automated Lambda Deploy"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }

# Configuration from environment or defaults
AWS_REGION=${AWS_REGION:-us-east-1}
FUNCTION_NAME="email-assistant-processor"
ECR_REPO_NAME="email-assistant"

echo "Configuration:"
echo "  - Region: $AWS_REGION"
echo "  - Function: $FUNCTION_NAME"
echo ""

# Check prerequisites
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not installed"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    print_error "Docker not installed"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_success "AWS Account: $AWS_ACCOUNT_ID"

# Get credentials from environment or GitHub secrets export
if [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    print_error "CLAUDE_CODE_OAUTH_TOKEN environment variable not set"
    echo ""
    echo "Options:"
    echo "1. Export from GitHub secrets:"
    echo "   gh secret list"
    echo "   export CLAUDE_CODE_OAUTH_TOKEN=\$(gh secret get CLAUDE_CODE_OAUTH_TOKEN)"
    echo ""
    echo "2. Get new token:"
    echo "   claude setup-token"
    echo "   export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-..."
    exit 1
fi

if [ -z "$GMAIL_OAUTH_CREDENTIALS" ] || [ -z "$GMAIL_CREDENTIALS" ]; then
    print_error "Gmail credentials not set in environment"
    echo ""
    echo "Options:"
    echo "1. Export from GitHub secrets:"
    echo "   export GMAIL_OAUTH_CREDENTIALS=\$(gh secret get GMAIL_OAUTH_CREDENTIALS)"
    echo "   export GMAIL_CREDENTIALS=\$(gh secret get GMAIL_CREDENTIALS)"
    echo ""
    echo "2. Encode from local files:"
    echo "   export GMAIL_OAUTH_CREDENTIALS=\$(cat ~/.gmail-mcp/gcp-oauth.keys.json | base64)"
    echo "   export GMAIL_CREDENTIALS=\$(cat ~/.gmail-mcp/credentials.json | base64)"
    exit 1
fi

print_success "All credentials found in environment"

# Optional credentials
ESCALATION_PHONE=${ESCALATION_PHONE:-+14077448449}

echo ""
echo "========================================="
echo "Step 1: Create ECR Repository"
echo "========================================="
echo ""

if aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION 2>&1 > /dev/null; then
    print_success "ECR repository exists: $ECR_REPO_NAME"
else
    echo "Creating ECR repository..."
    aws ecr create-repository \
        --repository-name $ECR_REPO_NAME \
        --region $AWS_REGION \
        --image-scanning-configuration scanOnPush=true \
        > /dev/null
    print_success "ECR repository created"
fi

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo ""
echo "========================================="
echo "Step 2: Build Docker Image"
echo "========================================="
echo ""

echo "Building Docker image..."
docker build --platform linux/amd64 -t $ECR_REPO_NAME:latest -f Dockerfile .
print_success "Docker image built"

echo ""
echo "========================================="
echo "Step 3: Push to ECR"
echo "========================================="
echo ""

echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_URI

print_success "Logged in to ECR"

echo "Tagging and pushing image..."
docker tag $ECR_REPO_NAME:latest $ECR_URI:latest
docker push $ECR_URI:latest
print_success "Image pushed to ECR"

echo ""
echo "========================================="
echo "Step 4: Create IAM Role"
echo "========================================="
echo ""

ROLE_NAME="EmailAssistantLambdaRole"

if aws iam get-role --role-name $ROLE_NAME 2>&1 > /dev/null; then
    print_success "IAM role exists: $ROLE_NAME"
else
    echo "Creating IAM role..."

    cat > /tmp/trust-policy.json <<'EOF'
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

    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        > /dev/null

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    print_success "IAM role created"
    echo "Waiting for role to propagate..."
    sleep 10
fi

ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)

echo ""
echo "========================================="
echo "Step 5: Create/Update Lambda Function"
echo "========================================="
echo ""

# Build environment variables
ENV_VARS="{\"CLAUDE_CODE_OAUTH_TOKEN\":\"$CLAUDE_CODE_OAUTH_TOKEN\",\"GMAIL_OAUTH_CREDENTIALS\":\"$GMAIL_OAUTH_CREDENTIALS\",\"GMAIL_CREDENTIALS\":\"$GMAIL_CREDENTIALS\",\"ESCALATION_PHONE\":\"$ESCALATION_PHONE\""

if [ -n "$TWILIO_ACCOUNT_SID" ]; then
    ENV_VARS="${ENV_VARS},\"TWILIO_ACCOUNT_SID\":\"$TWILIO_ACCOUNT_SID\""
fi

if [ -n "$TWILIO_AUTH_TOKEN" ]; then
    ENV_VARS="${ENV_VARS},\"TWILIO_AUTH_TOKEN\":\"$TWILIO_AUTH_TOKEN\""
fi

if [ -n "$TWILIO_FROM_NUMBER" ]; then
    ENV_VARS="${ENV_VARS},\"TWILIO_FROM_NUMBER\":\"$TWILIO_FROM_NUMBER\""
fi

ENV_VARS="${ENV_VARS}}"

if aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION 2>&1 > /dev/null; then
    echo "Updating existing Lambda function..."

    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --image-uri $ECR_URI:latest \
        --region $AWS_REGION \
        > /dev/null

    print_success "Function code updated"

    echo "Waiting for update..."
    aws lambda wait function-updated \
        --function-name $FUNCTION_NAME \
        --region $AWS_REGION

    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --environment "Variables=$ENV_VARS" \
        --region $AWS_REGION \
        > /dev/null

    print_success "Function configuration updated"

else
    echo "Creating new Lambda function..."

    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --package-type Image \
        --code ImageUri=$ECR_URI:latest \
        --role $ROLE_ARN \
        --timeout 600 \
        --memory-size 1024 \
        --environment "Variables=$ENV_VARS" \
        --region $AWS_REGION \
        > /dev/null

    print_success "Lambda function created"
fi

echo ""
echo "========================================="
echo "Step 6: Create EventBridge Schedule"
echo "========================================="
echo ""

RULE_NAME="email-assistant-hourly-schedule"

if aws events describe-rule --name $RULE_NAME --region $AWS_REGION 2>&1 > /dev/null; then
    print_success "EventBridge rule exists"
else
    echo "Creating EventBridge rule..."

    aws events put-rule \
        --name $RULE_NAME \
        --schedule-expression "cron(0 12-22 ? * MON-FRI *)" \
        --description "Hourly email processing 7 AM - 5 PM EST (Mon-Fri)" \
        --region $AWS_REGION \
        > /dev/null

    print_success "EventBridge rule created"
fi

echo "Adding Lambda permission..."
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id EventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:$AWS_REGION:$AWS_ACCOUNT_ID:rule/$RULE_NAME" \
    --region $AWS_REGION \
    2>&1 > /dev/null || true

FUNCTION_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION --query 'Configuration.FunctionArn' --output text)

echo "Adding EventBridge target..."
aws events put-targets \
    --rule $RULE_NAME \
    --targets "Id=1,Arn=$FUNCTION_ARN" \
    --region $AWS_REGION \
    > /dev/null

print_success "EventBridge schedule configured"

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
print_success "AWS Lambda function deployed!"
echo ""
echo "Function: $FUNCTION_NAME"
echo "Region: $AWS_REGION"
echo "ARN: $FUNCTION_ARN"
echo ""
echo "Next steps:"
echo "  1. Test: aws lambda invoke --function-name $FUNCTION_NAME response.json"
echo "  2. Logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
