# AWS Deployment Guide

Complete guide for deploying the Daily AI News Report to AWS Lambda with EventBridge scheduling.

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│   EventBridge   │────▶│    Lambda    │────▶│   AWS SES   │
│  (Daily Cron)   │     │  (Python)    │     │  (Email)    │
└─────────────────┘     └──────────────┘     └─────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   Secrets    │
                        │   Manager    │
                        └──────────────┘
```

## Prerequisites

1. **AWS CLI** installed and configured
2. **AWS Account** with appropriate permissions
3. **Verified email** in AWS SES (sender address)

### Required IAM Permissions

The Lambda execution role needs:
- `ses:SendEmail`
- `ses:SendRawEmail`
- `secretsmanager:GetSecretValue`
- `logs:CreateLogGroup`
- `logs:CreateLogStream`
- `logs:PutLogEvents`

## Step 1: Verify Email in SES

```bash
aws ses verify-email-identity --email-address your-email@example.com
```

Check your inbox and click the verification link.

> **Note**: If your SES account is in sandbox mode, you must also verify recipient emails.

## Step 2: Create Secrets in Secrets Manager

```bash
# Using the provided script
./scripts/setup-parameters.sh

# Or manually
aws secretsmanager create-secret \
    --name daily-ai-news/credentials \
    --secret-string '{
        "SENDER_EMAIL": "your-verified@email.com",
        "RECIPIENT_EMAIL": "recipient@email.com",
        "AWS_REGION": "us-east-1"
    }'
```

## Step 3: Create IAM Role for Lambda

```bash
# Create the role
aws iam create-role \
    --role-name daily-ai-news-lambda-role \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

# Attach basic Lambda execution policy
aws iam attach-role-policy \
    --role-name daily-ai-news-lambda-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create and attach custom policy for SES and Secrets Manager
aws iam put-role-policy \
    --role-name daily-ai-news-lambda-role \
    --policy-name daily-ai-news-permissions \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["ses:SendEmail", "ses:SendRawEmail"],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": "secretsmanager:GetSecretValue",
                "Resource": "arn:aws:secretsmanager:*:*:secret:daily-ai-news/*"
            }
        ]
    }'
```

## Step 4: Create Lambda Function

```bash
# Build deployment package
./scripts/deploy-lambda-zip.sh

# Create the function (first time)
aws lambda create-function \
    --function-name daily-ai-news-report \
    --runtime python3.9 \
    --role arn:aws:iam::YOUR_ACCOUNT_ID:role/daily-ai-news-lambda-role \
    --handler lambda_handler.lambda_handler \
    --zip-file fileb://deployment/lambda_package.zip \
    --timeout 120 \
    --memory-size 256 \
    --environment Variables='{
        "SECRETS_NAME": "daily-ai-news/credentials",
        "AWS_REGION": "us-east-1"
    }'
```

## Step 5: Create EventBridge Schedule

```bash
# Create the rule (8 AM UTC daily)
aws events put-rule \
    --name daily-ai-news-schedule \
    --schedule-expression "cron(0 8 * * ? *)" \
    --description "Trigger daily AI news report"

# Add Lambda as target
aws events put-targets \
    --rule daily-ai-news-schedule \
    --targets '[{
        "Id": "daily-ai-news-target",
        "Arn": "arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:daily-ai-news-report"
    }]'

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
    --function-name daily-ai-news-report \
    --statement-id daily-ai-news-eventbridge \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:us-east-1:YOUR_ACCOUNT_ID:rule/daily-ai-news-schedule
```

## Step 6: Test the Deployment

```bash
# Invoke with dry run
aws lambda invoke \
    --function-name daily-ai-news-report \
    --payload '{"dry_run": true}' \
    response.json

cat response.json

# Invoke for real
aws lambda invoke \
    --function-name daily-ai-news-report \
    --payload '{}' \
    response.json
```

## Updating the Function

After making code changes:

```bash
./scripts/deploy-lambda-zip.sh
```

## Monitoring

### CloudWatch Logs

```bash
# View recent logs
aws logs tail /aws/lambda/daily-ai-news-report --follow
```

### CloudWatch Metrics

Monitor these metrics in the AWS Console:
- Invocations
- Duration
- Errors
- Throttles

## Troubleshooting

### Email Not Sending

1. Check SES sandbox status
2. Verify sender email is confirmed
3. Check CloudWatch logs for errors
4. Verify Secrets Manager values

### Lambda Timeout

Increase timeout in Lambda configuration:
```bash
aws lambda update-function-configuration \
    --function-name daily-ai-news-report \
    --timeout 180
```

### Permission Errors

Check IAM role has required policies:
```bash
aws iam list-attached-role-policies --role-name daily-ai-news-lambda-role
aws iam list-role-policies --role-name daily-ai-news-lambda-role
```

## Cost Estimation

With daily execution:
- **Lambda**: ~$0.02/month (128MB, 60s execution)
- **SES**: $0.10 per 1,000 emails
- **Secrets Manager**: $0.40/month per secret
- **EventBridge**: Free for scheduled rules

**Total**: ~$0.50-1.00/month
