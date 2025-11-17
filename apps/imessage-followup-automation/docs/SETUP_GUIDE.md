# iMessage Follow-up Automation - Setup Guide

Complete step-by-step guide to set up the iMessage Follow-up Automation system.

## Prerequisites

Before you begin, ensure you have:

- ✅ macOS (Catalina or later)
- ✅ iMessage configured and active
- ✅ Python 3.8 or higher (`python3 --version`)
- ✅ pip installed (`pip3 --version`)
- ✅ An Anthropic account with API access
- ✅ A Google Cloud account (free tier works)

## Step 1: System Requirements

### Full Disk Access (macOS Catalina+)

The app needs to read your iMessage database. Grant Full Disk Access:

1. Open **System Preferences** → **Security & Privacy** → **Privacy**
2. Click **Full Disk Access** in the left sidebar
3. Click the lock icon and authenticate
4. Click **+** and add:
   - **Terminal** (if running from Terminal)
   - **Python** (`/usr/local/bin/python3` or your Python location)
5. Restart Terminal

**Find Python location:**
```bash
which python3
```

## Step 2: Install Dependencies

```bash
cd apps/imessage-followup-automation
pip3 install -r requirements.txt
```

This installs:
- Google API libraries (Gmail)
- Anthropic SDK (Claude)
- PyYAML, pytz, python-dateutil

## Step 3: Get Anthropic API Key

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to **API Keys**
4. Click **Create Key**
5. Copy the key (starts with `sk-ant-...`)
6. Save it securely - you'll need it in Step 5

**Pricing Note**: Claude API charges per token. For this use case, expect < $1/month for regular usage.

## Step 4: Set Up Google Gmail API

### 4.1 Create Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Click **Select a project** → **New Project**
3. Name it "iMessage Follow-up" or similar
4. Click **Create**

### 4.2 Enable Gmail API

1. In your project, go to **APIs & Services** → **Library**
2. Search for "Gmail API"
3. Click **Gmail API** → **Enable**

### 4.3 Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** (unless you have a Google Workspace)
3. Click **Create**
4. Fill in:
   - **App name**: "iMessage Follow-up Automation"
   - **User support email**: Your email
   - **Developer contact**: Your email
5. Click **Save and Continue**
6. On **Scopes**, click **Add or Remove Scopes**
7. Filter for "Gmail API" and select:
   - `.../auth/gmail.send` (Send email on your behalf)
8. Click **Update** → **Save and Continue**
9. On **Test users**, add your email address
10. Click **Save and Continue** → **Back to Dashboard**

### 4.4 Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Select **Application type**: **Desktop app**
4. Name it "iMessage Automation"
5. Click **Create**
6. Click **Download JSON** (download button on the right)
7. Save the file to your project:
   ```bash
   mkdir -p credentials
   # Move downloaded file to credentials/credentials.json
   mv ~/Downloads/client_secret_*.json credentials/credentials.json
   ```

## Step 5: Configure Environment Variables

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env`:
   ```bash
   nano .env  # or use your preferred editor
   ```

3. Fill in the values:
   ```bash
   # Anthropic Claude API (from Step 3)
   ANTHROPIC_API_KEY=sk-ant-your-key-here

   # Google Credentials (from Step 4)
   GOOGLE_CREDENTIALS_FILE=credentials/credentials.json
   GOOGLE_TOKEN_FILE=credentials/token.pickle

   # Your email address for notifications
   IMESSAGE_FOLLOWUP_EMAIL=your.email@gmail.com
   ```

4. Save and close (Ctrl+X, then Y, then Enter in nano)

## Step 6: Customize Configuration

Edit `config.yaml` to match your preferences:

```bash
nano config.yaml
```

Key settings to review:

```yaml
imessage_followup:
  # How often to check (for scheduling)
  check_interval_hours: 4

  # How far back to look
  lookback_hours: 48

  # Important contacts (always checked)
  priority_contacts:
    - "+15551234567"     # Add your important contacts
    - "spouse@email.com"

  # Analysis settings
  analysis:
    min_hours_since_message: 12  # Ignore very recent messages

  # Email settings
  email:
    recipient: "your.email@gmail.com"
    send_daily_summary: false  # Set true for daily emails even with no follow-ups
```

## Step 7: Initial Authentication

Run validation to set up Gmail authentication:

```bash
python src/imessage_main.py --validate
```

**What happens:**
1. Script checks configuration
2. Tests iMessage database access
3. Opens browser for Google OAuth
4. You authorize the app to send emails
5. Token is saved to `credentials/token.pickle`

**Expected output:**
```
====================================
iMESSAGE FOLLOW-UP AUTOMATION - SETUP VALIDATION
====================================

📋 Loading configuration...
✅ Config loaded
🔐 Loading environment variables...
✅ Environment loaded
✔️  Validating configuration...
✅ Configuration valid
📱 Testing iMessage database access...
✅ iMessage database accessible
🤖 Testing Anthropic Claude API...
✅ Anthropic API key found
📧 Testing Gmail connection...
✅ Gmail connection successful
💾 Testing state tracker...
✅ State tracker initialized

====================================
✅ ALL VALIDATIONS PASSED!
====================================
```

## Step 8: Test Run

Test the automation without sending email:

```bash
python src/imessage_main.py --check --no-email
```

**What happens:**
1. Scans your iMessages
2. Analyzes conversations
3. Generates recommendations using Claude
4. Creates HTML report in `output/` directory
5. Shows summary (no email sent)

**Review the output:**
```bash
open output/imessage_followup_*.html
```

## Step 9: Send Test Email

Once you're happy with the report, send a real email:

```bash
python src/imessage_main.py --check
```

Check your email inbox for the follow-up report!

## Step 10: Set Up Scheduling

Choose how you want to automate:

### Option A: Use the Scheduler Script (Recommended)

```bash
./scheduler.sh
```

Select option 1 (launchd) and follow prompts.

### Option B: Manual Cron Setup

Add to crontab (`crontab -e`):
```bash
# Every 4 hours
0 */4 * * * cd /path/to/My-Workspace-TB-/apps/imessage-followup-automation && /usr/bin/python3 src/imessage_main.py --check >> logs/cron.log 2>&1
```

### Option C: Manual launchd Setup

See README.md for full plist example.

## Verification

After setup, verify everything works:

1. **Check logs:**
   ```bash
   tail -f logs/imessage_followup.log
   ```

2. **View state database:**
   ```bash
   sqlite3 data/imessage_state.db "SELECT * FROM notifications ORDER BY notified_at DESC LIMIT 5;"
   ```

3. **Test force notification:**
   ```bash
   python src/imessage_main.py --check --force
   ```

## Troubleshooting

### "iMessage database not found"

- Check path: `ls ~/Library/Messages/chat.db`
- Ensure iMessage is set up and has messages
- Verify Full Disk Access (Step 1)

### "Permission denied" accessing chat.db

- Grant Full Disk Access to Terminal/Python (Step 1)
- Restart Terminal after granting access

### "Invalid API key" (Anthropic)

- Verify key in `.env` is correct
- Check key hasn't expired at https://console.anthropic.com/
- Ensure no extra spaces in `.env`

### "Gmail authentication failed"

- Delete `credentials/token.pickle`
- Run `--validate` again to re-authenticate
- Check `credentials.json` is correct
- Ensure Gmail API is enabled in Google Cloud Console

### "No conversations found"

- Check `lookback_hours` in config.yaml
- Verify you have recent messages in iMessage
- Try increasing `lookback_hours` to 168 (1 week)

### Cron job not running

- Check cron logs: `grep CRON /var/log/system.log`
- Verify crontab: `crontab -l`
- Ensure full paths in crontab
- Check Terminal has Full Disk Access

### launchd agent not running

- Check status: `launchctl list | grep imessage`
- View logs: `cat ~/Library/LaunchAgents/com.imessage.followup.plist`
- Reload: `launchctl unload ... && launchctl load ...`

## Next Steps

After successful setup:

1. **Monitor for a few days** - Check that notifications are helpful
2. **Adjust configuration** - Fine-tune based on your needs
3. **Review state tracker** - Ensure no duplicate notifications
4. **Customize analysis** - Modify criteria in `config.yaml`

## Support

For issues:
- Check logs in `logs/` directory
- Review configuration in `config.yaml` and `.env`
- Run validation: `python src/imessage_main.py --validate`
- Open an issue in the main repository

## Privacy Notes

- All message scanning happens **locally** on your Mac
- Only conversation **context** is sent to Claude API for analysis
- Messages are **not stored** permanently (only notification state)
- Database is opened **read-only** - never modifies iMessages
- Emails are sent **from your account** via Gmail API

---

**Setup Complete!** You now have automated iMessage follow-up reminders with AI-powered recommendations.
