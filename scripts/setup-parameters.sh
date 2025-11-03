#!/bin/bash
# Setup AWS Systems Manager Parameter Store with credentials

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWS_REGION=${AWS_REGION:-us-east-1}

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}AWS Parameter Store Setup${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

echo -e "${YELLOW}This script will upload your credentials to AWS Parameter Store.${NC}"
echo ""
echo "Required files (in credentials/ directory):"
echo "  - calendar_credentials.json"
echo "  - calendar_token.json"
echo "  - gmail_credentials.json"
echo "  - gmail_token.json"
echo ""

read -p "Do you want to continue? (y/n): " continue_setup
if [ "$continue_setup" != "y" ]; then
    echo "Exiting..."
    exit 0
fi

echo ""

# Check if credentials directory exists
if [ ! -d "credentials" ]; then
    echo -e "${RED}✗ credentials/ directory not found${NC}"
    exit 1
fi

# Upload calendar credentials
if [ -f "credentials/calendar_credentials.json" ]; then
    echo "Uploading calendar credentials..."
    aws ssm put-parameter \
        --name "/love-brittany/calendar-credentials" \
        --value file://credentials/calendar_credentials.json \
        --type "SecureString" \
        --region $AWS_REGION \
        --overwrite \
        > /dev/null 2>&1 && echo -e "${GREEN}✓ Calendar credentials uploaded${NC}"
else
    echo -e "${YELLOW}⚠ credentials/calendar_credentials.json not found, skipping...${NC}"
fi

# Upload calendar token
if [ -f "credentials/calendar_token.json" ]; then
    echo "Uploading calendar token..."
    aws ssm put-parameter \
        --name "/love-brittany/calendar-token" \
        --value file://credentials/calendar_token.json \
        --type "SecureString" \
        --region $AWS_REGION \
        --overwrite \
        > /dev/null 2>&1 && echo -e "${GREEN}✓ Calendar token uploaded${NC}"
else
    echo -e "${YELLOW}⚠ credentials/calendar_token.json not found, skipping...${NC}"
fi

# Upload Gmail credentials
if [ -f "credentials/gmail_credentials.json" ]; then
    echo "Uploading Gmail credentials..."
    aws ssm put-parameter \
        --name "/love-brittany/gmail-credentials" \
        --value file://credentials/gmail_credentials.json \
        --type "SecureString" \
        --region $AWS_REGION \
        --overwrite \
        > /dev/null 2>&1 && echo -e "${GREEN}✓ Gmail credentials uploaded${NC}"
else
    echo -e "${YELLOW}⚠ credentials/gmail_credentials.json not found, skipping...${NC}"
fi

# Upload Gmail token
if [ -f "credentials/gmail_token.json" ]; then
    echo "Uploading Gmail token..."
    aws ssm put-parameter \
        --name "/love-brittany/gmail-token" \
        --value file://credentials/gmail_token.json \
        --type "SecureString" \
        --region $AWS_REGION \
        --overwrite \
        > /dev/null 2>&1 && echo -e "${GREEN}✓ Gmail token uploaded${NC}"
else
    echo -e "${YELLOW}⚠ credentials/gmail_token.json not found, skipping...${NC}"
fi

# Upload API keys from .env
echo ""
echo "Uploading API keys..."
if [ -f ".env" ]; then
    source .env

    if [ -n "$TOGGL_API_TOKEN" ]; then
        aws ssm put-parameter \
            --name "/love-brittany/toggl-api-token" \
            --value "$TOGGL_API_TOKEN" \
            --type "SecureString" \
            --region $AWS_REGION \
            --overwrite \
            > /dev/null 2>&1 && echo -e "${GREEN}✓ Toggl API token uploaded${NC}"
    else
        echo -e "${YELLOW}⚠ TOGGL_API_TOKEN not found in .env${NC}"
    fi

    if [ -n "$TOGGL_WORKSPACE_ID" ]; then
        aws ssm put-parameter \
            --name "/love-brittany/toggl-workspace-id" \
            --value "$TOGGL_WORKSPACE_ID" \
            --type "String" \
            --region $AWS_REGION \
            --overwrite \
            > /dev/null 2>&1 && echo -e "${GREEN}✓ Toggl workspace ID uploaded${NC}"
    else
        echo -e "${YELLOW}⚠ TOGGL_WORKSPACE_ID not found in .env${NC}"
    fi
else
    echo -e "${YELLOW}⚠ .env file not found, skipping API keys...${NC}"
fi

echo ""
echo -e "${GREEN}✓ Parameter Store setup complete!${NC}"
echo ""
echo "View parameters:"
echo "  aws ssm get-parameters-by-path --path /love-brittany --region $AWS_REGION"
echo ""
echo -e "${YELLOW}💰 Cost: FREE (Parameter Store standard tier)${NC}"
echo ""
