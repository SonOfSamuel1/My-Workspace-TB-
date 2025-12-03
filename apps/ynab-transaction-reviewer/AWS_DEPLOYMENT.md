# AWS Lambda Deployment Guide

This guide walks through deploying the YNAB Transaction Reviewer to AWS Lambda for automated daily execution.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured (`aws configure`)
3. **Python 3.9** installed locally
4. **Your AWS Account ID** (find it with: `aws sts get-caller-identity`)

## Quick Deployment

### 1. Create IAM Role for Lambda

First, create an IAM role that Lambda will use:

```bash
# Create the role
aws iam create-role --role-name ynab-reviewer-lambda-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach necessary policies
aws iam attach-role-policy --role-name ynab-reviewer-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy --role-name ynab-reviewer-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess
```

### 2. Store Secrets in Parameter Store

Store your YNAB API key and email securely:

```bash
# Store YNAB API key (replace with your actual key)
aws ssm put-parameter \
  --name "/ynab-reviewer/ynab-api-key" \
  --value "YOUR_YNAB_API_KEY" \
  --type "SecureString" \
  --region us-east-1

# Store recipient email
aws ssm put-parameter \
  --name "/ynab-reviewer/recipient-email" \
  --value "terrancebrandon@me.com" \
  --type "String" \
  --region us-east-1
```

### 3. Upload Gmail Credentials to S3

Create a secure S3 bucket for credentials:

```bash
# Create bucket
aws s3 mb s3://ynab-reviewer-credentials-YOUR_ACCOUNT_ID

# Upload Gmail credentials
aws s3 cp credentials/gmail_credentials.json \
  s3://ynab-reviewer-credentials-YOUR_ACCOUNT_ID/

aws s3 cp credentials/gmail_token.pickle \
  s3://ynab-reviewer-credentials-YOUR_ACCOUNT_ID/

# Set bucket policy to restrict access
aws s3api put-bucket-policy --bucket ynab-reviewer-credentials-YOUR_ACCOUNT_ID \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "AllowLambdaAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ynab-reviewer-lambda-role"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::ynab-reviewer-credentials-YOUR_ACCOUNT_ID/*"
    }]
  }'
```

### 4. Deploy the Lambda Function

Run the deployment script:

```bash
cd apps/ynab-transaction-reviewer
./scripts/deploy-lambda.sh
```

If this is your first deployment, you'll need to create the function manually:

```bash
# Get your account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create the Lambda function
aws lambda create-function \
  --function-name ynab-transaction-reviewer \
  --runtime python3.9 \
  --role arn:aws:iam::${ACCOUNT_ID}:role/ynab-reviewer-lambda-role \
  --handler lambda.daily_review_handler.lambda_handler \
  --timeout 300 \
  --memory-size 512 \
  --region us-east-1

# Then run the deployment script again
./scripts/deploy-lambda.sh
```

### 5. Set Up EventBridge Schedule

The deployment script automatically creates an EventBridge rule, but you can also do it manually:

```bash
# Create rule for 5 PM ET daily (except Saturday)
aws events put-rule \
  --name ynab-daily-review-5pm \
  --schedule-expression "cron(0 21 ? * SUN,MON,TUE,WED,THU,FRI *)" \
  --description "Daily YNAB review at 5 PM ET (skip Saturday)" \
  --region us-east-1

# Add Lambda as target
aws events put-targets \
  --rule ynab-daily-review-5pm \
  --targets "[{
    \"Id\": \"1\",
    \"Arn\": \"arn:aws:lambda:us-east-1:${ACCOUNT_ID}:function:ynab-transaction-reviewer\"
  }]" \
  --region us-east-1
```

## Testing

### Test the Lambda Function

```bash
# Invoke the function manually
aws lambda invoke \
  --function-name ynab-transaction-reviewer \
  --payload '{"force": true, "dry_run": true}' \
  response.json \
  --region us-east-1

# Check the response
cat response.json
```

### View Logs

```bash
# View recent logs
aws logs tail /aws/lambda/ynab-transaction-reviewer --follow --region us-east-1
```

### Test with Dry Run

```bash
# Test without sending emails
aws lambda invoke \
  --function-name ynab-transaction-reviewer \
  --payload '{"dry_run": true}' \
  response.json \
  --region us-east-1
```

## Environment Variables

The Lambda function reads these from Parameter Store:
- `/ynab-reviewer/ynab-api-key` - Your YNAB API key
- `/ynab-reviewer/recipient-email` - Email to receive reviews
- `/ynab-reviewer/ynab-budget-id` - (Optional) Specific budget ID

## Schedule Details

The function runs daily at 5 PM ET with these specifics:
- **Monday-Friday**: 5 PM ET
- **Saturday**: Skipped
- **Sunday**: 5 PM ET (includes Saturday's transactions)

EventBridge uses UTC time:
- During EST (winter): 5 PM ET = 10 PM UTC (22:00)
- During EDT (summer): 5 PM ET = 9 PM UTC (21:00)

The cron expression accounts for this: `cron(0 21 ? * SUN,MON,TUE,WED,THU,FRI *)`

## Monitoring

### CloudWatch Metrics

Monitor your function in CloudWatch:
1. Go to CloudWatch Console
2. Navigate to Metrics → Lambda
3. View invocations, duration, errors, and throttles

### Set Up Alarms

```bash
# Create alarm for function errors
aws cloudwatch put-metric-alarm \
  --alarm-name ynab-reviewer-errors \
  --alarm-description "Alert when Lambda function has errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --dimensions Name=FunctionName,Value=ynab-transaction-reviewer \
  --evaluation-periods 1 \
  --region us-east-1
```

## Cost Estimation

Estimated monthly costs (based on daily execution):
- **Lambda invocations**: 30 invocations × $0.20/1M = ~$0.00
- **Lambda compute**: 30 × 5 seconds × 512 MB = ~$0.05
- **Parameter Store**: Free tier (no cost)
- **CloudWatch Logs**: ~$0.50
- **Total**: **< $1/month**

## Troubleshooting

### Function Times Out
- Increase timeout in Lambda configuration (max: 900 seconds)
- Check YNAB API rate limits

### Rate Limit Errors
- YNAB allows 200 requests/hour
- Function includes retry logic with exponential backoff
- Consider running at different times if sharing API key

### Gmail Authentication Issues
- Ensure credentials are in S3
- Update Lambda to download from S3 at runtime
- Check token expiration

### No Emails Received
- Check CloudWatch logs for errors
- Verify Parameter Store values
- Test Gmail authentication locally
- Check spam folder

## Updating the Function

After making code changes:

```bash
# Re-deploy
cd apps/ynab-transaction-reviewer
./scripts/deploy-lambda.sh

# Or update just the code
aws lambda update-function-code \
  --function-name ynab-transaction-reviewer \
  --zip-file fileb://deployment/lambda-package.zip \
  --region us-east-1
```

## Cleanup

To remove all resources:

```bash
# Delete Lambda function
aws lambda delete-function --function-name ynab-transaction-reviewer

# Delete EventBridge rule
aws events remove-targets --rule ynab-daily-review-5pm --ids "1"
aws events delete-rule --name ynab-daily-review-5pm

# Delete IAM role (first detach policies)
aws iam detach-role-policy --role-name ynab-reviewer-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam detach-role-policy --role-name ynab-reviewer-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess

aws iam delete-role --role-name ynab-reviewer-lambda-role

# Delete parameters
aws ssm delete-parameter --name /ynab-reviewer/ynab-api-key
aws ssm delete-parameter --name /ynab-reviewer/recipient-email

# Delete S3 bucket (first empty it)
aws s3 rm s3://ynab-reviewer-credentials-YOUR_ACCOUNT_ID --recursive
aws s3 rb s3://ynab-reviewer-credentials-YOUR_ACCOUNT_ID
```

## Support

For issues or questions:
1. Check CloudWatch logs first
2. Review this deployment guide
3. Test locally with `python3 src/reviewer_main.py --validate`

---

Last Updated: 2025-11-26