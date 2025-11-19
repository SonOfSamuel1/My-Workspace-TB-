#!/bin/bash

# Helper script to export credentials for Lambda deployment
# Run this before deploy-auto.sh

echo "========================================="
echo "Export Credentials for Lambda Deployment"
echo "========================================="
echo ""

echo "This script will help you export the required credentials."
echo ""

# Option 1: From GitHub Secrets
echo "Option 1: Export from GitHub Secrets"
echo "--------------------------------------"
echo ""
echo "Run these commands:"
echo ""
echo "export CLAUDE_CODE_OAUTH_TOKEN=\$(gh secret get CLAUDE_CODE_OAUTH_TOKEN)"
echo "export GMAIL_OAUTH_CREDENTIALS=\$(gh secret get GMAIL_OAUTH_CREDENTIALS)"
echo "export GMAIL_CREDENTIALS=\$(gh secret get GMAIL_CREDENTIALS)"
echo "export TWILIO_ACCOUNT_SID=\$(gh secret get TWILIO_ACCOUNT_SID)"
echo "export TWILIO_AUTH_TOKEN=\$(gh secret get TWILIO_AUTH_TOKEN)"
echo "export TWILIO_FROM_NUMBER=\$(gh secret get TWILIO_FROM_NUMBER)"
echo ""
echo "Then run: ./deploy-auto.sh"
echo ""
echo ""

# Option 2: From local files
echo "Option 2: Export from Local Files"
echo "--------------------------------------"
echo ""
echo "If you have the credentials locally:"
echo ""
echo "# Get Claude token"
echo "export CLAUDE_CODE_OAUTH_TOKEN=\$(claude setup-token | grep 'sk-ant-oat01')"
echo ""
echo "# Encode Gmail credentials"
echo "export GMAIL_OAUTH_CREDENTIALS=\$(cat ~/.gmail-mcp/gcp-oauth.keys.json | base64)"
echo "export GMAIL_CREDENTIALS=\$(cat ~/.gmail-mcp/credentials.json | base64)"
echo ""
echo "# Optional: Twilio"
echo "export TWILIO_ACCOUNT_SID='your-sid'"
echo "export TWILIO_AUTH_TOKEN='your-token'"
echo "export TWILIO_FROM_NUMBER='+1234567890'"
echo ""
echo "Then run: ./deploy-auto.sh"
echo ""
echo ""

# Option 3: Manual entry
echo "Option 3: Manual Entry"
echo "--------------------------------------"
echo ""
echo "Enter credentials manually when prompted by setup-lambda.sh:"
echo "./setup-lambda.sh"
echo ""
