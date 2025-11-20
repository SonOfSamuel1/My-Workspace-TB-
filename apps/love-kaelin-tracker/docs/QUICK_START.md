# Quick Start Guide - Love Kaelin Development Tracker

Get up and running with Kaelin development tracking in 10 minutes!

## Prerequisites

✅ Love Brittany tracker is already set up (shared credentials)
✅ Google APIs enabled (Calendar, Docs, Gmail)
✅ Toggl account with API token

## Step 1: Create Tracking Document (2 minutes)

1. **Open Google Docs** and create a new document
2. **Copy the template** from `docs/KAELIN_TRACKING_TEMPLATE.md`
3. **Paste into Google Doc** and format as needed
4. **Get the Document ID**:
   - Look at the URL: `https://docs.google.com/document/d/[DOCUMENT_ID]/edit`
   - Copy the `DOCUMENT_ID` part

## Step 2: Update Configuration (2 minutes)

Edit `config.yaml`:

```yaml
kaelin_tracking:
  enabled: true
  tracking_doc_id: "PASTE_YOUR_DOCUMENT_ID_HERE"
  toggl_project_name: "Love Kaelin"
  email:
    recipient: "terrance@goodportion.org"
```

## Step 3: Validate Setup (1 minute)

```bash
cd apps/love-kaelin-tracker
python src/kaelin_main.py --validate
```

You should see:
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

## Step 4: Create Toggl Project (Optional - 2 minutes)

1. Log into Toggl Track
2. Create a new project called "Love Kaelin"
3. Start tracking time when playing with Kaelin

## Step 5: Generate First Report (1 minute)

```bash
python src/kaelin_main.py --generate --no-email
```

This will:
- Generate a report from your tracking document
- Save HTML to `output/kaelin_report_[timestamp].html`
- NOT send an email (remove --no-email to send)

## Step 6: Review Report (2 minutes)

Open the generated HTML file in your browser:
```bash
open output/kaelin_report_*.html
```

Review:
- Executive summary with health score
- Alerts and action items
- All tracking sections

## Step 7: Start Tracking! (Ongoing)

### Daily Activities

1. **Play with Kaelin** - Track in Toggl or add to calendar
2. **Update tracking document** with:
   - Play session details
   - Activities done
   - Any new observations

### Weekly Activities

1. **Review the report** each Sunday morning
2. **Act on alerts** - critical items first
3. **Plan the week** based on insights

### Monthly Activities

1. **Introduce a new game** - at least once per month
2. **Update spiritual development plan** if needed
3. **Review progress** on Jesus teachings

### Quarterly Activities

1. **Plan Daddy Days** for upcoming quarters
2. **Schedule field trips** if needed
3. **Research new programs** for development

## Common Tracking Patterns

### Recording Play Time

**Option 1: Calendar Events**
Create calendar events with these names:
- "Play with Kaelin"
- "Kaelin time"
- "Daddy daughter time"

**Option 2: Toggl Tracking**
- Start timer when playing
- Use project "Love Kaelin"
- Add descriptions of activities

**Option 3: Manual Logging**
Update tracking document PLAY TIME LOG:
```
2025-01-17 | Duration: 2.5 hours | Activities: Building blocks, reading
```

### Recording Jesus Teachings

When you teach a lesson, update tracking document:
```
1. Love God with all your heart | 2025-01-17 | Beginning | Talked about loving God through prayer
```

### Planning Daddy Days

Add to tracking document AND calendar:
```
Q1 2025 (Jan-Mar):
- 2025-02-14 | Valentine's Daddy-Daughter Date | Status: Planned

Calendar Event:
Title: "Daddy Day - Valentine's Daddy-Daughter Date"
Date: Feb 14, 2025
```

## Automation Tips

### Set Up Calendar Sync

Create recurring calendar events:
- "Kaelin Daily Play" - Daily reminder
- "Review Kaelin Report" - Sunday mornings
- "Plan Daddy Day" - First of each quarter

### Use Toggl Templates

Create Toggl time entry templates:
- "Kaelin Play Time"
- "Kaelin Teaching Session"
- "Kaelin Field Trip"

### Email Report Schedule

The system generates reports automatically on:
- **Sunday at 5:00 AM EST**

To enable automatic sending, remove `--no-email` flag or set up cron:
```bash
crontab -e
# Add:
0 5 * * 0 cd /path/to/love-kaelin-tracker && python src/kaelin_main.py --generate
```

## Understanding the Report

### Health Score
- **80-100%** - Excellent! Keep it up
- **60-79%** - Good, but room for improvement
- **Below 60%** - Needs attention, review alerts

### Alert Levels
- **🚨 Critical** - Take action TODAY
- **⚠️ Warning** - Address soon (this week)
- **ℹ️ Info** - Keep in mind, plan ahead

### Key Metrics to Watch
1. **Days Since Last Play** - Should be 0-1 days
2. **Rolling 100-Day Average** - Target: 70%+
3. **Teachings Progress** - Steady increase
4. **Field Trips** - On track for 3/year

## Troubleshooting

### "No tracking document found"
- Check document ID in config.yaml
- Ensure document is accessible to your Google account
- Run validation to diagnose

### "No play time recorded"
- Add calendar events with search terms
- Update tracking document manually
- Start using Toggl tracking

### "Email not sending"
- Check recipient email in config
- Verify Gmail API is enabled
- Run with --no-email to test report generation first

## Next Steps

Once you're comfortable with basics:

1. **Customize targets** in config.yaml
2. **Add calendar events** for automatic tracking
3. **Set up automation** for weekly reports
4. **Review and adjust** based on your schedule
5. **Expand tracking** to more categories

## Tips for Success

1. **Start simple** - Don't try to track everything at once
2. **Be consistent** - Update daily or weekly
3. **Review regularly** - Use reports to guide actions
4. **Celebrate progress** - Notice improvements in health score
5. **Adjust as needed** - Modify targets to fit your life

## Getting Help

If you encounter issues:

```bash
# Validate configuration
python src/kaelin_main.py --validate

# Check logs
cat logs/kaelin_tracker.log

# Generate test report
python src/kaelin_main.py --generate --no-email
```

Review the full README.md for detailed documentation.

---

**You're all set!** Start tracking your amazing journey with Kaelin! 💖

Remember: This tool is here to support and encourage you, not to create pressure. Use it to celebrate the time you spend together and plan for even more meaningful moments.
