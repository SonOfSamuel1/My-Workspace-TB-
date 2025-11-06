# Autonomous Email Assistant

An intelligent, fully autonomous email management system built with Claude Code Max and GitHub Actions. Monitors Gmail inbox, classifies emails by priority tier, handles routine tasks automatically, and escalates urgent items via SMS.

## Overview

This system implements an Executive-Assistant Partnership Framework to autonomously manage email communications. It runs hourly during business hours (7 AM - 5 PM EST), processes incoming emails, applies intelligent tier-based classification, and takes appropriate actions without manual intervention.

## Features

### Core Capabilities
- **Autonomous Monitoring**: Runs every hour during business hours via GitHub Actions
- **Intelligent Classification**: 4-tier priority system (Escalate/Handle/Draft/Flag)
- **Gmail Integration**: Full access via Gmail MCP (Model Context Protocol)
- **Automatic Labeling**: Applies 9 custom Gmail labels for organization
- **SMS Escalation**: Sends SMS alerts for Tier 1 urgent emails (optional Twilio integration)
- **Daily Reports**: Morning brief (7 AM) and End-of-Day report (5 PM)
- **Zero Cost**: Uses existing Claude Code Max subscription ($100/month)

### Email Classification System

**Tier 1 - Escalate Immediately** (SMS + Priority)
- Revenue-impacting customer/prospect emails
- Strategic partnerships, major donors
- Speaking/media opportunities
- Financial approvals, HR issues, legal matters
- Off-limits contacts (family, key stakeholders)

**Tier 2 - Handle Independently** (Fully Autonomous)
- Meeting scheduling
- Newsletter subscriptions
- Vendor communications (routine)
- Follow-up reminders
- Information requests
- Travel confirmations, expense receipts

**Tier 3 - Draft for Approval** (Requires Review)
- Meeting decline requests
- Strategic communications
- First-time important contacts
- Requires user's expertise/voice

**Tier 4 - Flag Only, Never Send**
- HR/Employee performance matters
- Financial negotiations
- Legal communications
- Board communications
- Personal matters (health, family)

## Architecture

### Deployment Options

**Option 1: GitHub Actions** (Free, easier setup)
**Option 2: AWS Lambda** (More reliable, $2-5/month)

```
┌─────────────────────────────────────────────────┐
│   GitHub Actions OR Amazon EventBridge          │
│   Scheduled: Hourly 7 AM - 5 PM EST            │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│              Claude Code CLI                     │
│  Headless Mode + OAuth Authentication           │
│  Model: Claude Sonnet 4.5                       │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│          Gmail MCP Server                        │
│  @gongrzhe/server-gmail-autoauth-mcp            │
│  OAuth-based Gmail API access                   │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│         Gmail Account (terrance@...)            │
│  Read, Label, Draft, Send emails                │
└─────────────────────────────────────────────────┘
                  │
                  ▼ (Optional)
┌─────────────────────────────────────────────────┐
│              Twilio SMS                          │
│  Escalation alerts for Tier 1 urgent           │
└─────────────────────────────────────────────────┘
```

## Setup Instructions

Choose your deployment method:

- **[GitHub Actions Setup](#github-actions-setup)** - Free, easier setup, good for testing
- **[AWS Lambda Setup](#aws-lambda-setup)** - More reliable, production-grade, $2-5/month

---

## GitHub Actions Setup

### Prerequisites

1. **Claude Code Max Subscription** ($100/month)
2. **GitHub Account** (Free tier works - 2,000 min/month)
3. **Gmail Account** with API access enabled
4. **Google Cloud Project** with Gmail API enabled
5. **Twilio Account** (optional, for SMS escalations)
6. **Node.js** (v20 or later)

### Quick Setup (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/YOUR-USERNAME/App--Internal-Business--Autonomous-Email-Assistant.git
cd App--Internal-Business--Autonomous-Email-Assistant

# 2. Install dependencies
npm install

# 3. Run automated setup
npm run setup
```

The setup script will:
- Guide you through Gmail MCP authentication
- Collect your Claude Code OAuth token
- Set up Twilio credentials (optional)
- Automatically add all GitHub secrets via Playwright

**For detailed manual setup**, see [docs/SETUP.md](docs/SETUP.md)

---

### Manual Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/YOUR-USERNAME/App--Internal-Business--Autonomous-Email-Assistant.git
cd App--Internal-Business--Autonomous-Email-Assistant
npm install
```

### Step 2: Gmail API Setup

1. Create a Google Cloud Project:
   - Go to https://console.cloud.google.com
   - Create new project: "Email Assistant"
   - Enable Gmail API

2. Create OAuth Credentials:
   - Navigate to APIs & Services → Credentials
   - Create OAuth 2.0 Client ID (Desktop app)
   - Download JSON as `gcp-oauth.keys.json`

3. Authorize Gmail Access:
   ```bash
   npm install -g @gongrzhe/server-gmail-autoauth-mcp
   # Follow OAuth flow to generate credentials.json
   ```

### Step 3: Claude Code OAuth Setup

```bash
claude setup-token
# Follow browser prompt to authenticate
# Copy the token: sk-ant-oat01-...
```

### Step 4: Configure GitHub Secrets

Navigate to your GitHub repo → Settings → Secrets and variables → Actions

Add these secrets (encode credentials as base64):

```bash
# Claude Code OAuth Token
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-LYgbMJ...

# Gmail OAuth Credentials (base64 encoded)
cat ~/.gmail-mcp/gcp-oauth.keys.json | base64
# Copy output and add as GMAIL_OAUTH_CREDENTIALS

# Gmail User Credentials (base64 encoded)
cat ~/.gmail-mcp/credentials.json | base64
# Copy output and add as GMAIL_CREDENTIALS

# Optional: Twilio SMS (if using escalations)
TWILIO_ACCOUNT_SID=ACxxxxx...
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_FROM_NUMBER=+1234567890
```

### Step 5: Create Gmail Labels

```bash
cd scripts
node create-gmail-labels.js
```

This creates 9 labels:
- Action Required
- To Read
- Waiting For
- Completed
- VIP
- Meetings
- Travel
- Expenses
- Newsletters

### Step 6: Customize Configuration

Edit `claude-agents/executive-email-assistant-config-terrance.md`:

```yaml
email: your-email@domain.com
time_zone: EST
delegation_level: Level 2 (Manage)
escalation_phone: +1234567890

off_limits_contacts:
  - Family Member Name
  - Important Stakeholder

communication_style:
  greeting: Hi/Thanks
  closing: "Kind regards,"
  emojis: false
```

### Step 7: Test Workflow

Trigger manually from GitHub:
- Actions → Hourly Email Management → Run workflow

## Usage

### Automated Schedule

The system runs automatically:
- **Hourly**: 7 AM - 5 PM EST (Monday-Friday)
- **Morning Brief**: 7 AM - Overnight email summary
- **Midday Check**: 1 PM - Only if Tier 1 urgent items exist
- **End of Day Report**: 5 PM - Daily summary

### Manual Trigger

From GitHub Actions:
```
Actions → Hourly Email Management → Run workflow
```

From command line:
```bash
gh workflow run "Hourly Email Management"
```

### Monitoring

View logs in GitHub Actions:
- Check execution status
- Review email classifications
- Monitor escalations
- Verify actions taken

## Configuration

### Workflow Settings

Edit `.github/workflows/hourly-email-management.yml`:

```yaml
# Change schedule (cron format)
schedule:
  - cron: "0 12-22 * * 1-5"  # 7 AM-5 PM EST, Mon-Fri

# Modify timeout (default: 10 minutes)
timeout-minutes: 10
```

### Agent Behavior

Edit `claude-agents/executive-email-assistant.md` to customize:
- Delegation levels
- Tier classification rules
- Response templates
- Label system
- Communication protocols

### User-Specific Config

Edit `claude-agents/executive-email-assistant-config-terrance.md`:
- Email address
- Time zone
- Off-limits contacts
- Communication style
- Meeting preferences

## How It Works

### Processing Flow

1. **Trigger**: GitHub Actions runs on schedule
2. **Authentication**: Loads Claude Code OAuth token
3. **MCP Setup**: Initializes Gmail MCP server with credentials
4. **Email Fetch**: Retrieves new emails since last check
5. **Classification**: Claude analyzes each email and assigns tier
6. **Actions**: Based on tier:
   - **Tier 1**: Apply labels, send SMS, add to escalation queue
   - **Tier 2**: Apply labels, draft and send response, archive
   - **Tier 3**: Apply labels, draft response (don't send), queue for review
   - **Tier 4**: Apply labels, flag for manual handling
7. **Reporting**: Generate mode-specific output (brief/report/silent)
8. **Completion**: Log results and wait for next scheduled run

### Security

- **OAuth Authentication**: All API access uses OAuth tokens
- **GitHub Secrets**: Sensitive credentials stored encrypted
- **Base64 Encoding**: Prevents JSON escaping issues
- **Headless Mode**: `--dangerously-skip-permissions` for automation
- **No Storage**: No email content stored, only processing logs

### Cost

- **Claude Code Max**: $100/month (existing subscription)
- **GitHub Actions**: Free (2,000 min/month, uses ~30 min/month)
- **Gmail API**: Free (1 billion quota units/day)
- **Twilio SMS**: ~$0.0075/message (optional)

**Total Additional Cost**: $0-5/month

## Troubleshooting

### Gmail MCP Not Loading

Check MCP configuration:
```bash
cat ~/.config/claude/claude_code_config.json
```

Verify Gmail credentials:
```bash
cat ~/.gmail-mcp/credentials.json | jq '.'
```

Test MCP server directly:
```bash
npx @gongrzhe/server-gmail-autoauth-mcp
```

### Workflow Failures

View GitHub Actions logs:
```
Actions → [Failed Run] → View logs
```

Common issues:
- Invalid OAuth token (re-run `claude setup-token`)
- Expired Gmail credentials (re-authorize)
- Malformed base64 secrets (re-encode and update)

### Classification Issues

Monitor for misclassifications:
- Check daily reports
- Review Tier assignments
- Adjust rules in agent config
- Add to off-limits contacts if needed

## Development

### Local Testing

Test Claude Code locally:
```bash
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
claude --print --mcp-config ~/.config/claude/claude_code_config.json
# Paste test prompt
```

### Debugging

Enable MCP debug mode:
```bash
claude --debug --mcp-config ~/.config/claude/claude_code_config.json
```

### Modifying Workflow

1. Edit `.github/workflows/hourly-email-management.yml`
2. Commit changes
3. Push to GitHub
4. Test with manual trigger

## AWS Lambda Setup

For a more reliable, production-grade deployment, use AWS Lambda instead of GitHub Actions.

### Prerequisites

1. **Claude Code Max Subscription** ($100/month)
2. **AWS Account** with appropriate permissions
3. **AWS CLI** installed and configured ([Install guide](https://aws.amazon.com/cli/))
4. **Docker** installed and running ([Install guide](https://docs.docker.com/get-docker/))
5. **Gmail Account** with API access enabled
6. **Google Cloud Project** with Gmail API enabled
7. **Twilio Account** (optional, for SMS escalations)

### Quick Setup

```bash
cd lambda
./setup-lambda.sh
```

The script will:
1. Create ECR repository for Docker image
2. Build and push Docker container with Claude Code CLI
3. Create IAM role for Lambda
4. Deploy Lambda function
5. Set up EventBridge schedule (hourly 7 AM - 5 PM EST)

### Manual Deployment

If you prefer AWS SAM:

```bash
cd lambda
sam build --use-container
sam deploy --guided
```

For detailed Lambda setup instructions, see [lambda/README.md](lambda/README.md)

### Cost Estimate

- **Lambda**: ~$1.20/month (compute time)
- **CloudWatch Logs**: ~$0.50/month
- **Total**: ~$2-5/month (excluding Claude Code Max subscription)

### Monitoring

```bash
# View logs in real-time
aws logs tail /aws/lambda/email-assistant-processor --follow

# Test function manually
aws lambda invoke \
  --function-name email-assistant-processor \
  response.json
```

---

## Project Structure

```
.
├── .github/
│   └── workflows/
│       └── hourly-email-management.yml  # GitHub Actions workflow
├── lambda/
│   ├── index.js                         # Lambda handler
│   ├── Dockerfile                       # Container image definition
│   ├── template.yaml                    # AWS SAM template
│   ├── setup-lambda.sh                  # Automated setup script
│   └── README.md                        # Lambda deployment guide
├── claude-agents/
│   ├── executive-email-assistant.md     # Agent specification
│   └── executive-email-assistant-config-terrance.md # User config
├── docs/
│   └── SETUP.md                          # GitHub Actions setup guide
├── scripts/
│   ├── create-gmail-labels.js            # Gmail label creation
│   ├── setup-credentials.sh              # GitHub Actions setup
│   └── setup-github-secrets.js           # Automated secrets setup
└── README.md                              # This file
```

## Contributing

This is a personal automation project, but contributions welcome:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -m 'Add improvement'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open Pull Request

## License

MIT License - See LICENSE file for details

## Acknowledgments

- **Claude Code** by Anthropic - AI-powered development environment
- **Gmail MCP** by @gongrzhe - Gmail API integration via MCP
- **Executive-Assistant Partnership Framework** - Structured delegation model

## Support

For issues or questions:
- GitHub Issues: [Create issue](https://github.com/YOUR-USERNAME/App--Internal-Business--Autonomous-Email-Assistant/issues)
- Documentation: See `docs/SETUP.md`

---

Built with Claude Code Max | Powered by Claude Sonnet 4.5 | Runs on GitHub Actions or AWS Lambda
