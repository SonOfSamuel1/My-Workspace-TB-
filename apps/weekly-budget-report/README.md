# Weekly YNAB Budget Report

Automated weekly budget reports delivered to your inbox every Saturday at 7pm, powered by YNAB transaction data and beautiful HTML email reports.

## Features

- **Automated Weekly Reports** - Delivered every Saturday at 7pm EST via email
- **Comprehensive Budget Analysis** - Spending vs budgeted amounts with visual progress bars
- **Category Breakdown** - Top spending categories with detailed breakdowns
- **Merchant Analytics** - Top payees/merchants by spending
- **Notable Transactions** - Automatic highlighting of large transactions
- **Budget Alerts** - Warnings for overspending and budget concerns
- **Account Activity** - Summary of all account transactions
- **Beautiful HTML Emails** - Professional, easy-to-read reports

## Quick Start

```bash
# Navigate to project
cd apps/weekly-budget-report

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your YNAB API key and email

# Validate configuration
python src/budget_main.py --validate

# Generate a report now
python src/budget_main.py --generate
```

## Setup

### 1. Get Your YNAB API Key

1. Log in to YNAB at https://app.ynab.com
2. Go to **Account Settings** → **Developer Settings**
3. Click **New Token** and create a Personal Access Token
4. Copy your token (looks like: `hYPZEhxFtOZh0f5BDQMXdqHUsX5yrNgJtUJmyJlkYDs`)

### 2. Configure Environment

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` with your details:

```bash
# YNAB Configuration
YNAB_API_KEY=your_ynab_api_key_here
YNAB_BUDGET_ID=  # Optional: Leave blank to use first budget

# Email Configuration
BUDGET_REPORT_EMAIL=your_email@example.com

# Google API (for Gmail sending)
GOOGLE_CREDENTIALS_FILE=../../shared/credentials/credentials.json
GOOGLE_TOKEN_FILE=../../shared/credentials/token.pickle
```

### 3. Configure Google Gmail API (for sending emails)

Follow the Gmail API setup from the Love Brittany tracker or:

1. Enable Gmail API in Google Cloud Console
2. Download OAuth2 credentials
3. Place in `../../shared/credentials/credentials.json`
4. Run the app once to generate token

### 4. Customize Report Settings

Edit `config.yaml` to customize:

- Report schedule (default: Saturday 7pm)
- Lookback period (default: 7 days)
- Alert thresholds
- Number of top categories/payees to show
- Notable transaction threshold

Example:

```yaml
budget_report:
  enabled: true
  schedule:
    - "0 19 * * 6"   # Saturday 7pm EST

  report:
    lookback_days: 7  # 1 week
    top_payees_count: 10
    top_categories_count: 10
    notable_transaction_threshold: 100  # $100+

  alerts:
    overspending_threshold: 10  # Alert if 10% over budget
    total_spending_threshold: 90  # Alert if 90% of budget used
```

## Usage

### Generate Report Locally

```bash
# Generate and send email
python src/budget_main.py --generate

# Generate but don't send email (save to output/)
python src/budget_main.py --generate --no-email

# Validate setup
python src/budget_main.py --validate
```

### Deploy to AWS Lambda

For automated weekly reports, deploy to AWS Lambda:

1. **Package the application:**
   ```bash
   ./deploy_lambda.sh
   ```

2. **Upload to AWS Lambda:**
   - Create a Lambda function in AWS Console
   - Upload the ZIP file created by deploy script
   - Set runtime to Python 3.9 or higher
   - Set timeout to 5 minutes
   - Set memory to 512 MB

3. **Configure AWS Parameter Store:**
   Store sensitive credentials:
   - `/budget-report/ynab-api-key` - Your YNAB API key
   - `/budget-report/email-recipient` - Report recipient email
   - `/budget-report/credentials` - Google OAuth credentials (JSON)
   - `/budget-report/token` - Google OAuth token (base64 encoded pickle)

4. **Create EventBridge Rule:**
   - Rule type: Schedule
   - Cron expression: `0 23 * * 6` (Saturday 7pm EST = 11pm UTC)
   - Target: Your Lambda function

5. **Set Lambda environment variables:**
   ```
   AWS_REGION=us-east-1
   ```

See [AWS Deployment Guide](./docs/AWS_DEPLOYMENT.md) for detailed instructions.

## Report Contents

### Executive Summary
- Total spending for the week
- Total income
- Net cash flow
- Transaction count

### Budget Comparison
- Budget vs actual spending by category
- Visual progress bars
- Remaining amounts
- Over-budget warnings

### Category Breakdown
- Top spending categories
- Category groups
- Transaction counts

### Top Merchants
- Highest spending payees
- Total amounts per merchant
- Transaction frequency

### Notable Transactions
- Large transactions (default: $100+)
- Date, payee, category, amount
- Transaction memos

### Account Activity
- Activity per account
- Inflows and outflows
- Net change per account

### Smart Alerts
- Overspending warnings
- Budget threshold alerts
- Category-specific concerns

## Project Structure

```
weekly-budget-report/
├── src/
│   ├── __init__.py
│   ├── budget_main.py          # Main orchestrator
│   ├── ynab_service.py          # YNAB API client
│   ├── budget_analyzer.py       # Transaction analysis
│   └── budget_report.py         # HTML report generator
├── docs/
│   └── AWS_DEPLOYMENT.md        # AWS deployment guide
├── logs/                        # Application logs
├── output/                      # Generated reports
├── config.yaml                  # Configuration
├── requirements.txt             # Python dependencies
├── lambda_handler.py            # AWS Lambda handler
└── README.md                    # This file
```

## Configuration Reference

### Report Settings

```yaml
budget_report:
  report:
    lookback_days: 7              # Days to include in report
    trend_weeks: 4                # Weeks for trend comparison
    top_payees_count: 10          # Number of top merchants
    top_categories_count: 10      # Number of top categories
    notable_transaction_threshold: 100  # Dollar threshold for notable txns

    exclude_categories:           # Categories to exclude
      - "Inflow: Ready to Assign"
      - "Credit Card Payment"
```

### Alert Thresholds

```yaml
budget_report:
  alerts:
    overspending_threshold: 10      # % over budget to alert
    total_spending_threshold: 90    # % of total budget to warn
    discretionary_threshold: 80     # % of discretionary budget
```

### Email Settings

```yaml
budget_report:
  email:
    recipient: "your@email.com"
    subject_template: "Weekly Budget Report - {date}"
    include_charts: true
```

## Troubleshooting

### Common Issues

**YNAB API errors:**
- Verify your API key is correct
- Check that your budget exists
- Ensure API key hasn't expired

**Email not sending:**
- Verify Gmail API is enabled
- Check OAuth credentials are valid
- Ensure token.pickle exists
- Verify recipient email is correct

**No data in report:**
- Check date range in config
- Verify transactions exist in YNAB
- Review exclude_categories setting

### Debug Mode

Enable debug logging in `config.yaml`:

```yaml
logging:
  level: "DEBUG"
```

### View Logs

```bash
tail -f logs/budget_report.log
```

## YNAB API Notes

### Amount Format
YNAB uses "milliunits" for all monetary amounts:
- **1000 milliunits = $1.00**
- **-25000 milliunits = -$25.00 (outflow)**
- **100000 milliunits = $100.00 (inflow)**

The application automatically converts to dollars for display.

### Date Format
All dates are in ISO 8601 format: `YYYY-MM-DD`

### Rate Limiting
The YNAB API has a rate limit of **200 requests per hour** per access token.

## Development

### Run Tests
```bash
python -m pytest tests/
```

### Code Style
```bash
black src/
flake8 src/
```

## Contributing

This is a personal project, but improvements are welcome:
1. Follow existing code patterns
2. Update documentation
3. Test thoroughly before committing

## Support

For issues:
1. Check logs: `logs/budget_report.log`
2. Run validation: `python src/budget_main.py --validate`
3. Review YNAB API docs: https://api.ynab.com/

## License

Part of the My Workspace monorepo - see repository LICENSE

## Related Projects

- **[Love Brittany Tracker](../love-brittany-tracker/)** - Relationship tracking with similar architecture
- **[YNAB MCP Server](../../servers/ynab-mcp-server/)** - YNAB integration for Claude AI

---

**Last Updated:** 2025-11-17
**Version:** 1.0.0
