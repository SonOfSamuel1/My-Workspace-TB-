# Love Brittany Action Plan - Quick Start

Get your relationship tracking system running in under 10 minutes!

## Prerequisites Checklist

- [ ] Python 3.9+ installed
- [ ] Google Account with Calendar, Docs, Gmail
- [ ] Toggl Track account
- [ ] 10 minutes of focused time

---

## Step-by-Step Setup

### 1. Install (2 minutes)

```bash
cd "Life Automations"
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Google Cloud Setup (3 minutes)

**Quick Path:**
1. Go to: https://console.cloud.google.com/
2. Create project: "Relationship Tracker"
3. Enable APIs:
   - Google Calendar API
   - Google Docs API
   - Gmail API
4. Create OAuth credentials → Desktop app
5. Download → Rename to `credentials.json`
6. Move to: `credentials/credentials.json`

**Full details:** See `RELATIONSHIP_SETUP_GUIDE.md`

### 3. Toggl Setup (1 minute)

1. Get API token: https://track.toggl.com/profile
2. Find workspace ID in URL
3. Create project: "Love Brittany"

### 4. Configuration (2 minutes)

```bash
cp .env.example .env
nano .env  # or use your text editor
```

**Required values:**
```env
TOGGL_API_TOKEN=your_token_here
TOGGL_WORKSPACE_ID=your_workspace_id
RELATIONSHIP_TRACKING_DOC_ID=  # Add in next step
RELATIONSHIP_REPORT_EMAIL=your_email@example.com
TIMEZONE=America/New_York  # Your timezone
```

### 5. Create Tracking Document (2 minutes)

1. Create new Google Doc
2. Copy template from: `RELATIONSHIP_TRACKING_TEMPLATE.md`
3. Paste into document
4. Get Document ID from URL
5. Add to `.env` and `config.yaml`

---

## Test It Out

### Validate Everything

```bash
python src/relationship_main.py --validate
```

**Expected output:**
```
✅ Config loaded
✅ Environment loaded
✅ Configuration valid
✅ Calendar connection successful
✅ Docs connection successful
✅ Toggl connection successful
✅ Gmail connection successful
✅ ALL VALIDATIONS PASSED!
```

**Note:** First run will open browser for Google OAuth

### Generate Test Report

```bash
python src/relationship_main.py --generate --no-email
```

Check `output/` folder for HTML report!

### Send Real Email

```bash
python src/relationship_main.py --generate
```

Check your inbox! 📧

---

## Set Up Automation

### Option 1: Python Scheduler (Easiest)

```bash
python src/relationship_scheduler.py
```

Runs reports at:
- Saturday 7:00 PM EST
- Wednesday 6:30 PM EST

Keep this running in a terminal or use a process manager.

### Option 2: Cron (macOS/Linux)

```bash
crontab -e
```

Add:
```bash
# Saturday 7pm
0 19 * * 6 cd /full/path/to/Life\ Automations && /full/path/to/venv/bin/python src/relationship_main.py --generate >> logs/cron.log 2>&1

# Wednesday 6:30pm
30 18 * * 3 cd /full/path/to/Life\ Automations && /full/path/to/venv/bin/python src/relationship_main.py --generate >> logs/cron.log 2>&1
```

---

## Daily Usage

### Add to Your Tracking Document

1. Open your Google Doc
2. Add entries in format: `□ Date: YYYY-MM-DD | Details`
3. Mark completed: `☑ Date: YYYY-MM-DD | Details`

### Track Time in Toggl

1. Start timer
2. Add description
3. Select "Love Brittany" project
4. Stop when done

### Schedule Date Nights

1. Add to Google Calendar
2. Title: "Date Night with Brittany"
3. Create babysitter event: "Babysitter - [Name]"
4. Add "Reservation confirmed" in description

### Daily 10-Minute Focus

1. Add calendar event: "Love Action - [Activity]"
2. Duration: 10 minutes
3. Use time to update tracking doc, plan activities, or reflect

---

## Common Commands

```bash
# Check if everything is configured correctly
python src/relationship_main.py --validate

# Generate report (save to file, don't email)
python src/relationship_main.py --generate --no-email

# Generate and send email report
python src/relationship_main.py --generate

# Run scheduler (reports on schedule)
python src/relationship_scheduler.py

# Test scheduler immediately
python src/relationship_scheduler.py --test

# View logs
tail -f logs/relationship.log

# View latest HTML report
open output/relationship_report_*.html  # macOS
```

---

## Quick Troubleshooting

### "Module not found"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "Credentials invalid"
```bash
rm credentials/token.pickle
python src/relationship_main.py --validate
```

### "Document not found"
- Check Document ID in `.env`
- Verify doc is accessible with your Google account

### "No data in report"
- Add test entries to your tracking document
- Check date format: `YYYY-MM-DD`
- Verify section headers: `[GIFTS]`, `[LETTERS]`, etc.

---

## What Gets Tracked?

### Automatically from Calendar:
✅ Date nights (next 12 months)
✅ Babysitter bookings
✅ Reservations confirmed
✅ Daily 10-minute gaps

### Automatically from Toggl:
✅ Time invested (last 30 days)
✅ Days tracked
✅ Average daily time

### From Your Tracking Document:
✅ Unexpected gifts (every 3 months)
✅ Letters written (every 3 weeks)
✅ Action plan reviews
✅ Journal entries (monthly)
✅ Time together suggestions (monthly)
✅ Goal support actions (monthly)

---

## Sample Report Output

You'll receive a beautiful HTML email with:

📊 **Executive Summary**
- Relationship health score (0-100)
- Critical alerts count
- Warning count
- Key statistics

🚨 **Critical Alerts**
- Items needing immediate attention
- Red alerts for overdue activities

📅 **Date Nights**
- Next 12 months coverage
- Missing months highlighted
- Babysitter status for each
- Reservation confirmation

🎁 **Activity Tracking**
- Gift status (last, next due)
- Letter status
- Journal status
- Time suggestions
- Goal support

⏱️ **Time Investment**
- Total hours (30 days)
- Active days
- Average per day
- Recent entries

📋 **Action Items**
- Clear list of what needs to be done
- Prioritized by urgency

---

## Tips for Success

### Weekly Habit
- Sunday evening: Update tracking document
- Check off completed items
- Plan activities for upcoming week

### Monthly Ritual
- First of month: Review last month
- Add journal entry
- Plan upcoming gifts/letters/suggestions

### Daily Practice
- 10-minute calendar reminder
- Review gaps, plan, or reflect
- Track time in Toggl

### Date Night System
- Schedule all 12 months in January
- Book babysitters 2 weeks ahead
- Make reservations 1 week ahead

---

## Next Steps

Once you have your first report:

1. **Review alerts** - Address any critical items
2. **Fill in gaps** - Add historical data if available
3. **Set reminders** - Calendar alerts for regular activities
4. **Track consistently** - Use Toggl daily
5. **Adjust schedule** - Change report times if needed in `config.yaml`

---

## Full Documentation

- `RELATIONSHIP_SETUP_GUIDE.md` - Detailed setup instructions
- `RELATIONSHIP_TRACKING_TEMPLATE.md` - Document template and formatting guide
- `README.md` - Project overview

---

## Support

**Check logs:**
```bash
tail -f logs/relationship.log
```

**Run validation:**
```bash
python src/relationship_main.py --validate
```

**Review configuration:**
- `.env` - Environment variables
- `config.yaml` - Application settings

---

**You've got this! 💝**

The goal is to help you stay consistent in nurturing your relationship, not to create more stress. Start small, build habits, and let the automation handle the tracking and reminders.
