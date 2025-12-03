# YNAB Transaction Reviewer

An intelligent daily email system that proactively pushes uncategorized YNAB transactions for review, featuring smart categorization suggestions and one-click actions.

## Overview

Never miss categorizing a transaction again! This system sends you a daily email at 5 PM (except Saturdays) with all your uncategorized YNAB transactions, complete with:

- 🤖 **Smart Suggestions** - AI-powered category recommendations based on merchant patterns and historical data
- ✂️ **Split Detection** - Automatic detection of transactions that should be split (Amazon, Costco, restaurants with tips)
- 📧 **Beautiful Emails** - Clean, mobile-friendly HTML emails with all transaction details
- ⚡ **One-Click Actions** - Categorize directly from the email without opening YNAB
- 📊 **Learning System** - Gets smarter over time by learning from your categorization patterns
- 🎯 **Saturday Handling** - Saturday transactions are included in Sunday's email

## Features

### Smart Transaction Processing
- Fetches all uncategorized transactions from YNAB
- Groups transactions by account for better organization
- Tracks review state to avoid duplicate notifications
- Automatically cleans up old state data (90+ days)

### Intelligent Suggestions
- **Merchant Recognition** - Identifies known merchants and suggests their usual categories
- **Historical Analysis** - Looks at past transactions for the same payee
- **Merchant Type Detection** - Recognizes merchant types (grocery, gas station, restaurant, etc.)
- **Amount-Based Patterns** - Suggests categories based on typical amounts ($1-5 = Coffee, $20-60 = Gas)
- **Confidence Scoring** - Shows confidence percentage for each suggestion (0-100%)

### Split Transaction Analysis
- Detects transactions likely needing splits:
  - Amazon orders (suggests item categories)
  - Warehouse stores (Costco, Sam's Club)
  - Department stores with mixed categories
  - Restaurants (separates food from tip)
- Proposes split amounts and categories
- Configurable thresholds per merchant type

### Email System
- Daily digest sent at 5 PM (configurable)
- Skip Saturdays (transactions included in Sunday's email)
- Beautiful HTML formatting with summary statistics
- Mobile-responsive design
- Quick action buttons for common operations

## Quick Start

### Prerequisites
- Python 3.8+
- YNAB account with Personal Access Token
- Gmail account for sending emails
- (Optional) AWS account for Lambda deployment

### Installation

1. **Clone and navigate to the app:**
```bash
cd apps/ynab-transaction-reviewer
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up credentials:**
```bash
# Create credentials directory
mkdir -p credentials

# Add your YNAB API key to environment
export YNAB_API_KEY="your-ynab-personal-access-token"

# Download Gmail OAuth credentials from Google Cloud Console
# Save as credentials/gmail_credentials.json
```

4. **Configure the system:**
```bash
# Edit config/config.yaml
vi config/config.yaml

# Set your email address
notifications:
  recipient_email: "your-email@gmail.com"
```

5. **Validate setup:**
```bash
python src/reviewer_main.py --validate
```

6. **Run your first review:**
```bash
python src/reviewer_main.py --run
```

## Configuration

Edit `config/config.yaml` to customize:

### Schedule Settings
```yaml
schedule:
  daily_review_time: "17:00"  # 5 PM
  timezone: "America/New_York"
  skip_days: ["Saturday"]
  saturday_handling: "include_in_sunday"
```

### Notification Preferences
```yaml
notifications:
  recipient_email: "your-email@gmail.com"
  min_transactions: 1  # Minimum to trigger email
  empty_report: false  # Send even when all categorized
```

### Suggestion Settings
```yaml
suggestions:
  min_confidence: 60  # Only show 60%+ confidence
  max_suggestions: 3  # Show top 3 per transaction
```

### Split Detection
```yaml
split_detection:
  amazon_split_threshold: 50.00
  costco_split_threshold: 100.00
  restaurant_tip_split: true
  default_tip_percentage: 0.18
```

## Usage

### Command Line Interface

```bash
# Validate setup and connections
python src/reviewer_main.py --validate

# Run transaction review
python src/reviewer_main.py --run

# Dry run (no emails sent)
python src/reviewer_main.py --dry-run

# Force run on skip day
python src/reviewer_main.py --run --force

# Show statistics
python src/reviewer_main.py --stats
```

### Daily Workflow

1. **5:00 PM Daily** - Receive email with uncategorized transactions
2. **Review** - See smart suggestions and merchant details
3. **Categorize** - Click suggestion buttons or reply with categories
4. **Done** - Transactions instantly categorized in YNAB

**Saturday:** No email (enjoy your weekend!)
**Sunday 5 PM:** Includes both Saturday and Sunday transactions

## Email Format

Each transaction in the email includes:
- 📅 Date and 💳 Account information
- 🏪 Payee name and 💰 Amount
- 📝 Memo (if present)
- 🤖 Smart category suggestions with confidence scores
- ✂️ Split suggestions for applicable merchants
- ✅ Quick action buttons

### Example Email

```
Subject: [YNAB Review] 5 transactions need categorization

SUMMARY
- Uncategorized: 5
- Total Amount: $287.43
- Accounts: 2
- Oldest: 2 days

TRANSACTIONS

#1: AMAZON.COM
Amount: -$156.43 | Chase Sapphire | Nov 25
SUGGESTIONS:
• Shopping (85%) - Based on 23 similar transactions
• Suggested Split:
  - Electronics: $89.99
  - Household: $66.44
[✅ Categorize as Shopping] [✂️ Apply Split] [🔗 View in YNAB]

#2: SHELL OIL
Amount: -$45.00 | Debit Card | Nov 26
SUGGESTIONS:
• Auto & Transport: Gas (92%) - Merchant type: Gas Station
[✅ Categorize as Gas] [🔗 View in YNAB]
```

## AWS Lambda Deployment

### Setup AWS Resources

1. **Create Lambda function:**
```bash
aws lambda create-function \
  --function-name ynab-transaction-reviewer \
  --runtime python3.9 \
  --handler lambda/daily_review_handler.lambda_handler \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role
```

2. **Store credentials in Parameter Store:**
```bash
aws ssm put-parameter \
  --name /ynab-reviewer/ynab-api-key \
  --value "your-ynab-token" \
  --type SecureString

aws ssm put-parameter \
  --name /ynab-reviewer/recipient-email \
  --value "your-email@gmail.com" \
  --type String
```

3. **Create EventBridge schedule:**
```bash
# 5 PM ET daily, skip Saturday
aws events put-rule \
  --name ynab-daily-review \
  --schedule-expression "cron(0 21 ? * SUN,MON,TUE,WED,THU,FRI *)"
```

4. **Deploy code:**
```bash
./scripts/deploy-lambda.sh
```

## Data Storage

The system maintains several data files:

### Review State (`data/review_state.json`)
- Tracks which transactions have been reviewed
- Prevents duplicate notifications
- Auto-cleaned after 90 days

### Merchant Database (`data/merchants.json`)
- Learns from your categorization patterns
- Stores merchant → category mappings
- Improves suggestions over time

### Logs (`logs/reviewer.log`)
- Rotating log files with detailed execution info
- Useful for troubleshooting

## Learning System

The system gets smarter over time by:

1. **Tracking Categorizations** - Records every categorization choice
2. **Building Patterns** - Identifies consistent merchant → category mappings
3. **Improving Confidence** - Increases confidence for repeated patterns
4. **Merchant Intelligence** - Builds a database of known merchants

After 30 days of use, expect 90%+ suggestion accuracy for regular merchants.

## Troubleshooting

### No Email Received
- Check spam folder
- Verify Gmail authentication: `python src/reviewer_main.py --validate`
- Check logs: `tail -f logs/reviewer.log`
- Ensure not Saturday (unless forced)

### YNAB Connection Issues
- Verify API key is valid
- Check YNAB API status
- Ensure budget ID is correct (or omit for default)

### Missing Transactions
- Check lookback_days in config (default: 30)
- Verify transactions are truly uncategorized in YNAB
- Check if transactions are in excluded accounts

### Gmail Authentication
- Ensure credentials.json is in credentials/
- Delete gmail_token.pickle to re-authenticate
- Check OAuth scopes include gmail.send

## API Rate Limits

- **YNAB:** 200 requests per hour per access token
- **Gmail:** 250 quota units per user per second
- The system implements retry logic and respects rate limits

## Security

- YNAB API key stored securely (environment variable or Parameter Store)
- Gmail uses OAuth2 (no password storage)
- Action tokens include HMAC signatures (when deployed)
- All sensitive data excluded from logs

## Contributing

This is a personal project, but improvements are welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Future Enhancements

Planned features:
- [ ] Web dashboard for rule management
- [ ] Slack/Discord integration options
- [ ] Receipt photo OCR support
- [ ] Budget goal tracking in emails
- [ ] Multi-user support
- [ ] Advanced ML categorization

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
- Check the [troubleshooting guide](#troubleshooting)
- Review logs in `logs/reviewer.log`
- Open an issue on GitHub

---

**Created by:** Terrance Brandon
**Repository:** [My-Workspace-TB-](https://github.com/SonOfSamuel1/My-Workspace-TB-)
**Last Updated:** 2025-11-26