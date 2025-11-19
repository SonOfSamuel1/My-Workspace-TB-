## AWS Lambda Deployment Guide

This guide walks through deploying the Weekly YNAB Budget Report to AWS Lambda for automated weekly email delivery.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- YNAB API key
- Google OAuth credentials (for Gmail sending)

## Overview

The deployment consists of:
1. **AWS Lambda Function** - Runs the report generation code
2. **AWS EventBridge Rule** - Triggers Lambda on schedule (Saturdays 7pm EST)
3. **AWS Parameter Store** - Securely stores API keys and credentials
4. **IAM Role** - Permissions for Lambda to access Parameter Store

## Step 1: Prepare Credentials

### 1.1 Encode Google Credentials

The Google OAuth token (pickle file) needs to be base64 encoded for Parameter Store:

```bash
# From the project root
base64 -i ../../shared/credentials/token.pickle > token_b64.txt
```

Keep the JSON credentials file as-is (no encoding needed).

### 1.2 Store in AWS Parameter Store

Store all sensitive values in AWS Systems Manager Parameter Store:

```bash
# YNAB API Key
aws ssm put-parameter \
  --name "/budget-report/ynab-api-key" \
  --value "your_ynab_api_key_here" \
  --type "SecureString" \
  --description "YNAB API access token"

# Email recipient
aws ssm put-parameter \
  --name "/budget-report/email-recipient" \
  --value "your_email@example.com" \
  --type "String" \
  --description "Budget report email recipient"

# Google OAuth credentials (JSON file contents)
aws ssm put-parameter \
  --name "/budget-report/credentials" \
  --value "$(cat ../../shared/credentials/credentials.json)" \
  --type "SecureString" \
  --description "Google OAuth credentials"

# Google OAuth token (base64 encoded pickle)
aws ssm put-parameter \
  --name "/budget-report/token" \
  --value "$(cat token_b64.txt)" \
  --type "SecureString" \
  --description "Google OAuth token (base64)"

# Optional: Budget ID (leave blank to use first budget)
aws ssm put-parameter \
  --name "/budget-report/budget-id" \
  --value "" \
  --type "String" \
  --description "YNAB Budget ID (optional)"
```

Verify parameters are stored:

```bash
aws ssm get-parameters \
  --names "/budget-report/ynab-api-key" \
           "/budget-report/email-recipient" \
  --with-decryption
```

## Step 2: Create Lambda Deployment Package

### 2.1 Install Dependencies

```bash
# Create deployment directory
mkdir -p lambda_package

# Install dependencies to package directory
pip install -r requirements.txt -t lambda_package/

# Copy application code
cp -r src/* lambda_package/
cp lambda_handler.py lambda_package/
cp config.yaml lambda_package/

# Copy email sender from Love Brittany tracker
cp ../love-brittany-tracker/src/email_sender.py lambda_package/
```

### 2.2 Create ZIP Package

```bash
cd lambda_package
zip -r ../budget-report-lambda.zip .
cd ..
```

Alternatively, use the provided deployment script:

```bash
chmod +x deploy_lambda.sh
./deploy_lambda.sh
```

## Step 3: Create IAM Role

Create an IAM role for Lambda with permissions to access Parameter Store.

### 3.1 Create Trust Policy

Create `lambda-trust-policy.json`:

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

### 3.2 Create IAM Role

```bash
aws iam create-role \
  --role-name BudgetReportLambdaRole \
  --assume-role-policy-document file://lambda-trust-policy.json
```

### 3.3 Attach Policies

```bash
# Basic Lambda execution
aws iam attach-role-policy \
  --role-name BudgetReportLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# CloudWatch Logs
aws iam attach-role-policy \
  --role-name BudgetReportLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
```

### 3.4 Create Parameter Store Access Policy

Create `parameter-store-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": "arn:aws:ssm:us-east-1:*:parameter/budget-report/*"
    }
  ]
}
```

Create and attach the policy:

```bash
aws iam create-policy \
  --policy-name BudgetReportParameterStoreAccess \
  --policy-document file://parameter-store-policy.json

# Get the policy ARN from the output, then attach
aws iam attach-role-policy \
  --role-name BudgetReportLambdaRole \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/BudgetReportParameterStoreAccess
```

## Step 4: Create Lambda Function

### 4.1 Create Function

```bash
aws lambda create-function \
  --function-name weekly-budget-report \
  --runtime python3.9 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/BudgetReportLambdaRole \
  --handler lambda_handler.weekly_report_handler \
  --zip-file fileb://budget-report-lambda.zip \
  --timeout 300 \
  --memory-size 512 \
  --environment Variables="{AWS_REGION=us-east-1}" \
  --description "Weekly YNAB budget report generator"
```

### 4.2 Update Function (for subsequent deployments)

```bash
aws lambda update-function-code \
  --function-name weekly-budget-report \
  --zip-file fileb://budget-report-lambda.zip
```

### 4.3 Test Function

Test the Lambda function manually:

```bash
aws lambda invoke \
  --function-name weekly-budget-report \
  --payload '{}' \
  response.json

cat response.json
```

Check CloudWatch Logs:

```bash
aws logs tail /aws/lambda/weekly-budget-report --follow
```

## Step 5: Create EventBridge Schedule

### 5.1 Create Rule for Saturday 7pm EST

EventBridge uses UTC, so 7pm EST = 11pm UTC (12am UTC during DST).

```bash
aws events put-rule \
  --name weekly-budget-report-schedule \
  --schedule-expression "cron(0 23 ? * SAT *)" \
  --description "Trigger weekly budget report every Saturday at 7pm EST" \
  --state ENABLED
```

**Note:** Adjust for Daylight Saving Time if needed:
- Standard Time (EST): `cron(0 0 ? * SAT *)` = 7pm EST (midnight UTC)
- Daylight Time (EDT): `cron(0 23 ? * SAT *)` = 7pm EDT (11pm UTC)

### 5.2 Grant EventBridge Permission to Invoke Lambda

```bash
aws lambda add-permission \
  --function-name weekly-budget-report \
  --statement-id weekly-budget-report-event \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:YOUR_ACCOUNT_ID:rule/weekly-budget-report-schedule
```

### 5.3 Add Lambda as EventBridge Target

```bash
aws events put-targets \
  --rule weekly-budget-report-schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:weekly-budget-report"
```

### 5.4 Verify Schedule

```bash
aws events describe-rule --name weekly-budget-report-schedule
aws events list-targets-by-rule --rule weekly-budget-report-schedule
```

## Step 6: Monitor and Troubleshoot

### View Logs

```bash
# Tail logs in real-time
aws logs tail /aws/lambda/weekly-budget-report --follow

# View recent logs
aws logs tail /aws/lambda/weekly-budget-report --since 1h
```

### Test Manual Invocation

```bash
# Invoke manually
aws lambda invoke \
  --function-name weekly-budget-report \
  --payload '{}' \
  /tmp/response.json

# View response
cat /tmp/response.json
```

### Common Issues

**Permission denied errors:**
- Verify IAM role has Parameter Store access
- Check Parameter Store parameter names match exactly

**Timeout errors:**
- Increase Lambda timeout (default: 300 seconds)
- Check YNAB API response times

**Email not sending:**
- Verify Google OAuth credentials are correct
- Check token hasn't expired
- Ensure Gmail API is enabled

**YNAB API errors:**
- Verify API key in Parameter Store
- Check API rate limits (200 requests/hour)
- Ensure budget ID is correct

## Step 7: Update Configuration

### Update Lambda Environment Variables

```bash
aws lambda update-function-configuration \
  --function-name weekly-budget-report \
  --environment Variables="{AWS_REGION=us-east-1,LOG_LEVEL=INFO}"
```

### Update Parameter Store Values

```bash
# Update YNAB API key
aws ssm put-parameter \
  --name "/budget-report/ynab-api-key" \
  --value "new_api_key" \
  --type "SecureString" \
  --overwrite

# Update email recipient
aws ssm put-parameter \
  --name "/budget-report/email-recipient" \
  --value "new_email@example.com" \
  --type "String" \
  --overwrite
```

## Cost Estimation

Estimated AWS costs for weekly reports:

- **Lambda:** ~$0.00 (stays within free tier)
  - 1 invocation/week × 5 seconds × 512 MB = minimal cost
- **Parameter Store:** $0.00 (standard parameters are free)
- **EventBridge:** $0.00 (stays within free tier)
- **CloudWatch Logs:** ~$0.50/month (minimal logging)

**Total estimated cost:** < $1/month

## Security Best Practices

1. **Use SecureString for sensitive parameters**
   - API keys and credentials should use SecureString type
   - Encrypted at rest with KMS

2. **Minimal IAM permissions**
   - Lambda role has access only to required Parameter Store paths
   - No broad wildcard permissions

3. **Rotate credentials regularly**
   - Update YNAB API key periodically
   - Refresh Google OAuth token if expired

4. **Enable CloudWatch Logs encryption**
   - Encrypt log data at rest
   - Set log retention policy (7-14 days recommended)

5. **Use VPC (optional)**
   - For additional network isolation
   - May require NAT Gateway for internet access

## Cleanup

To remove all resources:

```bash
# Delete EventBridge rule targets
aws events remove-targets \
  --rule weekly-budget-report-schedule \
  --ids "1"

# Delete EventBridge rule
aws events delete-rule --name weekly-budget-report-schedule

# Delete Lambda function
aws lambda delete-function --function-name weekly-budget-report

# Delete IAM role policies
aws iam detach-role-policy \
  --role-name BudgetReportLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam detach-role-policy \
  --role-name BudgetReportLambdaRole \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/BudgetReportParameterStoreAccess

# Delete IAM role
aws iam delete-role --role-name BudgetReportLambdaRole

# Delete IAM policy
aws iam delete-policy \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/BudgetReportParameterStoreAccess

# Delete Parameter Store parameters
aws ssm delete-parameters \
  --names "/budget-report/ynab-api-key" \
          "/budget-report/email-recipient" \
          "/budget-report/credentials" \
          "/budget-report/token" \
          "/budget-report/budget-id"
```

## Alternative: Use AWS SAM or Terraform

For infrastructure-as-code deployments, consider:

- **AWS SAM** - Simplified Lambda deployment
- **Terraform** - Multi-cloud infrastructure management
- **CDK** - AWS Cloud Development Kit

Example SAM template available in `docs/sam-template.yaml`

---

**Questions or issues?** Check CloudWatch Logs first, then review the main README troubleshooting section.
