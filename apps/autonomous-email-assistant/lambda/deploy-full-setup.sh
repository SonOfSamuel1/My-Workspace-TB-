#!/bin/bash
set -e

# Complete setup and deployment for AWS Lambda
# This script handles EVERYTHING: credentials setup + Lambda deployment

echo "========================================="
echo "Email Assistant - Complete Lambda Setup"
echo "========================================="
echo ""
echo "This script will:"
echo "  1. Set up Gmail MCP credentials (if needed)"
echo "  2. Get Claude Code OAuth token"
echo "  3. Set up Twilio (optional)"
echo "  4. Deploy to AWS Lambda"
echo "  5. Create EventBridge schedule"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not installed. Install: https://aws.amazon.com/cli/"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    print_error "Docker not installed. Install: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v claude &> /dev/null; then
    print_error "Claude Code CLI not installed. Install: npm install -g @anthropic-ai/claude-code"
    exit 1
fi

print_success "All tools installed"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Run: aws configure"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}

print_success "AWS Account: $AWS_ACCOUNT_ID"
print_success "AWS Region: $AWS_REGION"

echo ""
echo "========================================="
echo "Step 1: Gmail MCP Setup"
echo "========================================="
echo ""

# Check if Gmail credentials exist
GMAIL_OAUTH_PATH="$HOME/.gmail-mcp/gcp-oauth.keys.json"
GMAIL_CREDS_PATH="$HOME/.gmail-mcp/credentials.json"

if [ -f "$GMAIL_OAUTH_PATH" ] && [ -f "$GMAIL_CREDS_PATH" ]; then
    print_success "Gmail credentials found at ~/.gmail-mcp/"

    # Encode credentials
    GMAIL_OAUTH_BASE64=$(cat "$GMAIL_OAUTH_PATH" | base64)
    GMAIL_CREDS_BASE64=$(cat "$GMAIL_CREDS_PATH" | base64)

else
    print_warning "Gmail MCP credentials not found"
    echo ""
    echo "You need to set up Gmail MCP first:"
    echo ""
    echo "1. Install Gmail MCP server:"
    echo "   npm install -g @gongrzhe/server-gmail-autoauth-mcp"
    echo ""
    echo "2. Set up Google Cloud Project:"
    echo "   - Go to https://console.cloud.google.com"
    echo "   - Create a new project"
    echo "   - Enable Gmail API"
    echo "   - Create OAuth 2.0 credentials (Desktop app)"
    echo "   - Download as gcp-oauth.keys.json"
    echo ""
    echo "3. Run the MCP server to authenticate:"
    echo "   npx @gongrzhe/server-gmail-autoauth-mcp"
    echo "   (This will create ~/.gmail-mcp/ directory with credentials)"
    echo ""
    read -p "Have you completed Gmail MCP setup? (y/n) " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Please set up Gmail MCP first, then run this script again"
        exit 1
    fi

    # Check again
    if [ ! -f "$GMAIL_OAUTH_PATH" ] || [ ! -f "$GMAIL_CREDS_PATH" ]; then
        print_error "Gmail credentials still not found at ~/.gmail-mcp/"
        exit 1
    fi

    GMAIL_OAUTH_BASE64=$(cat "$GMAIL_OAUTH_PATH" | base64)
    GMAIL_CREDS_BASE64=$(cat "$GMAIL_CREDS_PATH" | base64)
    print_success "Gmail credentials loaded"
fi

echo ""
echo "========================================="
echo "Step 2: Claude Code OAuth Token"
echo "========================================="
echo ""

if [ -n "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    print_success "Claude token found in environment"
else
    echo "Getting Claude Code OAuth token..."
    echo ""
    echo "Option 1: Run 'claude setup-token' to get a new token"
    echo "Option 2: Paste an existing token"
    echo ""
    read -p "Do you want to run 'claude setup-token'? (y/n) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "Running 'claude setup-token'..."
        echo "This will open your browser. After authentication, paste the token here."
        echo ""

        # This won't work in headless mode, so just prompt
        print_warning "Please run 'claude setup-token' in another terminal"
        print_warning "Then paste the token (starts with sk-ant-oat01-) when prompted"
        echo ""
    fi

    read -sp "Paste Claude Code OAuth Token: " CLAUDE_CODE_OAUTH_TOKEN
    echo ""

    if [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
        print_error "Claude Code OAuth token is required"
        exit 1
    fi

    print_success "Claude token received"
fi

echo ""
echo "========================================="
echo "Step 3: Twilio Setup (Optional)"
echo "========================================="
echo ""

echo "Twilio is used for SMS escalation alerts (Tier 1 urgent emails)"
read -p "Do you want to set up Twilio? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Twilio Account SID: " TWILIO_ACCOUNT_SID
    read -sp "Twilio Auth Token: " TWILIO_AUTH_TOKEN
    echo ""
    read -p "Twilio From Number (e.g., +1234567890): " TWILIO_FROM_NUMBER

    if [ -n "$TWILIO_ACCOUNT_SID" ]; then
        print_success "Twilio credentials saved"
    fi
else
    print_warning "Skipping Twilio setup (SMS alerts disabled)"
fi

ESCALATION_PHONE=${ESCALATION_PHONE:-+14077448449}

echo ""
echo "========================================="
echo "Step 4: Deploy to AWS Lambda"
echo "========================================="
echo ""

FUNCTION_NAME="email-assistant-processor"
ECR_REPO_NAME="email-assistant"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

# Create ECR repository
echo "Creating ECR repository..."
if aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION 2>&1 > /dev/null; then
    print_success "ECR repository exists"
else
    aws ecr create-repository \
        --repository-name $ECR_REPO_NAME \
        --region $AWS_REGION \
        --image-scanning-configuration scanOnPush=true \
        > /dev/null
    print_success "ECR repository created"
fi

# Build Docker image
echo ""
echo "Building Docker image (this may take a few minutes)..."
docker build --platform linux/amd64 -t $ECR_REPO_NAME:latest -f Dockerfile . || {
    print_error "Docker build failed"
    exit 1
}
print_success "Docker image built"

# Push to ECR
echo ""
echo "Pushing image to ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_URI

docker tag $ECR_REPO_NAME:latest $ECR_URI:latest
docker push $ECR_URI:latest
print_success "Image pushed to ECR"

# Create IAM role
echo ""
echo "Creating IAM role..."
ROLE_NAME="EmailAssistantLambdaRole"

if aws iam get-role --role-name $ROLE_NAME 2>&1 > /dev/null; then
    print_success "IAM role exists"
else
    cat > /tmp/trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
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
    sleep 10
fi

ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)

# Create Lambda function
echo ""
echo "Creating Lambda function..."

ENV_VARS="{\"CLAUDE_CODE_OAUTH_TOKEN\":\"$CLAUDE_CODE_OAUTH_TOKEN\",\"GMAIL_OAUTH_CREDENTIALS\":\"$GMAIL_OAUTH_BASE64\",\"GMAIL_CREDENTIALS\":\"$GMAIL_CREDS_BASE64\",\"ESCALATION_PHONE\":\"$ESCALATION_PHONE\""

if [ -n "$TWILIO_ACCOUNT_SID" ]; then
    ENV_VARS="${ENV_VARS},\"TWILIO_ACCOUNT_SID\":\"$TWILIO_ACCOUNT_SID\",\"TWILIO_AUTH_TOKEN\":\"$TWILIO_AUTH_TOKEN\",\"TWILIO_FROM_NUMBER\":\"$TWILIO_FROM_NUMBER\""
fi

ENV_VARS="${ENV_VARS}}"

if aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION 2>&1 > /dev/null; then
    print_warning "Function exists, updating..."

    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --image-uri $ECR_URI:latest \
        --region $AWS_REGION \
        > /dev/null

    aws lambda wait function-updated \
        --function-name $FUNCTION_NAME \
        --region $AWS_REGION

    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --environment "Variables=$ENV_VARS" \
        --region $AWS_REGION \
        > /dev/null

    print_success "Function updated"
else
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

    print_success "Function created"
fi

# Create EventBridge schedule
echo ""
echo "Creating EventBridge schedule..."

RULE_NAME="email-assistant-hourly-schedule"

if ! aws events describe-rule --name $RULE_NAME --region $AWS_REGION 2>&1 > /dev/null; then
    aws events put-rule \
        --name $RULE_NAME \
        --schedule-expression "cron(0 12-22 ? * MON-FRI *)" \
        --description "Hourly email processing 7 AM - 5 PM EST (Mon-Fri)" \
        --region $AWS_REGION \
        > /dev/null
fi

aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id EventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:$AWS_REGION:$AWS_ACCOUNT_ID:rule/$RULE_NAME" \
    --region $AWS_REGION \
    2>&1 > /dev/null || true

FUNCTION_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION --query 'Configuration.FunctionArn' --output text)

aws events put-targets \
    --rule $RULE_NAME \
    --targets "Id=1,Arn=$FUNCTION_ARN" \
    --region $AWS_REGION \
    > /dev/null

print_success "EventBridge schedule configured"

echo ""
echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""
print_success "Your email assistant is now running on AWS Lambda!"
echo ""
echo "Details:"
echo "  Function: $FUNCTION_NAME"
echo "  Region: $AWS_REGION"
echo "  Schedule: Every hour, 7 AM - 5 PM EST (Mon-Fri)"
echo ""
echo "Next steps:"
echo ""
echo "  1. Test the function:"
echo "     aws lambda invoke --function-name $FUNCTION_NAME response.json"
echo "     cat response.json"
echo ""
echo "  2. View logs:"
echo "     aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
echo "  3. Monitor in AWS Console:"
echo "     https://$AWS_REGION.console.aws.amazon.com/lambda/home#/functions/$FUNCTION_NAME"
echo ""
print_success "Setup complete!"
echo ""
