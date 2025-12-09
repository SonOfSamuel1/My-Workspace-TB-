#!/bin/bash

# Script to set up AWS Parameter Store values for Amazon-YNAB Reconciler

set -e

# Configuration
REGION=${AWS_REGION:-"us-east-1"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Amazon-YNAB Reconciler Parameter Store Setup${NC}"
echo -e "${GREEN}================================================${NC}"

# Function to create/update parameter
create_parameter() {
    local name=$1
    local description=$2
    local is_secret=$3

    echo -e "\n${YELLOW}Setting up parameter: $name${NC}"
    echo -e "Description: $description"

    if [ "$is_secret" = "true" ]; then
        echo -n "Enter value (hidden): "
        read -s value
        echo ""

        aws ssm put-parameter \
            --name "$name" \
            --value "$value" \
            --type "SecureString" \
            --overwrite \
            --region $REGION \
            2>/dev/null && echo -e "${GREEN}✓ Parameter created/updated${NC}" || echo -e "${RED}✗ Failed${NC}"
    else
        echo -n "Enter value: "
        read value

        aws ssm put-parameter \
            --name "$name" \
            --value "$value" \
            --type "String" \
            --overwrite \
            --region $REGION \
            2>/dev/null && echo -e "${GREEN}✓ Parameter created/updated${NC}" || echo -e "${RED}✗ Failed${NC}"
    fi
}

# Create parameters
echo -e "\n${YELLOW}This script will help you set up the required AWS Parameter Store values.${NC}"
echo -e "${YELLOW}All sensitive values will be encrypted using KMS.${NC}"

# Amazon credentials
create_parameter "/amazon-reconciler/amazon-email" "Your Amazon account email" false
create_parameter "/amazon-reconciler/amazon-password" "Your Amazon account password" true

echo -e "\n${YELLOW}Optional: Amazon 2FA Secret${NC}"
echo -n "Do you have 2FA enabled on Amazon? (y/n): "
read has_2fa
if [ "$has_2fa" = "y" ]; then
    create_parameter "/amazon-reconciler/amazon-otp-secret" "Your Amazon 2FA secret key" true
fi

# YNAB API
create_parameter "/amazon-reconciler/ynab-api-key" "Your YNAB Personal Access Token" true

# Email settings
create_parameter "/amazon-reconciler/email-recipient" "Email address for reports" false

# Gmail credentials (optional)
echo -e "\n${YELLOW}Gmail API Credentials (for sending reports)${NC}"
echo -n "Do you want to set up Gmail credentials? (y/n): "
read setup_gmail

if [ "$setup_gmail" = "y" ]; then
    echo -e "\n${YELLOW}For Gmail credentials:${NC}"
    echo "1. Copy your credentials.json content"
    echo "2. Paste it when prompted (as a single line)"
    create_parameter "/amazon-reconciler/gmail-credentials" "Gmail API credentials JSON" true

    echo -e "\n${YELLOW}For Gmail token:${NC}"
    echo "1. Base64 encode your token.pickle file:"
    echo "   base64 < token.pickle"
    echo "2. Paste the encoded string when prompted"
    create_parameter "/amazon-reconciler/gmail-token" "Gmail token (base64 encoded)" true
fi

# Browserbase credentials (optional)
echo -e "\n${YELLOW}Browserbase Cloud Browser Setup${NC}"
echo -e "Browserbase provides cloud-based browser automation for scraping Amazon."
echo -e "It's recommended for more reliable data extraction than email parsing."
echo -n "Do you want to set up Browserbase? (y/n): "
read setup_browserbase

if [ "$setup_browserbase" = "y" ]; then
    echo -e "\n${YELLOW}Get your API key from: https://www.browserbase.com/settings/api-keys${NC}"
    create_parameter "/amazon-reconciler/browserbase-api-key" "Browserbase API key" true

    echo -e "\n${YELLOW}Optional: SNS Topic for session expiry notifications${NC}"
    echo -n "Do you want to set up SNS notifications for session expiry? (y/n): "
    read setup_sns
    if [ "$setup_sns" = "y" ]; then
        create_parameter "/amazon-reconciler/notification-topic-arn" "SNS topic ARN for notifications" false
    fi

    echo -e "\n${YELLOW}Note: Browserbase session ID will be created when you run:${NC}"
    echo "python src/browserbase_setup.py --login"
    echo "Then upload to Parameter Store with:"
    echo "python src/browserbase_setup.py --upload"
fi

echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}Parameter Store Setup Complete!${NC}"
echo -e "${GREEN}================================================${NC}"

echo -e "\n${YELLOW}Parameters created:${NC}"
aws ssm describe-parameters \
    --filters "Key=Name,Values=/amazon-reconciler/" \
    --region $REGION \
    --query "Parameters[*].Name" \
    --output table

echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Deploy the Lambda function using ./deploy-lambda-container.sh"
echo "2. Test with: aws lambda invoke --function-name amazon-ynab-reconciler --payload '{\"dry_run\": true}' response.json"