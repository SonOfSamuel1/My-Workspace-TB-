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
echo "  - credentials.json (Google API credentials)"
echo "  - token.pickle (Google OAuth token)"
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

# Upload Google credentials
if [ -f "credentials/credentials.json" ]; then
    echo "Uploading Google API credentials..."
    aws ssm put-parameter \
        --name "/love-brittany/credentials" \
        --value file://credentials/credentials.json \
        --type "SecureString" \
        --region $AWS_REGION \
        --overwrite \
        > /dev/null 2>&1 && echo -e "${GREEN}✓ Google credentials uploaded${NC}"
else
    echo -e "${YELLOW}⚠ credentials/credentials.json not found, skipping...${NC}"
fi

# Upload Google token (convert pickle to base64 for storage)
if [ -f "credentials/token.pickle" ]; then
    echo "Uploading Google OAuth token..."
    # Base64 encode the pickle file for safe storage
    TOKEN_BASE64=$(base64 -i credentials/token.pickle)
    aws ssm put-parameter \
        --name "/love-brittany/token" \
        --value "$TOKEN_BASE64" \
        --type "SecureString" \
        --region $AWS_REGION \
        --overwrite \
        > /dev/null 2>&1 && echo -e "${GREEN}✓ Google token uploaded${NC}"
else
    echo -e "${YELLOW}⚠ credentials/token.pickle not found, skipping...${NC}"
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
