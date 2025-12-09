# Weekly Atlanta News Report

Automated weekly news digest for Atlanta, GA. Aggregates local news from major Atlanta news sources via RSS feeds and delivers a curated email report every Friday at 6:30 PM EST.

## Features

- **RSS Feed Aggregation**: Fetches news from AJC, 11Alive, WSB-TV, Fox 5, CBS46, and Atlanta Business Chronicle
- **Smart Deduplication**: Removes similar stories across sources using title similarity
- **Automatic Categorization**: Organizes stories into Top Stories, General News, and Business & Development
- **HTML Email Reports**: Professional, mobile-responsive email digest
- **AWS Lambda Deployment**: Serverless execution with EventBridge scheduling
- **AWS SES Integration**: Reliable email delivery without OAuth token hassles

## Quick Start

### 1. Install Dependencies

```bash
cd apps/weekly-atlanta-news-report
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your email
nano .env
```

Required environment variables:
```
ATLANTA_NEWS_EMAIL=your_email@example.com
SES_SENDER_EMAIL=brandonhome.appdev@gmail.com
AWS_REGION=us-east-1
```

### 3. Validate Setup

```bash
python src/news_main.py --validate
```

### 4. Test RSS Feeds

```bash
python src/news_main.py --test-feeds
```

### 5. Generate Report

```bash
# Generate and send email
python src/news_main.py --generate

# Generate without sending (saves to output/)
python src/news_main.py --generate --no-email
```

## Configuration

### config.yaml

The main configuration file controls RSS feeds, report settings, and email options:

```yaml
atlanta_news_report:
  enabled: true
  timezone: "America/New_York"

  feeds:
    - name: "Atlanta Journal-Constitution"
      url: "https://www.ajc.com/arc/outboundfeeds/rss/?outputType=xml"
      category: "general"
    # ... more feeds

  report:
    max_articles: 25
    min_articles: 15
    lookback_days: 7
    deduplicate: true
    similarity_threshold: 0.7

  email:
    subject_template: "Atlanta Weekly News Digest - {date}"
```

### Adding New RSS Feeds

Edit `config.yaml` to add new feeds:

```yaml
feeds:
  - name: "Source Name"
    url: "https://example.com/rss.xml"
    category: "general"  # or "business"
```

## AWS Lambda Deployment

### Prerequisites

1. AWS CLI configured with appropriate credentials
2. IAM role with permissions:
   - `AWSLambdaBasicExecutionRole`
   - `AmazonSESFullAccess` (or custom SES policy)
   - `AmazonSSMReadOnlyAccess`

### Set Up Parameter Store

```bash
# Email recipient
aws ssm put-parameter \
  --name "/atlanta-news/email-recipient" \
  --type "String" \
  --value "your_email@example.com"

# SES sender email
aws ssm put-parameter \
  --name "/atlanta-news/ses-sender-email" \
  --type "String" \
  --value "brandonhome.appdev@gmail.com"
```

### Deploy

```bash
# First deployment (creates function)
./deploy_lambda.sh --create

# Subsequent deployments (updates function)
./deploy_lambda.sh
```

### EventBridge Schedule

The deploy script automatically creates an EventBridge rule:
- **Schedule**: `cron(30 23 ? * FRI *)`
- **Time**: Friday 11:30pm UTC = 6:30pm EST

### Manual Test

```bash
# Invoke Lambda manually
aws lambda invoke \
  --function-name weekly-atlanta-news-report \
  --region us-east-1 \
  output.json

cat output.json
```

### View Logs

```bash
aws logs tail /aws/lambda/weekly-atlanta-news-report --follow --region us-east-1
```

## Project Structure

```
weekly-atlanta-news-report/
├── src/
│   ├── __init__.py
│   ├── news_main.py          # Main entry point (CLI)
│   ├── news_fetcher.py       # RSS feed fetching
│   ├── news_analyzer.py      # Article processing
│   ├── news_report.py        # HTML report generation
│   ├── ses_email_sender.py   # AWS SES integration
│   └── templates/
│       ├── base.html         # Base HTML template
│       └── weekly_news_report.html
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_news_fetcher.py
│   └── test_news_analyzer.py
├── config.yaml               # Main configuration
├── .env.example              # Environment template
├── requirements.txt          # Dependencies
├── lambda_handler.py         # AWS Lambda entry point
├── deploy_lambda.sh          # Deployment script
├── pytest.ini                # Test configuration
├── .gitignore
└── README.md
```

## CLI Reference

```bash
# Show help
python src/news_main.py

# Validate configuration
python src/news_main.py --validate

# Test RSS feed connectivity
python src/news_main.py --test-feeds

# Generate and send report
python src/news_main.py --generate

# Generate without sending email
python src/news_main.py --generate --no-email
```

## News Sources

### General News
| Source | Description |
|--------|-------------|
| Atlanta Journal-Constitution | Major daily newspaper |
| 11Alive (WXIA) | NBC affiliate |
| WSB-TV | ABC affiliate |
| Fox 5 Atlanta | Fox affiliate |
| CBS46 | CBS affiliate |
| Patch Atlanta | Hyperlocal news |

### Business & Development
| Source | Description |
|--------|-------------|
| Atlanta Business Chronicle | Business news |

## Troubleshooting

### RSS Feed Errors

```bash
# Test individual feeds
python src/news_main.py --test-feeds
```

If a feed is failing:
1. Check the URL is still valid
2. Verify the site hasn't changed their RSS structure
3. Update the URL in `config.yaml`

### Email Not Sending

1. Verify SES sender email is verified:
   ```bash
   aws ses get-identity-verification-attributes \
     --identities brandonhome.appdev@gmail.com
   ```

2. Check SES is out of sandbox mode (for production recipients)

3. Verify IAM permissions include `ses:SendEmail`

### Lambda Timeout

If the Lambda function times out:
1. Increase `TIMEOUT` in `deploy_lambda.sh` (max 900 seconds)
2. Reduce number of RSS feeds
3. Check network connectivity from Lambda VPC

### No Articles Found

1. Check RSS feeds are working: `--test-feeds`
2. Verify `lookback_days` in config (default: 7)
3. Check feed URLs haven't changed

## Development

### Running Tests

```bash
pytest
pytest --cov=src --cov-report=html
```

### Code Formatting

```bash
black src/
flake8 src/
```

## Dependencies

- `feedparser` - RSS/Atom feed parsing
- `beautifulsoup4` - HTML parsing and cleanup
- `requests` - HTTP client
- `python-dateutil` - Date parsing
- `pytz` - Timezone handling
- `PyYAML` - Configuration parsing
- `python-dotenv` - Environment variable loading
- `jinja2` - HTML templating
- `boto3` - AWS SDK (SES, SSM)

## License

Private - Personal use only.

## Author

Terrance Brandon
