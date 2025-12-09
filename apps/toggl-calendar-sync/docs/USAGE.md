# Toggl Calendar Sync - Quick Usage Guide

## ✅ Setup Complete!

Your Toggl entries now automatically sync to **"Time Tracking: Toggl"** calendar every 30 minutes!

## Automatic Sync

The cron job runs automatically every 30 minutes:
- :00 and :30 of every hour
- Syncs today's entries
- Logs output to `logs/cron.log`

**To check if it's running:**
```bash
crontab -l
```

**To disable automatic sync:**
```bash
crontab -r
```

**To re-enable:**
```bash
crontab -e
# Add this line:
*/30 * * * * cd '/Users/terrancebrandon/personal-workspace-1/projects/meeting-research-automation/Life Automations' && ./venv/bin/python3 src/main.py >> logs/cron.log 2>&1
```

## Manual Sync

### Using the Helper Script (Easiest)

```bash
cd "/Users/terrancebrandon/personal-workspace-1/projects/meeting-research-automation/Life Automations"

# Sync today
./toggl-sync.sh

# Sync yesterday
./toggl-sync.sh yesterday

# Sync this week
./toggl-sync.sh week

# Check status
./toggl-sync.sh status

# View logs
./toggl-sync.sh logs

# View cron logs
./toggl-sync.sh cron-logs
```

### Using Python Directly

```bash
cd "/Users/terrancebrandon/personal-workspace-1/projects/meeting-research-automation/Life Automations"
source venv/bin/activate

# Sync today
python src/main.py

# Sync yesterday
python src/main.py --mode yesterday

# Sync this week
python src/main.py --mode week

# Sync specific date
python src/main.py --mode date --date 2025-10-20

# Validate setup
python src/main.py --mode validate
```

## Monitoring

### View Sync Logs
```bash
tail -f logs/sync.log
```

### View Cron Logs
```bash
tail -f logs/cron.log
```

### Check Last Sync
```bash
cat cache/sync_state.json
```

## Configuration

### Target Calendar
- **Current:** Time Tracking: Toggl
- **Location:** `.env` → `GOOGLE_CALENDAR_ID`

### Sync Settings
Edit `.env` file:
```bash
TOGGL_SYNC_ENABLED=true          # Enable/disable sync
TOGGL_AUTO_SYNC=true             # Auto-sync new entries
TOGGL_SYNC_RUNNING=false         # Sync currently running timers
```

### Filtering
Edit `config.yaml` to filter:
- Specific projects
- Specific tags
- Minimum duration
- Billable only

## Troubleshooting

### Sync not running automatically
```bash
# Check cron is scheduled
crontab -l

# Check cron logs
tail -20 logs/cron.log

# Test manual sync
./toggl-sync.sh
```

### Authentication expired
```bash
# Delete token and re-authenticate
rm credentials/token.pickle
./toggl-sync.sh status
```

### Duplicate entries
```bash
# Clear sync state and re-sync
rm cache/sync_state.json
./toggl-sync.sh
```

### View detailed errors
```bash
tail -100 logs/sync.log
```

## Quick Commands

| Command | Description |
|---------|-------------|
| `./toggl-sync.sh` | Sync today |
| `./toggl-sync.sh yesterday` | Sync yesterday |
| `./toggl-sync.sh week` | Sync this week |
| `./toggl-sync.sh status` | Check connection |
| `./toggl-sync.sh logs` | View recent logs |
| `crontab -l` | View scheduled jobs |
| `tail -f logs/cron.log` | Monitor auto-sync |

## What Gets Synced

Each Toggl entry becomes a calendar event with:
- ✓ Title: `[Time] {description} - {project}`
- ✓ Duration: Shown in hours and minutes
- ✓ Project name: If available
- ✓ Tags: Listed in description
- ✓ Billable status: 💰 icon if billable
- ✓ Link to Toggl: Direct link to entry

## Support

- **Full docs:** `README.md`
- **Setup guide:** `SETUP_GUIDE.md`
- **Project overview:** `PROJECT_SUMMARY.md`
- **Logs:** `logs/sync.log`, `logs/cron.log`

---

**Last Updated:** October 24, 2025
**Status:** ✅ Active and running automatically every 30 minutes
