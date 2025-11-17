# Toggl Daily Report - Quick Start Guide

Get your daily Toggl reports running in 15 minutes!

## Prerequisites Checklist

- [ ] Python 3.9+ installed
- [ ] Toggl Track account
- [ ] Google account (for Gmail)
- [ ] Toggl API token (get from https://track.toggl.com/profile)
- [ ] Toggl Workspace ID

## Step-by-Step Setup

### 1. Install Dependencies (2 minutes)

```bash
cd apps/toggl-daily-report

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Get Toggl Credentials (3 minutes)

#### API Token
1. Go to https://track.toggl.com/profile
2. Scroll to "API Token" section
3. Click "Click to reveal" and copy token

#### Workspace ID
1. Go to https://track.toggl.com/
2. Look at URL: `https://track.toggl.com/timer/[WORKSPACE_ID]`
3. Copy the workspace ID number

### 3. Get Google Gmail Credentials (5 minutes)

1. Go to https://console.cloud.google.com/
2. Create new project: "Toggl Daily Report"
3. Enable Gmail API:
   - APIs & Services → Enable APIs
   - Search "Gmail API" → Enable
4. Create credentials:
   - APIs & Services → Credentials → Create Credentials
   - Choose "OAuth client ID"
   - Application type: "Desktop app"
   - Name: "Toggl Daily Report"
   - Click "Create"
5. Download JSON file
6. Save as `credentials/credentials.json`

### 4. Configure Application (2 minutes)

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env  # or use your favorite editor
```

Fill in:
```bash
TOGGL_API_TOKEN=your_toggl_token_here
TOGGL_WORKSPACE_ID=your_workspace_id_here
REPORT_RECIPIENT_EMAIL=your_email@example.com
```

Edit `config.yaml` if needed:
- Change `daily_goal_hours` (default: 8.0)
- Change `delivery_hour` (default: 18 = 6 PM)
- Adjust `active_days` for weekday-only reports

### 5. First Run & Authentication (3 minutes)

```bash
# Authenticate with Google (browser will open)
python src/toggl_daily.py --validate
```

**What happens:**
1. Browser opens for Google sign-in
2. Grant permissions to send emails
3. `token.pickle` file created automatically
4. Validates Toggl and Gmail credentials

**Expected output:**
```
✓ Toggl credentials validated
✓ Gmail credentials validated
✓ Setup validation complete
```

### 6. Test Report Generation (1 minute)

```bash
# Generate test report (saves to file)
python src/toggl_daily.py --save test_report.html

# Open test_report.html in browser to preview
```

### 7. Send First Report! (1 minute)

```bash
# Generate and send actual email
python src/toggl_daily.py --generate
```

Check your email! You should receive your first Toggl daily report.

---

## Troubleshooting

### "No time entries found"
- Make sure you tracked time in Toggl today
- Verify workspace ID is correct
- Try with a specific date: `--date 2025-11-15`

### "Failed to validate Gmail credentials"
- Ensure `credentials.json` is in `credentials/` directory
- Delete `token.pickle` and run `--validate` again
- Check Gmail API is enabled in Google Cloud Console

### "TOGGL_API_TOKEN not found"
- Make sure `.env` file exists (copy from `.env.example`)
- Verify token is correct (no extra spaces)
- Check you're in the right directory

### Module import errors
- Activate virtual environment: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

---

## What's Next?

### Manual Daily Reports
Run this command daily:
```bash
python src/toggl_daily.py --generate
```

### Automated with Cron (Linux/Mac)
```bash
# Edit crontab
crontab -e

# Add line for 6 PM daily
0 18 * * * cd /path/to/toggl-daily-report && venv/bin/python src/toggl_daily.py --generate
```

### Automated with AWS Lambda (Recommended)
See **AWS Deployment** section in README.md for:
- Lambda function setup
- EventBridge scheduling
- Parameter Store configuration
- Cost: < $1/month (free tier eligible)

---

## Quick Commands Reference

```bash
# Validate setup
python src/toggl_daily.py --validate

# Generate and send report
python src/toggl_daily.py --generate

# Generate for specific date
python src/toggl_daily.py --generate --date 2025-11-15

# Save to file (testing)
python src/toggl_daily.py --save report.html

# Verbose output
python src/toggl_daily.py --generate --verbose
```

---

## Daily Workflow

1. Track time in Toggl throughout the day
2. At 6 PM (or your configured time):
   - Report automatically generates
   - Email sent to your inbox
3. Review metrics:
   - Did you hit your daily goal?
   - How much was billable?
   - Which projects consumed most time?
   - How's your week tracking?

---

## Need Help?

- Check `logs/daily_report.log` for errors
- Review main README.md for detailed docs
- Verify all credentials are correct
- Try test report first before sending email

---

**Setup Time: ~15 minutes**
**Daily Time: 0 minutes (automated!)**

Enjoy your automated Toggl daily reports! 🎉
