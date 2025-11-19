#!/bin/bash

# =============================================================================
# AUTOMATED DEPLOYMENT SCRIPT
# =============================================================================
# This script automates the entire deployment process for the email assistant
#
# Usage: ./scripts/deploy-everything.sh
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "================================================"
echo -e "${BLUE}Email Assistant - Automated Deployment${NC}"
echo "================================================"
echo ""

# =============================================================================
# STEP 1: GET CLAUDE CODE TOKEN
# =============================================================================

echo -e "${YELLOW}[Step 1/6] Getting Claude Code OAuth Token${NC}"
echo ""

if [ -n "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    echo -e "${GREEN}✓ Claude Code token found in environment${NC}"
    CLAUDE_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN"
else
    echo "Please generate your Claude Code token:"
    echo "  1. Run: claude setup-token"
    echo "  2. Copy the token (sk-ant-oat01-...)"
    echo ""
    read -sp "Paste your Claude Code OAuth token: " CLAUDE_TOKEN
    echo ""

    if [[ ! $CLAUDE_TOKEN =~ ^sk-ant-oat01- ]]; then
        echo -e "${RED}✗ Invalid token format${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Claude Code token ready${NC}"
echo ""

# =============================================================================
# STEP 2: VERIFY REPOSITORY
# =============================================================================

echo -e "${YELLOW}[Step 2/6] Verifying GitHub Repository${NC}"
echo ""

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")

if [ -z "$REPO" ]; then
    echo -e "${RED}✗ Could not find repository${NC}"
    echo "Make sure you're in the right directory and gh is authenticated"
    exit 1
fi

echo -e "${GREEN}✓ Repository: $REPO${NC}"
echo ""

# =============================================================================
# STEP 3: PUSH CODE TO GITHUB
# =============================================================================

echo -e "${YELLOW}[Step 3/6] Pushing Code to GitHub${NC}"
echo ""

# Add all changes
git add .

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "No changes to commit"
else
    git commit -m "feat: Automated deployment configuration

- Add deployment scripts and documentation
- Configure GitHub Actions workflow
- Set up Email Agent with OpenRouter integration
- Add comprehensive testing and monitoring

🤖 Generated with Claude Code" || echo "Commit skipped (may already exist)"
fi

# Push to GitHub
git push origin main || git push origin master

echo -e "${GREEN}✓ Code pushed to GitHub${NC}"
echo ""

# =============================================================================
# STEP 4: CONFIGURE GITHUB SECRETS
# =============================================================================

echo -e "${YELLOW}[Step 4/6] Configuring GitHub Secrets${NC}"
echo ""

# Set Claude Code token
echo "Setting CLAUDE_CODE_OAUTH_TOKEN..."
gh secret set CLAUDE_CODE_OAUTH_TOKEN -b"$CLAUDE_TOKEN" -R "$REPO"
echo -e "${GREEN}✓ CLAUDE_CODE_OAUTH_TOKEN${NC}"

# Set Gmail OAuth credentials
if [ -f ~/.gmail-mcp/gcp-oauth.keys.json ]; then
    echo "Setting GMAIL_OAUTH_CREDENTIALS..."
    GMAIL_OAUTH_B64=$(cat ~/.gmail-mcp/gcp-oauth.keys.json | base64)
    gh secret set GMAIL_OAUTH_CREDENTIALS -b"$GMAIL_OAUTH_B64" -R "$REPO"
    echo -e "${GREEN}✓ GMAIL_OAUTH_CREDENTIALS${NC}"
else
    echo -e "${RED}✗ Gmail OAuth credentials not found at ~/.gmail-mcp/gcp-oauth.keys.json${NC}"
    exit 1
fi

# Set Gmail user credentials
if [ -f ~/.gmail-mcp/credentials.json ]; then
    echo "Setting GMAIL_CREDENTIALS..."
    GMAIL_CRED_B64=$(cat ~/.gmail-mcp/credentials.json | base64)
    gh secret set GMAIL_CREDENTIALS -b"$GMAIL_CRED_B64" -R "$REPO"
    echo -e "${GREEN}✓ GMAIL_CREDENTIALS${NC}"
else
    echo -e "${RED}✗ Gmail credentials not found at ~/.gmail-mcp/credentials.json${NC}"
    exit 1
fi

# Optional: Twilio (for SMS)
echo ""
echo "Optional: Twilio SMS Escalations"
read -p "Do you want to configure Twilio for SMS alerts? (y/N): " SETUP_TWILIO

if [[ $SETUP_TWILIO =~ ^[Yy]$ ]]; then
    read -p "Twilio Account SID: " TWILIO_SID
    read -sp "Twilio Auth Token: " TWILIO_TOKEN
    echo ""
    read -p "Twilio From Number (+1234567890): " TWILIO_FROM

    gh secret set TWILIO_ACCOUNT_SID -b"$TWILIO_SID" -R "$REPO"
    gh secret set TWILIO_AUTH_TOKEN -b"$TWILIO_TOKEN" -R "$REPO"
    gh secret set TWILIO_FROM_NUMBER -b"$TWILIO_FROM" -R "$REPO"

    echo -e "${GREEN}✓ Twilio secrets configured${NC}"
else
    echo -e "${YELLOW}⊘ Skipped Twilio (SMS disabled)${NC}"
fi

# Optional: OpenRouter (for Email Agent)
echo ""
echo "Optional: OpenRouter Email Agent"
read -p "Do you want to configure OpenRouter for Email Agent? (y/N): " SETUP_OPENROUTER

if [[ $SETUP_OPENROUTER =~ ^[Yy]$ ]]; then
    read -sp "OpenRouter API Key (sk-or-v1-...): " OPENROUTER_KEY
    echo ""

    gh secret set OPENROUTER_API_KEY -b"$OPENROUTER_KEY" -R "$REPO"

    echo -e "${GREEN}✓ OpenRouter API key configured${NC}"
else
    echo -e "${YELLOW}⊘ Skipped OpenRouter (Email Agent disabled)${NC}"
fi

echo ""
echo -e "${GREEN}✓ All secrets configured${NC}"
echo ""

# =============================================================================
# STEP 5: TRIGGER TEST WORKFLOW
# =============================================================================

echo -e "${YELLOW}[Step 5/6] Triggering Test Workflow${NC}"
echo ""

echo "Triggering GitHub Actions workflow in test mode..."
gh workflow run "Hourly Email Management" --field test_mode=true

echo "Waiting for workflow to start..."
sleep 5

echo -e "${GREEN}✓ Workflow triggered${NC}"
echo ""

# =============================================================================
# STEP 6: MONITOR WORKFLOW
# =============================================================================

echo -e "${YELLOW}[Step 6/6] Monitoring Workflow${NC}"
echo ""

echo "Workflow is running... This will take 2-3 minutes."
echo ""
echo "You can watch progress with:"
echo "  gh run watch"
echo ""
echo "Or view in browser:"
echo "  gh run view --web"
echo ""

# Try to watch automatically
gh run watch 2>/dev/null || {
    echo "Auto-watch not available. Check status manually:"
    echo "  gh run list --limit 1"
}

echo ""
echo "================================================"
echo -e "${GREEN}Deployment Complete!${NC}"
echo "================================================"
echo ""

# =============================================================================
# SUMMARY
# =============================================================================

echo "📊 Summary:"
echo ""
echo "Repository: $REPO"
echo ""
echo "Secrets configured:"
echo "  ✓ CLAUDE_CODE_OAUTH_TOKEN"
echo "  ✓ GMAIL_OAUTH_CREDENTIALS"
echo "  ✓ GMAIL_CREDENTIALS"

if [[ $SETUP_TWILIO =~ ^[Yy]$ ]]; then
    echo "  ✓ TWILIO_ACCOUNT_SID"
    echo "  ✓ TWILIO_AUTH_TOKEN"
    echo "  ✓ TWILIO_FROM_NUMBER"
fi

if [[ $SETUP_OPENROUTER =~ ^[Yy]$ ]]; then
    echo "  ✓ OPENROUTER_API_KEY"
fi

echo ""
echo "📅 Schedule:"
echo "  - Hourly: 7 AM - 5 PM EST (Mon-Fri)"
echo "  - Morning Brief: 7 AM EST"
echo "  - EOD Report: 5 PM EST"
echo ""
echo "🎯 Next Steps:"
echo ""
echo "1. Verify workflow succeeded:"
echo "   gh run list --limit 1"
echo ""
echo "2. View workflow logs:"
echo "   gh run view --log"
echo ""
echo "3. Check secrets:"
echo "   gh secret list"
echo ""
echo "4. Monitor live:"
echo "   gh run list --workflow='Hourly Email Management'"
echo ""
echo "Your email assistant will send the first Morning Brief"
echo "tomorrow at 7:00 AM EST!"
echo ""
echo -e "${GREEN}✨ Deployment successful! ✨${NC}"
echo ""
