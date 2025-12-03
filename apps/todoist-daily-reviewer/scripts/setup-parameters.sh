#!/bin/bash
#
# Setup AWS Parameter Store entries for Daily Todoist Reviewer
#
# Usage:
#   ./scripts/setup-parameters.sh
#
# This script will prompt for values and store them securely in AWS Parameter Store

set -e

AWS_REGION="${AWS_REGION:-us-east-1}"
PREFIX="/todoist-daily-reviewer"

echo "=============================================="
echo "AWS Parameter Store Setup"
echo "=============================================="
echo "Region: $AWS_REGION"
echo "Prefix: $PREFIX"
echo ""

# Function to set a parameter
set_parameter() {
    local name=$1
    local description=$2
    local type=$3
    local value=$4

    echo "Setting $name..."
    aws ssm put-parameter \
        --name "$PREFIX/$name" \
        --description "$description" \
        --type "$type" \
        --value "$value" \
        --overwrite \
        --region "$AWS_REGION"
    echo "  Done!"
}

# Todoist API Token
echo ""
echo "=== Todoist Configuration ==="
read -p "Enter your Todoist API token: " TODOIST_TOKEN
set_parameter "todoist-api-token" "Todoist API token" "SecureString" "$TODOIST_TOKEN"

# Review Email
read -p "Enter the email to receive daily reviews: " REVIEW_EMAIL
set_parameter "review-email" "Email address for daily reviews" "String" "$REVIEW_EMAIL"

# Gmail OAuth Credentials
echo ""
echo "=== Gmail Configuration ==="
echo "You need to provide your Gmail OAuth credentials."
echo "These should be the contents of your gcp-oauth.keys.json file."
read -p "Path to OAuth credentials file: " OAUTH_FILE

if [ -f "$OAUTH_FILE" ]; then
    OAUTH_BASE64=$(base64 -i "$OAUTH_FILE")
    set_parameter "gmail-oauth-credentials" "Gmail OAuth credentials (base64)" "SecureString" "$OAUTH_BASE64"
else
    echo "File not found: $OAUTH_FILE"
    exit 1
fi

# Gmail User Token
echo ""
echo "You need to provide your Gmail user credentials/token."
echo "This should be the contents of your credentials.json file from Gmail MCP."
read -p "Path to user credentials file: " CREDS_FILE

if [ -f "$CREDS_FILE" ]; then
    CREDS_BASE64=$(base64 -i "$CREDS_FILE")
    set_parameter "gmail-credentials" "Gmail user credentials (base64)" "SecureString" "$CREDS_BASE64"
else
    echo "File not found: $CREDS_FILE"
    exit 1
fi

echo ""
echo "=============================================="
echo "Parameter Store Setup Complete!"
echo "=============================================="
echo ""
echo "The following parameters have been created:"
echo "  $PREFIX/todoist-api-token"
echo "  $PREFIX/review-email"
echo "  $PREFIX/gmail-oauth-credentials"
echo "  $PREFIX/gmail-credentials"
echo ""
echo "You can now deploy the Lambda function:"
echo "  ./scripts/deploy.sh"
