# Credit Card Rewards Tracker

Track and optimize credit card rewards across multiple issuers. Get weekly email reports, CLI dashboard access, and intelligent recommendations for maximizing your rewards.

## Features

- **Multi-Program Tracking**: Track Chase Ultimate Rewards, Amex MR, Capital One Miles, cash back, and more
- **Redemption Logging**: Log redemptions with value received to calculate cents-per-point (cpp)
- **Annual Fee ROI**: Calculate if annual fees are worth it based on rewards earned
- **Category Optimization**: Get recommendations for which card to use per spending category
- **Weekly Email Reports**: Automated HTML email summaries with balances and tips
- **CLI Dashboard**: On-demand terminal interface for quick lookups
- **AWS Lambda Ready**: Deploy for scheduled automated reports

## Quick Start

### 1. Install Dependencies

```bash
cd apps/credit-card-rewards-tracker
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy and edit environment file
cp .env.example .env

# Edit .env with your email settings
REWARDS_REPORT_EMAIL=your_email@example.com
```

### 3. Validate Setup

```bash
python src/rewards_main.py --validate
```

### 4. Add Your Cards

```bash
python src/rewards_main.py --add-card
```

Follow the interactive prompts to add each credit card.

### 5. Update Balances

```bash
python src/rewards_main.py --add-balance
```

### 6. View Dashboard

```bash
python src/rewards_main.py --dashboard
```

## CLI Commands

### Validation & Setup
```bash
python src/rewards_main.py --validate       # Validate configuration
```

### Dashboard Views
```bash
python src/rewards_main.py --dashboard              # Interactive dashboard
python src/rewards_main.py --dashboard --balances   # View balances only
python src/rewards_main.py --dashboard --recommendations  # Category recommendations
python src/rewards_main.py --dashboard --fees       # Annual fee analysis
```

### Data Entry
```bash
python src/rewards_main.py --add-card        # Add new credit card
python src/rewards_main.py --add-balance     # Update rewards balance
python src/rewards_main.py --add-redemption  # Log a redemption
```

### Quick Lookups
```bash
python src/rewards_main.py --best-card dining    # Best card for dining
python src/rewards_main.py --best-card groceries # Best card for groceries
python src/rewards_main.py --roi                 # Annual fee ROI analysis
```

### Report Generation
```bash
python src/rewards_main.py --generate            # Generate and send weekly report
python src/rewards_main.py --generate --no-email # Generate report without sending
```

## Project Structure

```
credit-card-rewards-tracker/
├── src/
│   ├── rewards_main.py      # Main entry point with CLI
│   ├── data_manager.py      # JSON file persistence
│   ├── card_service.py      # Card management and recommendations
│   ├── rewards_analyzer.py  # ROI and optimization analysis
│   ├── cli_dashboard.py     # Rich terminal dashboard
│   └── rewards_report.py    # HTML email generation
├── data/                    # JSON data files (gitignored)
│   ├── cards.json
│   ├── rewards_balances.json
│   ├── transactions.json
│   ├── redemptions.json
│   └── annual_summary.json
├── templates/               # Email templates
├── config.yaml              # Configuration
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
├── lambda_handler.py        # AWS Lambda entry point
└── README.md
```

## Data Models

### Cards (`data/cards.json`)
```json
{
  "cards": [{
    "id": "chase-freedom-flex-1234",
    "issuer": "chase",
    "name": "Chase Freedom Flex",
    "last_four": "1234",
    "reward_type": "points",
    "reward_program": "chase_ultimate_rewards",
    "annual_fee": 0,
    "base_reward_rate": 1.0,
    "category_multipliers": [
      {"category": "dining", "multiplier": 3.0},
      {"category": "drugstores", "multiplier": 3.0}
    ]
  }],
  "reward_programs": {
    "chase_ultimate_rewards": {
      "name": "Chase Ultimate Rewards",
      "point_value_cents": 1.5,
      "transfer_partners": ["hyatt", "united", "southwest"]
    }
  }
}
```

### Balances (`data/rewards_balances.json`)
```json
{
  "balances": {
    "chase_ultimate_rewards": {
      "points": 85420,
      "value_cents": 128130,
      "last_updated": "2025-12-08T15:30:00Z"
    }
  }
}
```

### Redemptions (`data/redemptions.json`)
```json
{
  "redemptions": [{
    "id": "red_001",
    "date": "2025-11-15",
    "program": "chase_ultimate_rewards",
    "points_redeemed": 50000,
    "redemption_type": "transfer_partner",
    "partner": "hyatt",
    "value_received_cents": 100000,
    "cents_per_point": 2.0,
    "notes": "2 nights at Park Hyatt NYC"
  }]
}
```

## Configuration

### config.yaml

Key configuration options:

```yaml
rewards_tracker:
  enabled: true

  # Weekly report schedule
  schedule:
    day: "sunday"
    time: "09:00"
    timezone: "America/New_York"

  # Point valuations (cents per point)
  point_valuations:
    chase_ultimate_rewards: 1.5
    amex_membership_rewards: 1.0

  # Alert thresholds
  alerts:
    annual_fee_warning_days: 60
    min_acceptable_roi: 100
```

### Environment Variables

Required in `.env`:
- `REWARDS_REPORT_EMAIL` - Email recipient for weekly reports
- `SES_SENDER_EMAIL` - AWS SES verified sender email
- `AWS_REGION` - AWS region (default: us-east-1)

## Weekly Report Contents

The weekly email report includes:

1. **Total Rewards Value** - Combined value across all programs
2. **Current Balances** - Points/cash by program with estimated values
3. **Best Card by Category** - Optimization recommendations
4. **Recent Redemptions** - Last 5 redemptions with cpp analysis
5. **Upcoming Annual Fees** - Fees due in next 90 days
6. **Annual Fee ROI** - Net value from cards with fees
7. **Optimization Tips** - Actionable suggestions

## AWS Lambda Deployment

### Parameter Store Setup

Create these parameters in AWS Parameter Store:
- `/rewards-tracker/email-recipient`
- `/rewards-tracker/sender-email`

### Lambda Configuration
- Runtime: Python 3.11
- Handler: `lambda_handler.lambda_handler`
- Timeout: 60 seconds
- Memory: 256 MB

### EventBridge Schedule
Create an EventBridge rule with cron expression:
```
cron(0 14 ? * SUN *)  # Sunday 9 AM ET (14:00 UTC)
```

### IAM Permissions
Lambda role needs:
- `ssm:GetParameter` for Parameter Store
- `ses:SendEmail` for sending reports
- `s3:GetObject` / `s3:PutObject` if using S3 for data

## Optimization Tips

### Maximize Category Bonuses
Use the `--best-card` command before making purchases:
```bash
python src/rewards_main.py --best-card dining
python src/rewards_main.py --best-card groceries
python src/rewards_main.py --best-card gas
```

### Track Redemption Value
Always log redemptions to track your average cpp:
```bash
python src/rewards_main.py --add-redemption
```

Target redemption values:
- Cash back / statement credit: 1.0 cpp
- Travel portal: 1.25-1.5 cpp
- Transfer partners: 1.5-2.5+ cpp

### Annual Fee Strategy
Review annual fee cards 60 days before renewal:
1. Calculate ROI with `--roi` command
2. Call retention line for offers
3. Consider product change if ROI < 100%

## Future Enhancements

- **Plaid Integration**: Automatic transaction sync from bank accounts
- **Transfer Partner Valuations**: Real-time partner point values
- **Spending Analysis**: Track spending by category over time
- **Goal Setting**: Set and track redemption goals

## Troubleshooting

### No cards showing
Add cards first: `python src/rewards_main.py --add-card`

### Balance not updating
Manually update: `python src/rewards_main.py --add-balance`

### Email not sending
1. Verify AWS SES sender email is verified
2. Check AWS credentials are configured
3. Verify recipient email in `.env`

### Dashboard not displaying
Ensure `rich` library is installed: `pip install rich`

## License

MIT License - See LICENSE file for details.

---

**Last Updated**: December 2025
