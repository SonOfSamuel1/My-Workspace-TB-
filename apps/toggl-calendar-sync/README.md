# Toggl to Google Calendar Sync

Automatically synchronize your Toggl Track time entries to Google Calendar in real-time.

## Features

- **Real-time Sync** - Webhook-based instant synchronization when you start/stop timers
- **Batch Sync** - Sync today, yesterday, or any date range
- **Smart Updates** - Automatically updates existing calendar events
- **Project Integration** - Includes project names and colors in calendar events
- **Billable Tracking** - Shows billable status in event descriptions
- **Tag Support** - Syncs Toggl tags to calendar event descriptions
- **Running Entry Handling** - Optional sync of currently running timers
- **Duplicate Prevention** - Smart detection prevents duplicate calendar events

## Quick Start

```bash
# Navigate to project
cd toggl-calendar-sync

# Sync today's entries
python src/main.py --mode today

# Sync yesterday
python src/main.py --mode yesterday

# Sync current week
python src/main.py --mode week

# Start continuous sync (every 5 minutes)
python src/main.py --continuous --interval 5
```

## Documentation

- [Setup Guide](./docs/SETUP_GUIDE.md) - Complete installation and configuration
- [Project Summary](./docs/PROJECT_SUMMARY.md) - Technical overview and architecture
- [Quick Reference](./docs/QUICK_REFERENCE.md) - Command cheat sheet
- [Usage Guide](./docs/USAGE.md) - Detailed usage instructions

## Configuration

Edit `../config.yaml` and `../.env` to customize:
- Sync behavior and filters
- Event title format
- Calendar colors
- Webhook settings

## Requirements

- Python 3.8+
- Google Calendar API credentials
- Toggl Track API token

See [Setup Guide](./docs/SETUP_GUIDE.md) for detailed instructions.

## Project Structure

```
toggl-calendar-sync/
├── src/
│   ├── main.py              # Main entry point
│   ├── sync_service.py      # Sync orchestration
│   ├── webhook_server.py    # Webhook listener
│   └── toggl_service.py     # Toggl API client
├── docs/
│   ├── SETUP_GUIDE.md
│   ├── PROJECT_SUMMARY.md
│   ├── QUICK_REFERENCE.md
│   └── USAGE.md
└── toggl-sync.sh            # Shell script wrapper
```

## Support

For issues or questions:
1. Check the logs: `tail -f ../logs/sync.log`
2. Run validation: `python src/main.py --mode validate`
3. Review the [Setup Guide](./docs/SETUP_GUIDE.md)

---

[← Back to Life Automations](../README.md)
