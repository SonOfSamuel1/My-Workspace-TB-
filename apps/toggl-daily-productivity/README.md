# Toggl Daily Productivity Report

Automated daily email reports showing your Toggl time tracking performance metrics.

## Features

- **Twice-daily reports** at 6:00 AM and 7:00 PM (except Saturday)
- **Saturday special schedule** - only evening report at 7:30 PM
- **Rolling metrics** - 7-day, 30-day, and 90-day averages
- **Category breakdowns** - Personal, W2 Job, P1 Total
- **Goal tracking** - 6 hours daily (360 minutes), Saturday off
- **AWS SES email delivery** - reliable, cost-effective

## Schedule

| Day | Morning (6 AM) | Evening (7 PM) |
|-----|----------------|----------------|
| Mon-Fri | Yes | Yes |
| Saturday | No | 7:30 PM |
| Sunday | Yes | Yes |

## Quick Start

```bash
# Navigate to app
cd apps/toggl-daily-productivity

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# - TOGGL_API_TOKEN (from track.toggl.com/profile)
# - TOGGL_WORKSPACE_ID
# - AWS credentials for SES

# Install dependencies
pip install -r requirements.txt

# Validate configuration
python src/main.py --validate

# Generate test report (no email sent)
python src/main.py --test

# Generate and send report now
python src/main.py --generate

# Run as scheduled daemon
python src/main.py --schedule
```

## Configuration

### config.yaml

Edit `config.yaml` to customize:

1. **Daily goal** - default 360 minutes (6 hours)
2. **Categories** - map your Toggl projects to Personal/W2/P1
3. **Email settings** - recipient and subject template

### Environment Variables

| Variable | Description |
|----------|-------------|
| `TOGGL_API_TOKEN` | Your Toggl API token |
| `TOGGL_WORKSPACE_ID` | Your Toggl workspace ID |
| `AWS_ACCESS_KEY_ID` | AWS credentials for SES |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials for SES |
| `AWS_REGION` | AWS region (default: us-east-1) |
| `REPORT_RECIPIENT` | Email recipient |
| `SES_SENDER_EMAIL` | Sender email (must be SES verified) |

## Report Contents

### Header Stats
- Daily Goal (360 mins)
- Yesterday's Total with percentage
- Rolling 7-day average
- Rolling 30-day average

### Rolling 7 Days Table
Daily breakdown showing:
- P1 Total (time and minutes)
- W2 Total (time and minutes)
- Combined total
- Goal attainment score

### Category Breakdown Tables
For 7-day, 30-day, and 90-day periods:
- Effort Actual vs Goal
- Attainment percentage
- Color coding (red < 50%, yellow 50-80%, green > 80%)

## Project Structure

```
toggl-daily-productivity/
├── src/
│   ├── main.py                 # CLI entry point
│   ├── productivity_service.py # Metrics calculation
│   ├── report_generator.py     # HTML report generation
│   ├── scheduler.py            # Schedule management
│   ├── toggl_service.py        # Toggl API client
│   └── ses_email_sender.py     # AWS SES email sender
├── templates/
├── logs/
├── cache/
├── config.yaml
├── .env.example
├── requirements.txt
└── README.md
```

## CLI Commands

```bash
# Validate configuration
python src/main.py --validate

# Generate report without sending
python src/main.py --test

# Generate and send report
python src/main.py --generate

# Run as scheduler daemon
python src/main.py --schedule

# Set log level
python src/main.py --generate --log-level DEBUG
```

## Customizing Categories

Edit `config.yaml` to map your Toggl projects:

```yaml
categories:
  personal:
    projects:
      - "Personal Projects"
      - "Side Hustle"
      - "Learning"
    daily_goal: 60

  w2_job:
    projects:
      - "Client Work"
      - "Day Job"
    daily_goal: 240

  p1_total:
    projects:
      - "Important Tasks"
      - "Priority 1"
    daily_goal: 60
```

## Troubleshooting

### Toggl credentials invalid
1. Verify your API token at track.toggl.com/profile
2. Check workspace ID is correct
3. Run `python src/main.py --validate`

### Email not sending
1. Verify AWS credentials have SES permissions
2. Check sender email is verified in SES
3. Ensure you're not in SES sandbox (or recipient is verified)

### No data in report
1. Check you have time entries in Toggl for the period
2. Verify project names in config match Toggl exactly
3. Check timezone settings

## Support

For issues, check:
1. Logs in `logs/productivity.log`
2. Run with `--log-level DEBUG` for more detail
3. Validate config with `--validate`
