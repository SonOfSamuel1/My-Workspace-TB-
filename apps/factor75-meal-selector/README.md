# Factor 75 Meal Selector

Automate your weekly Factor 75 meal selection with email-based interaction.

## How It Works

1. **Weekly Email**: Receive a beautifully formatted email with all available
   meals (images, nutrition info, descriptions)
2. **Simple Reply**: Reply to the email with your meal numbers (e.g.,
   `1, 3, 5, 7, 9, 11, 13, 15, 17, 19`)
3. **Automatic Submission**: Your selections are automatically submitted to
   Factor 75

## Features

- Beautiful HTML emails with meal images and nutrition info
- Simple reply-based selection (just numbers!)
- Support for duplicate meals (`1, 1, 3, 5, 5, ...`)
- Deadline reminders
- Confirmation emails after submission
- AWS Lambda ready for fully automated operation

## Quick Start

### 1. Install Dependencies

```bash
cd apps/factor75-meal-selector
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```
FACTOR75_EMAIL=your-factor75-email@example.com
FACTOR75_PASSWORD=your-factor75-password
USER_EMAIL=your-email@example.com
SES_SENDER_EMAIL=verified-ses-sender@yourdomain.com
```

### 3. Set Up Gmail API (for reply polling)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download as `credentials.json` and place in `credentials/` directory

### 4. Validate Setup

```bash
python src/factor75_main.py --validate
```

### 5. Send Test Email

```bash
python src/factor75_main.py --test-email
```

## Usage

### Command Line Options

```bash
# Validate configuration
python src/factor75_main.py --validate

# Send test email with mock data
python src/factor75_main.py --test-email

# Scrape meals and send selection email
python src/factor75_main.py --scrape

# Scrape without sending email (save to file)
python src/factor75_main.py --scrape --no-email

# Check for email replies
python src/factor75_main.py --check-replies

# Submit pending selections
python src/factor75_main.py --submit

# Dry run (don't make changes)
python src/factor75_main.py --submit --dry-run
```

### Using with Claude Code + Playwright MCP

The actual Factor 75 website scraping is designed to work with Claude Code's
Playwright MCP:

1. Start the meal selection workflow:

   ```bash
   python src/factor75_main.py --scrape --mock-data
   ```

2. For real scraping, ask Claude Code to:
   - Navigate to <https://www.factor75.com/login>
   - Enter your credentials
   - Navigate to the menu page
   - Extract the meal data

## Email Format

When you receive the selection email, simply reply with meal numbers:

**Basic selection (10 meals):**

```
1, 3, 5, 7, 9, 11, 13, 15, 17, 19
```

**With duplicates:**

```
1, 1, 3, 5, 5, 7, 9, 11, 13, 15
```

(This selects meal #1 twice and meal #5 twice)

## Configuration

Edit `config.yaml` for advanced settings:

```yaml
factor75:
  meal_count: 10 # Your plan's meal count

email:
  subject_template: "Factor 75 Meal Selection - Week of {date}"
  include_images: true

schedule:
  hours_before_deadline: 48
  reply_check_interval: 15 # minutes
```

## AWS Lambda Deployment

### Prerequisites

- AWS CLI configured
- AWS SES sender email verified
- Parameter Store values set up

### Set Up Parameter Store

```bash
aws ssm put-parameter \
  --name "/factor75-selector/factor75-email" \
  --value "your-email@example.com" \
  --type SecureString

aws ssm put-parameter \
  --name "/factor75-selector/factor75-password" \
  --value "your-password" \
  --type SecureString

# ... repeat for other parameters
```

### Deploy Lambda

```bash
# Create deployment package
cd apps/factor75-meal-selector
pip install -r requirements.txt -t package/
cp -r src/* package/
cp lambda_handler.py package/
cd package && zip -r ../lambda.zip .

# Upload to Lambda
aws lambda update-function-code \
  --function-name factor75-selector \
  --zip-file fileb://lambda.zip
```

### EventBridge Schedule

Create EventBridge rules for:

- **Weekly scrape**: `cron(0 13 ? * SUN *)` (Sunday 8 AM ET)
- **Reply check**: `rate(15 minutes)` (when selection window is open)

## Project Structure

```
factor75-meal-selector/
├── src/
│   ├── factor75_main.py        # Main entry point
│   ├── factor75_scraper.py     # Web scraping logic
│   ├── meal_report_generator.py # HTML email generation
│   ├── reply_parser.py         # Parse email replies
│   ├── selection_submitter.py  # Submit to Factor 75
│   ├── gmail_service.py        # Gmail API for replies
│   └── ses_email_sender.py     # AWS SES email sending
├── credentials/                 # Gmail OAuth credentials (gitignored)
├── lambda_handler.py           # AWS Lambda entry point
├── requirements.txt
├── config.yaml.example
├── .env.example
└── README.md
```

## Troubleshooting

### Gmail Authentication

If Gmail authentication fails:

1. Delete `credentials/token.pickle`
2. Run `--validate` to re-authenticate
3. Make sure OAuth consent screen is configured

### SES Email Not Sending

1. Verify sender email in SES console
2. Check SES is out of sandbox mode (or recipient is verified)
3. Check IAM permissions for `ses:SendEmail`

### Selection Parsing Fails

Make sure your reply contains only meal numbers:

- Numbers should be comma or space separated
- Total count should match your plan (default: 10)
- Numbers should be within valid range

## Security Notes

- Never commit `.env` file (it's in `.gitignore`)
- Store sensitive values in AWS Parameter Store for Lambda
- Gmail credentials require OAuth flow (no password storage)
