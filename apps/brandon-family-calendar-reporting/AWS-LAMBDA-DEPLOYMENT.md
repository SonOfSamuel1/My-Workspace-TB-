# AWS Lambda Deployment Guide

Complete guide to deploy the Calendar Report Automation to AWS Lambda.

---

## 📋 Prerequisites

Before you begin, ensure you have:

- ✅ AWS Account with appropriate permissions
- ✅ Node.js 18.x or later installed
- ✅ AWS CLI installed and configured
- ✅ Google Cloud Project with Calendar API enabled
- ✅ Google Service Account with Calendar access

---

## 🚀 Quick Start

### Step 1: Set Up Google Calendar API

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing

2. **Enable Google Calendar API**
   - In your project, go to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable"

3. **Create Service Account**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in service account details
   - Click "Create and Continue"
   - Skip granting roles (optional)
   - Click "Done"

4. **Create Service Account Key**
   - Click on your newly created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create New Key"
   - Choose "JSON" format
   - Download the JSON file (keep it secure!)

5. **Grant Calendar Access**
   - Open Google Calendar
   - Go to Calendar Settings
   - Find your calendars and click "Share with specific people"
   - Add your service account email (found in the JSON file)
   - Grant "See all event details" permission

### Step 2: Set Up AWS SES (Email Service)

1. **Verify Email Addresses**
   - Go to AWS SES Console
   - Click "Verified identities"
   - Click "Create identity"
   - Choose "Email address"
   - Enter the email you want to send FROM
   - Verify it via the confirmation email
   - Repeat for the recipient email (TO address)

2. **Request Production Access (Optional)**
   - By default, SES is in sandbox mode (can only send to verified emails)
   - To send to any email, request production access:
     - Go to SES Console > "Account dashboard"
     - Click "Request production access"
     - Fill out the form

3. **Note Your Region**
   - Remember which AWS region you're using for SES (e.g., us-east-1)

### Step 3: Install Dependencies

```bash
npm install
```

### Step 4: Configure Environment Variables

1. **Create .env file for local testing**
   ```bash
   cp .env.example .env
   ```

2. **Edit .env with your values**
   ```bash
   # From Google Service Account JSON file:
   GOOGLE_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
   GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour key here\n-----END PRIVATE KEY-----\n"

   # From Google Calendar settings:
   UNIQUE_EVENTS_CALENDAR_ID=your-calendar-id@group.calendar.google.com
   BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID=your-calendar-id@group.calendar.google.com

   # Your email addresses (must be verified in AWS SES):
   EMAIL_TO=recipient@example.com
   EMAIL_FROM=sender@example.com

   # AWS Configuration:
   AWS_REGION=us-east-1
   TIMEZONE=America/New_York
   ```

3. **Find Calendar IDs**
   - Open Google Calendar
   - Click on the calendar you want to use
   - Click the 3 dots > "Settings and sharing"
   - Scroll down to "Integrate calendar"
   - Copy the "Calendar ID"

### Step 5: Test Locally

```bash
node test-local.js
```

If successful, you should receive an email with your calendar report!

---

## 📦 Deployment Options

### Option A: Deploy with Serverless Framework (Recommended)

1. **Install Serverless Framework**
   ```bash
   npm install -g serverless
   ```

2. **Configure AWS Credentials**
   ```bash
   serverless config credentials --provider aws --key YOUR_ACCESS_KEY --secret YOUR_SECRET_KEY
   ```

3. **Set Environment Variables**

   Export environment variables before deploying:
   ```bash
   export GOOGLE_CLIENT_EMAIL="your-service-account@your-project.iam.gserviceaccount.com"
   export GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour key\n-----END PRIVATE KEY-----\n"
   export UNIQUE_EVENTS_CALENDAR_ID="your-calendar-id@group.calendar.google.com"
   export BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID="your-calendar-id@group.calendar.google.com"
   export EMAIL_TO="recipient@example.com"
   export EMAIL_FROM="sender@example.com"
   export AWS_REGION="us-east-1"
   export TIMEZONE="America/New_York"
   ```

4. **Deploy**
   ```bash
   serverless deploy
   ```

5. **Test the deployed function**
   ```bash
   serverless invoke -f generateReport
   ```

6. **View logs**
   ```bash
   serverless logs -f generateReport --tail
   ```

### Option B: Deploy with AWS CLI

1. **Create deployment package**
   ```bash
   npm install --production
   zip -r function.zip . -x '*.git*' 'test-local.js' '.env*'
   ```

2. **Create IAM Role**

   Create a file named `trust-policy.json`:
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

   Create the role:
   ```bash
   aws iam create-role \
     --role-name calendar-report-lambda-role \
     --assume-role-policy-document file://trust-policy.json
   ```

   Attach policies:
   ```bash
   # Basic Lambda execution
   aws iam attach-role-policy \
     --role-name calendar-report-lambda-role \
     --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

   # SES sending permission
   aws iam attach-role-policy \
     --role-name calendar-report-lambda-role \
     --policy-arn arn:aws:iam::aws:policy/AmazonSESFullAccess
   ```

3. **Create Lambda Function**
   ```bash
   aws lambda create-function \
     --function-name calendar-report \
     --runtime nodejs18.x \
     --role arn:aws:iam::YOUR_ACCOUNT_ID:role/calendar-report-lambda-role \
     --handler index.handler \
     --zip-file fileb://function.zip \
     --timeout 60 \
     --memory-size 512 \
     --environment Variables="{
       GOOGLE_CLIENT_EMAIL=your-service-account@project.iam.gserviceaccount.com,
       GOOGLE_PRIVATE_KEY=your-private-key,
       UNIQUE_EVENTS_CALENDAR_ID=your-calendar-id@group.calendar.google.com,
       BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID=your-calendar-id@group.calendar.google.com,
       EMAIL_TO=recipient@example.com,
       EMAIL_FROM=sender@example.com,
       AWS_REGION=us-east-1,
       TIMEZONE=America/New_York
     }"
   ```

4. **Create EventBridge Rule (Schedule)**
   ```bash
   # Create rule for every Saturday at 7pm ET (11pm UTC)
   aws events put-rule \
     --name calendar-report-weekly \
     --schedule-expression "cron(0 23 ? * SAT *)"

   # Give EventBridge permission to invoke Lambda
   aws lambda add-permission \
     --function-name calendar-report \
     --statement-id calendar-report-weekly \
     --action lambda:InvokeFunction \
     --principal events.amazonaws.com \
     --source-arn arn:aws:events:us-east-1:YOUR_ACCOUNT_ID:rule/calendar-report-weekly

   # Add Lambda as target
   aws events put-targets \
     --rule calendar-report-weekly \
     --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:calendar-report"
   ```

5. **Test the function**
   ```bash
   aws lambda invoke \
     --function-name calendar-report \
     --payload '{}' \
     response.json

   cat response.json
   ```

### Option C: Deploy via AWS Console (Manual)

1. **Create the function**
   - Go to AWS Lambda Console
   - Click "Create function"
   - Choose "Author from scratch"
   - Function name: `calendar-report`
   - Runtime: Node.js 18.x
   - Click "Create function"

2. **Upload code**
   - Create deployment package: `npm install --production && zip -r function.zip .`
   - In Lambda console, go to "Code" tab
   - Click "Upload from" > ".zip file"
   - Upload your function.zip

3. **Configure environment variables**
   - Go to "Configuration" > "Environment variables"
   - Add all required variables from .env.example

4. **Adjust settings**
   - Go to "Configuration" > "General configuration"
   - Set Timeout to 60 seconds
   - Set Memory to 512 MB

5. **Add SES permissions**
   - Go to "Configuration" > "Permissions"
   - Click on the role name
   - Add "AmazonSESFullAccess" policy

6. **Create schedule**
   - Go to "Configuration" > "Triggers"
   - Click "Add trigger"
   - Select "EventBridge (CloudWatch Events)"
   - Create new rule
   - Schedule expression: `cron(0 23 ? * SAT *)`
   - Save

---

## 🧪 Testing

### Test Locally
```bash
node test-local.js
```

### Test Deployed Function

**With Serverless:**
```bash
serverless invoke -f generateReport
```

**With AWS CLI:**
```bash
aws lambda invoke \
  --function-name calendar-report \
  --payload '{}' \
  response.json && cat response.json
```

**In AWS Console:**
- Go to Lambda function
- Click "Test" tab
- Create test event (use empty JSON: `{}`)
- Click "Test"

---

## 📊 Monitoring

### View Logs

**With Serverless:**
```bash
serverless logs -f generateReport --tail
```

**With AWS CLI:**
```bash
aws logs tail /aws/lambda/calendar-report --follow
```

**In AWS Console:**
- Go to Lambda function
- Click "Monitor" tab
- Click "View logs in CloudWatch"

### Set Up Alerts

1. **Create SNS Topic**
   ```bash
   aws sns create-topic --name calendar-report-alerts
   ```

2. **Subscribe to topic**
   ```bash
   aws sns subscribe \
     --topic-arn arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:calendar-report-alerts \
     --protocol email \
     --notification-endpoint your-email@example.com
   ```

3. **Create CloudWatch Alarm**
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name calendar-report-errors \
     --alarm-description "Alert on Lambda errors" \
     --metric-name Errors \
     --namespace AWS/Lambda \
     --statistic Sum \
     --period 300 \
     --evaluation-periods 1 \
     --threshold 1 \
     --comparison-operator GreaterThanOrEqualToThreshold \
     --dimensions Name=FunctionName,Value=calendar-report \
     --alarm-actions arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:calendar-report-alerts
   ```

---

## 🔧 Customization

### Change Schedule

Edit the cron expression in `serverless.yml`:

```yaml
events:
  - schedule:
      # Every Sunday at 9am ET (1pm UTC)
      rate: cron(0 13 ? * SUN *)
```

Common schedules:
- Daily at 9am ET: `cron(0 13 * * ? *)`
- Weekly Monday 7pm ET: `cron(0 23 ? * MON *)`
- Bi-weekly Saturday 7pm ET: `cron(0 23 ? * SAT#2,SAT#4 *)`

### Adjust Time Windows

Edit `index.js`:

```javascript
// Change unique events to 120 days
endDate.setDate(endDate.getDate() + 120);

// Change medical to 6 months
endDate.setMonth(endDate.getMonth() + 6);
```

### Add Medical Keywords

Edit `index.js`:

```javascript
const MEDICAL_KEYWORDS = [
  // ... existing keywords
  'veterinarian', 'vet',  // Pet care
  'therapy', 'counseling'  // Mental health
];
```

---

## 💰 Cost Estimate

**AWS Lambda:**
- Free tier: 1M requests/month + 400,000 GB-seconds
- This function: ~4 requests/month (weekly)
- Cost: **$0.00** (well within free tier)

**AWS SES:**
- $0.10 per 1,000 emails
- This function: ~4 emails/month
- Cost: **$0.00** (negligible)

**Total monthly cost: ~$0.00**

---

## 🐛 Troubleshooting

### No Email Received

1. **Check Lambda logs**
   ```bash
   serverless logs -f generateReport --tail
   ```

2. **Verify SES email addresses**
   - Both FROM and TO must be verified in SES
   - Check SES Console > "Verified identities"

3. **Check spam folder**

### "Calendar not found" Error

1. **Verify calendar IDs**
   - Go to Google Calendar settings
   - Copy the exact Calendar ID

2. **Check service account permissions**
   - Calendar must be shared with service account email
   - Grant "See all event details" permission

### "Invalid credentials" Error

1. **Check private key format**
   - Must include `\n` for line breaks
   - Must be wrapped in quotes
   - Example: `"-----BEGIN PRIVATE KEY-----\nYour key\n-----END PRIVATE KEY-----\n"`

2. **Verify service account email**

### Empty Sections

- **Medical:** Add custom keywords matching your appointment names
- **Birthdays:** Event titles must contain "birthday"
- **Anniversaries:** Event titles must contain "anniversary"

---

## 🔒 Security Best Practices

1. **Never commit credentials**
   - .env file is in .gitignore
   - Never commit service account JSON

2. **Use AWS Secrets Manager** (Optional but recommended)
   ```bash
   # Store private key
   aws secretsmanager create-secret \
     --name calendar-report/google-private-key \
     --secret-string "your-private-key"

   # Update Lambda to fetch from Secrets Manager
   ```

3. **Limit IAM permissions**
   - Only grant necessary SES permissions
   - Use least-privilege principle

4. **Rotate service account keys**
   - Regularly create new keys
   - Delete old keys

---

## 🔄 Updates and Maintenance

### Update the Function

1. **Make changes to code**

2. **Test locally**
   ```bash
   node test-local.js
   ```

3. **Redeploy**
   ```bash
   serverless deploy
   ```

### Update Dependencies

```bash
npm update
npm audit fix
serverless deploy
```

---

## 📞 Support

### Common Issues

- **Timeout errors:** Increase timeout in serverless.yml or Lambda console
- **Out of memory:** Increase memory in serverless.yml or Lambda console
- **Rate limiting:** Google Calendar API has quotas (10,000 requests/day per project)

### Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS SES Documentation](https://docs.aws.amazon.com/ses/)
- [Google Calendar API Documentation](https://developers.google.com/calendar/api)
- [Serverless Framework Documentation](https://www.serverless.com/framework/docs)

---

## 🎉 Success!

Once deployed, you'll receive automated calendar reports every Saturday at 7pm ET!

The Lambda function will:
- ✅ Run automatically on schedule
- ✅ Fetch events from your calendars
- ✅ Generate beautiful HTML reports
- ✅ Send emails via AWS SES
- ✅ Cost practically nothing to run

**Enjoy your automated calendar reports!** 📅✨
