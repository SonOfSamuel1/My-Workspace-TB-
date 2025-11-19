# Migration Guide: GitHub Actions to AWS Lambda

This guide helps you migrate your Autonomous Email Assistant from GitHub Actions to AWS Lambda.

## Why Migrate to AWS Lambda?

### Advantages

1. **Better Reliability**: 99.95% SLA vs best-effort GitHub Actions
2. **More Resources**: Dedicated compute, configurable memory (up to 10 GB)
3. **Longer Timeout**: 15 minutes max vs 6 hours (but typically completes in 2-5 min)
4. **Better Monitoring**: CloudWatch Logs, metrics, and alarms built-in
5. **Professional**: Production-grade infrastructure

### Disadvantages

1. **Cost**: ~$2-5/month (GitHub Actions is free within limits)
2. **Complexity**: Requires AWS account and basic AWS knowledge
3. **Setup Time**: More initial setup than GitHub Actions

## Cost Comparison

| Item | GitHub Actions | AWS Lambda |
|------|----------------|------------|
| Compute | Free (2,000 min/month) | ~$1.20/month |
| Logs | Free | ~$0.50/month |
| Storage | Free | Minimal |
| **Total** | **$0/month** | **~$2-5/month** |

## Migration Steps

### Step 1: Verify Current GitHub Actions Setup

Ensure your GitHub Actions workflow is working correctly:

```bash
# Check recent workflow runs
gh run list --workflow=hourly-email-management.yml --limit 5

# View logs from latest run
gh run view --log
```

### Step 2: Deploy to AWS Lambda

Choose one of these methods:

#### Option A: Automated Setup (Recommended)

```bash
cd lambda
./setup-lambda.sh
```

This interactive script will:
- Check all prerequisites
- Create ECR repository
- Build and push Docker image
- Create Lambda function
- Set up EventBridge schedule

#### Option B: AWS SAM Deployment

```bash
cd lambda
sam build --use-container
sam deploy --guided
```

#### Option C: Manual AWS Console

See [lambda/README.md](README.md) for detailed manual setup steps.

### Step 3: Test Lambda Function

```bash
# Invoke manually
aws lambda invoke \
  --function-name email-assistant-processor \
  --region us-east-1 \
  response.json

# View output
cat response.json

# Check logs
aws logs tail /aws/lambda/email-assistant-processor --follow
```

### Step 4: Run Both in Parallel (Recommended)

For the first week, run both GitHub Actions and Lambda:

1. Keep GitHub Actions enabled
2. Deploy Lambda
3. Compare results daily
4. Verify Lambda is working correctly

### Step 5: Disable GitHub Actions

Once confident in Lambda:

```bash
# Rename workflow file to disable it
git mv .github/workflows/hourly-email-management.yml \
        .github/workflows/hourly-email-management.yml.disabled

git add .
git commit -m "Migrate to AWS Lambda, disable GitHub Actions"
git push
```

Or simply delete the workflow:

```bash
git rm .github/workflows/hourly-email-management.yml
git commit -m "Remove GitHub Actions workflow (migrated to Lambda)"
git push
```

## Configuration Differences

### GitHub Actions

Environment variables stored in GitHub Secrets:
- CLAUDE_CODE_OAUTH_TOKEN
- GMAIL_OAUTH_CREDENTIALS (base64)
- GMAIL_CREDENTIALS (base64)
- TWILIO_ACCOUNT_SID
- TWILIO_AUTH_TOKEN
- TWILIO_FROM_NUMBER

### AWS Lambda

Same environment variables stored in Lambda configuration:
- Set during deployment via `setup-lambda.sh`
- Can be updated via AWS Console or CLI
- Automatically encrypted at rest

### Schedule Syntax

Both use cron expressions, but with slight differences:

**GitHub Actions** (uses UTC):
```yaml
cron: "0 12-22 * * 1-5"
```

**EventBridge** (uses UTC):
```
cron(0 12-22 ? * MON-FRI *)
```

Note: Both are equivalent for 7 AM - 5 PM EST (UTC-5)

## Updating Lambda After Migration

### Update Code

```bash
cd lambda

# Edit index.js or other files

# Rebuild and redeploy
docker build -t email-assistant:latest -f Dockerfile .

# Push to ECR and update function
./setup-lambda.sh  # Re-run to update
```

### Update Environment Variables

```bash
# Update Claude Code token
aws lambda update-function-configuration \
  --function-name email-assistant-processor \
  --environment "Variables={
    CLAUDE_CODE_OAUTH_TOKEN=new-token,
    GMAIL_OAUTH_CREDENTIALS=$GMAIL_OAUTH_BASE64,
    GMAIL_CREDENTIALS=$GMAIL_CREDS_BASE64,
    ESCALATION_PHONE=+14077448449
  }" \
  --region us-east-1
```

### Update Schedule

Edit EventBridge rule:

```bash
aws events put-rule \
  --name email-assistant-hourly-schedule \
  --schedule-expression "cron(0 11-23 ? * MON-FRI *)" \
  --region us-east-1
```

## Monitoring and Debugging

### View Logs

```bash
# Real-time logs
aws logs tail /aws/lambda/email-assistant-processor --follow

# Filter errors
aws logs tail /aws/lambda/email-assistant-processor \
  --filter-pattern "ERROR"

# Specific time range
aws logs tail /aws/lambda/email-assistant-processor --since 1h
```

### CloudWatch Metrics

View in AWS Console:
- Lambda → email-assistant-processor → Monitor
- Key metrics: Invocations, Duration, Errors, Throttles

### Set Up Alarms

```bash
# Create alarm for function errors
aws cloudwatch put-metric-alarm \
  --alarm-name email-assistant-errors \
  --alarm-description "Alert on Lambda function errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=email-assistant-processor
```

## Rollback Plan

If you need to rollback to GitHub Actions:

### Step 1: Re-enable GitHub Actions

```bash
# Restore workflow file
git mv .github/workflows/hourly-email-management.yml.disabled \
        .github/workflows/hourly-email-management.yml

git add .
git commit -m "Rollback to GitHub Actions"
git push
```

### Step 2: Disable Lambda (Optional)

```bash
# Disable EventBridge rule (keeps function but stops scheduling)
aws events disable-rule \
  --name email-assistant-hourly-schedule \
  --region us-east-1
```

Or delete everything:

```bash
# Delete EventBridge rule
aws events remove-targets \
  --rule email-assistant-hourly-schedule \
  --ids 1 \
  --region us-east-1

aws events delete-rule \
  --name email-assistant-hourly-schedule \
  --region us-east-1

# Delete Lambda function
aws lambda delete-function \
  --function-name email-assistant-processor \
  --region us-east-1

# Delete ECR repository
aws ecr delete-repository \
  --repository-name email-assistant \
  --force \
  --region us-east-1
```

## Troubleshooting

### Lambda Times Out

**Symptom**: Function execution exceeds 10 minutes

**Solutions**:
1. Increase timeout: Edit `template.yaml` and set `Timeout: 900` (15 min max)
2. Increase memory: More memory = more CPU power
3. Optimize Claude Code prompt

### Higher Costs Than Expected

**Symptom**: Lambda bill higher than $5/month

**Solutions**:
1. Check invocation count: Should be ~242/month (11/day × 22 days)
2. Check duration: Should be 2-5 minutes per run
3. Verify no unintended invocations
4. Review CloudWatch Logs retention (set to 30 days)

### Environment Variables Not Working

**Symptom**: "Missing environment variable" errors

**Solutions**:
1. Verify all variables are set:
   ```bash
   aws lambda get-function-configuration \
     --function-name email-assistant-processor \
     --query 'Environment'
   ```
2. Check base64 encoding is correct
3. Update variables using `aws lambda update-function-configuration`

## FAQ

### Can I use both GitHub Actions and Lambda simultaneously?

Yes! You can run both during a transition period. Just ensure they're not processing the same emails at the exact same time to avoid duplicate actions.

### How do I rotate the Claude Code OAuth token?

```bash
# Get new token
claude setup-token

# Update Lambda
aws lambda update-function-configuration \
  --function-name email-assistant-processor \
  --environment "Variables={CLAUDE_CODE_OAUTH_TOKEN=new-token,...}"
```

### Can I deploy to multiple AWS regions?

Yes, for redundancy or reduced latency:

```bash
# Deploy to us-west-2
cd lambda
AWS_REGION=us-west-2 ./setup-lambda.sh
```

Just ensure you don't have duplicate schedules processing the same inbox.

### How do I know if Lambda is working?

Check these indicators:
1. EventBridge rule shows "Triggered" count increasing
2. Lambda invocations metric shows hourly invocations
3. CloudWatch Logs show successful processing
4. You receive morning briefs and EOD reports
5. Emails are being labeled and processed

## Next Steps

After successful migration:

1. Monitor for one week
2. Set up CloudWatch alarms for errors
3. Review costs after first full month
4. Optimize timeout and memory based on actual usage
5. Consider adding additional automation features

## Support

For migration help:
- Review [lambda/README.md](README.md) for detailed documentation
- Check AWS Lambda logs first
- Verify all credentials are current
- Test locally with Docker before deploying

---

**Migration checklist:**

- [ ] GitHub Actions working correctly
- [ ] AWS CLI and Docker installed
- [ ] Lambda deployed successfully
- [ ] Test invocation works
- [ ] EventBridge schedule created
- [ ] Logs show successful processing
- [ ] Run both in parallel for 1 week
- [ ] Disable GitHub Actions
- [ ] Set up CloudWatch alarms
- [ ] Monitor costs
