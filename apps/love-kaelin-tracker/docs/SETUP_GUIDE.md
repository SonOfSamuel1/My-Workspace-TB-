# Love Kaelin Development Tracker - Complete Setup Guide

This guide walks you through setting up the Love Kaelin Development Tracker from scratch.

## Overview

The Love Kaelin tracker monitors your father-daughter relationship and development activities, generating weekly HTML email reports with comprehensive analytics and alerts.

## Architecture

The system consists of:

1. **Data Collection**
   - Google Calendar (play time, daddy days, field trips)
   - Google Docs (tracking document with all metrics)
   - Toggl Track (time tracking)

2. **Processing**
   - `kaelin_tracker.py` - Collects and analyzes data
   - `kaelin_report.py` - Generates beautiful HTML reports

3. **Delivery**
   - Gmail API - Sends HTML email reports
   - Local files - Saves reports for review

## Prerequisites

### Required

- **Python 3.8 or higher**
- **Google Account** with access to:
  - Google Calendar
  - Google Docs
  - Gmail
- **Toggl Track Account** (free tier is fine)

### Optional

- AWS Account (for Lambda deployment)
- Cron access (for scheduling)

## Installation

### Step 1: Install Dependencies

The Love Kaelin tracker shares dependencies with Love Brittany tracker:

```bash
# From workspace root
cd "My Workspace"

# Install Python dependencies (if not already installed)
pip install -r requirements.txt

# Or install specific packages
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
pip install pyyaml pytz requests
```

### Step 2: Google Cloud Setup

If you already have Love Brittany tracker set up, **skip to Step 3** - you'll use the same credentials!

Otherwise:

1. **Create Google Cloud Project**
   - Go to https://console.cloud.google.com/
   - Create a new project or use existing
   - Note the project ID

2. **Enable Required APIs**
   - Google Calendar API
   - Google Docs API
   - Gmail API

   ```bash
   # Or use gcloud CLI
   gcloud services enable calendar-json.googleapis.com
   gcloud services enable docs.googleapis.com
   gcloud services enable gmail.googleapis.com
   ```

3. **Create OAuth 2.0 Credentials**
   - Go to APIs & Services > Credentials
   - Create OAuth 2.0 Client ID
   - Application type: Desktop app
   - Download JSON file

4. **Save Credentials**
   ```bash
   # From workspace root
   mkdir -p credentials
   # Copy downloaded file to:
   cp ~/Downloads/client_secret_*.json credentials/credentials.json
   ```

### Step 3: Toggl Setup

1. **Get API Token**
   - Log into Toggl Track
   - Go to Profile Settings
   - Scroll to API Token
   - Copy the token

2. **Create Project** (Optional but recommended)
   - Create new project called "Love Kaelin"
   - Note the project name

### Step 4: Create Tracking Document

1. **Open Google Docs**
   - Go to https://docs.google.com/
   - Click "Blank document"

2. **Copy Template**
   - Open `apps/love-kaelin-tracker/docs/KAELIN_TRACKING_TEMPLATE.md`
   - Copy all content
   - Paste into new Google Doc
   - Format as desired (optional)

3. **Get Document ID**
   - Look at URL: `https://docs.google.com/document/d/DOCUMENT_ID_HERE/edit`
   - Copy the `DOCUMENT_ID_HERE` part
   - Save it for configuration

4. **Name the Document**
   - Rename to "Love Kaelin Development Tracking"

### Step 5: Configure the Tracker

1. **Update config.yaml**

   ```bash
   cd apps/love-kaelin-tracker
   nano config.yaml
   ```

   Update these values:
   ```yaml
   kaelin_tracking:
     enabled: true
     tracking_doc_id: "PASTE_YOUR_DOCUMENT_ID"
     toggl_project_name: "Love Kaelin"
     email:
       recipient: "your-email@example.com"
   ```

2. **Set Environment Variables**

   If sharing credentials with Love Brittany tracker:
   ```bash
   # The system will automatically find the shared .env file
   # No action needed!
   ```

   If creating separate setup:
   ```bash
   cd apps/love-kaelin-tracker
   cat > .env << EOF
   GOOGLE_CREDENTIALS_FILE=../../credentials/credentials.json
   GOOGLE_TOKEN_FILE=../../credentials/token.pickle
   TOGGL_API_TOKEN=your_toggl_api_token_here
   EOF
   ```

### Step 6: Validate Setup

```bash
cd apps/love-kaelin-tracker
python3 src/kaelin_main.py --validate
```

Expected output:
```
====================================== ==============================
KAELIN DEVELOPMENT TRACKING SETUP VALIDATION
============================================================

📋 Loading configuration...
✅ Config loaded
🔐 Loading environment variables...
✅ Environment loaded
✔️  Validating configuration...
✅ Configuration valid

📅 Testing Google Calendar connection...
✅ Calendar connection successful
📄 Testing Google Docs connection...
✅ Docs connection successful - Found document: Love Kaelin Development Tracking
⏱️  Testing Toggl connection...
✅ Toggl connection successful
📧 Testing Gmail connection...
✅ Gmail connection successful

============================================================
✅ ALL VALIDATIONS PASSED!
============================================================
```

If validation fails, see Troubleshooting section below.

### Step 7: Initial Authentication

The first time you run validation or generate a report, you'll need to authenticate:

1. Browser window will open automatically
2. Select your Google account
3. Click "Allow" for Calendar, Docs, and Gmail access
4. Close the browser when done
5. Token will be saved to `credentials/token.pickle`

### Step 8: Generate First Report

```bash
python3 src/kaelin_main.py --generate --no-email
```

This will:
- Collect data from calendar, docs, and Toggl
- Generate HTML report
- Save to `output/kaelin_report_YYYYMMDD_HHMMSS.html`
- NOT send email (use `--generate` without `--no-email` to send)

### Step 9: Review Report

```bash
# On Mac:
open output/kaelin_report_*.html

# On Linux:
xdg-open output/kaelin_report_*.html

# Or manually open in browser
```

Review all sections and verify data is being collected correctly.

## Configuration Reference

### config.yaml Structure

```yaml
kaelin_tracking:
  enabled: true                    # Master on/off switch
  tracking_doc_id: "DOC_ID"        # Google Doc ID
  toggl_project_name: "Love Kaelin"  # Toggl project name
  timezone: "America/New_York"     # Report timezone

  email:
    recipient: "email@example.com"
    subject_template: "Love Kaelin Development Report - {date}"

  tracking_periods:
    play_time_rolling_days: 100    # Rolling average window
    play_days_per_week_target: 5   # Target play days per week
    play_hours_per_day_target: 2.0 # Target hours per play day
    new_game_frequency_days: 30    # How often to introduce games
    spiritual_planning_months: 6   # Spiritual plan horizon
    field_trips_per_year_target: 3 # Annual field trip goal
    daddy_day_quarters_ahead: 4    # How far to plan ahead

  alerts:
    no_play_critical_days: 3       # Days without play = critical
    no_play_warning_days: 2        # Days without play = warning
    play_average_warning_threshold: 70  # % of target
    game_overdue_warning_days: 7
    teaching_warning_threshold: 15
```

### Environment Variables

```bash
# Google API Credentials
GOOGLE_CREDENTIALS_FILE=path/to/credentials.json
GOOGLE_TOKEN_FILE=path/to/token.pickle

# Toggl API
TOGGL_API_TOKEN=your_token_here
```

## Using the Tracker

### Daily Tracking

**Method 1: Calendar Events**
Create events with these keywords:
- "play with kaelin"
- "kaelin time"
- "daddy daughter time"

**Method 2: Toggl Tracking**
- Start timer when playing with Kaelin
- Use project "Love Kaelin"
- Add activity descriptions

**Method 3: Manual Logging**
Update tracking document play time section:
```
2025-01-17 | Duration: 2.5 hours | Activities: Building blocks, reading
```

### Weekly Review

Every Sunday at 5am EST (or on demand):
1. Report generates automatically
2. Email arrives with full report
3. Review alerts and metrics
4. Plan week based on insights

### Monthly Tasks

- Introduce a new game
- Update tracking document
- Review Jesus teachings progress
- Plan upcoming activities

### Quarterly Tasks

- Schedule Daddy Days for next 4 quarters
- Review development programs
- Update spiritual development plan
- Plan field trips

## Scheduling

### Option 1: Cron (Mac/Linux)

```bash
# Edit crontab
crontab -e

# Add this line for Sunday 5am EST
0 5 * * 0 cd /path/to/apps/love-kaelin-tracker && python3 src/kaelin_main.py --generate
```

### Option 2: Manual Generation

```bash
# Generate and send report
python3 src/kaelin_main.py --generate

# Generate without sending email
python3 src/kaelin_main.py --generate --no-email
```

### Option 3: Scheduler Script (Future)

A dedicated scheduler script similar to Love Brittany tracker can be created.

## Troubleshooting

### "Module not found" Error

```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client pyyaml pytz requests
```

### "No module named 'yaml'"

```bash
pip install pyyaml
```

### "Configuration file not found"

Make sure you're running from the correct directory:
```bash
cd apps/love-kaelin-tracker
python3 src/kaelin_main.py --validate
```

### "Tracking document not found"

1. Check document ID in config.yaml
2. Ensure document exists and is accessible
3. Verify Google account has access
4. Run validation to diagnose

### "Calendar connection failed"

1. Verify Calendar API is enabled
2. Check credentials file exists
3. Re-authenticate: delete `credentials/token.pickle` and run again
4. Review scopes in credentials

### "Toggl connection failed"

1. Verify API token is correct
2. Check token has not expired
3. Ensure token is in .env or environment variables

### "No play time recorded"

This is normal if you haven't tracked any activities yet:
1. Add calendar events with proper keywords
2. Update tracking document manually
3. Start Toggl tracking

### Authentication Issues

If authentication fails:
```bash
# Remove existing token
rm ../../credentials/token.pickle

# Run validation again
python3 src/kaelin_main.py --validate

# Browser will open for re-authentication
```

## Advanced Configuration

### Custom Calendar Search Terms

Edit `config.yaml`:
```yaml
calendar:
  play_time_terms:
    - "play with kaelin"
    - "kaelin playtime"
    - "daughter time"
  daddy_day_terms:
    - "daddy day"
    - "special kaelin day"
```

### Adjust Targets

Modify targets based on your schedule:
```yaml
tracking_periods:
  play_days_per_week_target: 4  # More realistic for busy weeks
  play_hours_per_day_target: 1.5
```

### Custom Jesus Teachings

Add or modify teachings in `config.yaml`:
```yaml
jesus_teachings:
  teachings:
    - "Your custom teaching here"
    - "Another teaching"
```

### Alert Thresholds

Make alerts more or less strict:
```yaml
alerts:
  no_play_critical_days: 4  # More lenient
  play_average_warning_threshold: 80  # More strict
```

## Sharing with Love Brittany Tracker

The Love Kaelin tracker is designed to work alongside Love Brittany tracker:

**Shared:**
- Google API credentials
- Environment variables (.env)
- Service modules (calendar, docs, email, toggl)

**Separate:**
- Configuration files (config.yaml)
- Tracking documents
- Reports and metrics
- Email schedules

## Security Best Practices

1. **Never commit credentials**
   - credentials.json
   - token.pickle
   - .env files

2. **Protect API tokens**
   - Store in environment variables
   - Don't share publicly
   - Rotate periodically

3. **Limit OAuth scopes**
   - Only request needed permissions
   - Review granted scopes regularly

4. **Backup tracking data**
   - Export Google Doc regularly
   - Save report history
   - Archive important data

## Support

For issues:
1. Run validation: `python3 src/kaelin_main.py --validate`
2. Check logs: `tail -f logs/kaelin_tracker.log`
3. Review README.md
4. Check Love Brittany tracker if sharing services

## Next Steps

After setup:
1. ✅ Review QUICK_START.md for daily usage
2. ✅ Customize config.yaml for your needs
3. ✅ Set up calendar integration
4. ✅ Start tracking activities
5. ✅ Schedule automatic reports
6. ✅ Review weekly reports and act on alerts

---

**Setup Version:** 1.0.0
**Last Updated:** 2025-01-17

Made with 💖 for Kaelin's development journey
