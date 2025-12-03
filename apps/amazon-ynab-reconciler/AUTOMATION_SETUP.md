# Amazon-YNAB Reconciler - Full Automation Setup Guide

This guide walks you through setting up the complete automated reconciliation system that runs daily without any manual intervention.

## Overview

The automated system:
- **Primary Mode**: Parses Amazon order emails from Gmail (no browser automation needed)
- **Fallback Mode**: Imports from CSV files if email parsing fails
- **Daily Schedule**: Runs automatically at 2 AM ET via AWS EventBridge
- **Cost-Efficient**: Uses AWS Lambda ZIP deployment (~$0.01/day vs $0.38/day for container)
- **State Management**: Prevents duplicate processing via S3 storage

## Prerequisites

1. **AWS Account** with AWS CLI configured
2. **YNAB Account** with Personal Access Token
3. **Gmail Account** with API access enabled
4. **Python 3.9+** installed locally

## Step-by-Step Setup

### Step 1: Configure Gmail API Access

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" as application type
   - Download the JSON file
5. Save credentials:
   ```bash
   mkdir -p credentials
   # Save downloaded JSON as:
   mv ~/Downloads/client_secret_*.json credentials/gmail_credentials.json
   ```

### Step 2: Authenticate Gmail Locally

First-time authentication to generate token:

```bash
cd src
python3 gmail_service.py
# This will open a browser for authentication
# Grant permissions to read emails
# Token will be saved to credentials/gmail_token.pickle
```

### Step 3: Test Email Mode Locally

Verify email parsing works:

```bash
# Test with dry run (no YNAB updates)
python3 reconciler_main.py --use-email --days 7 --dry-run

# Check output for parsed transactions
# You should see: "Parsed X transactions from emails"
```

### Step 4: Set Up AWS Parameters

Store credentials securely in AWS:

```bash
cd scripts
./setup-parameters.sh

# You'll be prompted for:
# - YNAB API Key (from https://app.ynab.com/settings/developer)
# - Amazon account email (terrancebrandon@me.com)
# - Report email address
```

### Step 5: Deploy to AWS Lambda

Deploy the Lambda function with EventBridge schedule:

```bash
./deploy-lambda-zip.sh

# This script will:
# 1. Create a ZIP deployment package
# 2. Create/update Lambda function
# 3. Set up IAM roles and permissions
# 4. Create S3 bucket for state management
# 5. Configure EventBridge for daily execution
```

Expected output:
```
✓ Deployment complete!
Function Name: amazon-ynab-reconciler
Region: us-east-1
Memory: 512MB
Timeout: 300s
Schedule: Daily at 2 AM ET
```

### Step 6: Test Lambda Function

Run a test execution:

```bash
# Invoke Lambda function
aws lambda invoke \
  --function-name amazon-ynab-reconciler \
  --payload '{"lookback_days": 7, "force_email": true}' \
  output.json

# Check output
cat output.json | jq

# View logs
aws logs tail /aws/lambda/amazon-ynab-reconciler --follow
```

### Step 7: Verify Daily Schedule

Check EventBridge rule:

```bash
# View rule details
aws events describe-rule --name amazon-ynab-reconciler-daily

# List targets
aws events list-targets-by-rule --rule amazon-ynab-reconciler-daily
```

## How It Works

### Email Parsing Flow

1. **Gmail API** fetches order confirmation emails from:
   - ship-confirm@amazon.com
   - auto-confirm@amazon.com
   - order-update@amazon.com
   - digital-no-reply@amazon.com

2. **Email Parser** extracts:
   - Order ID (e.g., 123-4567890-1234567)
   - Order total amount
   - Item names and categories
   - Product ASINs and links
   - Order/delivery dates

3. **Transaction Matcher** finds YNAB matches using:
   - Date tolerance: ±2 days
   - Amount tolerance: ±$0.50
   - Confidence scoring (0-100%)

4. **YNAB Updater** applies memo format:
   ```
   [Amazon: Electronics] | Echo Dot (5th Gen) | amazon.com/dp/B09B8V1LZ3
   ```

### Fallback Mechanisms

If email parsing fails, the system falls back to:
1. **CSV Import**: Reads from `data/amazon_orders.csv`
2. **Sample Data**: Uses test transactions for validation

### State Management

- **S3 Bucket**: `amazon-ynab-reconciler`
- **State File**: `state/reconciliation_state.json`
- **Purpose**: Tracks matched transactions to prevent duplicates
- **Retention**: 90 days of history

## Monitoring & Troubleshooting

### CloudWatch Logs

View execution logs:
```bash
# Recent executions
aws logs tail /aws/lambda/amazon-ynab-reconciler --since 1h

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/amazon-ynab-reconciler \
  --filter-pattern "ERROR"
```

### Common Issues

#### No Amazon Emails Found
- **Cause**: Gmail API not finding order emails
- **Solution**: Check email filters, ensure orders are in inbox
- **Workaround**: Use CSV import mode

#### Low Match Confidence
- **Cause**: Date/amount differences
- **Solution**: Adjust tolerances in config
- **Check**: Transaction dates in YNAB vs Amazon

#### Lambda Timeout
- **Cause**: Too many transactions to process
- **Solution**: Reduce lookback_days or increase timeout

#### Missing Credentials
- **Cause**: Parameter Store not configured
- **Solution**: Run `./scripts/setup-parameters.sh`

### Email Reports

Daily reports are sent to your configured email with:
- Number of transactions found
- Matches by confidence level
- Updates applied
- Any errors encountered

## Cost Analysis

### Lambda Costs (Monthly)
- **Invocations**: 30 × $0.0000002 = $0.000006
- **Compute**: 30 × 5 sec × 512MB = ~$0.30
- **Total**: ~$0.30/month

### Additional AWS Services
- **Parameter Store**: Free tier (< 10,000 requests)
- **S3 Storage**: < $0.01/month
- **CloudWatch Logs**: < $0.10/month
- **SES Email**: $0.10 per 1,000 emails

**Total Monthly Cost**: ~$0.50

## Advanced Configuration

### Modify Schedule

Change execution time:
```bash
# Update to run at 6 AM ET (11 AM UTC)
aws events put-rule \
  --name amazon-ynab-reconciler-daily \
  --schedule-expression "cron(0 11 * * ? *)"
```

### Adjust Matching Parameters

Edit Lambda environment variables:
```bash
aws lambda update-function-configuration \
  --function-name amazon-ynab-reconciler \
  --environment Variables='{
    "DATE_TOLERANCE_DAYS":"3",
    "AMOUNT_TOLERANCE_CENTS":"100",
    "MATCH_THRESHOLD":"75"
  }'
```

### Manual CSV Upload

For historical data import:
1. Export Amazon order history as CSV
2. Upload to S3:
   ```bash
   aws s3 cp amazon_orders.csv s3://amazon-ynab-reconciler/imports/
   ```
3. Trigger Lambda with CSV mode

## Security Best Practices

1. **Rotate API Keys** quarterly
2. **Use IAM roles** with least privilege
3. **Enable CloudTrail** for audit logging
4. **Encrypt parameters** in Parameter Store
5. **Review Lambda permissions** regularly

## Support & Maintenance

### Update Lambda Code

After making changes:
```bash
cd scripts
./deploy-lambda-zip.sh
```

### View Reconciliation State

Check processed transactions:
```bash
aws s3 cp s3://amazon-ynab-reconciler/state/reconciliation_state.json - | jq
```

### Force Reprocessing

Clear state to reprocess transactions:
```bash
aws s3 rm s3://amazon-ynab-reconciler/state/reconciliation_state.json
```

## Conclusion

Your Amazon-YNAB reconciliation is now fully automated! The system will:
- Run daily at 2 AM ET
- Parse Amazon order emails
- Match with YNAB transactions
- Update transaction memos
- Send email reports
- Maintain state to prevent duplicates

For issues or questions, check CloudWatch logs first, then review this guide's troubleshooting section.