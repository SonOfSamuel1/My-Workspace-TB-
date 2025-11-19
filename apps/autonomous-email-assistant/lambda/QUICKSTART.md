# AWS Lambda Deployment - Quick Start

Get your email assistant running on AWS Lambda in under 10 minutes.

## Prerequisites Check

```bash
# Check AWS CLI
aws --version
# If missing: https://aws.amazon.com/cli/

# Check Docker
docker --version
# If missing: https://docs.docker.com/get-docker/

# Check AWS credentials
aws sts get-caller-identity
# If error: aws configure
```

## One-Command Deployment

```bash
cd lambda
./setup-lambda.sh
```

The script will prompt for:
1. AWS Region (default: us-east-1)
2. Claude Code OAuth token
3. Twilio credentials (optional)
4. Escalation phone number

Then it will automatically:
- Create ECR repository
- Build Docker image
- Push to ECR
- Create IAM role
- Deploy Lambda function
- Set up hourly schedule (7 AM - 5 PM EST)

## Test It

```bash
# Manual test
aws lambda invoke \
  --function-name email-assistant-processor \
  response.json

cat response.json

# Watch logs
aws logs tail /aws/lambda/email-assistant-processor --follow
```

## Next Steps

1. Wait for the next scheduled run (check the hour)
2. Monitor CloudWatch Logs for processing
3. Verify morning brief arrives at 7 AM EST
4. Check EOD report at 5 PM EST

## Troubleshooting

**"AccessDenied" errors?**
- Ensure your AWS user has Lambda, ECR, IAM, and EventBridge permissions

**Docker build fails?**
- Ensure Docker is running: `docker ps`
- Increase Docker memory in Docker Desktop preferences

**Function times out?**
- Increase memory in template.yaml (more memory = more CPU)
- Increase timeout (max 15 minutes)

## Update Function

```bash
# Edit code
vi lambda/index.js

# Redeploy
cd lambda
./setup-lambda.sh
```

## Cost

Expected monthly cost: **$2-5**

- Lambda compute: ~$1.20
- CloudWatch Logs: ~$0.50
- Data transfer: Minimal

## Documentation

- Full guide: [README.md](README.md)
- Migration from GitHub Actions: [MIGRATION-GUIDE.md](MIGRATION-GUIDE.md)
- Project overview: [../README.md](../README.md)

## Support

Issues? Check:
1. CloudWatch Logs first
2. Environment variables are set
3. Claude Code token is valid
4. Gmail credentials are correct

---

**That's it!** Your email assistant is now running on AWS Lambda.
