# Love Brittany Action Plan Tracker

Intelligent relationship tracking automation that monitors relationship activities and generates beautiful bi-weekly HTML email reports.

## Features

- **Automated Reports** - Bi-weekly HTML emails (Saturday 7pm, Wednesday 6:30pm EST)
- **Comprehensive Tracking** - 9 activity categories monitored
- **Date Night Planning** - 12-month lookahead with babysitter verification
- **Time Investment** - Toggl tracking with 30-day analytics
- **Health Scoring** - Overall relationship health indicators
- **Critical Alerts** - Notifications for overdue activities
- **Google Integration** - Calendar, Docs, and Gmail

## Tracked Activities

1. **Action Plan Reviews** - Regular check-ins
2. **Date Nights** - With reservation and babysitter verification
3. **Unexpected Gifts** - Quarterly surprise tracking
4. **Love Letters** - Every 3 weeks
5. **Daily 10-Minute Gaps** - Daily relationship focus time
6. **Time Suggestions** - Monthly quality time ideas
7. **Monthly Journals** - Relationship reflections
8. **Goal Support** - Monthly goal assistance
9. **Time Investment** - Toggl time tracking analytics

## Quick Start

```bash
# Navigate to project
cd relationship-tracker

# Validate configuration
python src/relationship_main.py --validate

# Generate a report now
python src/relationship_main.py --generate

# Start scheduled reports
python src/relationship_scheduler.py
```

## Setup

**Fast Track (5 minutes):**
See [Quick Start Guide](./docs/QUICK_START_RELATIONSHIP.md)

**Complete Setup:**
See [Full Setup Guide](./docs/RELATIONSHIP_SETUP_GUIDE.md)

### Quick Setup Steps

1. **Install dependencies:**
   ```bash
   pip install -r ../requirements.txt
   ```

2. **Configure Google APIs:**
   - Enable Calendar, Docs, and Gmail APIs
   - Add credentials to `../credentials/credentials.json`

3. **Setup tracking document:**
   - Create Google Doc from [template](./docs/RELATIONSHIP_TRACKING_TEMPLATE.md)
   - Add document ID to `../config.yaml`

4. **Configure environment:**
   - Update `../.env` with credentials
   - Set email recipient in `../config.yaml`

5. **Run setup wizard:**
   ```bash
   ./setup_wizard.sh
   ```

## Documentation

- [Relationship Setup Guide](./docs/RELATIONSHIP_SETUP_GUIDE.md) - Complete setup instructions
- [Quick Start](./docs/QUICK_START_RELATIONSHIP.md) - 5-minute setup
- [Implementation Summary](./docs/IMPLEMENTATION_SUMMARY.md) - Technical details
- [Tracking Template](./docs/RELATIONSHIP_TRACKING_TEMPLATE.md) - Google Doc template
- [Your Setup Steps](./docs/YOUR_SETUP_STEPS.md) - Personalized guide

## Configuration

### Email Schedule
Reports are sent:
- **Saturday at 7:00 PM EST**
- **Wednesday at 6:30 PM EST**

Configure in `../config.yaml`:
```yaml
relationship_tracking:
  schedule:
    - "0 19 * * 6"   # Saturday 7pm
    - "30 18 * * 3"  # Wednesday 6:30pm
```

### Tracking Periods
Customize frequency in `../config.yaml`:
- Gifts: Every 90 days (3 months)
- Letters: Every 21 days (3 weeks)
- Journals: Every 30 days (monthly)
- Other activities: Configurable

## Project Structure

```
relationship-tracker/
├── src/
│   ├── relationship_main.py         # Main orchestrator
│   ├── relationship_tracker.py      # Tracking logic
│   ├── relationship_report.py       # Report generator
│   ├── relationship_scheduler.py    # Bi-weekly scheduler
│   ├── docs_service.py              # Google Docs integration
│   ├── email_sender.py              # Gmail integration
│   ├── calendar_service.py          # Google Calendar integration
│   └── toggl_service.py             # Toggl integration
├── docs/
│   ├── RELATIONSHIP_SETUP_GUIDE.md
│   ├── QUICK_START_RELATIONSHIP.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── RELATIONSHIP_TRACKING_TEMPLATE.md
│   └── YOUR_SETUP_STEPS.md
└── setup_wizard.sh                  # Interactive setup
```

## Report Format

Reports include:
- **Executive Summary** - Overall health score
- **Activity Status** - All 9 tracked categories
- **Date Night Calendar** - 12-month schedule
- **Time Investment** - 30-day Toggl stats
- **Critical Alerts** - Overdue activities
- **Next Actions** - Upcoming tasks

## Troubleshooting

### Common Issues

1. **Report not generating:**
   - Check Google Doc ID in config
   - Verify credentials are valid
   - Review logs: `tail -f ../logs/relationship.log`

2. **Email not sending:**
   - Verify Gmail API is enabled
   - Check recipient email in config
   - Ensure OAuth scopes include Gmail

3. **Calendar data missing:**
   - Verify calendar ID in config
   - Check date range settings
   - Ensure events use correct search terms

### Validation
```bash
python src/relationship_main.py --validate
```

## Support

For issues or questions:
1. Run validation to diagnose issues
2. Check logs in `../logs/relationship.log`
3. Review setup guides in `docs/`

---

[← Back to Life Automations](../README.md)
