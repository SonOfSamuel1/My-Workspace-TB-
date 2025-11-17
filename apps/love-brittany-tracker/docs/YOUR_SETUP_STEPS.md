# Your Personal Setup Steps

**Email:** ✅ Configured (terrance@goodportion.org)
**Status:** 2 more steps to complete!

---

## Step 1: Enable Google APIs (5 minutes)

You need to enable two more APIs in Google Cloud Console:

### Open Google Cloud Console
1. Go to: https://console.cloud.google.com/
2. Make sure you're in the same project where you created credentials
   (You can see the project name at the top of the page)

### Enable Google Docs API
1. In the left sidebar, click: **APIs & Services** → **Library**
2. In the search bar, type: **Google Docs API**
3. Click on "Google Docs API"
4. Click the blue **"Enable"** button
5. Wait for confirmation (should take a few seconds)

### Enable Gmail API
1. While still in the Library, search: **Gmail API**
2. Click on "Gmail API"
3. Click the blue **"Enable"** button
4. Wait for confirmation

**✅ Done with Step 1 when both APIs show as "Enabled"**

---

## Step 2: Create Your Tracking Document (5 minutes)

### Create the Google Doc

1. Go to: https://docs.google.com/
2. Click **"Blank"** to create a new document
3. At the top, name it: **"Love Brittany Action Plan Tracker"**

### Add the Template Content

I've created a template for you. Open the file:
**`RELATIONSHIP_TRACKING_TEMPLATE.md`**

In your terminal, run:
```bash
open RELATIONSHIP_TRACKING_TEMPLATE.md
```

Or open it in your text editor.

### Copy Template to Your Doc

1. Scroll down in the template file to the section that starts with:
   ```
   # LOVE BRITTANY ACTION PLAN TRACKER
   ```

2. Copy **everything from that point down** (all the [GIFTS], [LETTERS], etc. sections)

3. Go back to your Google Doc

4. Paste the content into your document

5. **Important:** Keep the formatting exactly as is, especially:
   - Section headers: `[GIFTS]`, `[LETTERS]`, etc.
   - Entry format: `□ Date: YYYY-MM-DD | Details`

### Get Your Document ID

1. Look at the URL in your browser when viewing the doc
2. The URL looks like:
   ```
   https://docs.google.com/document/d/[LONG_STRING_HERE]/edit
   ```

3. Copy the `[LONG_STRING_HERE]` part (the Document ID)

4. Save it - you'll need it in the next step!

**Example Document ID:**
```
1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
```

---

## Step 3: Update Configuration (1 minute)

### Add Document ID to .env

1. Open the `.env` file in your text editor:
   ```bash
   nano .env
   ```
   Or use your preferred editor.

2. Find the line that says:
   ```
   RELATIONSHIP_TRACKING_DOC_ID=
   ```

3. Paste your Document ID after the `=`:
   ```
   RELATIONSHIP_TRACKING_DOC_ID=your_document_id_here
   ```

4. Save the file (in nano: Ctrl+O, Enter, Ctrl+X)

### Also Update config.yaml

1. Open `config.yaml`:
   ```bash
   nano config.yaml
   ```

2. Scroll down to find:
   ```yaml
   relationship_tracking:
     tracking_doc_id: ""
   ```

3. Add your Document ID between the quotes:
   ```yaml
   relationship_tracking:
     tracking_doc_id: "your_document_id_here"
   ```

4. Save the file

---

## Step 4: Validate & Test! (2 minutes)

### Run Validation

```bash
source venv/bin/activate
python src/relationship_main.py --validate
```

**You should see:**
```
✅ Config loaded
✅ Environment loaded
✅ Configuration valid
✅ Calendar connection successful
✅ Docs connection successful - Found document: Love Brittany Action Plan Tracker
✅ Toggl connection successful
✅ Gmail connection successful
✅ ALL VALIDATIONS PASSED!
```

**Note:** The first time you run this, a browser will open asking you to:
1. Sign in to your Google account
2. Grant permissions for Calendar, Docs, and Gmail access
3. This is normal! Just approve the permissions.

### Generate Your First Report

```bash
python src/relationship_main.py --generate --no-email
```

This will:
- Create a report based on your current tracking
- Save it as HTML in the `output/` folder
- NOT send an email (so you can review it first)

### View the Report

```bash
open output/relationship_report_*.html
```

This will open the HTML report in your browser!

### Send Test Email

Once you're happy with the report:

```bash
python src/relationship_main.py --generate
```

This will send the report to: **terrance@goodportion.org**

Check your inbox!

---

## Step 5: Start Using the System

### Add Your First Entries

1. Open your tracking document in Google Docs
2. Add some sample data:

```
[GIFTS]
□ Date: 2025-10-15 | Gift: Surprise flowers and her favorite book

[LETTERS]
□ Date: 2025-10-20 | Letter: Wrote about our favorite memories together

[JOURNAL ENTRIES]
□ Date: 2025-10-01 | Journal: Documented ways she showed love this month
```

3. Save the document

4. Generate a new report to see your data:
   ```bash
   python src/relationship_main.py --generate --no-email
   ```

### Create "Love Brittany" Project in Toggl

1. Go to: https://track.toggl.com/
2. Click "Projects" in the sidebar
3. Click "New Project"
4. Name it: **"Love Brittany"**
5. Choose a color
6. Save

Now when you track time for relationship activities, assign it to this project!

### Schedule Date Nights

1. Open Google Calendar
2. Create events for the next 12 months
3. Title them: "Date Night with Brittany"
4. Add corresponding babysitter events: "Babysitter - [Name]"

---

## Step 6: Set Up Automation

Once everything is working, set up automatic reports:

### Option A: Python Scheduler (Easiest)

Run this command and leave it running:

```bash
python src/relationship_scheduler.py
```

Reports will be sent automatically:
- **Saturday at 7:00 PM EST**
- **Wednesday at 6:30 PM EST**

### Option B: Cron (for macOS)

```bash
crontab -e
```

Add these lines (update the path to YOUR actual path):

```bash
# Saturday 7pm
0 19 * * 6 cd /Users/terrancebrandon/personal-workspace-1/projects/meeting-research-automation/Life\ Automations && /Users/terrancebrandon/personal-workspace-1/projects/meeting-research-automation/Life\ Automations/venv/bin/python src/relationship_main.py --generate >> logs/cron.log 2>&1

# Wednesday 6:30pm
30 18 * * 3 cd /Users/terrancebrandon/personal-workspace-1/projects/meeting-research-automation/Life\ Automations && /Users/terrancebrandon/personal-workspace-1/projects/meeting-research-automation/Life\ Automations/venv/bin/python src/relationship_main.py --generate >> logs/cron.log 2>&1
```

---

## Quick Reference

### Useful Commands

```bash
# Validate everything
python src/relationship_main.py --validate

# Generate report (no email)
python src/relationship_main.py --generate --no-email

# Generate and email report
python src/relationship_main.py --generate

# Run scheduler
python src/relationship_scheduler.py

# Test scheduler immediately
python src/relationship_scheduler.py --test

# View logs
tail -f logs/relationship.log
```

### Document Format Reminder

Always use this format in your tracking document:

```
□ Date: YYYY-MM-DD | Details here
```

Examples:
```
□ Date: 2025-10-24 | Gift: Surprise dinner at her favorite restaurant
☑ Date: 2025-10-15 | Letter: Love letter about our future together
```

Mark completed items with ☑

---

## Need Help?

**Documentation:**
- `QUICK_START_RELATIONSHIP.md` - 10-minute quick start
- `RELATIONSHIP_SETUP_GUIDE.md` - Detailed setup instructions
- `RELATIONSHIP_TRACKING_TEMPLATE.md` - Document template guide

**Check Logs:**
```bash
tail -f logs/relationship.log
```

**Re-run Validation:**
```bash
python src/relationship_main.py --validate
```

---

## Your Checklist

- [ ] Step 1: Enable Google Docs API and Gmail API
- [ ] Step 2: Create tracking document in Google Docs
- [ ] Step 2: Copy template content into document
- [ ] Step 2: Get Document ID from URL
- [ ] Step 3: Add Document ID to .env file
- [ ] Step 3: Add Document ID to config.yaml
- [ ] Step 4: Run validation (should pass all checks)
- [ ] Step 4: Generate test report (--no-email)
- [ ] Step 4: Send test email
- [ ] Step 5: Add sample data to tracking document
- [ ] Step 5: Create "Love Brittany" project in Toggl
- [ ] Step 5: Schedule date nights in calendar
- [ ] Step 6: Set up automation (scheduler or cron)

---

**You're almost there!** 💪

Just follow these steps one by one, and you'll have your automated relationship tracking system running in no time!

**Questions?** Check the logs or run the validation command to see what might be missing.

Good luck! 💝
