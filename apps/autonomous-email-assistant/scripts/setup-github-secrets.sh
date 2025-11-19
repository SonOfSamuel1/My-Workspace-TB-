#!/bin/bash

# GitHub Secrets Setup Script for Email Assistant
# This script helps you configure all required GitHub secrets for deployment

set -e

echo "================================================"
echo "Email Assistant - GitHub Secrets Setup"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}✗ GitHub CLI (gh) is not installed${NC}"
    echo "Install it with: brew install gh"
    echo "Or visit: https://cli.github.com/"
    exit 1
fi

echo -e "${GREEN}✓ GitHub CLI found${NC}"
echo ""

# Check if user is authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}! You need to authenticate with GitHub${NC}"
    echo "Run: gh auth login"
    exit 1
fi

echo -e "${GREEN}✓ GitHub authentication verified${NC}"
echo ""

# Get repository info
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo "Repository: $REPO"
echo ""

echo "================================================"
echo "Setting up secrets..."
echo "================================================"
echo ""

# 1. CLAUDE_CODE_OAUTH_TOKEN
echo -e "${YELLOW}[1/7] CLAUDE_CODE_OAUTH_TOKEN${NC}"
echo "This is your Claude Code CLI authentication token."
echo ""
echo "To get your token, run:"
echo "  claude setup-token"
echo ""
read -sp "Enter your Claude Code OAuth token (sk-ant-oat01-...): " CLAUDE_TOKEN
echo ""

if [[ ! $CLAUDE_TOKEN =~ ^sk-ant-oat01- ]]; then
    echo -e "${RED}✗ Invalid token format. Token should start with 'sk-ant-oat01-'${NC}"
    exit 1
fi

gh secret set CLAUDE_CODE_OAUTH_TOKEN -b"$CLAUDE_TOKEN" -R "$REPO"
echo -e "${GREEN}✓ CLAUDE_CODE_OAUTH_TOKEN set${NC}"
echo ""

# 2. GMAIL_OAUTH_CREDENTIALS
echo -e "${YELLOW}[2/7] GMAIL_OAUTH_CREDENTIALS${NC}"
echo "Encoding Gmail OAuth credentials..."

if [ ! -f ~/.gmail-mcp/gcp-oauth.keys.json ]; then
    echo -e "${RED}✗ Gmail OAuth credentials not found at ~/.gmail-mcp/gcp-oauth.keys.json${NC}"
    echo "Please set up Gmail MCP first."
    exit 1
fi

GMAIL_OAUTH_B64=$(cat ~/.gmail-mcp/gcp-oauth.keys.json | base64)
gh secret set GMAIL_OAUTH_CREDENTIALS -b"$GMAIL_OAUTH_B64" -R "$REPO"
echo -e "${GREEN}✓ GMAIL_OAUTH_CREDENTIALS set${NC}"
echo ""

# 3. GMAIL_CREDENTIALS
echo -e "${YELLOW}[3/7] GMAIL_CREDENTIALS${NC}"
echo "Encoding Gmail user credentials..."

if [ ! -f ~/.gmail-mcp/credentials.json ]; then
    echo -e "${RED}✗ Gmail credentials not found at ~/.gmail-mcp/credentials.json${NC}"
    echo "Please authenticate with Gmail MCP first."
    exit 1
fi

GMAIL_CRED_B64=$(cat ~/.gmail-mcp/credentials.json | base64)
gh secret set GMAIL_CREDENTIALS -b"$GMAIL_CRED_B64" -R "$REPO"
echo -e "${GREEN}✓ GMAIL_CREDENTIALS set${NC}"
echo ""

# 4. TWILIO_ACCOUNT_SID (Optional)
echo -e "${YELLOW}[4/7] TWILIO_ACCOUNT_SID (Optional)${NC}"
echo "For SMS escalations. Leave blank to skip."
echo ""
read -p "Enter Twilio Account SID (or press Enter to skip): " TWILIO_SID

if [ -n "$TWILIO_SID" ]; then
    gh secret set TWILIO_ACCOUNT_SID -b"$TWILIO_SID" -R "$REPO"
    echo -e "${GREEN}✓ TWILIO_ACCOUNT_SID set${NC}"
else
    echo -e "${YELLOW}⊘ Skipped (SMS escalations disabled)${NC}"
fi
echo ""

# 5. TWILIO_AUTH_TOKEN (Optional)
echo -e "${YELLOW}[5/7] TWILIO_AUTH_TOKEN (Optional)${NC}"
if [ -n "$TWILIO_SID" ]; then
    read -sp "Enter Twilio Auth Token: " TWILIO_TOKEN
    echo ""
    gh secret set TWILIO_AUTH_TOKEN -b"$TWILIO_TOKEN" -R "$REPO"
    echo -e "${GREEN}✓ TWILIO_AUTH_TOKEN set${NC}"
else
    echo -e "${YELLOW}⊘ Skipped (no Twilio SID provided)${NC}"
fi
echo ""

# 6. TWILIO_FROM_NUMBER (Optional)
echo -e "${YELLOW}[6/7] TWILIO_FROM_NUMBER (Optional)${NC}"
if [ -n "$TWILIO_SID" ]; then
    read -p "Enter Twilio phone number (+1234567890): " TWILIO_FROM
    gh secret set TWILIO_FROM_NUMBER -b"$TWILIO_FROM" -R "$REPO"
    echo -e "${GREEN}✓ TWILIO_FROM_NUMBER set${NC}"
else
    echo -e "${YELLOW}⊘ Skipped (no Twilio SID provided)${NC}"
fi
echo ""

# 7. OPENROUTER_API_KEY (Optional - for Email Agent)
echo -e "${YELLOW}[7/7] OPENROUTER_API_KEY (Optional)${NC}"
echo "For Email Agent autonomous actions. Leave blank to skip."
echo ""
read -sp "Enter OpenRouter API key (or press Enter to skip): " OPENROUTER_KEY

if [ -n "$OPENROUTER_KEY" ]; then
    gh secret set OPENROUTER_API_KEY -b"$OPENROUTER_KEY" -R "$REPO"
    echo ""
    echo -e "${GREEN}✓ OPENROUTER_API_KEY set${NC}"
else
    echo ""
    echo -e "${YELLOW}⊘ Skipped (Email Agent disabled)${NC}"
fi
echo ""

# Summary
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "Secrets configured:"
echo -e "${GREEN}✓${NC} CLAUDE_CODE_OAUTH_TOKEN"
echo -e "${GREEN}✓${NC} GMAIL_OAUTH_CREDENTIALS"
echo -e "${GREEN}✓${NC} GMAIL_CREDENTIALS"

if [ -n "$TWILIO_SID" ]; then
    echo -e "${GREEN}✓${NC} TWILIO_ACCOUNT_SID"
    echo -e "${GREEN}✓${NC} TWILIO_AUTH_TOKEN"
    echo -e "${GREEN}✓${NC} TWILIO_FROM_NUMBER"
fi

if [ -n "$OPENROUTER_KEY" ]; then
    echo -e "${GREEN}✓${NC} OPENROUTER_API_KEY"
fi

echo ""
echo "Next steps:"
echo "1. Test workflow manually:"
echo "   gh workflow run 'Hourly Email Management' --field test_mode=true"
echo ""
echo "2. Monitor workflow:"
echo "   gh run list --workflow='Hourly Email Management'"
echo ""
echo "3. View logs:"
echo "   gh run view --log"
echo ""
echo "Your email assistant will now run hourly during business hours!"
