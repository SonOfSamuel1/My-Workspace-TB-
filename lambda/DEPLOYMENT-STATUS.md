# AWS Lambda Deployment Status

## Current Status: Ready to Deploy ✅

All infrastructure code has been created. The deployment is ready to run, but requires credentials setup first.

## What Was Created

### Lambda Function Code
- ✅ `index.js` - Main Lambda handler
- ✅ `Dockerfile` - Container image with Claude Code CLI
- ✅ `package.json` - Node.js dependencies

### Infrastructure Templates
- ✅ `template.yaml` - AWS SAM CloudFormation template
- ✅ `.dockerignore` - Docker build optimization

### Deployment Scripts
- ✅ `deploy-full-setup.sh` - **RECOMMENDED**: Complete setup (credentials + deployment)
- ✅ `setup-lambda.sh` - Interactive deployment (prompts for all inputs)
- ✅ `deploy-auto.sh` - Automated deployment (uses environment variables)
- ✅ `deploy.sh` - SAM-based deployment

### Documentation
- ✅ `README.md` - Complete Lambda deployment guide
- ✅ `MIGRATION-GUIDE.md` - Migration from GitHub Actions
- ✅ `QUICKSTART.md` - 10-minute quick start
- ✅ `DEPLOYMENT-STATUS.md` - This file

## What's Needed Before Deployment

### 1. Gmail MCP Credentials

**Status**: ❌ Not set up locally

**Required files**:
- `~/.gmail-mcp/gcp-oauth.keys.json` (OAuth client credentials)
- `~/.gmail-mcp/credentials.json` (Access/refresh tokens)

**How to set up**:

```bash
# Install Gmail MCP server
npm install -g @gongrzhe/server-gmail-autoauth-mcp

# Follow these steps:
# 1. Create Google Cloud Project: https://console.cloud.google.com
# 2. Enable Gmail API
# 3. Create OAuth 2.0 credentials (Desktop app)
# 4. Download as gcp-oauth.keys.json
# 5. Run the MCP server to authenticate:
npx @gongrzhe/server-gmail-autoauth-mcp
# This creates ~/.gmail-mcp/ directory with both files
```

**Alternatively**: If you already have Gmail MCP configured elsewhere, copy the files:
```bash
mkdir -p ~/.gmail-mcp
cp /path/to/gcp-oauth.keys.json ~/.gmail-mcp/
cp /path/to/credentials.json ~/.gmail-mcp/
```

### 2. Claude Code OAuth Token

**Status**: ❌ Not in environment

**How to get**:

```bash
# Method 1: Generate new token
claude setup-token
# Follow browser prompt, copy the token (starts with sk-ant-oat01-)

# Method 2: Export existing token
export CLAUDE_CODE_OAUTH_TOKEN="sk-ant-oat01-..."
```

### 3. Twilio Credentials (Optional)

**Status**: ❌ Not set (optional for SMS alerts)

**How to get**:
- Sign up at https://www.twilio.com
- Get Account SID, Auth Token, and phone number

## Deployment Options

### Option 1: Complete Automated Setup (Recommended)

This script handles EVERYTHING - credential setup AND deployment:

```bash
cd lambda
./deploy-full-setup.sh
```

**This will**:
1. Check if Gmail MCP credentials exist
2. Prompt for Claude Code token
3. Ask if you want Twilio SMS alerts
4. Build Docker image
5. Deploy to AWS Lambda
6. Create EventBridge schedule

**Prerequisites**: Gmail MCP must be set up first (see above)

### Option 2: Manual Credential Export + Auto Deploy

If you have all credentials ready:

```bash
cd lambda

# Export credentials
export CLAUDE_CODE_OAUTH_TOKEN="sk-ant-oat01-..."
export GMAIL_OAUTH_CREDENTIALS=$(cat ~/.gmail-mcp/gcp-oauth.keys.json | base64)
export GMAIL_CREDENTIALS=$(cat ~/.gmail-mcp/credentials.json | base64)
export TWILIO_ACCOUNT_SID="AC..."  # Optional
export TWILIO_AUTH_TOKEN="..."    # Optional
export TWILIO_FROM_NUMBER="+1..." # Optional

# Deploy
./deploy-auto.sh
```

### Option 3: Interactive Setup

Prompts for each credential one by one:

```bash
cd lambda
./setup-lambda.sh
```

### Option 4: AWS SAM

Using AWS SAM CLI:

```bash
cd lambda
sam build --use-container
sam deploy --guided
```

## Recommended Next Steps

1. **Set up Gmail MCP** (if not already done):
   ```bash
   npm install -g @gongrzhe/server-gmail-autoauth-mcp
   npx @gongrzhe/server-gmail-autoauth-mcp
   ```

2. **Get Claude Code token**:
   ```bash
   claude setup-token
   ```

3. **Run complete setup**:
   ```bash
   cd lambda
   ./deploy-full-setup.sh
   ```

4. **Test deployment**:
   ```bash
   aws lambda invoke \
     --function-name email-assistant-processor \
     response.json

   cat response.json
   ```

5. **Monitor logs**:
   ```bash
   aws logs tail /aws/lambda/email-assistant-processor --follow
   ```

## Deployment Timeline

**Estimated time**: 15-20 minutes

- Gmail MCP setup: 5-10 minutes (one-time)
- Claude Code token: 1 minute
- Docker build + push: 5-10 minutes
- Lambda deployment: 2-3 minutes
- EventBridge setup: 1 minute

## Current AWS Configuration

**Account ID**: 718881314209
**Default Region**: us-east-1
**AWS CLI**: ✅ Configured
**Docker**: ✅ Installed

## What Gets Deployed

Once you run the deployment:

1. **ECR Repository**: `email-assistant`
2. **Docker Image**: Contains Claude Code CLI + Gmail MCP server
3. **Lambda Function**: `email-assistant-processor`
   - Runtime: Node.js 20 (container)
   - Memory: 1024 MB
   - Timeout: 600 seconds (10 minutes)
4. **IAM Role**: `EmailAssistantLambdaRole`
5. **EventBridge Rule**: `email-assistant-hourly-schedule`
   - Schedule: `cron(0 12-22 ? * MON-FRI *)`
   - Runs: Every hour, 7 AM - 5 PM EST, Monday-Friday
6. **CloudWatch Logs**: `/aws/lambda/email-assistant-processor`

## Cost Estimate

**Monthly cost**: $2-5

- Lambda compute: ~$1.20/month
- CloudWatch Logs: ~$0.50/month
- ECR storage: ~$0.10/month
- Data transfer: Minimal

## Troubleshooting

### "Gmail MCP credentials not found"

Set up Gmail MCP first:
```bash
npm install -g @gongrzhe/server-gmail-autoauth-mcp
npx @gongrzhe/server-gmail-autoauth-mcp
```

### "Docker build failed"

- Ensure Docker Desktop is running: `docker ps`
- Increase Docker memory in preferences (need ~4GB)

### "AccessDenied" during deployment

Your AWS user needs these permissions:
- ECR: Full access
- Lambda: Full access
- IAM: CreateRole, AttachRolePolicy
- EventBridge: PutRule, PutTargets
- CloudWatch Logs: CreateLogGroup, CreateLogStream

## Summary

Everything is ready for deployment. You just need to:

1. Set up Gmail MCP credentials (one-time setup)
2. Get Claude Code OAuth token
3. Run `./deploy-full-setup.sh`

The script will handle the rest automatically!

---

**Status**: Ready for deployment
**Last Updated**: November 6, 2024
**Created by**: Claude Code (Autonomous migration from GitHub Actions)
