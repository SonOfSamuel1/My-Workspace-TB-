# Cron Job Setup for Toggl Calendar Sync

## Current Configuration

The Toggl calendar sync runs automatically every 30 minutes via cron.

### Cron Entry

```bash
*/30 * * * * cd '/Users/terrancebrandon/personal-workspace-1/projects/Life Automations' && ./venv/bin/python3 toggl-calendar-sync/src/main.py --mode today >> logs/cron.log 2>&1
```

### Important Notes

1. **Working Directory**: The cron job must run from the `Life Automations` directory (parent directory) so that:
   - The `.env` file can be found
   - The `venv` virtual environment is accessible
   - Logs are written to the correct location

2. **Script Path**: The script is referenced relatively as `toggl-calendar-sync/src/main.py`

3. **Logs**: Output is appended to `logs/cron.log`

## Viewing Cron Jobs

```bash
crontab -l
```

## Editing Cron Jobs

```bash
crontab -e
```

## Troubleshooting

If the sync stops working:

1. Check that the cron job is still configured:
   ```bash
   crontab -l | grep toggl
   ```

2. Verify the working directory path is correct in the cron entry

3. Check the logs for errors:
   ```bash
   tail -f ~/personal-workspace-1/projects/Life\ Automations/logs/cron.log
   ```

4. Test the sync manually:
   ```bash
   cd '/Users/terrancebrandon/personal-workspace-1/projects/Life Automations'
   ./venv/bin/python3 toggl-calendar-sync/src/main.py --mode today
   ```

## Manual Sync Commands

From the `Life Automations` directory:

```bash
# Sync today
./venv/bin/python3 toggl-calendar-sync/src/main.py --mode today

# Sync yesterday
./venv/bin/python3 toggl-calendar-sync/src/main.py --mode yesterday

# Sync current week
./venv/bin/python3 toggl-calendar-sync/src/main.py --mode week

# Sync specific date
./venv/bin/python3 toggl-calendar-sync/src/main.py --mode date --date 2025-10-26
```

## Fix Applied (2025-10-27)

Fixed broken cron job after project reorganization:
- **Old path**: `/Users/terrancebrandon/personal-workspace-1/projects/meeting-research-automation/Life Automations`
- **New path**: `/Users/terrancebrandon/personal-workspace-1/projects/Life Automations`

This fix restored automatic syncing and backfilled 152 missing entries from October.
