# AWS Lambda Deployment Guide

This guide explains how to deploy the Love Brittany relationship tracking automation to AWS Lambda with EventBridge scheduling.

## Architecture Overview

The automation runs as a serverless Lambda function that executes every **Sunday at 4:00 AM EST**:

- **AWS Lambda**: Containerized Python function using Docker
- **Amazon ECR**: Stores the Docker container image
- **EventBridge**: Triggers the Lambda on a cron schedule
- **Parameter Store**: Securely stores credentials and API keys (FREE tier)
- **CloudWatch Logs**: Monitors execution and errors

## Prerequisites

1. **AWS CLI** installed and configured
   ```bash
   aws configure
   ```

2. **Docker** installed and running

3. **Credentials** ready in the `credentials/` directory:
   - `calendar_credentials.json`
   - `calendar_token.json`
   - `gmail_credentials.json`
   - `gmail_token.json`

4. **API Keys** set in `.env` file:
   - `TOGGL_API_TOKEN`
   - `TOGGL_WORKSPACE_ID`

## Quick Start

### 1. Initial Deployment

Run the complete deployment script:

```bash
./scripts/deploy-to-aws.sh
```

This will:
1. Create IAM role with necessary permissions
2. Create ECR repository
3. Build and push Docker image
4. Create Lambda function
5. Set up EventBridge schedule (Sundays at 4 AM EST)

### 2. Upload Parameters

Upload your credentials to AWS Parameter Store (FREE):

```bash
./scripts/setup-parameters.sh
```

This uploads:
- Google Calendar credentials and tokens
- Gmail credentials and tokens
- Toggl API keys

**Cost: $0/month** (uses free Standard tier)

### 3. Test the Function

Test that everything works:

```bash
./scripts/test-lambda.sh
```

## Schedule Details

The automation runs on this schedule:

| Schedule | Cron Expression | Description |
|----------|----------------|-------------|
| Sundays at 4:00 AM EST | `cron(0 9 ? * SUN *)` | Weekly relationship report |

**Note**: EventBridge uses UTC, so 4 AM EST = 9 AM UTC

## Updating the Function

After making code changes, update the Lambda function:

```bash
./scripts/update-lambda-function.sh
```

This will:
1. Build a new Docker image
2. Push it to ECR
3. Update the Lambda function code

## Monitoring

### View Logs

Watch live logs:
```bash
aws logs tail /aws/lambda/love-brittany-weekly-report --follow
```

View recent logs:
```bash
aws logs tail /aws/lambda/love-brittany-weekly-report --since 1h
```

### Check Invocations

See when the function ran:
```bash
aws lambda get-function --function-name love-brittany-weekly-report
```

View EventBridge rule:
```bash
aws events describe-rule --name love-brittany-weekly-report
```

## Manual Invocation

Trigger the function manually (for testing):

```bash
aws lambda invoke \
  --function-name love-brittany-weekly-report \
  --log-type Tail \
  response.json
```

## Troubleshooting

### Function Fails with "Parameter not found"

Make sure you uploaded parameters:
```bash
./scripts/setup-parameters.sh
```

Verify parameters exist:
```bash
aws ssm get-parameters-by-path --path /love-brittany
```

### Permission Denied Errors

The IAM role may need time to propagate:
```bash
# Wait a few minutes, then retry
./scripts/create-iam-role.sh
```

### Docker Build Fails

Ensure Docker is running:
```bash
docker ps
```

### Function Times Out

Increase timeout (currently 900 seconds = 15 minutes):
```bash
aws lambda update-function-configuration \
  --function-name love-brittany-weekly-report \
  --timeout 900
```

## Cost Estimate

This setup costs approximately **$0.03/month** (or **$0.36/year**):

| Service | Monthly Cost | Details |
|---------|--------------|---------|
| Lambda invocations | **$0.00** | 4/month (well under 1M free tier) |
| Lambda compute | **$0.01** | 4 runs × 5 min (under 400K GB-sec free tier) |
| Parameter Store | **$0.00** | FREE (standard tier, up to 10,000 parameters) |
| ECR storage | **$0.01-0.02** | ~150 MB image × $0.10/GB |
| CloudWatch Logs | **$0.00-0.01** | Under 5 GB free tier |
| **Total** | **~$0.03/month** | **~$0.36/year** 🎉 |

### Cost Comparison:

| Storage Option | Monthly | Annual | Savings |
|----------------|---------|--------|---------|
| **Parameter Store** (current) | $0.03 | $0.36 | - |
| Secrets Manager | $2.03 | $24.36 | ❌ $24/year MORE |
| Local scheduling (no AWS) | $0.00 | $0.00 | ✅ Free but requires always-on computer |

### Why So Cheap?

- ✅ Parameter Store is completely FREE (no per-parameter charges)
- ✅ Lambda free tier covers 1M requests + 400K GB-seconds/month
- ✅ CloudWatch free tier covers 5 GB of logs/month
- ✅ ECR only charges for actual storage (~150 MB = $0.015/month)
- ✅ All data transfer within same AWS region is FREE

**You're essentially running this automation for free!** The tiny ECR storage cost is the only real expense.

### Reduce ECR Costs Further (Optional):

Keep only the latest Docker image to minimize storage:

```bash
# Add this to scripts/update-lambda-function.sh after deploying
# Deletes all images except the latest one
aws ecr list-images \
  --repository-name love-brittany-automation \
  --filter tagStatus=UNTAGGED \
  --query 'imageIds[*]' \
  --output json | \
jq -r '.[] | .imageDigest' | \
xargs -I {} aws ecr batch-delete-image \
  --repository-name love-brittany-automation \
  --image-ids imageDigest={}
```

This keeps ECR costs at **$0.01/month** instead of accumulating multiple images over time.

## Cleanup

To remove all AWS resources:

```bash
# Delete Lambda function
aws lambda delete-function --function-name love-brittany-weekly-report

# Delete EventBridge rule
aws events remove-targets --rule love-brittany-weekly-report --ids "1"
aws events delete-rule --name love-brittany-weekly-report

# Delete ECR repository
aws ecr delete-repository --repository-name love-brittany-automation --force

# Delete IAM role
aws iam detach-role-policy \
  --role-name LoveBrittanyLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role-policy --role-name LoveBrittanyLambdaRole --policy-name ParameterStoreAccess
aws iam delete-role-policy --role-name LoveBrittanyLambdaRole --policy-name CloudWatchLogsAccess
aws iam delete-role --role-name LoveBrittanyLambdaRole

# Delete parameters (optional - this deletes your credentials!)
# aws ssm delete-parameter --name /love-brittany/calendar-credentials
# aws ssm delete-parameter --name /love-brittany/calendar-token
# aws ssm delete-parameter --name /love-brittany/gmail-credentials
# aws ssm delete-parameter --name /love-brittany/gmail-token
# aws ssm delete-parameter --name /love-brittany/toggl-api-token
# aws ssm delete-parameter --name /love-brittany/toggl-workspace-id
```

## Directory Structure

```
.
├── lambda_handler.py           # Lambda entry point
├── Dockerfile.lambda           # Container image definition
├── requirements.txt            # Python dependencies
├── config.yaml                 # App configuration
├── src/                        # Application code
│   ├── relationship_main.py
│   ├── relationship_tracker.py
│   └── ...
├── credentials/                # Local credentials (not committed)
│   ├── calendar_credentials.json
│   ├── calendar_token.json
│   ├── gmail_credentials.json
│   └── gmail_token.json
└── scripts/                    # Deployment scripts
    ├── deploy-to-aws.sh        # Main deployment script
    ├── setup-secrets.sh        # Upload secrets
    ├── create-iam-role.sh      # Create IAM role
    ├── create-lambda-function.sh
    ├── update-lambda-function.sh
    ├── setup-eventbridge.sh
    └── test-lambda.sh
```

## Support

For issues:
1. Check CloudWatch Logs for error messages
2. Verify all secrets are uploaded correctly
3. Ensure IAM role has proper permissions
4. Test locally first with `python3 src/relationship_main.py --generate`
