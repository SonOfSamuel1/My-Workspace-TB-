# AWS Lambda Deployment Guide

This guide walks you through deploying the Email Assistant to AWS Lambda for automatic hourly execution.

## Prerequisites

1. **AWS CLI installed and configured**
   - Your AWS credentials are already configured at `~/.aws/credentials`
   - Region: `us-east-1`

2. **Docker installed**
   - Required for building Lambda container images

3. **Claude Code OAuth token**
   - Run `claude setup-token` to generate

4. **Gmail MCP credentials**
   - Located at `~/.gmail-mcp/gcp-oauth.keys.json`
   - Located at `~/.gmail-mcp/credentials.json`

## Step 1: Configure Environment Variables

Create a `.env` file with your credentials:

```bash
# Copy the example file
cp .env.example .env

# Edit the file
nano .env
```

Fill in the required values:

```bash
# Claude Code OAuth Token
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-YOUR_TOKEN_HERE

# Gmail MCP Credentials (base64-encoded)
GMAIL_OAUTH_CREDENTIALS=$(cat ~/.gmail-mcp/gcp-oauth.keys.json | base64 | tr -d '\n')
GMAIL_CREDENTIALS=$(cat ~/.gmail-mcp/credentials.json | base64 | tr -d '\n')

# Phone number for escalations
ESCALATION_PHONE=+14077448449

# Optional: Twilio for SMS (leave empty if not using)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=

# Test mode
TEST_MODE=false
```

**Quick setup:**
```bash
# Get Claude token
CLAUDE_TOKEN=$(cat ~/.config/claude/oauth_token)

# Create .env file
cat > .env <<EOF
CLAUDE_CODE_OAUTH_TOKEN=$CLAUDE_TOKEN
GMAIL_OAUTH_CREDENTIALS=$(cat ~/.gmail-mcp/gcp-oauth.keys.json | base64 | tr -d '\n')
GMAIL_CREDENTIALS=$(cat ~/.gmail-mcp/credentials.json | base64 | tr -d '\n')
ESCALATION_PHONE=+14077448449
TEST_MODE=false
AWS_REGION=us-east-1
EOF

echo "✓ .env file created"
```

## Step 2: Setup IAM Role

Create the IAM role for Lambda execution:

```bash
./scripts/setup-iam-role.sh
```

This creates:
- IAM role: `EmailAssistantLambdaRole`
- Permissions for CloudWatch Logs and SNS

## Step 3: Build and Push Docker Image

Build the Docker image and push to ECR:

```bash
./scripts/build-and-push.sh
```

This will:
1. Create ECR repository if needed
2. Build Docker image with Claude Code and Gmail MCP
3. Push to ECR

**Note:** This step may take 5-10 minutes on first run.

## Step 4: Create Lambda Function

Create the Lambda function:

```bash
./scripts/create-lambda-function.sh
```

This creates:
- Lambda function: `email-assistant-processor`
- Memory: 1024 MB
- Timeout: 900 seconds (15 minutes)
- Environment variables from `.env`

## Step 5: Setup Hourly Schedule

Configure EventBridge to run hourly:

```bash
./scripts/setup-eventbridge-schedule.sh
```

This creates:
- EventBridge rule: `email-assistant-hourly-schedule`
- Schedule: Every hour from 7 AM - 5 PM EST, Monday-Friday
- Automatic invocation of Lambda function

## Step 6: Test the Function

Test the Lambda function manually:

```bash
./scripts/test-lambda.sh
```

This will:
1. Invoke the function with a test event
2. Display the response
3. Show recent CloudWatch logs

## Updating the Function

After making code changes, update the Lambda function:

```bash
# Rebuild and push new image
./scripts/build-and-push.sh

# Update Lambda function
./scripts/update-lambda-function.sh
```

## Viewing Logs

View real-time Lambda execution logs:

```bash
aws logs tail /aws/lambda/email-assistant-processor --follow --region us-east-1
```

Or view logs in AWS Console:
- https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Faws$252Flambda$252Femail-assistant-processor

## Monitoring

Monitor your Lambda function:

```bash
# View recent invocations
aws lambda get-function --function-name email-assistant-processor --region us-east-1

# View CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=email-assistant-processor \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum \
  --region us-east-1
```

## Cost Estimation

Based on hourly execution (Mon-Fri, 7 AM - 5 PM = 11 executions/day = ~55/week):

- **Lambda**: ~$2-3/month
  - 1024 MB memory
  - ~2 min average execution
  - ~220 invocations/month
  - Free tier covers first 1M requests + 400,000 GB-seconds

- **ECR Storage**: <$1/month
  - ~2 GB image storage

- **CloudWatch Logs**: <$1/month
  - ~500 MB/month logs

**Total estimated cost: $3-5/month**

## Troubleshooting

### Function fails with "OAuth token invalid"

Update your Claude Code token:
```bash
# Get new token
claude setup-token

# Update .env file
nano .env  # Update CLAUDE_CODE_OAUTH_TOKEN

# Update Lambda
./scripts/update-lambda-function.sh
```

### Gmail MCP not working

Re-encode your Gmail credentials:
```bash
# Update .env
export GMAIL_OAUTH_CREDENTIALS=$(cat ~/.gmail-mcp/gcp-oauth.keys.json | base64 | tr -d '\n')
export GMAIL_CREDENTIALS=$(cat ~/.gmail-mcp/credentials.json | base64 | tr -d '\n')

# Update .env file and re-deploy
./scripts/update-lambda-function.sh
```

### Function timeout

Increase timeout:
```bash
aws lambda update-function-configuration \
  --function-name email-assistant-processor \
  --timeout 900 \
  --region us-east-1
```

### View detailed error logs

```bash
aws logs tail /aws/lambda/email-assistant-processor --since 1h --format short --region us-east-1
```

## Deleting Resources

To completely remove the Lambda deployment:

```bash
./scripts/delete-lambda-function.sh
```

This removes:
- Lambda function
- EventBridge rule
- EventBridge targets

**Note:** ECR repository and IAM role are preserved. Delete manually if needed:

```bash
# Delete ECR repository
aws ecr delete-repository --repository-name email-assistant-automation --force --region us-east-1

# Delete IAM role (first detach policies)
aws iam detach-role-policy --role-name EmailAssistantLambdaRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam detach-role-policy --role-name EmailAssistantLambdaRole --policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/EmailAssistantLambdaPolicy
aws iam delete-role --role-name EmailAssistantLambdaRole
```

## Schedule Customization

To change the execution schedule, edit the cron expression in `scripts/setup-eventbridge-schedule.sh`:

```bash
# Current: Every hour from 7 AM - 5 PM EST (12:00-22:00 UTC), Mon-Fri
cron(0 12-22 ? * MON-FRI *)

# Every 2 hours:
cron(0 12-22/2 ? * MON-FRI *)

# Only 9 AM, 12 PM, 3 PM EST:
cron(0 14,17,20 ? * MON-FRI *)
```

Then update:
```bash
./scripts/setup-eventbridge-schedule.sh
```

## Support

For issues:
1. Check CloudWatch logs: `aws logs tail /aws/lambda/email-assistant-processor --follow`
2. Test locally first: `claude --print --mcp-config ~/.config/claude/claude_code_config.json`
3. Review GitHub Actions workflow for comparison
