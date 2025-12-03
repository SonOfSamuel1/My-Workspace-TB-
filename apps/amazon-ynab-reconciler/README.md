# Amazon-YNAB Transaction Reconciliation Automation

An automated system that scrapes Amazon order history, intelligently matches transactions with YNAB, and updates transaction memos with Amazon categorization and item links.

## Features

- **Downloads Folder Monitoring**: Automatically detects and imports Amazon CSV reports from Downloads folder
- **Enhanced Purchase Details**: Rich YNAB memos with item names, quantities, and categories
- **Multiple Data Sources**: Downloads folder, Gmail parsing, CSV import, or web scraping
- **Smart Matching Engine**: Fuzzy matching with configurable date/amount tolerances
- **YNAB Integration**: Updates transaction memos with detailed Amazon purchase information
- **Duplicate Prevention**: Tracks processed files and reconciliation history
- **Email Reports**: Sends detailed HTML reports of reconciliation results
- **AWS Lambda Deployment**: Runs serverlessly with scheduled triggers
- **Dry Run Mode**: Test matching logic without modifying YNAB data

## How It Works

1. **Data Collection** (in priority order):
   - **Downloads Folder**: Checks for Amazon CSV reports downloaded by browser
   - **Email Parsing**: Reads Amazon order confirmation emails from Gmail
   - **CSV Import**: Uses manually placed CSV files
   - **Web Scraping**: Playwright automation (fallback)
2. **Fetches YNAB Transactions**: Retrieves uncleared transactions from specified accounts
3. **Intelligent Matching**: Uses fuzzy logic to match based on:
   - Date proximity (±2 days default)
   - Amount tolerance (±$0.50 default)
   - Payment method correlation
4. **Updates YNAB**: Adds detailed purchase info to transaction memos
5. **Archives Processed Files**: Moves processed CSVs to archive folder
6. **Sends Report**: Emails comprehensive reconciliation summary

## Memo Format

Transactions are updated with enhanced purchase details:
```
[Amazon #234567] Echo Dot (5th Gen), USB-C Cable (x2) | Electronics (+1 more)
```

For single items:
```
[Amazon #234567] Echo Dot (5th Gen) | Electronics
```

The memo includes:
- Order ID (last 6 digits for reference)
- Item names (up to 3 items shown)
- Quantities if > 1
- Category if consistent across items
- Count of additional items if order has > 3 items

## Quick Start

### Prerequisites

- Python 3.9+
- YNAB Personal Access Token
- Amazon account credentials
- Gmail API credentials (for email reports)
- AWS account (for Lambda deployment)

### Local Setup

1. **Clone and navigate to the app:**
   ```bash
   cd apps/amazon-ynab-reconciler
   ```

2. **Install dependencies:**
   ```bash
   pip install -r lambda/requirements.txt
   playwright install chromium
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Run dry-run test:**
   ```bash
   python src/reconciler_main.py --dry-run --days 7
   ```

5. **Run full reconciliation:**
   ```bash
   python src/reconciler_main.py --days 30
   ```

### Using Downloads Folder (Recommended)

The easiest way to use this tool is with Amazon transaction reports downloaded to your Downloads folder:

1. **Download Amazon transaction report:**
   - Go to: https://www.amazon.com/gp/b2b/reports
   - OR: Your Account → Download order reports
   - Select Report Type: 'Items'
   - Choose date range (e.g., last 30 days)
   - Click 'Request Report' and download the CSV

2. **Run reconciliation with downloads mode:**
   ```bash
   python src/reconciler_main.py --use-downloads --days 30
   ```

3. **Enable continuous monitoring (optional):**
   ```bash
   python src/reconciler_main.py --monitor --use-downloads
   ```
   This will check your Downloads folder every 5 minutes for new Amazon CSV files.

4. **Specify custom downloads directory:**
   ```bash
   python src/reconciler_main.py --use-downloads --download-dir ~/Documents/AmazonReports
   ```

The CSV files will be automatically:
- Detected in ~/Downloads (or specified directory)
- Parsed with full item details
- Matched with YNAB transactions
- Archived to data/processed/ after processing

### Other Data Source Options

**Email parsing mode:**
```bash
python src/reconciler_main.py --use-email --days 30
```

**CSV file mode (manual placement):**
```bash
python src/reconciler_main.py --use-csv --days 30
```

**Sample data mode (for testing):**
```bash
python src/reconciler_main.py --use-sample --dry-run
```

### Configuration

Edit `config.yaml` to customize:

```yaml
reconciliation:
  lookback_days: 30           # Days to look back
  match_threshold: 80         # Minimum confidence (0-100)
  date_tolerance_days: 2      # Date matching tolerance
  amount_tolerance_cents: 50  # Amount matching tolerance

amazon:
  max_pages: 10              # Max order history pages to scrape
  browser:
    headless: true           # Run browser in background

ynab:
  budget_name: 'Main Budget'
  account_names:
    - 'Chase Credit Card'
    - 'Amex'
  only_uncleared: true       # Only process uncleared transactions
```

## AWS Lambda Deployment

### Build and Deploy

1. **Build Docker image:**
   ```bash
   cd lambda
   docker build -t amazon-ynab-reconciler .
   ```

2. **Push to ECR:**
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin [YOUR_ECR_URI]
   docker tag amazon-ynab-reconciler:latest [YOUR_ECR_URI]/amazon-ynab-reconciler:latest
   docker push [YOUR_ECR_URI]/amazon-ynab-reconciler:latest
   ```

3. **Create Lambda function:**
   - Use container image from ECR
   - Memory: 3008 MB (for Playwright)
   - Timeout: 300 seconds
   - Environment: Set AWS_REGION

4. **Configure Parameter Store:**
   ```bash
   aws ssm put-parameter --name "/amazon-reconciler/amazon-email" --value "your@email.com" --type "SecureString"
   aws ssm put-parameter --name "/amazon-reconciler/amazon-password" --value "password" --type "SecureString"
   aws ssm put-parameter --name "/amazon-reconciler/ynab-api-key" --value "token" --type "SecureString"
   ```

5. **Set up EventBridge schedule:**
   ```bash
   # Daily at 2 AM ET
   aws events put-rule --name amazon-ynab-daily --schedule-expression "cron(0 7 * * ? *)"
   ```

## Match Confidence Scoring

The matching algorithm calculates confidence scores (0-100%):

- **Date Proximity (40 points max)**:
  - Same day: 40 points
  - 1 day diff: 20 points
  - 2 days diff: 10 points

- **Amount Proximity (60 points max)**:
  - Exact match: 60 points
  - Within $0.25: 30 points
  - Within $0.50: 15 points

- **Bonus Points**:
  - Same day: +5 points
  - Exact amount: +5 points
  - Payment method match: +10 points

### Confidence Levels

- **High (90%+)**: Green flag, auto-update
- **Medium (70-89%)**: Yellow flag, auto-update with review
- **Low (<70%)**: Red flag, skip or manual review

## State Management

The system tracks reconciliation history to prevent duplicates:

- Stored in `logs/reconciliation_state.json`
- Records matched transaction pairs
- Automatically prunes entries older than 90 days
- Prevents re-reconciling previously matched transactions

## Email Reports

HTML reports include:

- Summary statistics
- Match confidence breakdown
- Detailed transaction table
- Unmatched transaction warnings
- Processing time and errors

### Report Sections

1. **Summary Grid**: Key metrics at a glance
2. **Confidence Analysis**: Distribution of match quality
3. **Matched Transactions**: Detailed table with:
   - Date and amount differences
   - Amazon item details
   - YNAB account info
   - Confidence scores
4. **Unmatched Items**: Transactions requiring manual review

## Troubleshooting

### Common Issues

**Amazon login fails:**
- Verify credentials in `.env`
- Check for 2FA requirements
- Update selectors in `config.yaml` if Amazon changes UI

**No matches found:**
- Increase date/amount tolerances
- Check account name mappings
- Verify transaction date ranges

**Lambda timeout:**
- Increase Lambda timeout (max 15 minutes)
- Reduce `max_pages` in config
- Process smaller date ranges

**Playwright errors:**
- Ensure Chromium is installed: `playwright install chromium`
- Check Docker image has all dependencies
- Verify Lambda has sufficient memory (3GB+)

### Validation

Run validation to check setup:
```bash
python src/reconciler_main.py --validate
```

This verifies:
- Amazon credentials
- YNAB API connection
- Email configuration
- State file access

## Testing

### Dry Run Mode

Test without modifying YNAB:
```bash
python src/reconciler_main.py --dry-run --days 7
```

### Test with Mock Data

The scraper includes mock data for development. Set `USE_MOCK_DATA=true` in environment.

### Manual Lambda Test

```bash
aws lambda invoke \
  --function-name amazon-ynab-reconciler \
  --payload '{"dry_run": true, "lookback_days": 7}' \
  response.json
```

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│                 │     │              │     │             │
│  EventBridge    ├────▶│    Lambda    │────▶│   Amazon    │
│  (Daily Trigger)│     │   Function   │     │  (Scraping) │
│                 │     │              │     │             │
└─────────────────┘     └──────┬───────┘     └─────────────┘
                               │
                               │
                        ┌──────▼───────┐
                        │              │
                        │   Matching   │
                        │    Engine    │
                        │              │
                        └──────┬───────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
             ┌──────▼───────┐     ┌──────▼───────┐
             │              │     │              │
             │     YNAB     │     │    Email     │
             │   Updates    │     │   Reports    │
             │              │     │              │
             └──────────────┘     └──────────────┘
```

## Security

- **Credentials**: Stored encrypted in AWS Parameter Store
- **2FA Support**: Handles TOTP-based two-factor authentication
- **No Logging**: Sensitive data excluded from logs
- **Secure Transport**: All API calls use HTTPS

## Future Enhancements

- [ ] Support for Amazon Business accounts
- [ ] Multi-currency transaction handling
- [ ] Interactive approval dashboard
- [ ] Machine learning for improved matching
- [ ] Support for split transactions
- [ ] Integration with other shopping sites
- [ ] Mobile app notifications

## Dependencies

- **playwright**: Web automation for Amazon scraping
- **requests**: YNAB API communication
- **pyotp**: 2FA token generation
- **boto3**: AWS services integration
- **pyyaml**: Configuration management

## License

Private use only - Part of personal automation suite

## Author

Terrance Brandon

---

**Note**: This automation requires careful configuration of credentials and should be monitored regularly to ensure accurate matching. Always review reconciliation reports for accuracy.