# Brandon Family Calendar Reporting System - AWS Lambda Version

**Automated weekly calendar report system powered by AWS Lambda that generates and emails comprehensive calendar summaries.**

[![Platform](https://img.shields.io/badge/platform-AWS%20Lambda-orange.svg)]()
[![Runtime](https://img.shields.io/badge/runtime-Node.js%2018.x-green.svg)]()
[![Cost](https://img.shields.io/badge/cost-free-brightgreen.svg)]()

---

## 🚀 What is This?

This is an **AWS Lambda** version of the Brandon Family Calendar Reporting System. It replaces the original Google Apps Script version with a serverless Node.js function that:

- 🔄 Runs automatically every Saturday at 7:00 PM ET
- 📅 Fetches events from Google Calendar via API
- 📧 Sends beautifully formatted email reports via AWS SES
- 💰 Costs practically $0/month to run
- ⚡ Fully serverless - no servers to manage

---

## 📊 Features

### What You Get Every Week

**Section 1: Unique Events (Next 90 Days)**
- All upcoming unique events from your main calendar
- Trips, reservations, special activities

**Section 2: Medical Appointments (Next 12 Months)**
- Auto-detected medical appointments across ALL calendars
- Dentist, doctor visits, health checkups

**Section 3: Birthdays (Next 60 Days)**
- Upcoming birthdays so you never miss a celebration

**Section 4: Anniversaries (Next 60 Days)**
- Important anniversaries and milestones

---

## 🆚 Why AWS Lambda vs Google Apps Script?

| Feature | AWS Lambda | Google Apps Script |
|---------|------------|-------------------|
| **Platform** | AWS (your infrastructure) | Google (locked in) |
| **Cost** | Free tier: 1M requests/month | Free |
| **Flexibility** | Full Node.js ecosystem | Limited to Apps Script |
| **Monitoring** | CloudWatch, X-Ray | Basic logs only |
| **Testing** | Local testing with Node.js | Must run in Google environment |
| **CI/CD** | Easy integration | Limited |
| **Email Service** | AWS SES (scalable) | Gmail (quotas) |

---

## 📁 Project Structure

```
.
├── index.js                      # Main Lambda function
├── package.json                  # Node.js dependencies
├── serverless.yml                # Serverless Framework config
├── .env.example                  # Environment variables template
├── test-local.js                 # Local testing script
├── AWS-LAMBDA-DEPLOYMENT.md      # Complete deployment guide
├── README-AWS-LAMBDA.md          # This file
└── calendar-report-automation.gs # Original Google Apps Script (reference)
```

---

## ⚡ Quick Start

### Prerequisites

- AWS Account
- Node.js 18.x or later
- Google Cloud Project with Calendar API enabled
- Google Service Account

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Test Locally

```bash
node test-local.js
```

### 4. Deploy to AWS

**Option A: Serverless Framework (Recommended)**
```bash
npm install -g serverless
serverless deploy
```

**Option B: AWS CLI**
```bash
# Create deployment package
npm run package

# Upload to Lambda (see AWS-LAMBDA-DEPLOYMENT.md for details)
aws lambda create-function ...
```

**Option C: AWS Console**
- Upload `function.zip` manually
- Configure environment variables
- Set up EventBridge schedule

---

## 📖 Full Documentation

For complete setup instructions, see:
- **[AWS-LAMBDA-DEPLOYMENT.md](AWS-LAMBDA-DEPLOYMENT.md)** - Complete deployment guide
- **[CALENDAR-SETUP.md](CALENDAR-SETUP.md)** - Google Calendar configuration

---

## 🔧 Configuration

All configuration is done via environment variables:

```bash
# Google Calendar API
GOOGLE_CLIENT_EMAIL=your-service-account@project.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"

# Calendar IDs
UNIQUE_EVENTS_CALENDAR_ID=your-calendar-id@group.calendar.google.com
BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID=your-calendar-id@group.calendar.google.com

# Email Configuration (must be verified in AWS SES)
EMAIL_TO=recipient@example.com
EMAIL_FROM=sender@example.com

# AWS & Timezone
AWS_REGION=us-east-1
TIMEZONE=America/New_York
```

---

## 🧪 Testing

### Local Testing

```bash
# With .env file
node test-local.js
```

### Test Deployed Function

```bash
# Serverless Framework
serverless invoke -f generateReport

# AWS CLI
aws lambda invoke --function-name calendar-report --payload '{}' response.json
```

---

## 📊 Monitoring & Logs

### View Logs

```bash
# Serverless Framework
serverless logs -f generateReport --tail

# AWS CLI
aws logs tail /aws/lambda/calendar-report --follow
```

### AWS Console
- Go to Lambda > Monitor > View logs in CloudWatch

---

## 🎨 Customization

### Change Schedule

Edit `serverless.yml`:

```yaml
events:
  - schedule:
      # Daily at 9am ET
      rate: cron(0 13 * * ? *)
```

### Adjust Time Windows

Edit `index.js`:

```javascript
// Unique Events: 120 days instead of 90
endDate.setDate(endDate.getDate() + 120);

// Medical: 6 months instead of 12
endDate.setMonth(endDate.getMonth() + 6);
```

### Add Medical Keywords

Edit `index.js`:

```javascript
const MEDICAL_KEYWORDS = [
  // ... existing keywords
  'veterinarian', 'vet',
  'therapy', 'counseling'
];
```

---

## 💰 Cost Breakdown

**AWS Lambda:**
- Free tier: 1M requests/month
- This app: ~4 requests/month
- Cost: **$0.00**

**AWS SES:**
- $0.10 per 1,000 emails
- This app: ~4 emails/month
- Cost: **$0.00**

**Total: ~$0.00/month** ✅

---

## 🐛 Troubleshooting

### No Email Received

1. Check Lambda logs: `serverless logs -f generateReport`
2. Verify SES email addresses are verified
3. Check spam folder

### "Calendar not found" Error

1. Verify calendar IDs in Google Calendar settings
2. Share calendar with service account email
3. Grant "See all event details" permission

### "Invalid credentials" Error

1. Check private key format (must include `\n` line breaks)
2. Verify service account email
3. Ensure Calendar API is enabled

See [AWS-LAMBDA-DEPLOYMENT.md](AWS-LAMBDA-DEPLOYMENT.md) for detailed troubleshooting.

---

## 🔒 Security

- ✅ Service account with limited permissions
- ✅ Environment variables for credentials
- ✅ No hardcoded secrets
- ✅ AWS IAM for access control
- ✅ SES in sandbox mode by default

**Never commit:**
- `.env` file
- Service account JSON files
- Private keys

---

## 🚀 Deployment Options

### Serverless Framework (Recommended)

**Pros:**
- Simple deployment: `serverless deploy`
- Easy rollbacks
- Great for CI/CD
- Manages everything automatically

**Cons:**
- Requires Serverless Framework installation

### AWS CLI

**Pros:**
- No additional tools needed
- Direct AWS control
- Good for automation

**Cons:**
- More manual steps
- Need to manage IAM roles separately

### AWS Console

**Pros:**
- Visual interface
- Good for learning
- No CLI required

**Cons:**
- Not repeatable
- Manual process
- Hard to version control

---

## 🔄 Updates

### Update Code

1. Make changes to `index.js`
2. Test locally: `node test-local.js`
3. Redeploy: `serverless deploy`

### Update Dependencies

```bash
npm update
npm audit fix
serverless deploy
```

---

## 📚 Architecture

```
┌─────────────────┐
│  EventBridge    │  Triggers every Saturday 7pm ET
│  (CloudWatch)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Lambda         │  Executes Node.js function
│  Function       │
└────────┬────────┘
         │
         ├──────────────────┐
         │                  │
         ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│  Google         │  │  AWS SES        │
│  Calendar API   │  │  (Email)        │
└─────────────────┘  └─────────────────┘
```

---

## 🎯 Use Cases

Perfect for:

✅ **Family Organization** - Keep everyone informed
✅ **Health Management** - Never miss medical appointments
✅ **Event Planning** - See upcoming trips and reservations
✅ **Weekly Reviews** - Understand what's coming up
✅ **Enterprise Deployments** - Scale to multiple teams/calendars

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Test thoroughly (run `node test-local.js`)
4. Submit a pull request

---

## 📝 License

MIT License - Free to use and modify

---

## 🆘 Support

1. **Read the docs**: [AWS-LAMBDA-DEPLOYMENT.md](AWS-LAMBDA-DEPLOYMENT.md)
2. **Check logs**: `serverless logs -f generateReport`
3. **Review troubleshooting**: See deployment guide
4. **Test locally**: `node test-local.js` for faster debugging

---

## 📞 Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS SES Documentation](https://docs.aws.amazon.com/ses/)
- [Google Calendar API](https://developers.google.com/calendar/api)
- [Serverless Framework](https://www.serverless.com/framework/docs)
- [Node.js googleapis](https://github.com/googleapis/google-api-nodejs-client)

---

## 🎉 Get Started

Ready to deploy? Follow these steps:

1. **Read**: [AWS-LAMBDA-DEPLOYMENT.md](AWS-LAMBDA-DEPLOYMENT.md)
2. **Configure**: Set up Google Service Account and AWS SES
3. **Test**: Run `node test-local.js`
4. **Deploy**: Run `serverless deploy`
5. **Enjoy**: Receive automated reports every Saturday!

**Happy automating!** 📅✨
