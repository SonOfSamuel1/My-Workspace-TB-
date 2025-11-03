# Next Steps - Love Brittany Automation Deployment

**Date:** November 2, 2025
**Status:** Ready for AWS deployment
**Repository:** https://github.com/SonOfSamuel1/App-Personal-Love-Brittany-Reporting

---

## 📋 What We Accomplished Today

### ✅ Completed Items:

1. **Fixed automation bugs:**
   - Fixed Toggl API parameter passing issue
   - Added date validation to handle placeholder dates (YYYY-MM-DD)
   - Successfully ran automation and sent test report

2. **Set up AWS Lambda infrastructure:**
   - Created Lambda handler with Parameter Store integration
   - Built Docker container configuration
   - Created deployment scripts for AWS
   - Configured EventBridge scheduling (Sunday 4:00 AM EST)
   - Migrated from Secrets Manager to Parameter Store (saves $24/year!)

3. **Created comprehensive documentation:**
   - AWS_DEPLOYMENT.md with full deployment guide
   - Cost estimates (~$0.03/month)
   - Troubleshooting guide

4. **Pushed all changes to GitHub:**
   - Commit: `feec322` - "Add AWS Lambda deployment infrastructure"
   - All deployment scripts are ready to use

---

## 🚀 What's Left to Do (On Your Other Computer)

### Step 1: Clone the Repository

```bash
cd ~/Desktop
git clone https://github.com/SonOfSamuel1/App-Personal-Love-Brittany-Reporting.git
cd App-Personal-Love-Brittany-Reporting
```

### Step 2: Install Prerequisites

```bash
# Install AWS CLI (if not already installed)
brew install awscli

# Install Docker Desktop (if not already installed)
# Download from: https://www.docker.com/products/docker-desktop

# Verify installations
aws --version
docker --version
```

### Step 3: Configure AWS Credentials

```bash
aws configure
```

**You'll need:**
- AWS Access Key ID
- AWS Secret Access Key
- Default region: `us-east-1`
- Default output format: `json`

**To get AWS credentials:**
1. Go to https://console.aws.amazon.com/iam/
2. Click "Users" → Your username → "Security credentials"
3. Click "Create access key"
4. Choose "Command Line Interface (CLI)"
5. Copy the Access Key ID and Secret Access Key

### Step 4: Set Up Environment Variables

```bash
# Create .env file with your credentials
cp .env.example .env
nano .env
```

**Required variables in `.env`:**
```bash
TOGGL_API_TOKEN=your_toggl_api_token_here
TOGGL_WORKSPACE_ID=your_workspace_id_here
RECIPIENT_EMAIL=terrance@goodportion.org
AWS_REGION=us-east-1
```

### Step 5: Copy Credentials to Project

Make sure you have these credential files in the `credentials/` directory:

```bash
mkdir -p credentials

# Copy your existing credential files:
credentials/
├── calendar_credentials.json
├── calendar_token.json
├── gmail_credentials.json
└── gmail_token.json
```

**Where to find these files:**
- They should be on your current computer in the `credentials/` folder
- You can transfer them via email, USB, or secure cloud storage
- **IMPORTANT:** These files contain OAuth tokens - keep them secure!

### Step 6: Deploy to AWS

```bash
# Make scripts executable (should already be done, but just in case)
chmod +x scripts/*.sh

# Run the deployment
./scripts/deploy-to-aws.sh
```

This script will:
1. Create IAM role with permissions
2. Create ECR repository
3. Build Docker image
4. Push image to ECR
5. Create Lambda function
6. Set up EventBridge schedule (Sunday 4:00 AM EST)

**Expected time:** 5-10 minutes

### Step 7: Upload Credentials to AWS

```bash
./scripts/setup-parameters.sh
```

This uploads your credentials to AWS Parameter Store (FREE tier).

### Step 8: Test the Deployment

```bash
./scripts/test-lambda.sh
```

This manually triggers the Lambda function to verify it works.

### Step 9: Monitor the First Run

```bash
# Watch logs in real-time
aws logs tail /aws/lambda/love-brittany-weekly-report --follow
```

The automation will run automatically every **Sunday at 4:00 AM EST**.

---

## 📁 Important Files Reference

| File | Purpose |
|------|---------|
| `AWS_DEPLOYMENT.md` | Complete deployment guide and troubleshooting |
| `lambda_handler.py` | Lambda entry point |
| `Dockerfile.lambda` | Container configuration |
| `config.yaml` | Automation settings (schedule, tracking periods, etc.) |
| `scripts/deploy-to-aws.sh` | Main deployment script |
| `scripts/setup-parameters.sh` | Upload credentials to Parameter Store |
| `scripts/test-lambda.sh` | Test the Lambda function |
| `scripts/update-lambda-function.sh` | Update after code changes |

---

## 💰 Cost Summary

**Monthly Cost: ~$0.03** (~$0.36/year)

| Service | Cost |
|---------|------|
| Lambda | $0.00-0.01 (free tier) |
| Parameter Store | $0.00 (FREE) |
| ECR Storage | $0.01-0.02 (~150 MB) |
| CloudWatch Logs | $0.00-0.01 (free tier) |

---

## 🔧 Troubleshooting Common Issues

### Issue: "aws: command not found"
**Solution:** Install AWS CLI: `brew install awscli`

### Issue: "Docker daemon is not running"
**Solution:** Start Docker Desktop application

### Issue: "Parameter not found"
**Solution:** Run `./scripts/setup-parameters.sh` to upload credentials

### Issue: "Permission denied" errors
**Solution:** IAM role may need time to propagate. Wait 1-2 minutes and retry.

### Issue: Lambda function times out
**Solution:** Check CloudWatch Logs for errors:
```bash
aws logs tail /aws/lambda/love-brittany-weekly-report --since 1h
```

---

## 📞 Support Resources

- **Full Deployment Guide:** See `AWS_DEPLOYMENT.md`
- **AWS Lambda Docs:** https://docs.aws.amazon.com/lambda/
- **Parameter Store Docs:** https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html
- **GitHub Repository:** https://github.com/SonOfSamuel1/App-Personal-Love-Brittany-Reporting

---

## 🎯 Success Criteria

You'll know the deployment is successful when:

✅ Deployment script completes without errors
✅ Test Lambda invocation returns 200 status code
✅ You receive a test email report
✅ CloudWatch Logs show successful execution
✅ EventBridge rule is active (check in AWS Console)

---

## 📝 Notes

- The automation runs **every Sunday at 4:00 AM EST**
- First scheduled run will be this coming Sunday
- You can manually trigger it anytime with: `./scripts/test-lambda.sh`
- Update the code anytime with: `./scripts/update-lambda-function.sh`
- Cost stays minimal (~$0.03/month) regardless of usage

---

## 🚨 Important Reminders

1. **Never commit credential files** - They're in `.gitignore` for a reason
2. **Keep `.env` file private** - Contains API keys
3. **AWS credentials are sensitive** - Store securely
4. **Parameter Store is FREE** - No per-parameter charges (Standard tier)
5. **Monitor costs** - Check AWS billing dashboard monthly

---

Good luck with the deployment! The hardest part is done - you just need to run the scripts now. 🎉
