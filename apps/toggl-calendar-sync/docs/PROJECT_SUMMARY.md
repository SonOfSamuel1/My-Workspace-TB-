# Toggl to Google Calendar Sync - Project Summary

## What This Does

Automatically syncs your Toggl Track time entries to Google Calendar as calendar events. No more manual entry creation!

## Project Structure

```
Life Automations/
├── src/
│   ├── main.py              # Main entry point - run sync operations
│   ├── toggl_service.py     # Toggl Track API client
│   ├── calendar_service.py  # Google Calendar API client
│   ├── sync_service.py      # Sync orchestration logic
│   └── webhook_server.py    # Real-time webhook listener
│
├── credentials/
│   ├── credentials.json     # Google OAuth credentials (you add this)
│   └── token.pickle         # Saved auth token (auto-generated)
│
├── logs/
│   ├── sync.log            # Sync operation logs
│   └── webhook.log         # Webhook server logs
│
├── cache/
│   └── sync_state.json     # Tracks synced entries
│
├── .env                    # Your credentials (you create this)
├── .env.example           # Template for .env
├── config.yaml            # Application settings
├── requirements.txt       # Python dependencies
│
├── README.md             # Complete documentation
├── SETUP_GUIDE.md       # Step-by-step setup
├── QUICK_REFERENCE.md   # Command cheat sheet
└── PROJECT_SUMMARY.md   # This file
```

## Core Components

### 1. toggl_service.py
- Connects to Toggl Track API
- Fetches time entries
- Retrieves project information
- Formats entry data

**Key Methods:**
- `get_time_entries(start_date, end_date)` - Get entries for date range
- `get_current_time_entry()` - Get running timer
- `get_time_entry_by_id(id)` - Get specific entry

### 2. calendar_service.py
- Connects to Google Calendar API
- Creates calendar events
- Updates existing events
- Manages OAuth authentication

**Key Methods:**
- `create_time_entry_event(time_entry)` - Create calendar event
- `update_time_entry_event(time_entry, event_id)` - Update event
- `delete_time_entry_event(event_id)` - Remove event

### 3. sync_service.py
- Orchestrates sync between Toggl and Calendar
- Tracks which entries are synced
- Prevents duplicate events
- Manages sync state

**Key Methods:**
- `sync_time_entry(time_entry)` - Sync single entry
- `sync_today()` - Sync today's entries
- `sync_date_range(start, end)` - Sync date range

### 4. main.py
- CLI entry point
- Argument parsing
- Logging setup
- Continuous mode support

**Usage:**
```bash
python src/main.py                    # Sync today
python src/main.py --mode yesterday   # Sync yesterday
python src/main.py --continuous       # Keep running
```

### 5. webhook_server.py
- Flask webhook server
- Receives Toggl webhooks
- Triggers real-time sync
- Signature verification

**Usage:**
```bash
python src/webhook_server.py  # Start webhook server
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      SYNC PROCESS                           │
└─────────────────────────────────────────────────────────────┘

1. Fetch Time Entries
   ┌─────────────┐
   │ Toggl Track │ ─── API ──→ TogglService
   └─────────────┘             │
                               ▼
                     [Get entries for date range]
                               │
                               ▼
                     [Format entry data]

2. Check Sync Status
                               │
                               ▼
                        SyncService
                               │
                               ▼
                  [Check sync_state.json]
                  Already synced? ──→ Yes ──→ Update event
                        │
                        No
                        │
                        ▼

3. Create Calendar Event
                               │
                               ▼
                    CalendarService
                               │
                               ▼
                [Create/update event]
                               │
                               ▼
                [Build event structure]
                  - Title: [Time] {description} - {project}
                  - Body: Duration, tags, billable status
                  - Time: Start/end from entry
                  - Color: Configurable
                               │
                               ▼
   ┌─────────────────┐
   │ Google Calendar │ ←── API ──┘
   └─────────────────┘

4. Track State
                               │
                               ▼
                  [Save to sync_state.json]
                  {
                    "toggl_id": "calendar_event_id",
                    ...
                  }
```

## Configuration System

### Environment Variables (.env)
- API credentials (Toggl token, workspace ID)
- Google Calendar settings
- Timezone configuration
- Webhook settings

### Application Config (config.yaml)
- Sync behavior (enabled, auto-sync, running entries)
- Event formatting (title, color, reminders)
- Filtering (projects, tags, duration)
- Logging preferences

## Sync Modes

### 1. Manual Sync
Run once and exit:
```bash
python src/main.py --mode today
```

### 2. Continuous Sync
Keep running, check every N minutes:
```bash
python src/main.py --continuous --interval 5
```

### 3. Scheduled Sync (Cron)
Run automatically on schedule:
```bash
*/30 * * * * cd /path/to/project && python src/main.py
```

### 4. Real-time Sync (Webhook)
Instant sync via webhook notifications:
```bash
python src/webhook_server.py
```

## Key Features

### ✅ Smart Duplicate Prevention
- Tracks synced entries in `cache/sync_state.json`
- Maps Toggl entry IDs to Calendar event IDs
- Updates existing events instead of creating duplicates

### ✅ Comprehensive Event Details
- Entry description as event title
- Project name included
- Duration displayed
- Tags shown
- Billable status indicator
- Direct link to Toggl entry

### ✅ Flexible Filtering
- Include/exclude specific projects
- Filter by tags
- Minimum duration threshold
- Billable-only option

### ✅ Error Handling
- Retry logic for API failures
- Comprehensive logging
- Graceful degradation
- State recovery

## API Integration

### Toggl Track API
- **Base URL:** `https://api.track.toggl.com/api/v9`
- **Authentication:** HTTP Basic Auth (API token)
- **Endpoints Used:**
  - `GET /me/time_entries` - List entries
  - `GET /time_entries/{id}` - Get entry details
  - `GET /workspaces/{id}/projects` - List projects

### Google Calendar API
- **API Version:** v3
- **Authentication:** OAuth 2.0
- **Scopes:** `https://www.googleapis.com/auth/calendar`
- **Endpoints Used:**
  - `POST /calendars/{id}/events` - Create event
  - `PUT /calendars/{id}/events/{eventId}` - Update event
  - `DELETE /calendars/{id}/events/{eventId}` - Delete event

## State Management

### sync_state.json Structure
```json
{
  "synced_entries": {
    "123456789": "abc123xyz",  // toggl_id: calendar_event_id
    "987654321": "xyz789abc"
  },
  "last_sync": "2025-10-24T10:30:00",
  "total_synced": 42
}
```

### Calendar Event Extended Properties
```json
{
  "extendedProperties": {
    "private": {
      "toggl_entry_id": "123456789",
      "source": "toggl_track",
      "sync_version": "1.0"
    }
  }
}
```

## Logging

### Log Levels
- **INFO:** Normal operations (syncs, creates, updates)
- **WARNING:** Non-critical issues (running entries skipped)
- **ERROR:** Failures (API errors, auth problems)

### Log Files
- `logs/sync.log` - Main sync operations
- `logs/webhook.log` - Webhook server events
- `logs/cron.log` - Cron job output (if using cron)

### Log Format
```
2025-10-24 10:30:00 - module_name - LEVEL - Message
```

## Security Considerations

### Credentials Storage
- **API tokens:** Stored in `.env` (gitignored)
- **OAuth tokens:** Stored in `credentials/token.pickle` (gitignored)
- **Never committed:** All sensitive files in `.gitignore`

### Webhook Security
- HMAC signature verification
- Secret key validation
- Request payload verification

### API Permissions
- **Toggl:** Read-only (time entries, projects)
- **Google Calendar:** Full access (create, update, delete events)

## Performance

### Typical Sync Times
- **Single entry:** ~0.5-1 second
- **10 entries:** ~5-10 seconds
- **100 entries:** ~50-100 seconds

### API Rate Limits
- **Toggl:** 1 request/second recommended
- **Google Calendar:** 5 queries/second (well within limits)

### Optimization
- Batch operations where possible
- State tracking prevents unnecessary API calls
- Caching of project information

## Extensibility

### Adding Custom Filters
Edit `config.yaml`:
```yaml
filters:
  include_projects: ["Client Work"]
  exclude_tags: ["personal"]
  min_duration_minutes: 15
```

### Custom Event Formatting
Edit `config.yaml`:
```yaml
calendar:
  title_format: "⏱️ {description} [{project}]"
  default_color_id: 9
```

### Adding New Sync Modes
Extend `sync_service.py`:
```python
def sync_last_week(self) -> Dict:
    start = datetime.now() - timedelta(days=7)
    return self.sync_date_range(start)
```

## Testing

### Test Individual Services
```bash
# Test Toggl connection
python src/toggl_service.py

# Test Calendar connection
python src/calendar_service.py

# Test sync logic
python src/sync_service.py
```

### Validate Setup
```bash
python src/main.py --mode validate
```

### Check Logs
```bash
tail -f logs/sync.log
```

## Maintenance

### Regular Tasks
- Review logs weekly
- Clear old cache files monthly
- Update dependencies quarterly
- Rotate API tokens annually

### Troubleshooting
1. Check logs first
2. Verify credentials
3. Test API connectivity
4. Clear sync state if needed
5. Re-authenticate if OAuth fails

## Future Enhancements

Potential improvements:
- [ ] Desktop notifications for syncs
- [ ] Web dashboard for sync status
- [ ] Bi-directional sync (Calendar → Toggl)
- [ ] Multiple calendar support
- [ ] Custom color mapping per project
- [ ] Conflict resolution strategies
- [ ] Export sync reports
- [ ] Integration with other time tracking tools

## Quick Command Reference

```bash
# Setup
pip install -r requirements.txt
cp .env.example .env

# Sync
python src/main.py                    # Today
python src/main.py --mode yesterday   # Yesterday
python src/main.py --mode week        # This week
python src/main.py --mode date --date 2025-10-15

# Validate
python src/main.py --mode validate

# Continuous
python src/main.py --continuous --interval 5

# Webhook
python src/webhook_server.py

# Logs
tail -f logs/sync.log
```

## Documentation Files

- **README.md** - Complete user guide with all features
- **SETUP_GUIDE.md** - Step-by-step installation and configuration
- **QUICK_REFERENCE.md** - Command cheat sheet
- **PROJECT_SUMMARY.md** - This technical overview

---

**Version:** 1.0.0
**Created:** October 24, 2025
**Status:** Production Ready ✅
