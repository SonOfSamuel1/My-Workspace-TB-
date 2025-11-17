# Love Brittany Action Plan Tracker - Setup Guide

Complete setup instructions for the Relationship Tracking Automation system.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Google API Setup](#google-api-setup)
4. [Toggl Track Setup](#toggl-track-setup)
5. [Configuration](#configuration)
6. [Creating Your Tracking Document](#creating-your-tracking-document)
7. [Testing](#testing)
8. [Scheduling Automated Reports](#scheduling-automated-reports)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.9 or higher**
- **Google Account** with Calendar and Docs access
- **Toggl Track Account** (free tier works)
- **Gmail account** for sending reports

---

## Installation

### 1. Navigate to Project Directory

```bash
cd "Life Automations"
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
```

### 3. Activate Virtual Environment

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Google API Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Name it something like "Relationship Tracker"

### Step 2: Enable Required APIs

Enable these three APIs:

1. **Google Calendar API**
   - In Cloud Console: APIs & Services → Library
   - Search "Google Calendar API"
   - Click "Enable"

2. **Google Docs API**
   - Search "Google Docs API"
   - Click "Enable"

3. **Gmail API**
   - Search "Gmail API"
   - Click "Enable"

### Step 3: Create OAuth 2.0 Credentials

1. Go to: APIs & Services → Credentials
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure OAuth consent screen:
   - User Type: External (if not a Google Workspace account)
   - App name: "Love Brittany Tracker"
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Add the following scopes:
     - `https://www.googleapis.com/auth/calendar`
     - `https://www.googleapis.com/auth/documents.readonly`
     - `https://www.googleapis.com/auth/gmail.send`
   - Test users: Add your email address
4. Back to Create OAuth client ID:
   - Application type: **Desktop app**
   - Name: "Relationship Tracker Desktop"
5. Click "Create"
6. Download the credentials JSON file
7. Rename it to `credentials.json`
8. Move it to `credentials/` directory:

```bash
mkdir -p credentials
mv ~/Downloads/credentials.json credentials/
```

---

## Toggl Track Setup

### Step 1: Get API Token

1. Go to [Toggl Track Profile](https://track.toggl.com/profile)
2. Scroll to "API Token" section
3. Copy your API token
4. Save it for later use in `.env`

### Step 2: Find Workspace ID

1. Go to: Settings → Workspace
2. The workspace ID is in the URL: `https://track.toggl.com/[workspace_id]/settings`
3. Copy the workspace ID
4. Save it for later use in `.env`

### Step 3: Create "Love Brittany" Project

1. In Toggl Track, create a new project
2. Name it: **"Love Brittany"** (or customize in config)
3. Choose a color that stands out
4. This project will track all relationship-related time

---

## Configuration

### Step 1: Create Environment File

```bash
cp .env.example .env
```

### Step 2: Edit .env File

Open `.env` in your text editor and update:

```env
# Toggl Track API Configuration
TOGGL_API_TOKEN=your_actual_toggl_api_token_here
TOGGL_WORKSPACE_ID=your_workspace_id_here

# Toggl Sync Settings
TOGGL_SYNC_ENABLED=true
TOGGL_AUTO_SYNC=true
TOGGL_SYNC_RUNNING=false

# Google Calendar Configuration
GOOGLE_CALENDAR_ID=primary
GOOGLE_CREDENTIALS_FILE=credentials/credentials.json
GOOGLE_TOKEN_FILE=credentials/token.pickle

# Timezone
TIMEZONE=America/New_York  # Change to your timezone

# Webhook Configuration (for real-time sync)
WEBHOOK_ENABLED=false
WEBHOOK_PORT=8080
WEBHOOK_SECRET=your_webhook_secret_here

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/sync.log

# Relationship Tracking Configuration
RELATIONSHIP_TRACKING_ENABLED=true
RELATIONSHIP_TRACKING_DOC_ID=  # Will add in next section
RELATIONSHIP_REPORT_EMAIL=your_email@example.com  # Your email
TOGGL_RELATIONSHIP_PROJECT=Love Brittany
```

### Step 3: Update config.yaml

Open `config.yaml` and update the relationship tracking section:

```yaml
relationship_tracking:
  enabled: true

  # Report schedule (default: Saturday 7pm, Wednesday 6:30pm EST)
  schedule:
    - "0 19 * * 6"   # Saturday 7pm
    - "30 18 * * 3"  # Wednesday 6:30pm

  timezone: "America/New_York"  # Change to your timezone

  # Google Doc ID (will add after creating document)
  tracking_doc_id: ""

  # Toggl project name
  toggl_project_name: "Love Brittany"

  # Email settings
  email:
    recipient: "your_email@example.com"  # Your email
    subject_template: "Love Brittany Action Plan Report - {date}"
    include_summary: true
    include_details: true
```

---

## Creating Your Tracking Document

### Step 1: Create Google Doc

1. Go to [Google Docs](https://docs.google.com)
2. Click "Blank" to create a new document
3. Name it: **"Love Brittany Action Plan Tracker"**

### Step 2: Add Template Content

1. Open the file: `RELATIONSHIP_TRACKING_TEMPLATE.md`
2. Copy all the template content (starting from the tracking sections)
3. Paste into your Google Doc
4. Format as needed (keep section headers exactly as shown!)

### Step 3: Get Document ID

1. Look at the URL of your Google Doc
2. Format: `https://docs.google.com/document/d/[DOCUMENT_ID]/edit`
3. Copy the `DOCUMENT_ID` portion
4. Add to `.env`:

```env
RELATIONSHIP_TRACKING_DOC_ID=your_document_id_here
```

5. Also add to `config.yaml`:

```yaml
relationship_tracking:
  tracking_doc_id: "your_document_id_here"
```

---

## Testing

### Step 1: Validate Setup

Run the validation command to check all connections:

```bash
python src/relationship_main.py --validate
```

You should see:
```
✅ Config loaded
✅ Environment loaded
✅ Configuration valid
✅ Calendar connection successful
✅ Docs connection successful - Found document: [Your Doc Title]
✅ Toggl connection successful
✅ Gmail connection successful
✅ ALL VALIDATIONS PASSED!
```

**First Time Setup:**
- The script will open a browser for Google OAuth consent
- Sign in with your Google account
- Grant permissions for Calendar, Docs, and Gmail
- Credentials will be saved to `credentials/token.pickle`

### Step 2: Generate Test Report

Generate a report without sending email:

```bash
python src/relationship_main.py --generate --no-email
```

This will:
- Generate relationship tracking data
- Create HTML report
- Save to `output/` directory
- Display summary in terminal

**Review the HTML file:**
```bash
open output/relationship_report_*.html  # macOS
# or
start output\relationship_report_*.html  # Windows
```

### Step 3: Send Test Email

Send an actual email report:

```bash
python src/relationship_main.py --generate
```

Check your email inbox for the report!

---

## Scheduling Automated Reports

You have three options for automation:

### Option 1: Python Scheduler (Recommended for Testing)

Run the built-in scheduler:

```bash
python src/relationship_scheduler.py
```

This runs continuously and sends reports at:
- Saturday 7:00 PM EST
- Wednesday 6:30 PM EST

**Keep this running:**
- Run in terminal session
- Or use a process manager like `pm2` or `supervisord`
- Or run in a screen/tmux session

**Test the scheduler:**
```bash
python src/relationship_scheduler.py --test
```

### Option 2: Cron (macOS/Linux)

**Edit crontab:**
```bash
crontab -e
```

**Add these lines:**
```bash
# Saturday at 7:00 PM EST (19:00)
0 19 * * 6 cd /full/path/to/Life\ Automations && /full/path/to/venv/bin/python src/relationship_main.py --generate >> logs/cron.log 2>&1

# Wednesday at 6:30 PM EST (18:30)
30 18 * * 3 cd /full/path/to/Life\ Automations && /full/path/to/venv/bin/python src/relationship_main.py --generate >> logs/cron.log 2>&1
```

**Important:**
- Replace `/full/path/to/` with actual paths
- Use absolute paths for both directory and python
- Schedule times are in your system timezone

**Verify cron jobs:**
```bash
crontab -l
```

### Option 3: Task Scheduler (Windows)

1. Open Task Scheduler
2. Create Basic Task
3. **For Saturday report:**
   - Name: "Love Brittany Report - Saturday"
   - Trigger: Weekly → Saturday at 7:00 PM
   - Action: Start a program
   - Program: `C:\full\path\to\venv\Scripts\python.exe`
   - Arguments: `src\relationship_main.py --generate`
   - Start in: `C:\full\path\to\Life Automations`

4. **Repeat for Wednesday:**
   - Name: "Love Brittany Report - Wednesday"
   - Trigger: Weekly → Wednesday at 6:30 PM
   - Same program and arguments

---

## Usage

### Manual Report Generation

**Generate and send report:**
```bash
python src/relationship_main.py --generate
```

**Generate without sending:**
```bash
python src/relationship_main.py --generate --no-email
```

**Validate setup:**
```bash
python src/relationship_main.py --validate
```

### Updating Your Tracking Document

1. Open your Google Doc
2. Add new entries in each section
3. Use format: `□ Date: YYYY-MM-DD | Details`
4. Mark completed with `☑` or `[x]`

### Tracking Time in Toggl

1. Start timer in Toggl
2. Add description of activity
3. Assign to "Love Brittany" project
4. Add tags if desired (optional)
5. Stop timer when done

### Calendar Events

**Date Nights:**
- Title: "Date Night" or "Date Night with Brittany"
- Add: "Reservation confirmed at [restaurant]" in description

**Babysitters:**
- Title: "Babysitter - [Name]"
- Same date/time as date night

**Daily Gaps:**
- Title: "Love Action" or "Brittany Time"
- 10-minute events
- Add notes about what you did

---

## Troubleshooting

### "No module named..."

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### "Failed to validate credentials"

**For Google APIs:**
```bash
# Delete token and re-authenticate
rm credentials/token.pickle
python src/relationship_main.py --validate
```

**For Toggl:**
- Check API token in `.env`
- Verify workspace ID
- Test at: https://track.toggl.com/profile

### "Document not found" or "Permission denied"

1. Check Document ID in `.env` and `config.yaml`
2. Ensure document is accessible with your Google account
3. Re-authenticate if needed

### "No events found" in calendar

1. Check search terms in `config.yaml`
2. Verify calendar ID is correct
3. Ensure events exist with matching titles
4. Check timezone settings

### Email not sending

1. Verify Gmail API is enabled
2. Check recipient email in `.env`
3. Re-authenticate Gmail permissions
4. Check logs: `tail -f logs/relationship.log`

### Report shows "N/A" for many fields

1. Check your tracking document formatting
2. Ensure dates are in YYYY-MM-DD format
3. Verify section headers match exactly: `[GIFTS]`, `[LETTERS]`, etc.
4. Add some test data to each section

---

## Maintenance

### Weekly
- Check logs for errors: `tail -f logs/relationship.log`
- Review generated reports
- Update tracking document

### Monthly
- Check Google API quotas (rarely an issue)
- Review Toggl project time stats
- Clear old report files: `rm output/relationship_report_*.html`

### Quarterly
- Review and update goals in tracking document
- Adjust schedule if needed in `config.yaml`
- Rotate API keys if desired

---

## Security Best Practices

1. **Never commit credentials**
   - `.env` and `credentials/` are in `.gitignore`
   - Keep credentials secure

2. **Token management**
   - `token.pickle` stores OAuth tokens
   - Delete and re-authenticate if compromised

3. **Email security**
   - Reports contain personal information
   - Send only to your own email
   - Use secure email provider

4. **Document access**
   - Keep tracking document private
   - Don't share Document ID publicly

---

## Next Steps

Once everything is set up:

1. **Fill out your tracking document** with current data
2. **Schedule your first 12 date nights** in Google Calendar
3. **Start tracking time** in Toggl for Love Brittany project
4. **Set up automated scheduling** (cron or Task Scheduler)
5. **Review your first report** when it arrives!

---

## Support

For issues:
1. Check logs: `logs/relationship.log`
2. Run validation: `python src/relationship_main.py --validate`
3. Review this guide
4. Check `RELATIONSHIP_TRACKING_TEMPLATE.md` for formatting

---

**Remember: This system is here to support you, not create pressure. Focus on progress and consistency!** 💝
