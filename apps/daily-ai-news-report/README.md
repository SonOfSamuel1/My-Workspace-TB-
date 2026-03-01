# Daily AI News Report

Automated AI news aggregation and email delivery service. Fetches articles from multiple RSS feeds, processes and ranks them by relevance, and sends a beautifully formatted daily email digest.

## Features

- **Multi-source RSS Aggregation**: Fetches from MIT Tech Review, VentureBeat, The Verge, Wired, TechCrunch, and more
- **Smart Relevance Scoring**: AI-focused keyword matching to prioritize the most relevant articles
- **Deduplication**: Prevents repeated articles across days
- **Beautiful HTML Emails**: Modern, responsive email template
- **AWS Lambda Ready**: Deploy as a serverless function with EventBridge scheduling
- **AWS SES Integration**: Reliable email delivery via Amazon SES

## Quick Start

### Local Development

1. **Clone and navigate to the app**:
   ```bash
   cd apps/daily-ai-news-report
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run locally** (dry run - no email sent):
   ```bash
   python -m src.news_main --dry-run
   ```

6. **Run with email**:
   ```bash
   python -m src.news_main
   ```

### Using the Run Script

```bash
# Dry run (no email)
./scripts/run-local.sh --dry-run

# Full run with email
./scripts/run-local.sh

# Verbose output
./scripts/run-local.sh --dry-run --verbose
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SENDER_EMAIL` | Email address to send from (must be verified in SES) | Yes |
| `RECIPIENT_EMAIL` | Email address(es) to send to (comma-separated) | Yes |
| `AWS_REGION` | AWS region for SES | Yes |
| `AWS_ACCESS_KEY_ID` | AWS credentials (not needed in Lambda) | Local only |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials (not needed in Lambda) | Local only |

### Config File

Edit `config/config.yaml` to customize:
- RSS feed sources
- Number of articles per email
- Relevance score threshold
- Email subject prefix

## Project Structure

```
daily-ai-news-report/
├── src/
│   ├── __init__.py
│   ├── news_main.py          # Main orchestration
│   ├── rss_fetcher.py        # RSS feed parsing
│   ├── web_scraper.py        # Web content extraction
│   ├── news_processor.py     # Filtering & scoring
│   ├── email_report.py       # Report generation
│   └── ses_email_sender.py   # AWS SES integration
├── lambda/
│   ├── lambda_handler.py     # AWS Lambda entry point
│   └── requirements.txt      # Lambda dependencies
├── config/
│   └── config.yaml           # App configuration
├── templates/
│   └── news_email.html       # Email template
├── scripts/
│   ├── deploy-lambda-zip.sh  # Deploy to Lambda
│   ├── run-local.sh          # Local development
│   └── setup-parameters.sh   # AWS Secrets Manager
├── tests/
│   ├── conftest.py
│   ├── test_rss_fetcher.py
│   ├── test_news_processor.py
│   └── test_email_report.py
├── requirements.txt
├── pytest.ini
└── README.md
```

## AWS Lambda Deployment

### Prerequisites

1. AWS CLI configured with appropriate permissions
2. AWS SES sender email verified
3. Lambda execution role with SES and Secrets Manager access

### Deploy

1. **Setup secrets**:
   ```bash
   ./scripts/setup-parameters.sh
   ```

2. **Deploy to Lambda**:
   ```bash
   ./scripts/deploy-lambda-zip.sh
   ```

3. **Create EventBridge rule** for daily scheduling:
   ```bash
   aws events put-rule \
     --name daily-ai-news-schedule \
     --schedule-expression "cron(0 8 * * ? *)" \
     --description "Trigger daily AI news report at 8 AM UTC"
   ```

### Lambda Environment Variables

Set these in the Lambda console:
- `SECRETS_NAME`: `daily-ai-news/credentials`
- `AWS_REGION`: `us-east-1`

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_news_processor.py
```

## Adding New RSS Feeds

Edit `config/config.yaml`:

```yaml
feeds:
  - name: "New Source Name"
    url: "https://example.com/rss/feed.xml"
    category: "research"  # or "industry", "tech"
```

## Customizing the Email Template

Edit `templates/news_email.html` to customize the email appearance. The template uses Jinja2 syntax with these available variables:

- `{{ title }}` - Report title
- `{{ date }}` - Current date
- `{{ articles }}` - List of Article objects
- `{{ article_count }}` - Number of articles
- `{{ source_count }}` - Number of sources

## License

MIT
