# Homeschool Events Gwinnett

Weekly automated digest of homeschooling events in Gwinnett County, GA. Searches
using Perplexity AI and delivers styled HTML emails with one-click "Add to
Calendar" buttons.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Validate setup
python src/events_main.py --validate

# Dry run (saves HTML, no email)
python src/events_main.py --generate --dry-run

# Full run (search + email)
python src/events_main.py --generate
```

## Configuration

### Environment Variables

| Variable                 | Description                     |
| ------------------------ | ------------------------------- |
| `PERPLEXITY_API_KEY`     | Perplexity AI API key           |
| `EVENTS_EMAIL_RECIPIENT` | Email recipient address         |
| `SES_SENDER_EMAIL`       | AWS SES verified sender email   |
| `AWS_REGION`             | AWS region (default: us-east-1) |

### config.yaml

- **search.area** - Geographic search area
- **search.lookahead_days** - Days ahead to search (default: 30)
- **search.categories** - Event categories to look for
- **search.known_sources** - Specific sources to check

## AWS Lambda Deployment

```bash
# First time
./deploy_lambda.sh --create

# Updates
./deploy_lambda.sh
```

### Parameter Store Keys

```text
/homeschool-events/perplexity-api-key   (SecureString)
/homeschool-events/email-recipient
/homeschool-events/ses-sender-email
```

### Schedule

Monday 9:00 AM EST via EventBridge: `cron(0 14 ? * MON *)`

## CLI Options

```text
--validate    Validate configuration and credentials
--generate    Generate and send event digest
--no-email    Generate without sending email
--dry-run     Generate, save HTML locally, no email
```
