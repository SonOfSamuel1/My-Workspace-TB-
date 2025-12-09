# Quick Reference

## Installation

```bash
cd "Life Automations"
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
```

## Commands

### Basic Sync
```bash
python src/main.py                    # Sync today
python src/main.py --mode yesterday   # Sync yesterday
python src/main.py --mode week        # Sync this week
python src/main.py --mode date --date 2025-10-15  # Specific date
```

### Validation
```bash
python src/main.py --mode validate    # Check credentials
```

### Continuous Sync
```bash
python src/main.py --continuous --interval 5  # Every 5 minutes
```

### Webhook Server
```bash
python src/webhook_server.py          # Start webhook listener
```

## Quick Setup

1. **Get Toggl API Token:** https://track.toggl.com/profile
2. **Get Workspace ID:** Check URL in Toggl settings
3. **Enable Google Calendar API:** https://console.cloud.google.com/
4. **Download OAuth credentials:** Save as `credentials/credentials.json`
5. **Configure `.env`:** Add tokens and settings
6. **Authenticate:** Run `python src/main.py --mode validate`
7. **First Sync:** Run `python src/main.py`

## Configuration Files

### `.env` - Credentials
```env
TOGGL_API_TOKEN=your_token
TOGGL_WORKSPACE_ID=1234567
TOGGL_SYNC_ENABLED=true
GOOGLE_CALENDAR_ID=primary
TIMEZONE=America/New_York
```

### `config.yaml` - Settings
```yaml
sync:
  enabled: true
  sync_running_entries: false

calendar:
  title_format: "[Time] {description} - {project}"
  default_color_id: 8

filters:
  include_projects: []
  exclude_tags: []
  min_duration_minutes: 0
```

## Cron Setup

```bash
# Edit crontab
crontab -e

# Sync every 30 minutes
*/30 * * * * cd /path/to/Life\ Automations && /path/to/venv/bin/python src/main.py >> logs/cron.log 2>&1

# Sync every hour
0 * * * * cd /path/to/Life\ Automations && /path/to/venv/bin/python src/main.py >> logs/cron.log 2>&1
```

## Troubleshooting

### Check Logs
```bash
tail -f logs/sync.log
```

### Clear Sync State
```bash
rm cache/sync_state.json
```

### Reset Google Authentication
```bash
rm credentials/token.pickle
python src/main.py --mode validate
```

### Test Services
```bash
python src/toggl_service.py      # Test Toggl
python src/calendar_service.py   # Test Calendar
python src/sync_service.py       # Test Sync
```

## Key Features

✅ Syncs time entries to calendar
✅ Updates existing events
✅ Prevents duplicates
✅ Includes project & tags
✅ Shows billable status
✅ Real-time webhook support
✅ Configurable filtering
✅ Batch sync modes

## File Locations

- **Credentials:** `credentials/credentials.json`, `credentials/token.pickle`
- **Configuration:** `.env`, `config.yaml`
- **Logs:** `logs/sync.log`, `logs/webhook.log`
- **State:** `cache/sync_state.json`

## Important Links

- **Toggl API Docs:** https://developers.track.toggl.com/
- **Google Calendar API:** https://developers.google.com/calendar/api
- **Toggl Profile:** https://track.toggl.com/profile
- **Google Cloud Console:** https://console.cloud.google.com/

## Support

Read full documentation: `README.md`
Setup guide: `SETUP_GUIDE.md`
