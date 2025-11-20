# Love Kaelin Development Tracker

Intelligent father-daughter relationship and development tracking automation that monitors activities and generates beautiful weekly HTML email reports.

## Features

- **Automated Reports** - Weekly HTML emails (Sunday 5am EST)
- **Comprehensive Tracking** - 13 development categories monitored
- **Play Time Analytics** - Rolling 100-day average with daily breakdowns
- **Quarterly Planning** - Daddy Days scheduled 4 quarters ahead
- **Jesus Teachings** - Track progress teaching 20 key lessons
- **Development Programs** - Ivy League prep and social program tracking
- **Time Investment** - Toggl tracking with analytics
- **Health Scoring** - Overall development health indicators
- **Critical Alerts** - Notifications for missed activities
- **Google Integration** - Calendar, Docs, and Gmail

## Tracked Activities

1. **Play Time** - Daily play sessions with rolling 100-day average
2. **Daddy Days** - Quarterly special father-daughter days
3. **Jesus Teachings** - Progress on 20 core teachings
4. **Monthly Games** - New game introductions (monthly target)
5. **Ivy League Prep** - Programs researched and enrolled
6. **Social Programs** - Activities for making friends
7. **Spiritual Development** - 6-month rolling plan
8. **Christmas Planning** - Special holiday preparations
9. **Crafting Activities** - Creative projects together
10. **Imaginative Play** - Creative play games
11. **Field Trips** - Educational outings (minimum 3/year)
12. **Gift Planning** - Thoughtful gift ideas and tracking
13. **Fun Contests** - Creative challenges and competitions

## Quick Start

```bash
# Navigate to project
cd apps/love-kaelin-tracker

# Validate configuration
python src/kaelin_main.py --validate

# Generate a report now
python src/kaelin_main.py --generate

# Generate without sending email
python src/kaelin_main.py --generate --no-email
```

## Setup

### Prerequisites

1. **Google Cloud Project** with the following APIs enabled:
   - Google Calendar API
   - Google Docs API
   - Gmail API

2. **Toggl Track Account** with API token

3. **Python 3.8+** installed

### Quick Setup Steps

1. **Install dependencies** (shared with love-brittany-tracker):
   ```bash
   # From workspace root
   pip install -r requirements.txt
   ```

2. **Configure Google APIs**:
   - Use existing credentials from `love-brittany-tracker`
   - Or add new credentials to `credentials/credentials.json`

3. **Create tracking document**:
   - Create a new Google Doc
   - Copy content from `docs/KAELIN_TRACKING_TEMPLATE.md`
   - Get document ID from URL: `https://docs.google.com/document/d/[DOCUMENT_ID]/edit`
   - Add ID to `config.yaml` under `kaelin_tracking.tracking_doc_id`

4. **Update configuration**:
   ```yaml
   # config.yaml
   kaelin_tracking:
     enabled: true
     tracking_doc_id: "YOUR_GOOGLE_DOC_ID"
     toggl_project_name: "Love Kaelin"
     email:
       recipient: "your-email@example.com"
   ```

5. **Set up environment variables**:
   ```bash
   # Can use shared .env from love-brittany-tracker
   # Or create local .env
   GOOGLE_CREDENTIALS_FILE=../credentials/credentials.json
   GOOGLE_TOKEN_FILE=../credentials/token.pickle
   TOGGL_API_TOKEN=your_toggl_token
   ```

6. **Run validation**:
   ```bash
   python src/kaelin_main.py --validate
   ```

7. **Generate your first report**:
   ```bash
   python src/kaelin_main.py --generate
   ```

## Configuration

### Report Schedule

Reports are sent weekly:
- **Sunday at 5:00 AM EST**

Configure in `config.yaml`:
```yaml
kaelin_tracking:
  schedule:
    - "0 5 * * 0"   # Sunday 5am EST
```

### Tracking Targets

Customize goals in `config.yaml`:
```yaml
tracking_periods:
  play_days_per_week_target: 5
  play_hours_per_day_target: 2.0
  new_game_frequency_days: 30
  field_trips_per_year_target: 3
  daddy_day_quarters_ahead: 4
  spiritual_planning_months: 6
```

### Jesus Teachings

20 core teachings tracked (customizable in config.yaml):
- Love God with all your heart
- Love your neighbor as yourself
- The Beatitudes
- The Lord's Prayer
- And 16 more...

## Project Structure

```
love-kaelin-tracker/
├── src/
│   ├── kaelin_main.py           # Main orchestrator
│   ├── kaelin_tracker.py        # Tracking logic
│   └── kaelin_report.py         # Report generator
├── docs/
│   └── KAELIN_TRACKING_TEMPLATE.md  # Google Doc template
├── output/                       # Generated reports
├── config.yaml                   # Configuration
└── README.md                     # This file
```

## Shared Services

This tracker uses shared services from `love-brittany-tracker`:
- `calendar_service.py` - Google Calendar integration
- `docs_service.py` - Google Docs integration
- `toggl_service.py` - Toggl integration
- `email_sender.py` - Gmail integration

## Report Format

Reports include:

### Executive Summary
- Overall development health score (0-100%)
- Play time statistics
- Recent activity summary
- Alert counts

### Detailed Sections
- **Play Time Analysis** - Rolling 100-day average, recent sessions
- **Daddy Days Calendar** - Quarterly planning status
- **Jesus Teachings Progress** - Taught vs. pending teachings
- **Monthly Games** - Game introduction tracking
- **Development Programs** - Ivy League prep and social programs
- **Spiritual Development** - 6-month planning status
- **Creative Activities** - Crafting and imaginative play
- **Field Trips** - Annual trip tracking
- **Planning** - Christmas and gift planning

### Alerts
- Critical alerts (red)
- Warnings (yellow)
- Information (blue)

## Metrics Tracked

### Play Time Metrics
- Days played (last 100 days)
- Total hours (last 100 days)
- Rolling 100-day average percentage
- Average hours per play day
- Days since last play session
- Recent 14-day breakdown

### Development Metrics
- Jesus teachings progress (20 total)
- Monthly games introduced
- Daddy Days planned (4 quarters)
- Field trips completed (annual)
- Ivy League programs researched/enrolled
- Active social programs
- Spiritual development plan status

### Quality Metrics
- Crafting success rate (high enjoyment %)
- Imaginative play engagement rate
- Christmas planning completeness
- Gift planning status

## Calendar Integration

The tracker monitors Google Calendar events with these search terms:

**Play Time:**
- "play with kaelin"
- "kaelin time"
- "daddy daughter time"

**Daddy Days:**
- "daddy day"
- "kaelin daddy day"
- "special day kaelin"

**Field Trips:**
- "kaelin field trip"
- "field trip"
- "kaelin outing"

**Teachings:**
- "kaelin lesson"
- "jesus teaching"
- "bible story kaelin"

Customize search terms in `config.yaml` under `calendar` section.

## Alert System

### Critical Alerts
- No play time for 3+ days
- Missing Daddy Day plans

### Warnings
- No play time for 2+ days
- Rolling average below 70% of target
- No new game introduced this month
- 6-month spiritual plan incomplete
- Missing quarterly Daddy Days

### Information
- 15+ teachings not yet taught
- Field trip target not met
- Program suggestions

## Toggl Integration

Tracks time spent with Kaelin through Toggl:
- Project name: "Love Kaelin" (configurable)
- 30-day statistics
- Average hours per day
- Total time investment

## Health Score Calculation

Overall development health score (0-100%) weighted by:
- Play Time (30%) - Rolling 100-day average
- Daddy Days (15%) - Quarterly coverage
- Jesus Teachings (20%) - Progress percentage
- Field Trips (10%) - Annual target met
- Monthly Games (10%) - Current month status
- Spiritual Development (15%) - Planning completion

## Troubleshooting

### Common Issues

1. **Report not generating:**
   - Check tracking document ID in config.yaml
   - Verify Google Docs credentials
   - Review logs: `tail -f logs/kaelin_tracker.log`

2. **Calendar events not found:**
   - Verify calendar search terms in config
   - Check event names match search terms
   - Ensure calendar is accessible

3. **Email not sending:**
   - Verify Gmail API is enabled
   - Check recipient email in config
   - Ensure OAuth scopes include Gmail

4. **Toggl data missing:**
   - Verify API token is valid
   - Check project name matches config
   - Ensure time entries exist

### Validation

Run setup validation to diagnose issues:
```bash
python src/kaelin_main.py --validate
```

This checks:
- Configuration file validity
- Environment variables
- Google services connectivity
- Toggl API access
- Gmail integration

## Output

Generated reports are saved to:
- `output/kaelin_report_YYYYMMDD_HHMMSS.html`

Open in browser to preview before email delivery.

## Scheduling

For automated weekly reports, use cron:

```bash
# Edit crontab
crontab -e

# Add this line for Sunday 5am EST
0 5 * * 0 cd /path/to/love-kaelin-tracker && python src/kaelin_main.py --generate
```

Or use the scheduler script (similar to love-brittany-tracker):
```bash
python src/kaelin_scheduler.py
```

## Development

### Adding New Metrics

1. Update `config.yaml` with new tracking configuration
2. Add tracking method to `kaelin_tracker.py`
3. Add report section to `kaelin_report.py`
4. Update tracking template in `docs/`
5. Add alert logic if needed

### Customizing Reports

Edit `kaelin_report.py`:
- Modify HTML templates
- Adjust color schemes
- Change stat calculations
- Add/remove sections

### Extending Functionality

The modular design allows easy extension:
- `kaelin_tracker.py` - Add new data collection methods
- `kaelin_report.py` - Add new report sections
- `kaelin_main.py` - Add new CLI commands

## Integration with Love Brittany Tracker

This tracker shares services and infrastructure with the Love Brittany tracker:

**Shared:**
- Google API credentials
- Toggl service
- Calendar integration
- Email sender
- Docs service

**Separate:**
- Tracking documents
- Configuration files
- Report templates
- Metrics and alerts

## Support

For issues or questions:
1. Run validation: `python src/kaelin_main.py --validate`
2. Check logs: `logs/kaelin_tracker.log`
3. Review configuration: `config.yaml`
4. Verify tracking document structure

## Relationship to Love Brittany Tracker

This is a sibling project to the Love Brittany Action Plan Tracker. Both systems:
- Use the same Google API infrastructure
- Share service modules
- Generate HTML email reports
- Track relationship activities

Key differences:
- **Focus:** Father-daughter development vs. romantic relationship
- **Metrics:** Play time, teachings, development programs vs. date nights, letters, gifts
- **Frequency:** Weekly vs. bi-weekly reports
- **Goals:** Child development milestones vs. relationship health

## Best Practices

1. **Update tracking document regularly** - Daily is ideal for play time
2. **Plan ahead** - Schedule Daddy Days quarterly
3. **Review reports** - Use insights to improve engagement
4. **Set realistic targets** - Adjust config.yaml based on schedule
5. **Use calendar integration** - Automatically track scheduled activities
6. **Track Toggl time** - Provides accurate time investment data

## Future Enhancements

Potential additions:
- Mobile app for quick tracking
- Photo/memory attachments
- Milestone celebrations
- Developmental assessments
- Reading list tracking
- Educational resource recommendations
- Automated backup of tracking data

## License

Part of the My Workspace monorepo. See repository LICENSE.

## Contact

Repository Owner: Terrance Brandon
GitHub: @SonOfSamuel1

---

**Last Updated:** 2025-01-17
**Version:** 1.0.0
**Status:** Production Ready

Made with 💖 for Kaelin's development journey
