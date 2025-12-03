# Sleep Eight Daily Reporter

Automated daily sleep reports from your Eight Sleep mattress, delivered to your email via AWS Lambda and SES.

## Features

- Daily sleep score and quality assessment
- Time asleep tracking
- Sleep quality breakdown (fitness, routine scores)
- Biometrics (heart rate, HRV, breath rate)
- Temperature monitoring (bed and room)
- Personalized insights based on your sleep data
- Beautiful HTML email reports
- AWS Lambda for serverless automation

## Quick Start

### Prerequisites

- Python 3.9+
- Eight Sleep account and Pod mattress
- AWS account with SES configured
- AWS CLI configured locally

### Installation

1. **Navigate to the app directory:**
   ```bash
   cd apps/sleep-eight-reporter
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Validate setup:**
   ```bash
   python src/sleep_main.py --validate
   ```

5. **Generate a test report:**
   ```bash
   python src/sleep_main.py --generate --no-email
   ```

## Configuration

### Environment Variables (.env)

| Variable | Description | Required |
|----------|-------------|----------|
| `EIGHT_SLEEP_EMAIL` | Your Eight Sleep account email | Yes |
| `EIGHT_SLEEP_PASSWORD` | Your Eight Sleep account password | Yes |
| `SLEEP_REPORT_EMAIL` | Email to receive reports | Yes |
| `SES_SENDER_EMAIL` | AWS SES verified sender email | Yes |
| `AWS_REGION` | AWS region (default: us-east-1) | No |

### Config File (config.yaml)

```yaml
sleep_report:
  enabled: true
  timezone: "America/New_York"
  report:
    include_insights: true
    include_temperature: true
    include_biometrics: true
```

## Usage

### Local Execution

```bash
# Validate configuration
python src/sleep_main.py --validate

# Generate and send report
python src/sleep_main.py --generate

# Generate without sending email
python src/sleep_main.py --generate --no-email
```

### AWS Lambda Deployment

See [docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md) for detailed instructions.

Quick deploy:
```bash
./scripts/deploy-lambda-zip.sh
```

## Report Contents

The daily email report includes:

1. **Sleep Score** - Overall sleep quality (0-100)
2. **Quality Assessment** - Excellent/Good/Fair/Needs Improvement
3. **Time Asleep** - Total sleep duration
4. **Quality Breakdown**
   - Fitness Score
   - Routine Score
   - HRV
5. **Biometrics**
   - Average Heart Rate
   - Breath Rate
6. **Temperature**
   - Bed Temperature
   - Room Temperature
7. **Insights** - Personalized recommendations

## Architecture

```
sleep-eight-reporter/
├── src/
│   ├── eight_sleep_service.py  # Eight Sleep API client
│   ├── sleep_report.py         # HTML report generator
│   ├── ses_email_sender.py     # AWS SES email sender
│   └── sleep_main.py           # Main orchestration
├── lambda_handler.py           # AWS Lambda entry point
├── config.yaml                 # Application configuration
├── requirements.txt            # Python dependencies
└── scripts/
    ├── deploy-lambda-zip.sh    # Lambda deployment
    └── setup-parameters.sh     # Parameter Store setup
```

## API Reference

### Eight Sleep Data

The app uses the [pyeight](https://github.com/mezz64/pyEight) library to access Eight Sleep data:

- Sleep scores (overall, fitness, routine)
- Time metrics (duration, latency)
- Biometrics (HR, HRV, breath rate)
- Temperature (bed, room)
- Presence detection

### AWS Services Used

- **Lambda** - Serverless function execution
- **EventBridge** - Scheduled triggers (daily at 7 AM)
- **SES** - Email delivery
- **Parameter Store** - Secure credential storage

## Troubleshooting

### Eight Sleep Connection Issues

```
Failed to connect to Eight Sleep: [error]
```

1. Verify your Eight Sleep credentials in `.env`
2. Check that pyeight is installed: `pip install pyeight`
3. Ensure your Eight Sleep account is active

### Email Not Sending

1. Verify SES sender email is verified
2. Check AWS credentials have SES permissions
3. Verify recipient email (if in SES sandbox)

### Lambda Timeout

If Lambda times out:
1. Increase timeout to 60-120 seconds
2. Increase memory to 512MB

## Contributing

This is part of the My-Workspace monorepo. See the root README for contribution guidelines.

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- [pyeight](https://github.com/mezz64/pyEight) - Eight Sleep Python library
- [Eight Sleep](https://www.eightsleep.com/) - Smart mattress technology
