# iMessage Follow-up Automation

Automated system that reads your iMessages, identifies conversations requiring follow-up, and emails you with AI-powered recommendations on how to respond.

## Features

- **Automated Message Scanning**: Reads your macOS iMessage database to find conversations needing attention
- **Smart Analysis**: Uses rule-based and AI-powered analysis to identify:
  - Unanswered questions
  - Pending responses (where you haven't replied yet)
  - Action items and commitments
  - Time-sensitive messages
- **AI-Powered Recommendations**: Claude provides:
  - Suggested response messages
  - Task creation recommendations
  - Calendar event suggestions
  - Automation ideas for Claude Code
- **Email Notifications**: Beautiful HTML email reports with:
  - Messages grouped by priority (urgent, high, medium, low)
  - Message previews
  - Time since last message
  - AI analysis and recommendations
- **Smart State Tracking**: Prevents duplicate notifications while allowing re-notifications for unresolved conversations
- **Privacy-Focused**: All processing happens locally; only conversation context is sent to Claude API for analysis

## How It Works

```
┌─────────────────┐
│  iMessage DB    │  ← Reads your local chat.db database
│  (chat.db)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Message         │  ← Analyzes conversations
│ Analyzer        │     (rules + AI)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Action          │  ← Generates recommendations
│ Recommender     │     (Claude API)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Email Report    │  ← Sends beautiful HTML email
└─────────────────┘
```

## Installation

### Prerequisites

- macOS (for iMessage access)
- Python 3.8+
- iMessage configured on your Mac
- Anthropic API key (for Claude)
- Google Cloud credentials (for Gmail sending)

### Setup

1. **Install dependencies:**
   ```bash
   cd apps/imessage-followup-automation
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add:
   - `ANTHROPIC_API_KEY`: Your Anthropic API key from https://console.anthropic.com/
   - `GOOGLE_CREDENTIALS_FILE`: Path to Google OAuth2 credentials
   - `IMESSAGE_FOLLOWUP_EMAIL`: Email address to receive notifications

3. **Set up Google Gmail API:**
   - Go to https://console.cloud.google.com/
   - Create a new project or use existing
   - Enable Gmail API
   - Create OAuth2 credentials (Desktop app)
   - Download credentials JSON and save to `credentials/credentials.json`

4. **Customize configuration:**
   Edit `config.yaml` to:
   - Set check interval and lookback period
   - Add priority contacts
   - Configure analysis criteria
   - Customize email settings

5. **Validate setup:**
   ```bash
   python src/imessage_main.py --validate
   ```

## Usage

### Manual Check

Run a one-time check and send email:
```bash
python src/imessage_main.py --check
```

Generate report without sending email:
```bash
python src/imessage_main.py --check --no-email
```

Force notification even for recently-notified conversations:
```bash
python src/imessage_main.py --check --force
```

### Automated Scheduling

#### Option 1: Cron (macOS/Linux)

Add to crontab (`crontab -e`):
```bash
# Check every 4 hours
0 */4 * * * cd /path/to/My-Workspace-TB-/apps/imessage-followup-automation && /usr/bin/python3 src/imessage_main.py --check >> logs/cron.log 2>&1

# Daily summary at 9 AM
0 9 * * * cd /path/to/My-Workspace-TB-/apps/imessage-followup-automation && /usr/bin/python3 src/imessage_main.py --check >> logs/cron.log 2>&1
```

#### Option 2: launchd (macOS)

Create a plist file in `~/Library/LaunchAgents/`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.imessage.followup</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/My-Workspace-TB-/apps/imessage-followup-automation/src/imessage_main.py</string>
        <string>--check</string>
    </array>
    <key>StartInterval</key>
    <integer>14400</integer> <!-- 4 hours -->
    <key>StandardOutPath</key>
    <string>/path/to/logs/imessage_followup.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/logs/imessage_followup_error.log</string>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.imessage.followup.plist
```

## Configuration

### config.yaml

Key configuration options:

```yaml
imessage_followup:
  # How often to check (used by scheduler)
  check_interval_hours: 4

  # How far back to look for messages
  lookback_hours: 48

  # Priority contacts (always checked)
  priority_contacts:
    - "+1234567890"
    - "email@example.com"

  # Analysis criteria
  analysis:
    use_ai_analysis: true
    criteria:
      unanswered_questions: true
      pending_responses: true
      action_items: true
      time_sensitive: true
      min_hours_since_message: 12

  # State tracking
  state:
    renotify_after_days: 3  # Re-notify if not resolved after 3 days
```

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key
IMESSAGE_FOLLOWUP_EMAIL=your.email@example.com
GOOGLE_CREDENTIALS_FILE=credentials/credentials.json

# Optional
GOOGLE_TOKEN_FILE=credentials/token.pickle
IMESSAGE_DB_PATH=~/Library/Messages/chat.db  # Default location
```

## Privacy & Security

- **Local Processing**: All iMessage data is read locally from your Mac's database
- **API Usage**: Only conversation context is sent to Claude API for analysis
- **No Storage**: Messages are not stored permanently (only notification state)
- **Read-Only**: Database is opened in read-only mode; never modifies iMessages
- **Secure Credentials**: Uses OAuth2 for Gmail; API keys via environment variables

## Troubleshooting

### "iMessage database not found"

- Make sure you're running on macOS
- Ensure iMessage is set up and has messages
- Check if path is correct: `ls ~/Library/Messages/chat.db`

### "Full Disk Access required" (macOS Catalina+)

1. Open System Preferences → Security & Privacy → Privacy
2. Click "Full Disk Access"
3. Add Terminal or your Python executable
4. Restart Terminal

### "Failed to authenticate"

- Check Google credentials file exists
- Delete `credentials/token.pickle` and re-authenticate
- Ensure Gmail API is enabled in Google Cloud Console

### "AI analysis disabled"

- Check `ANTHROPIC_API_KEY` is set correctly
- Verify API key is valid at https://console.anthropic.com/

## Example Email Report

The generated email includes:

- **Summary**: Total conversations needing attention
- **Priority Stats**: Count by urgency level
- **Grouped Items**: Messages organized by priority
- **Message Previews**: Last message from each conversation
- **AI Analysis**: Claude's assessment of each conversation
- **Recommendations**: Specific actions you can take:
  - 💬 Suggested response messages
  - ✅ Tasks to create
  - 📅 Calendar events to schedule
  - 🤖 Claude Code automation ideas

## Advanced Usage

### Custom Analysis Criteria

Modify `src/message_analyzer.py` to add custom logic:

```python
# Add custom keywords
ACTION_KEYWORDS = [
    'schedule', 'confirm', 'send',
    'your-custom-keyword'
]
```

### Integration with Task Managers

The recommendations include task suggestions. You could extend this to:
- Auto-create Todoist tasks via API
- Send to Things.app via URL scheme
- Create calendar events via Google Calendar API

### Extending Recommendations

Modify `src/action_recommender.py` to customize the AI prompts or add new recommendation types.

## File Structure

```
imessage-followup-automation/
├── src/
│   ├── imessage_main.py           # Main entry point
│   ├── imessage_service.py        # iMessage database reader
│   ├── message_analyzer.py        # Message analysis logic
│   ├── action_recommender.py      # AI-powered recommendations
│   ├── state_tracker.py           # Notification state management
│   ├── report_generator.py        # HTML email generation
│   └── email_sender.py            # Gmail API integration (symlink)
├── config.yaml                     # Configuration
├── .env                           # Environment variables
├── requirements.txt               # Python dependencies
├── logs/                          # Log files
├── data/                          # State database
├── output/                        # Generated HTML reports
└── credentials/                   # Google OAuth credentials
```

## Contributing

This is part of a personal workspace monorepo. For issues or suggestions, open an issue in the main repository.

## License

Personal project - See repository root for license information.

## Credits

- Built with Claude AI (Anthropic)
- Uses Google Gmail API for email sending
- Accesses macOS iMessage database (SQLite)

---

**Author**: Terrance Brandon
**Repository**: My-Workspace-TB-
**Last Updated**: 2025-11-17
