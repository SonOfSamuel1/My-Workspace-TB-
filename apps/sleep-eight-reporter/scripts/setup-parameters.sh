#!/bin/bash
# Setup AWS Parameter Store for Sleep Eight Reporter
# ==================================================
#
# This script creates the required Parameter Store entries for Lambda.
# Run this before deploying the Lambda function.
#
# Usage: ./scripts/setup-parameters.sh

set -e

REGION="${AWS_REGION:-us-east-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Sleep Eight Reporter - Parameter Setup${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to create or update parameter
create_parameter() {
    local name=$1
    local description=$2
    local value=$3
    local type=${4:-SecureString}

    if [ -z "$value" ]; then
        echo -e "${YELLOW}Skipping $name (no value provided)${NC}"
        return
    fi

    echo -e "${YELLOW}Setting $name...${NC}"
    aws ssm put-parameter \
        --name "$name" \
        --description "$description" \
        --value "$value" \
        --type "$type" \
        --overwrite \
        --region "$REGION" > /dev/null

    echo -e "${GREEN}  Created/updated $name${NC}"
}

# Prompt for values if not provided via environment
if [ -z "$EIGHT_SLEEP_EMAIL" ]; then
    read -p "Enter Eight Sleep email: " EIGHT_SLEEP_EMAIL
fi

if [ -z "$EIGHT_SLEEP_PASSWORD" ]; then
    read -sp "Enter Eight Sleep password: " EIGHT_SLEEP_PASSWORD
    echo
fi

if [ -z "$SLEEP_REPORT_EMAIL" ]; then
    read -p "Enter email to receive reports: " SLEEP_REPORT_EMAIL
fi

if [ -z "$SES_SENDER_EMAIL" ]; then
    read -p "Enter SES sender email [brandonhome.appdev@gmail.com]: " SES_SENDER_EMAIL
    SES_SENDER_EMAIL=${SES_SENDER_EMAIL:-brandonhome.appdev@gmail.com}
fi

echo -e "\n${YELLOW}Creating Parameter Store entries...${NC}\n"

# Create parameters
create_parameter \
    "/sleep-eight-reporter/eight-sleep-email" \
    "Eight Sleep account email" \
    "$EIGHT_SLEEP_EMAIL" \
    "SecureString"

create_parameter \
    "/sleep-eight-reporter/eight-sleep-password" \
    "Eight Sleep account password" \
    "$EIGHT_SLEEP_PASSWORD" \
    "SecureString"

create_parameter \
    "/sleep-eight-reporter/email-recipient" \
    "Email address to receive sleep reports" \
    "$SLEEP_REPORT_EMAIL" \
    "String"

create_parameter \
    "/sleep-eight-reporter/ses-sender-email" \
    "AWS SES verified sender email" \
    "$SES_SENDER_EMAIL" \
    "String"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Parameter Store setup complete!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\nParameters created:"
echo "  /sleep-eight-reporter/eight-sleep-email"
echo "  /sleep-eight-reporter/eight-sleep-password"
echo "  /sleep-eight-reporter/email-recipient"
echo "  /sleep-eight-reporter/ses-sender-email"

echo -e "\n${YELLOW}Make sure your Lambda IAM role has the following policy:${NC}"
echo '{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter"
            ],
            "Resource": "arn:aws:ssm:*:*:parameter/sleep-eight-reporter/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ses:SendEmail",
                "ses:SendRawEmail"
            ],
            "Resource": "*"
        }
    ]
}'
