# AWS Lambda Deployment Guide

Complete guide for deploying the Sleep Eight Reporter to AWS Lambda with EventBridge scheduling.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **SES Sender Email** verified in AWS SES
4. **Eight Sleep Account** with active Pod mattress

## Architecture Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  EventBridge │────▶│    Lambda    │────▶│   AWS SES    │
│  (Schedule)  │     │  (Function)  │     │   (Email)    │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Parameter   │
                     │    Store     │
                     └──────────────┘
```

## Step 1: Create IAM Role

Create a Lambda execution role with the following permissions:

### Trust Policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

### Permission Policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter"
            ],
            "Resource": "arn:aws:ssm:*:*:parameter/sleep-eight-reporter/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ses:SendEmail",
                "ses:SendRawEmail"
            ],
            "Resource": "*"
        }
    ]
}
```

### AWS CLI Command
```bash
# Create role
aws iam create-role \
    --role-name lambda-sleep-eight-role \
    --assume-role-policy-document file://trust-policy.json

# Attach basic execution policy
aws iam attach-role-policy \
    --role-name lambda-sleep-eight-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create and attach custom policy
aws iam put-role-policy \
    --role-name lambda-sleep-eight-role \
    --policy-name sleep-eight-permissions \
    --policy-document file://permission-policy.json
```

## Step 2: Setup Parameter Store

Store credentials securely in AWS Systems Manager Parameter Store:

### Using the Script
```bash
./scripts/setup-parameters.sh
```

### Manual Creation
```bash
# Eight Sleep email (SecureString)
aws ssm put-parameter \
    --name "/sleep-eight-reporter/eight-sleep-email" \
    --type "SecureString" \
    --value "your@email.com"

# Eight Sleep password (SecureString)
aws ssm put-parameter \
    --name "/sleep-eight-reporter/eight-sleep-password" \
    --type "SecureString" \
    --value "your-password"

# Report recipient (String)
aws ssm put-parameter \
    --name "/sleep-eight-reporter/email-recipient" \
    --type "String" \
    --value "recipient@email.com"

# SES sender email (String)
aws ssm put-parameter \
    --name "/sleep-eight-reporter/ses-sender-email" \
    --type "String" \
    --value "brandonhome.appdev@gmail.com"
```

### Parameter Store Keys

| Parameter Path | Type | Description |
|----------------|------|-------------|
| `/sleep-eight-reporter/eight-sleep-email` | SecureString | Eight Sleep account email |
| `/sleep-eight-reporter/eight-sleep-password` | SecureString | Eight Sleep account password |
| `/sleep-eight-reporter/email-recipient` | String | Email to receive reports |
| `/sleep-eight-reporter/ses-sender-email` | String | AWS SES verified sender |

## Step 3: Verify SES Sender Email

If you haven't already, verify your sender email in SES:

```bash
aws ses verify-email-identity \
    --email-address brandonhome.appdev@gmail.com \
    --region us-east-1
```

Check verification status:
```bash
aws ses get-identity-verification-attributes \
    --identities brandonhome.appdev@gmail.com \
    --region us-east-1
```

## Step 4: Create Lambda Function

### Using the Script
```bash
./scripts/deploy-lambda-zip.sh
```

### Manual Creation

1. **Package the application:**
   ```bash
   mkdir lambda_package
   pip install -r requirements.txt -t lambda_package/
   cp -r src/* lambda_package/
   cp lambda_handler.py lambda_package/
   cp config.yaml lambda_package/
   cd lambda_package && zip -r ../function.zip . && cd ..
   ```

2. **Create the function:**
   ```bash
   aws lambda create-function \
       --function-name sleep-eight-reporter \
       --runtime python3.9 \
       --handler lambda_handler.daily_sleep_report_handler \
       --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-sleep-eight-role \
       --timeout 120 \
       --memory-size 512 \
       --zip-file fileb://function.zip \
       --region us-east-1
   ```

## Step 5: Create EventBridge Schedule

Schedule the Lambda to run daily:

### Daily at 7 AM EST
```bash
# Create rule
aws events put-rule \
    --name "daily-sleep-report" \
    --schedule-expression "cron(0 12 * * ? *)" \
    --description "Trigger daily sleep report at 7 AM EST (12 UTC)" \
    --region us-east-1

# Add Lambda as target
aws events put-targets \
    --rule "daily-sleep-report" \
    --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:sleep-eight-reporter" \
    --region us-east-1

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
    --function-name sleep-eight-reporter \
    --statement-id "daily-sleep-report" \
    --action "lambda:InvokeFunction" \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:us-east-1:YOUR_ACCOUNT_ID:rule/daily-sleep-report" \
    --region us-east-1
```

## Step 6: Test the Deployment

### Manual Test
```bash
aws lambda invoke \
    --function-name sleep-eight-reporter \
    --payload '{}' \
    --region us-east-1 \
    response.json

cat response.json
```

### View Logs
```bash
aws logs tail /aws/lambda/sleep-eight-reporter --follow
```

## Troubleshooting

### Lambda Timeout
If the function times out:
1. Increase timeout: `aws lambda update-function-configuration --function-name sleep-eight-reporter --timeout 180`
2. Increase memory: `aws lambda update-function-configuration --function-name sleep-eight-reporter --memory-size 1024`

### Eight Sleep Connection Issues
- Verify credentials in Parameter Store
- Check Eight Sleep account is active
- Ensure pyeight library is included in package

### SES Email Not Sending
- Verify sender email in SES
- Check if account is in SES sandbox (verify recipient too)
- Review CloudWatch logs for specific errors

### Permission Denied Errors
- Verify IAM role has correct policies
- Check Parameter Store paths match exactly
- Ensure SES permissions are attached

## Cost Estimate

| Service | Usage | Estimated Cost |
|---------|-------|---------------|
| Lambda | 30 invocations/month, 30s each | ~$0.01 |
| EventBridge | 30 invocations/month | Free |
| SES | 30 emails/month | ~$0.01 |
| Parameter Store | 4 parameters | Free |
| CloudWatch Logs | ~10 MB/month | ~$0.05 |

**Total: ~$0.10/month**

## Security Best Practices

1. **Use SecureString** for sensitive parameters
2. **Minimize IAM permissions** to only what's needed
3. **Enable CloudWatch Logs** encryption
4. **Rotate Eight Sleep password** periodically
5. **Monitor CloudWatch** for unusual activity

## Updating the Function

To update the code:
```bash
./scripts/deploy-lambda-zip.sh
```

To update parameters:
```bash
aws ssm put-parameter \
    --name "/sleep-eight-reporter/email-recipient" \
    --value "new-email@example.com" \
    --overwrite
```
