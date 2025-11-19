#!/bin/bash
set -e

# AWS Lambda Deployment Script for Email Assistant
# This script builds and deploys the Lambda function using AWS SAM

echo "========================================="
echo "Email Assistant - AWS Lambda Deployment"
echo "========================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI not installed. Install: https://aws.amazon.com/cli/"
    exit 1
fi

if ! command -v sam &> /dev/null; then
    echo "Error: AWS SAM CLI not installed. Install: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "Error: Docker not installed. Install: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✓ AWS CLI found"
echo "✓ SAM CLI found"
echo "✓ Docker found"
echo ""

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured. Run: aws configure"
    exit 1
fi

echo "✓ AWS credentials configured"
echo ""

# Prompt for parameters
echo "Enter deployment parameters:"
echo ""

read -p "AWS Region (default: us-east-1): " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

read -p "Stack Name (default: email-assistant): " STACK_NAME
STACK_NAME=${STACK_NAME:-email-assistant}

read -p "S3 Bucket for deployment artifacts (will be created if doesn't exist): " S3_BUCKET

if [ -z "$S3_BUCKET" ]; then
    echo "Error: S3 bucket name is required"
    exit 1
fi

echo ""
echo "Checking credentials files..."

# Check if credential files exist
GMAIL_OAUTH_PATH="$HOME/.gmail-mcp/gcp-oauth.keys.json"
GMAIL_CREDS_PATH="$HOME/.gmail-mcp/credentials.json"

if [ ! -f "$GMAIL_OAUTH_PATH" ]; then
    echo "Error: Gmail OAuth credentials not found at $GMAIL_OAUTH_PATH"
    exit 1
fi

if [ ! -f "$GMAIL_CREDS_PATH" ]; then
    echo "Error: Gmail credentials not found at $GMAIL_CREDS_PATH"
    exit 1
fi

echo "✓ Gmail credentials found"
echo ""

# Encode credentials
echo "Encoding credentials to base64..."
GMAIL_OAUTH_BASE64=$(cat "$GMAIL_OAUTH_PATH" | base64)
GMAIL_CREDS_BASE64=$(cat "$GMAIL_CREDS_PATH" | base64)

# Prompt for Claude Code token
echo ""
read -sp "Claude Code OAuth Token (sk-ant-oat01-...): " CLAUDE_TOKEN
echo ""

if [ -z "$CLAUDE_TOKEN" ]; then
    echo "Error: Claude Code OAuth token is required"
    exit 1
fi

# Optional: Twilio credentials
echo ""
read -p "Twilio Account SID (optional, press Enter to skip): " TWILIO_SID
read -sp "Twilio Auth Token (optional, press Enter to skip): " TWILIO_TOKEN
echo ""
read -p "Twilio From Number (e.g., +1234567890, optional): " TWILIO_FROM

# Escalation phone
read -p "Escalation Phone Number (default: +14077448449): " ESCALATION_PHONE
ESCALATION_PHONE=${ESCALATION_PHONE:-+14077448449}

# Create S3 bucket if it doesn't exist
echo ""
echo "Checking S3 bucket..."
if ! aws s3 ls "s3://$S3_BUCKET" 2>&1 > /dev/null; then
    echo "Creating S3 bucket: $S3_BUCKET"
    if [ "$AWS_REGION" == "us-east-1" ]; then
        aws s3 mb "s3://$S3_BUCKET" --region "$AWS_REGION"
    else
        aws s3 mb "s3://$S3_BUCKET" --region "$AWS_REGION" --create-bucket-configuration LocationConstraint="$AWS_REGION"
    fi
else
    echo "✓ S3 bucket exists: $S3_BUCKET"
fi

# Build parameters file
echo ""
echo "Creating parameter overrides..."
PARAMS="ParameterKey=ClaudeCodeOAuthToken,ParameterValue=\"$CLAUDE_TOKEN\""
PARAMS="$PARAMS ParameterKey=GmailOAuthCredentials,ParameterValue=\"$GMAIL_OAUTH_BASE64\""
PARAMS="$PARAMS ParameterKey=GmailCredentials,ParameterValue=\"$GMAIL_CREDS_BASE64\""
PARAMS="$PARAMS ParameterKey=EscalationPhone,ParameterValue=\"$ESCALATION_PHONE\""

if [ -n "$TWILIO_SID" ]; then
    PARAMS="$PARAMS ParameterKey=TwilioAccountSid,ParameterValue=\"$TWILIO_SID\""
fi

if [ -n "$TWILIO_TOKEN" ]; then
    PARAMS="$PARAMS ParameterKey=TwilioAuthToken,ParameterValue=\"$TWILIO_TOKEN\""
fi

if [ -n "$TWILIO_FROM" ]; then
    PARAMS="$PARAMS ParameterKey=TwilioFromNumber,ParameterValue=\"$TWILIO_FROM\""
fi

# Build and deploy
echo ""
echo "Building Lambda function with Docker..."
sam build --use-container

echo ""
echo "Deploying to AWS Lambda..."
sam deploy \
    --stack-name "$STACK_NAME" \
    --s3-bucket "$S3_BUCKET" \
    --region "$AWS_REGION" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides $PARAMS \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Stack Name: $STACK_NAME"
echo "Region: $AWS_REGION"
echo "Function Name: email-assistant-processor"
echo ""
echo "To view logs:"
echo "  aws logs tail /aws/lambda/email-assistant-processor --follow --region $AWS_REGION"
echo ""
echo "To invoke manually:"
echo "  aws lambda invoke --function-name email-assistant-processor --region $AWS_REGION response.json"
echo ""
echo "Scheduled runs: Every hour from 7 AM - 5 PM EST (Mon-Fri)"
echo ""
