# AWS Lambda Deployment for Email Assistant

This directory contains the AWS Lambda deployment configuration for the Autonomous Email Assistant, providing an alternative to GitHub Actions.

## Overview

The Lambda function runs the same Claude Code email processing logic as the GitHub Actions workflow, but with these advantages:

- **Better performance**: Dedicated compute resources
- **More reliable**: No dependency on GitHub Actions minutes
- **Scalable**: Can handle larger workloads
- **Integrated monitoring**: CloudWatch Logs and metrics
- **Cost-effective**: Pay only for execution time (~$5-10/month)

## Architecture

```
┌─────────────────────────────────────────────────┐
│      Amazon EventBridge (Schedule)              │
│    Hourly: 7 AM - 5 PM EST (Mon-Fri)           │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│         AWS Lambda Function                      │
│  Runtime: Node.js 20 (Container)                │
│  Memory: 1024 MB, Timeout: 10 min               │
│  - Claude Code CLI                              │
│  - Gmail MCP Server                             │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│          Gmail Account                           │
│  Read, Label, Draft, Send emails                │
└─────────────────────────────────────────────────┘
                  │
                  ▼ (Optional)
┌─────────────────────────────────────────────────┐
│              Twilio SMS                          │
│  Escalation alerts for Tier 1                  │
└─────────────────────────────────────────────────┘
```

## Prerequisites

### 1. AWS Account Setup

- **AWS Account** with appropriate permissions
- **AWS CLI** installed and configured ([Install guide](https://aws.amazon.com/cli/))
- **AWS SAM CLI** installed ([Install guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html))
- **Docker** installed and running ([Install guide](https://docs.docker.com/get-docker/))

### 2. Verify Installations

```bash
# Check AWS CLI
aws --version

# Check SAM CLI
sam --version

# Check Docker
docker --version

# Configure AWS credentials (if not already done)
aws configure
```

### 3. Required Credentials

You need the same credentials as the GitHub Actions setup:

- **Claude Code OAuth Token** (from `claude setup-token`)
- **Gmail OAuth Credentials** (`~/.gmail-mcp/gcp-oauth.keys.json`)
- **Gmail User Credentials** (`~/.gmail-mcp/credentials.json`)
- **Twilio Credentials** (optional, for SMS alerts)

## Quick Deployment

### Option 1: Automated Deployment Script

```bash
cd lambda
./deploy.sh
```

The script will:
1. Check all prerequisites
2. Prompt for AWS region and stack name
3. Read your Gmail credentials
4. Ask for Claude Code token
5. Build the Docker container
6. Deploy to AWS Lambda
7. Set up EventBridge schedule

### Option 2: Manual Deployment

```bash
cd lambda

# Build the Lambda function
sam build --use-container

# Deploy (you'll be prompted for parameters)
sam deploy --guided
```

During guided deployment, provide:
- **Stack Name**: `email-assistant` (or your choice)
- **AWS Region**: `us-east-1` (or your preferred region)
- **Parameters**:
  - ClaudeCodeOAuthToken: `sk-ant-oat01-...`
  - GmailOAuthCredentials: `<base64-encoded>`
  - GmailCredentials: `<base64-encoded>`
  - TwilioAccountSid: (optional)
  - TwilioAuthToken: (optional)
  - TwilioFromNumber: (optional)
  - EscalationPhone: `+14077448449`

## Getting Credentials

### Claude Code OAuth Token

```bash
claude setup-token
# Follow browser prompt, copy the token starting with sk-ant-oat01-
```

### Gmail Credentials (Base64)

```bash
# OAuth credentials
cat ~/.gmail-mcp/gcp-oauth.keys.json | base64

# User credentials
cat ~/.gmail-mcp/credentials.json | base64
```

## Configuration

### Modify Schedule

Edit [template.yaml](template.yaml) and change the cron expression:

```yaml
Schedule: cron(0 12-22 ? * MON-FRI *)
```

Examples:
- `cron(0 11-23 ? * MON-FRI *)` - 6 AM to 6 PM EST
- `cron(0 */2 12-22 ? * MON-FRI *)` - Every 2 hours
- `cron(0 12-22 ? * *)` - Every day (including weekends)

### Adjust Timeout and Memory

Edit [template.yaml](template.yaml):

```yaml
Globals:
  Function:
    Timeout: 600  # Max 900 (15 min) for Lambda
    MemorySize: 1024  # Increase for better performance
```

## Monitoring and Logs

### View Logs in Real-Time

```bash
# Follow logs
aws logs tail /aws/lambda/email-assistant-processor --follow

# Filter for errors
aws logs tail /aws/lambda/email-assistant-processor --filter-pattern "ERROR"

# View specific time range
aws logs tail /aws/lambda/email-assistant-processor --since 1h
```

### Manual Invocation

Test the function manually:

```bash
aws lambda invoke \
  --function-name email-assistant-processor \
  --region us-east-1 \
  response.json

cat response.json
```

### CloudWatch Metrics

View in AWS Console:
- **CloudWatch** → **Logs** → `/aws/lambda/email-assistant-processor`
- **Lambda** → **email-assistant-processor** → **Monitor** tab

Key metrics:
- Invocations
- Duration
- Errors
- Throttles

## Cost Estimate

### Lambda Costs

- **Compute**: ~$0.000016/GB-second
- **Requests**: $0.20 per 1M requests

**Monthly estimate** (assuming 5 min per run, 11 runs/day, 22 days/month):
- Compute time: 242 runs × 300 sec × 1 GB = 72,600 GB-seconds
- Cost: 72,600 × $0.000016 = **$1.16/month**
- Requests: 242 × $0.20/1M = **$0.05/month**

**Total Lambda cost: ~$1.20/month**

### Additional Costs

- **CloudWatch Logs**: ~$0.50/month (30-day retention)
- **Data Transfer**: Negligible
- **Claude Code Max**: $100/month (existing subscription)
- **Twilio SMS**: ~$0.0075/message (optional)

**Total: ~$2-5/month** (excluding Claude Code Max subscription)

## Updating the Function

### Update Code

```bash
cd lambda

# Edit index.js or other files

# Rebuild and redeploy
sam build --use-container
sam deploy
```

### Update Environment Variables

```bash
# Update a single environment variable
aws lambda update-function-configuration \
  --function-name email-assistant-processor \
  --environment "Variables={CLAUDE_CODE_OAUTH_TOKEN=new-token}"
```

Or update via CloudFormation:
```bash
sam deploy --parameter-overrides ClaudeCodeOAuthToken=new-token
```

## Troubleshooting

### Lambda Function Timeout

**Symptom**: Function times out after 10 minutes

**Solutions**:
- Increase timeout in `template.yaml` (max 15 min)
- Increase memory (more memory = more CPU power)
- Optimize Claude Code prompt

### Claude Code Authentication Failed

**Symptom**: "Invalid OAuth token" error

**Solution**:
```bash
# Get fresh token
claude setup-token

# Update Lambda environment variable
aws lambda update-function-configuration \
  --function-name email-assistant-processor \
  --environment "Variables={CLAUDE_CODE_OAUTH_TOKEN=new-token,...}"
```

### Gmail MCP Connection Failed

**Symptom**: "Cannot connect to Gmail" error

**Solutions**:
1. Verify base64-encoded credentials are correct
2. Re-authorize Gmail MCP locally
3. Update Lambda environment variables with fresh credentials

### Docker Build Fails

**Symptom**: `sam build` fails during Docker build

**Solutions**:
- Ensure Docker is running: `docker ps`
- Increase Docker memory limit (Preferences → Resources)
- Clear Docker cache: `docker system prune -a`

### Insufficient Permissions

**Symptom**: "AccessDenied" errors during deployment

**Solution**:
```bash
# Your AWS user needs these permissions:
# - cloudformation:*
# - lambda:*
# - iam:CreateRole, iam:PassRole
# - logs:*
# - events:*
# - ecr:* (for container images)
# - s3:* (for deployment bucket)
```

## Cleanup / Deletion

To completely remove the Lambda deployment:

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name email-assistant

# Verify deletion
aws cloudformation describe-stacks --stack-name email-assistant

# (Optional) Delete S3 deployment bucket
aws s3 rb s3://your-deployment-bucket --force
```

## Migration from GitHub Actions

If you're migrating from the GitHub Actions workflow:

1. **Deploy Lambda** using this guide
2. **Test manually** to verify it works
3. **Monitor for 1 week** alongside GitHub Actions
4. **Disable GitHub Actions** workflow:
   ```bash
   # Move workflow file to disable it
   mv .github/workflows/hourly-email-management.yml \
      .github/workflows/hourly-email-management.yml.disabled

   git add .
   git commit -m "Migrate to AWS Lambda, disable GitHub Actions"
   git push
   ```

## Comparison: Lambda vs GitHub Actions

| Feature | AWS Lambda | GitHub Actions |
|---------|-----------|----------------|
| **Cost** | ~$2-5/month | Free (2,000 min/month) |
| **Performance** | Dedicated resources | Shared runners |
| **Reliability** | 99.95% SLA | Best effort |
| **Max timeout** | 15 minutes | 6 hours |
| **Monitoring** | CloudWatch (built-in) | GitHub logs only |
| **Complexity** | Higher (AWS setup) | Lower (just push to repo) |
| **Scalability** | Excellent | Limited by free tier |

## Support

For issues:
- Check CloudWatch Logs first
- Verify all environment variables are set correctly
- Test Gmail MCP connection locally
- Ensure Claude Code token is valid

## Files in This Directory

- **index.js** - Lambda handler function
- **package.json** - Node.js dependencies
- **Dockerfile** - Container image definition
- **template.yaml** - AWS SAM/CloudFormation template
- **deploy.sh** - Automated deployment script
- **.dockerignore** - Files to exclude from Docker build
- **README.md** - This file

## Next Steps

After successful deployment:

1. Monitor first few runs in CloudWatch
2. Verify emails are being processed correctly
3. Check morning briefs and EOD reports
4. Adjust tier classification rules if needed
5. Fine-tune timeout and memory settings

---

**Questions?** Open an issue in the GitHub repository.
