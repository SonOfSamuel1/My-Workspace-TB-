# Toggl Daily Report

**Automated daily performance reports for Toggl Track time tracking**

Send yourself a beautiful HTML email every day with your Toggl Track performance metrics, including total hours tracked, project breakdowns, billable analysis, and week-to-date summaries.

---

## Features

- **Daily Summary**: Total hours tracked and goal achievement percentage
- **Project Breakdown**: Visual breakdown of time by project with percentages
- **Billable Analysis**: Billable vs non-billable hours comparison
- **Week-to-Date Summary**: Running totals and averages for the current week
- **Detailed Entries**: Complete list of all time entries for the day
- **Beautiful HTML Emails**: Professional, responsive email design
- **AWS Lambda Deployment**: Serverless, automated daily delivery

---

## Quick Start

### 1. Prerequisites

- Python 3.9 or higher
- Toggl Track account with API token
- Google account for Gmail integration
- AWS account (for automated deployment)

### 2. Installation

```bash
# Navigate to project directory
cd apps/toggl-daily-report

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

#### Get Toggl API Credentials

1. Log in to [Toggl Track](https://track.toggl.com/)
2. Go to Profile Settings → API Token
3. Copy your API token
4. Find your Workspace ID in the URL when viewing your workspace

#### Get Google Gmail Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download the credentials JSON file
6. Save as `credentials/credentials.json`

#### Set Up Environment Variables

```bash
# Copy example file
cp .env.example .env

# Edit .env with your values
nano .env
```

Required values:
```bash
TOGGL_API_TOKEN=your_toggl_api_token
TOGGL_WORKSPACE_ID=your_workspace_id
REPORT_RECIPIENT_EMAIL=your_email@example.com
```

#### Configure Settings

Edit `config.yaml` to customize:
- Daily goal hours (default: 8.0)
- Report delivery time
- Email recipient
- Projects to exclude/highlight
- Week start day

### 4. First Run (Local Testing)

```bash
# Validate setup
python src/toggl_daily.py --validate

# Generate test report (save to file)
python src/toggl_daily.py --save test_report.html

# Generate and send email
python src/toggl_daily.py --generate
```

On first run, you'll be prompted to authenticate with Google (browser will open automatically). This creates a `token.pickle` file for future use.

---

## Usage

### Command Line

```bash
# Validate configuration and credentials
python src/toggl_daily.py --validate

# Generate and send daily report
python src/toggl_daily.py --generate

# Generate report for specific date
python src/toggl_daily.py --generate --date 2025-11-15

# Save report to file (testing)
python src/toggl_daily.py --save report.html

# Verbose logging
python src/toggl_daily.py --generate --verbose
```

### Python API

```python
from toggl_daily import TogglDailyReport

# Initialize system
system = TogglDailyReport(config_path='config.yaml', env_path='.env')

# Validate setup
if system.validate_setup():
    # Generate and send report
    system.generate_report()
```

---

## AWS Lambda Deployment

### Setup

#### 1. Create Lambda Function

```bash
aws lambda create-function \
    --function-name toggl-daily-report \
    --runtime python3.9 \
    --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
    --handler lambda_handler.handler \
    --timeout 300 \
    --memory-size 512 \
    --zip-file fileb://lambda-deployment.zip
```

#### 2. Store Credentials in Parameter Store

```bash
# Toggl API token (SecureString)
aws ssm put-parameter \
    --name "/toggl-daily-report/toggl-api-token" \
    --value "your_toggl_token" \
    --type SecureString

# Toggl workspace ID
aws ssm put-parameter \
    --name "/toggl-daily-report/toggl-workspace-id" \
    --value "your_workspace_id" \
    --type String

# Recipient email
aws ssm put-parameter \
    --name "/toggl-daily-report/recipient-email" \
    --value "your_email@example.com" \
    --type String

# Google credentials (base64 encoded)
cat credentials/credentials.json | aws ssm put-parameter \
    --name "/toggl-daily-report/credentials" \
    --value file:///dev/stdin \
    --type SecureString

# Google token (base64 encoded)
base64 -i credentials/token.pickle | aws ssm put-parameter \
    --name "/toggl-daily-report/token" \
    --value file:///dev/stdin \
    --type SecureString
```

#### 3. Create EventBridge Schedule

```bash
# Create rule for daily execution at 6:00 PM EST
aws events put-rule \
    --name toggl-daily-report-schedule \
    --schedule-expression "cron(0 23 * * ? *)" \
    --state ENABLED \
    --description "Trigger Toggl daily report at 6 PM EST"

# Add Lambda as target
aws events put-targets \
    --rule toggl-daily-report-schedule \
    --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:ACCOUNT:function:toggl-daily-report"

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
    --function-name toggl-daily-report \
    --statement-id AllowEventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:us-east-1:ACCOUNT:rule/toggl-daily-report-schedule
```

### Deployment Script

```bash
# Deploy using automated script
./scripts/deploy-lambda-zip.sh
```

This script:
1. Cleans previous builds
2. Installs dependencies
3. Packages source code
4. Creates ZIP file
5. Uploads to Lambda

---

## Configuration Reference

### config.yaml

```yaml
report:
  daily_goal_hours: 8.0          # Daily tracking goal
  week_start_day: 0              # 0=Monday, 6=Sunday
  email:
    recipient: "your@email.com"
    subject_template: "Toggl Daily Report - {date}"

schedule:
  delivery_hour: 18              # 24-hour format (6 PM)
  delivery_minute: 0
  timezone: "America/New_York"
  active_days: [0, 1, 2, 3, 4]  # Mon-Fri

toggl:
  exclude_projects: []           # Projects to exclude
  highlight_projects: []         # Projects to highlight
  include_tags: false
  min_duration_minutes: 1

logging:
  level: "INFO"
  file: "logs/daily_report.log"
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TOGGL_API_TOKEN` | Toggl Track API token | Yes |
| `TOGGL_WORKSPACE_ID` | Toggl workspace ID | Yes |
| `REPORT_RECIPIENT_EMAIL` | Email recipient | Yes |
| `GOOGLE_CREDENTIALS_FILE` | Path to credentials.json | Yes |
| `GOOGLE_TOKEN_FILE` | Path to token.pickle | Yes |
| `DAILY_GOAL_HOURS` | Daily goal (overrides config) | No |
| `TIMEZONE` | Timezone for reports | No |
| `LOG_LEVEL` | Logging level | No |

---

## Report Metrics

### 1. Daily Summary
- **Total Hours Tracked**: Sum of all time entries for the day
- **Daily Goal**: Configured target hours (default: 8.0)
- **Goal Achievement**: Percentage and status indicator

### 2. Project Breakdown
- Hours per project with percentage of total
- Visual progress bars
- Sorted by hours (descending)

### 3. Billable Breakdown
- Billable vs non-billable hours
- Percentages of total time
- Side-by-side comparison

### 4. Week-to-Date Summary
- Total hours for current week
- Average hours per day
- Expected hours (based on daily goal)
- Week achievement percentage

### 5. Detailed Entries
- Complete list of time entries
- Start time, duration, project
- Billable indicator
- Tags (if enabled)

---

## Troubleshooting

### Common Issues

#### No time entries found
- Verify you tracked time in Toggl today
- Check workspace ID is correct
- Ensure API token has proper permissions

#### Gmail authentication fails
- Regenerate credentials in Google Cloud Console
- Delete `token.pickle` and re-authenticate
- Check Gmail API is enabled

#### Lambda timeout
- Increase Lambda timeout (current: 300s)
- Check CloudWatch logs for errors
- Verify Parameter Store values

#### Report not sent
- Check spam/junk folder
- Verify recipient email in config
- Review logs for errors

### Logs

Local development:
```bash
tail -f logs/daily_report.log
```

AWS Lambda:
```bash
aws logs tail /aws/lambda/toggl-daily-report --follow
```

---

## Development

### Project Structure

```
toggl-daily-report/
├── src/
│   ├── toggl_daily.py           # Main entry point
│   ├── toggl_service.py         # Toggl API integration
│   ├── daily_report_generator.py # Data aggregation
│   ├── report_formatter.py      # HTML email formatting
│   └── email_sender.py          # Gmail integration
├── scripts/
│   └── deploy-lambda-zip.sh     # Lambda deployment
├── lambda_handler.py            # AWS Lambda handler
├── config.yaml                  # Configuration
├── .env.example                 # Environment template
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

### Testing

```bash
# Run with test data
python src/toggl_daily.py --save test.html --date 2025-11-15

# Validate all credentials
python src/toggl_daily.py --validate

# Test Toggl service
python src/toggl_service.py

# Test report generator
python src/daily_report_generator.py

# Test formatter
python src/report_formatter.py
```

---

## Architecture

### Data Flow

```
Toggl API
    ↓
TogglService (fetch time entries)
    ↓
DailyReportGenerator (aggregate metrics)
    ↓
ReportFormatter (generate HTML)
    ↓
EmailSender (send via Gmail)
```

### AWS Lambda Flow

```
EventBridge (6 PM daily)
    ↓
Lambda Function
    ↓
Parameter Store (load credentials)
    ↓
Generate Report
    ↓
Send Email
```

---

## Customization

### Change Report Time

Edit `config.yaml`:
```yaml
schedule:
  delivery_hour: 20  # 8 PM instead of 6 PM
```

Update EventBridge cron:
```bash
# For 8 PM EST (convert to UTC: 8 PM + 5 hours = 1 AM UTC)
aws events put-rule \
    --name toggl-daily-report-schedule \
    --schedule-expression "cron(0 1 * * ? *)"
```

### Exclude Weekends

Edit `config.yaml`:
```yaml
schedule:
  active_days: [0, 1, 2, 3, 4]  # Monday-Friday only
```

### Custom Goal Hours

Edit `config.yaml`:
```yaml
report:
  daily_goal_hours: 6.5  # Part-time schedule
```

### Email Styling

Edit `src/report_formatter.py` to customize:
- Colors and fonts
- Layout and sections
- Metric calculations
- Visual elements

---

## Cost Estimate (AWS)

- **Lambda**: ~$0.20/month (free tier eligible)
- **EventBridge**: Free
- **Parameter Store**: Free (standard parameters)
- **CloudWatch Logs**: ~$0.50/month

**Total: < $1/month** (likely free with AWS Free Tier)

---

## Support

### Issues
- Check logs first
- Review configuration
- Verify credentials
- See troubleshooting section

### Resources
- [Toggl Track API Docs](https://developers.track.toggl.com/)
- [Gmail API Guide](https://developers.google.com/gmail/api)
- [AWS Lambda Docs](https://docs.aws.amazon.com/lambda/)

---

## License

See repository root for license information.

## Author

**Terrance Brandon**
- GitHub: [@SonOfSamuel1](https://github.com/SonOfSamuel1)
- Email: terrance@goodportion.org

---

**Last Updated:** 2025-11-17
**Version:** 1.0.0
