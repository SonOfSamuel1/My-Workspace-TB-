#!/bin/bash
set -e

# Interactive AWS Lambda Setup Script
# Simplified deployment without SAM - uses AWS CLI directly

echo "========================================="
echo "Email Assistant - AWS Lambda Setup"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not installed. Install: https://aws.amazon.com/cli/"
    exit 1
fi
print_success "AWS CLI found"

if ! command -v docker &> /dev/null; then
    print_error "Docker not installed. Install: https://docs.docker.com/get-docker/"
    exit 1
fi
print_success "Docker found"

if ! command -v zip &> /dev/null; then
    print_error "zip command not found"
    exit 1
fi
print_success "zip found"

echo ""

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Run: aws configure"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_success "AWS credentials configured (Account: $AWS_ACCOUNT_ID)"

echo ""
echo "========================================="
echo "Deployment Configuration"
echo "========================================="
echo ""

# Get configuration
read -p "AWS Region (default: us-east-1): " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

FUNCTION_NAME="email-assistant-processor"
ECR_REPO_NAME="email-assistant"

print_success "Configuration set:"
echo "  - Region: $AWS_REGION"
echo "  - Function: $FUNCTION_NAME"
echo "  - ECR Repo: $ECR_REPO_NAME"

echo ""
echo "========================================="
echo "Gathering Credentials"
echo "========================================="
echo ""

# Check Gmail credentials
GMAIL_OAUTH_PATH="$HOME/.gmail-mcp/gcp-oauth.keys.json"
GMAIL_CREDS_PATH="$HOME/.gmail-mcp/credentials.json"

if [ ! -f "$GMAIL_OAUTH_PATH" ]; then
    print_error "Gmail OAuth credentials not found at $GMAIL_OAUTH_PATH"
    exit 1
fi

if [ ! -f "$GMAIL_CREDS_PATH" ]; then
    print_error "Gmail credentials not found at $GMAIL_CREDS_PATH"
    exit 1
fi

print_success "Gmail credentials found"

# Encode credentials
GMAIL_OAUTH_BASE64=$(cat "$GMAIL_OAUTH_PATH" | base64)
GMAIL_CREDS_BASE64=$(cat "$GMAIL_CREDS_PATH" | base64)

# Get Claude Code token
echo ""
read -sp "Enter Claude Code OAuth Token (sk-ant-oat01-...): " CLAUDE_TOKEN
echo ""

if [ -z "$CLAUDE_TOKEN" ]; then
    print_error "Claude Code OAuth token is required"
    exit 1
fi
print_success "Claude token received"

# Optional Twilio
echo ""
read -p "Enter Twilio Account SID (optional, press Enter to skip): " TWILIO_SID
if [ -n "$TWILIO_SID" ]; then
    read -sp "Enter Twilio Auth Token: " TWILIO_TOKEN
    echo ""
    read -p "Enter Twilio From Number (e.g., +1234567890): " TWILIO_FROM
fi

read -p "Escalation Phone (default: +14077448449): " ESCALATION_PHONE
ESCALATION_PHONE=${ESCALATION_PHONE:-+14077448449}

echo ""
echo "========================================="
echo "Step 1: Create ECR Repository"
echo "========================================="
echo ""

# Check if ECR repo exists
if aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION 2>&1 > /dev/null; then
    print_success "ECR repository already exists: $ECR_REPO_NAME"
else
    echo "Creating ECR repository: $ECR_REPO_NAME"
    aws ecr create-repository \
        --repository-name $ECR_REPO_NAME \
        --region $AWS_REGION \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256 \
        > /dev/null
    print_success "ECR repository created"
fi

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"
echo "ECR URI: $ECR_URI"

echo ""
echo "========================================="
echo "Step 2: Build Docker Image"
echo "========================================="
echo ""

echo "Building Docker image for x86_64 architecture..."
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

echo "Tagging image..."
docker tag $ECR_REPO_NAME:latest $ECR_URI:latest

echo "Pushing image to ECR..."
docker push $ECR_URI:latest
print_success "Image pushed to ECR"

echo ""
echo "========================================="
echo "Step 4: Create IAM Role for Lambda"
echo "========================================="
echo ""

ROLE_NAME="EmailAssistantLambdaRole"

# Check if role exists
if aws iam get-role --role-name $ROLE_NAME 2>&1 > /dev/null; then
    print_success "IAM role already exists: $ROLE_NAME"
else
    echo "Creating IAM role: $ROLE_NAME"

    # Create trust policy
    cat > /tmp/trust-policy.json <<EOF
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

    # Attach basic execution policy
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    print_success "IAM role created"

    # Wait for role to propagate
    echo "Waiting for IAM role to propagate..."
    sleep 10
fi

ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
echo "Role ARN: $ROLE_ARN"

echo ""
echo "========================================="
echo "Step 5: Create/Update Lambda Function"
echo "========================================="
echo ""

# Build environment variables JSON
ENV_VARS=$(cat <<EOF
{
  "CLAUDE_CODE_OAUTH_TOKEN": "$CLAUDE_TOKEN",
  "GMAIL_OAUTH_CREDENTIALS": "$GMAIL_OAUTH_BASE64",
  "GMAIL_CREDENTIALS": "$GMAIL_CREDS_BASE64",
  "ESCALATION_PHONE": "$ESCALATION_PHONE"
EOF
)

if [ -n "$TWILIO_SID" ]; then
    ENV_VARS="$ENV_VARS,"
    ENV_VARS="$ENV_VARS
  \"TWILIO_ACCOUNT_SID\": \"$TWILIO_SID\",
  \"TWILIO_AUTH_TOKEN\": \"$TWILIO_TOKEN\",
  \"TWILIO_FROM_NUMBER\": \"$TWILIO_FROM\""
fi

ENV_VARS="$ENV_VARS
}"

# Check if function exists
if aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION 2>&1 > /dev/null; then
    echo "Updating existing Lambda function..."

    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --image-uri $ECR_URI:latest \
        --region $AWS_REGION \
        > /dev/null

    print_success "Function code updated"

    # Wait for update to complete
    echo "Waiting for update to complete..."
    aws lambda wait function-updated \
        --function-name $FUNCTION_NAME \
        --region $AWS_REGION

    # Update environment variables
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

# Create EventBridge rule
if aws events describe-rule --name $RULE_NAME --region $AWS_REGION 2>&1 > /dev/null; then
    print_success "EventBridge rule already exists: $RULE_NAME"
else
    echo "Creating EventBridge rule..."

    aws events put-rule \
        --name $RULE_NAME \
        --schedule-expression "cron(0 12-22 ? * MON-FRI *)" \
        --description "Hourly email processing from 7 AM to 5 PM EST (Mon-Fri)" \
        --region $AWS_REGION \
        > /dev/null

    print_success "EventBridge rule created"
fi

# Add Lambda permission for EventBridge
echo "Adding Lambda invoke permission for EventBridge..."

aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id EventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:$AWS_REGION:$AWS_ACCOUNT_ID:rule/$RULE_NAME" \
    --region $AWS_REGION \
    2>&1 > /dev/null || true

print_success "Lambda permission added"

# Add target to EventBridge rule
echo "Adding Lambda as target to EventBridge rule..."

FUNCTION_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION --query 'Configuration.FunctionArn' --output text)

aws events put-targets \
    --rule $RULE_NAME \
    --targets "Id=1,Arn=$FUNCTION_ARN" \
    --region $AWS_REGION \
    > /dev/null

print_success "EventBridge target added"

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
print_success "AWS Lambda function deployed successfully!"
echo ""
echo "Function details:"
echo "  - Name: $FUNCTION_NAME"
echo "  - Region: $AWS_REGION"
echo "  - ARN: $FUNCTION_ARN"
echo ""
echo "Schedule:"
echo "  - Runs every hour from 7 AM - 5 PM EST (Mon-Fri)"
echo "  - EventBridge rule: $RULE_NAME"
echo ""
echo "Next steps:"
echo "  1. Test function manually:"
echo "     aws lambda invoke --function-name $FUNCTION_NAME --region $AWS_REGION response.json"
echo ""
echo "  2. View logs:"
echo "     aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region $AWS_REGION"
echo ""
echo "  3. Monitor in AWS Console:"
echo "     https://$AWS_REGION.console.aws.amazon.com/lambda/home?region=$AWS_REGION#/functions/$FUNCTION_NAME"
echo ""
