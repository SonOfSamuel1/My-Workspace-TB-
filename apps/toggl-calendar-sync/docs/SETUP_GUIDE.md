# Complete Setup Guide

This guide will walk you through setting up the Toggl to Google Calendar sync step-by-step.

## Prerequisites

- Python 3.9 or higher
- Active Toggl Track account
- Google account with Calendar access
- Terminal/Command Prompt access

## Step 1: Install Python Dependencies

```bash
# Navigate to project directory
cd "Life Automations"

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

You should see installation progress for all packages. When complete:
```
Successfully installed google-api-python-client-2.108.0 ...
```

## Step 2: Get Toggl Track API Credentials

### 2.1 Get API Token

1. Open browser and go to: https://track.toggl.com/profile
2. Log in to your Toggl account
3. Scroll down to **"API Token"** section
4. Click **"Click to reveal"** button
5. Copy the token (format: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`)

### 2.2 Get Workspace ID

1. Go to: https://track.toggl.com/
2. Click on workspace name (top left)
3. Click **"Settings"**
4. Look at URL in browser: `https://track.toggl.com/[WORKSPACE_ID]/settings`
5. Copy the workspace ID (it's a number, like: `1234567`)

**Save these values** - you'll need them in Step 4.

## Step 3: Setup Google Calendar API

### 3.1 Create Google Cloud Project

1. Go to: https://console.cloud.google.com/
2. Click **"Select a project"** → **"New Project"**
3. Enter project name: `Toggl Calendar Sync`
4. Click **"Create"**
5. Wait for project creation (10-30 seconds)

### 3.2 Enable Google Calendar API

1. In Cloud Console, click **"APIs & Services"** → **"Enable APIs and Services"**
2. Search for: `Google Calendar API`
3. Click on **"Google Calendar API"**
4. Click **"Enable"** button
5. Wait for API to enable (5-10 seconds)

### 3.3 Create OAuth 2.0 Credentials

1. Go to: **"APIs & Services"** → **"Credentials"**
2. Click **"Create Credentials"** → **"OAuth client ID"**
3. If prompted, configure consent screen:
   - Click **"Configure Consent Screen"**
   - Select **"External"** (unless you have Google Workspace)
   - Click **"Create"**
   - Fill in required fields:
     - App name: `Toggl Calendar Sync`
     - User support email: Your email
     - Developer contact: Your email
   - Click **"Save and Continue"**
   - Skip "Scopes" → Click **"Save and Continue"**
   - Add your email as test user → Click **"Save and Continue"**
   - Click **"Back to Dashboard"**

4. Return to **"Credentials"**
5. Click **"Create Credentials"** → **"OAuth client ID"**
6. Application type: **"Desktop app"**
7. Name: `Toggl Sync Desktop Client`
8. Click **"Create"**

### 3.4 Download Credentials

1. Click the **download button** (⬇️) next to your newly created OAuth client
2. This downloads a JSON file named like: `client_secret_123456.json`
3. **Rename it** to: `credentials.json`
4. **Move it** to: `Life Automations/credentials/` directory

```bash
# Create credentials directory
mkdir -p credentials

# Move downloaded file (adjust path as needed)
mv ~/Downloads/client_secret_*.json credentials/credentials.json
```

## Step 4: Configure Environment

### 4.1 Create .env File

```bash
# Copy example file
cp .env.example .env
```

### 4.2 Edit .env File

Open `.env` in your favorite editor:

```bash
# macOS
nano .env

# Windows
notepad .env

# Or use VS Code
code .env
```

### 4.3 Update Credentials

Replace the placeholder values with your actual credentials:

```env
# Toggl Track API Configuration
TOGGL_API_TOKEN=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6  # From Step 2.1
TOGGL_WORKSPACE_ID=1234567                         # From Step 2.2

# Toggl Sync Settings
TOGGL_SYNC_ENABLED=true
TOGGL_AUTO_SYNC=true
TOGGL_SYNC_RUNNING=false

# Google Calendar Configuration
GOOGLE_CALENDAR_ID=primary
GOOGLE_CREDENTIALS_FILE=credentials/credentials.json
GOOGLE_TOKEN_FILE=credentials/token.pickle

# Timezone (update to your timezone)
TIMEZONE=America/New_York

# Webhook Configuration (optional - for real-time sync)
WEBHOOK_ENABLED=false
WEBHOOK_PORT=8080
WEBHOOK_SECRET=your_random_secret_key_here

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/sync.log
```

**Important timezone values:**
- `America/New_York` - Eastern Time
- `America/Chicago` - Central Time
- `America/Denver` - Mountain Time
- `America/Los_Angeles` - Pacific Time
- `Europe/London` - UK
- `Europe/Paris` - Central Europe
- Full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

Save and close the file.

## Step 5: First-Time Authentication

### 5.1 Run Validation

```bash
python src/main.py --mode validate
```

### 5.2 Complete Google OAuth Flow

1. A browser window will open automatically
2. You may see: **"Google hasn't verified this app"**
   - Click **"Advanced"**
   - Click **"Go to Toggl Calendar Sync (unsafe)"**
   - This is safe - it's your own app
3. Select your Google account
4. Review permissions:
   - **See, edit, share, and permanently delete all calendars**
   - This is required to create calendar events
5. Click **"Allow"**
6. You'll see: **"The authentication flow has completed"**
7. Close the browser tab

### 5.3 Verify Success

In terminal, you should see:

```
✓ Credentials validated
✓ All services validated successfully
Sync enabled: True
Total synced entries: 0
Last sync: Never
```

If you see errors, check:
- `credentials/credentials.json` exists and is valid JSON
- `.env` file has correct Toggl credentials
- Internet connection is working

## Step 6: Test Your First Sync

### 6.1 Check Toggl Has Entries

1. Go to: https://track.toggl.com/
2. Verify you have completed time entries for today
3. Make sure at least one entry is **stopped** (not running)

### 6.2 Run First Sync

```bash
python src/main.py --mode today
```

You should see output like:

```
2025-10-24 10:30:00 - INFO - === Toggl to Calendar Sync Started ===
2025-10-24 10:30:00 - INFO - Syncing today's entries...
2025-10-24 10:30:01 - INFO - Retrieved 5 time entries
2025-10-24 10:30:01 - INFO - Created calendar event: abc123 for 'Project work'
2025-10-24 10:30:02 - INFO - === Sync Complete ===
2025-10-24 10:30:02 - INFO - Total entries: 5
2025-10-24 10:30:02 - INFO - Newly synced: 5
2025-10-24 10:30:02 - INFO - Updated: 0
2025-10-24 10:30:02 - INFO - Skipped: 0
2025-10-24 10:30:02 - INFO - Failed: 0
```

### 6.3 Verify Calendar Events

1. Go to: https://calendar.google.com/
2. Look at today's date
3. You should see calendar events like: `[Time] Project work - Client Name`
4. Click an event to see details (duration, project, tags, etc.)

## Step 7: Setup Automated Sync (Optional)

### Option A: Continuous Mode (Simple)

Run sync every 5 minutes:

```bash
# Run in background
nohup python src/main.py --continuous --interval 5 > logs/continuous.log 2>&1 &

# Check it's running
tail -f logs/sync.log
```

To stop:
```bash
# Find process ID
ps aux | grep "main.py"

# Kill process
kill [PID]
```

### Option B: Cron Job (Recommended for macOS/Linux)

```bash
# Open crontab editor
crontab -e

# Add one of these lines:

# Sync every 30 minutes
*/30 * * * * cd /path/to/Life\ Automations && /path/to/venv/bin/python src/main.py >> logs/cron.log 2>&1

# Sync every hour (at :00)
0 * * * * cd /path/to/Life\ Automations && /path/to/venv/bin/python src/main.py >> logs/cron.log 2>&1

# Sync every 4 hours (at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00)
0 */4 * * * cd /path/to/Life\ Automations && /path/to/venv/bin/python src/main.py >> logs/cron.log 2>&1
```

**Important:** Replace `/path/to/Life\ Automations` with actual path:
```bash
# Get current directory path
pwd
# Example output: /Users/terrancebrandon/Life Automations

# Get venv python path
which python
# Example output: /Users/terrancebrandon/Life Automations/venv/bin/python
```

Save and exit (Ctrl+X, then Y, then Enter in nano).

Verify cron job:
```bash
crontab -l
```

### Option C: Windows Task Scheduler

1. Open **Task Scheduler**
2. Click **"Create Basic Task"**
3. Name: `Toggl Calendar Sync`
4. Trigger: **"Daily"**
5. Start time: `12:00 AM`
6. Recur every: `1 days`
7. Action: **"Start a program"**
8. Program/script: `C:\path\to\venv\Scripts\python.exe`
9. Add arguments: `src\main.py`
10. Start in: `C:\path\to\Life Automations`
11. Click **"Finish"**

For more frequent sync:
1. Right-click task → **"Properties"**
2. **"Triggers"** tab → **"Edit"**
3. Check **"Repeat task every"** → Select interval (30 minutes, 1 hour, etc.)

## Step 8: Setup Real-Time Webhook Sync (Advanced, Optional)

**Note:** Requires Toggl paid plan and public server/ngrok.

### 8.1 Install ngrok (for local testing)

```bash
# macOS
brew install ngrok

# Or download from: https://ngrok.com/download
```

### 8.2 Configure Webhook

Edit `.env`:
```env
WEBHOOK_ENABLED=true
WEBHOOK_PORT=8080
WEBHOOK_SECRET=choose_a_random_secret_key_here
```

### 8.3 Start Webhook Server

```bash
# Start server
python src/webhook_server.py

# In another terminal, start ngrok
ngrok http 8080
```

Copy the ngrok URL (like: `https://abc123.ngrok.io`)

### 8.4 Configure Toggl Webhook

1. Go to: https://track.toggl.com/
2. Settings → Integrations → Webhooks (requires paid plan)
3. Click **"Add Webhook"**
4. Webhook URL: `https://abc123.ngrok.io/toggl-webhook`
5. Secret: (same as in `.env`)
6. Events: Select all time entry events
7. Click **"Save"**

### 8.5 Test Webhook

1. Create new time entry in Toggl
2. Stop the timer
3. Check calendar - event should appear immediately
4. Check webhook logs: `tail -f logs/webhook.log`

## Common Issues & Solutions

### Issue: "ModuleNotFoundError: No module named 'google'"

**Solution:**
```bash
# Make sure venv is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "TOGGL_API_TOKEN not found in environment"

**Solution:**
```bash
# Verify .env file exists
ls -la .env

# Check contents (should have TOGGL_API_TOKEN=...)
cat .env

# If missing, copy from example
cp .env.example .env
# Then edit with your credentials
```

### Issue: "Failed to validate credentials" (Toggl)

**Solution:**
- Verify API token: https://track.toggl.com/profile
- Copy token carefully (no extra spaces)
- Check workspace ID is a number
- Test API manually:
  ```bash
  curl -u YOUR_API_TOKEN:api_token https://api.track.toggl.com/api/v9/me
  ```

### Issue: "Failed to validate credentials" (Google)

**Solution:**
```bash
# Delete saved token
rm credentials/token.pickle

# Run validation again
python src/main.py --mode validate

# Complete OAuth flow in browser
```

### Issue: "No time entries found"

**Solution:**
- Check you have stopped time entries in Toggl for today
- Running entries won't sync (unless `TOGGL_SYNC_RUNNING=true`)
- Try syncing yesterday: `python src/main.py --mode yesterday`

### Issue: Duplicate calendar events

**Solution:**
```bash
# Clear sync state
rm cache/sync_state.json

# Manually delete duplicates from Google Calendar

# Re-sync
python src/main.py --mode today
```

### Issue: Cron job not working

**Solution:**
```bash
# Check cron logs
cat logs/cron.log

# Verify paths are absolute (not relative)
crontab -l

# Test command manually
cd /path/to/Life\ Automations && /path/to/venv/bin/python src/main.py

# Check cron daemon is running
# macOS
sudo launchctl list | grep cron

# Linux
systemctl status cron
```

## Next Steps

1. **Customize event format** - Edit `config.yaml` → `calendar.title_format`
2. **Filter projects** - Edit `config.yaml` → `filters.include_projects`
3. **Change colors** - Edit `config.yaml` → `calendar.default_color_id`
4. **Review logs** - Monitor `logs/sync.log` for issues
5. **Sync historical data** - Run for past dates with `--mode date`

## Getting Help

1. Check logs: `tail -f logs/sync.log`
2. Run validation: `python src/main.py --mode validate`
3. Test individual services:
   - `python src/toggl_service.py`
   - `python src/calendar_service.py`
   - `python src/sync_service.py`

## Success Checklist

- [ ] Python dependencies installed
- [ ] Toggl API token obtained
- [ ] Google Calendar API enabled
- [ ] OAuth credentials downloaded
- [ ] `.env` file configured
- [ ] First authentication completed
- [ ] First sync successful
- [ ] Calendar events visible
- [ ] Automated sync scheduled (optional)
- [ ] Webhook configured (optional)

**Congratulations! Your Toggl to Calendar sync is ready!** 🎉
