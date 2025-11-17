# Toggl Daily Report - Quick Start Implementation Guide

Based on Love Brittany Tracker Architecture Analysis

---

## Phase 1: Setup & Structure (Day 1)

### 1.1 Create Project Structure
```bash
mkdir -p toggl-daily-report/src
mkdir -p toggl-daily-report/scripts
mkdir -p toggl-daily-report/docs
mkdir -p toggl-daily-report/logs
mkdir -p toggl-daily-report/tests
```

### 1.2 Copy Foundation Files
```bash
# Copy from love-brittany-tracker
cp apps/love-brittany-tracker/config.yaml toggl-daily-report/
cp apps/love-brittany-tracker/.env.example toggl-daily-report/
cp apps/love-brittany-tracker/requirements.txt toggl-daily-report/
cp apps/love-brittany-tracker/src/email_sender.py toggl-daily-report/src/
cp apps/love-brittany-tracker/lambda_handler.py toggl-daily-report/  # Adapt
cp apps/love-brittany-tracker/Dockerfile.lambda toggl-daily-report/
```

### 1.3 Create Initial Files
```bash
# Create entry point
touch toggl-daily-report/src/toggl_daily.py

# Create services
touch toggl-daily-report/src/toggl_service.py
touch toggl-daily-report/src/calendar_service.py

# Create business logic
touch toggl-daily-report/src/daily_report_generator.py
touch toggl-daily-report/src/report_formatter.py

# Create scheduler
touch toggl-daily-report/src/toggl_scheduler.py

# Create main docs
touch toggl-daily-report/README.md
```

### 1.4 Update config.yaml
```yaml
toggl_daily_report:
  enabled: true
  
  # Cron: 6 PM weekdays EST
  schedule: "0 18 * * 1-5"
  timezone: "America/New_York"
  
  email:
    recipient: "${TOGGL_REPORT_EMAIL}"
    subject_template: "Daily Time Report - {date}"
    include_summary: true
    include_breakdown: true
    include_insights: true
  
  toggl:
    api_token: "${TOGGL_API_TOKEN}"
    workspace_id: "${TOGGL_WORKSPACE_ID}"
    project_name: ""  # Optional filter
  
  display:
    min_duration_minutes: 1
    group_by_project: true
    show_tags: true
  
  thresholds:
    alert_over_hours: 10
    goal_hours: 8

logging:
  level: "INFO"
  file: "logs/toggl_daily.log"
```

### 1.5 Update .env.example
```
# Toggl API
TOGGL_API_TOKEN=your_api_token_here
TOGGL_WORKSPACE_ID=your_workspace_id_here

# Google
GOOGLE_CREDENTIALS_FILE=credentials/credentials.json
GOOGLE_TOKEN_FILE=credentials/token.pickle

# Email
TOGGL_REPORT_EMAIL=your-email@example.com

# Optional
TOGGL_REPORT_TIMEZONE=America/New_York
TOGGL_DAILY_GOAL_HOURS=8
```

---

## Phase 2: Core Implementation (Days 2-3)

### 2.1 Toggl Service (toggl_service.py)

**Key Methods:**
```python
class TogglService:
    def __init__(self, api_token: str, workspace_id: str)
    
    def get_time_entries(self, start_date: datetime, end_date: datetime) -> List[Dict]
        # Returns: [{'id', 'description', 'project_name', 'start', 'duration_seconds', 'tags'}]
    
    def get_project_summary(self, entries: List[Dict]) -> Dict
        # Returns: {'total_hours', 'by_project': {...}, 'by_tag': {...}}
    
    def get_running_entry(self) -> Optional[Dict]
        # For active timer (optional)
    
    def validate_credentials(self) -> bool
        # Test API connection
```

**Implementation Pattern:**
```python
import requests
from base64 import b64encode

class TogglService:
    def __init__(self, api_token: str, workspace_id: str):
        self.api_token = api_token
        self.workspace_id = workspace_id
        self.base_url = "https://api.track.toggl.com/api/v9"
        
        # Basic Auth: token:api_token
        auth_string = f"{api_token}:api_token"
        auth_b64 = b64encode(auth_string.encode()).decode()
        self.headers = {'Authorization': f'Basic {auth_b64}'}
    
    def get_time_entries(self, start_date, end_date):
        # GET /me/time_entries?start_date=2025-11-17T00:00:00Z&end_date=2025-11-18T00:00:00Z
        # Format as ISO strings
        params = {
            'start_date': start_date.isoformat() + 'Z',
            'end_date': end_date.isoformat() + 'Z'
        }
        response = requests.get(f"{self.base_url}/me/time_entries", 
                               headers=self.headers, params=params)
        return response.json()
```

### 2.2 Daily Report Generator (daily_report_generator.py)

**Key Methods:**
```python
class DailyReportGenerator:
    def __init__(self, toggl_service, config: Dict)
    
    def generate_report(self, date: datetime) -> Dict
        # Returns complete report data structure
    
    def _calculate_summary(self, entries: List[Dict]) -> Dict
        # Total hours, projects, tags
    
    def _generate_insights(self, entries: List[Dict]) -> List[str]
        # Pattern analysis, suggestions
    
    def _check_thresholds(self, summary: Dict) -> List[Dict]
        # Alerts if over goal
```

**Implementation Pattern:**
```python
class DailyReportGenerator:
    def generate_report(self, date: datetime) -> Dict:
        # Get 24-hour window
        start = date.replace(hour=0, minute=0, second=0)
        end = date.replace(hour=23, minute=59, second=59)
        
        # Fetch entries
        entries = self.toggl_service.get_time_entries(start, end)
        
        # Aggregate
        summary = self._calculate_summary(entries)
        
        return {
            'date': date.isoformat(),
            'entries': entries,
            'summary': summary,
            'insights': self._generate_insights(entries),
            'alerts': self._check_thresholds(summary)
        }
    
    def _calculate_summary(self, entries):
        total_seconds = sum(e['duration'] for e in entries if e['duration'] > 0)
        total_hours = total_seconds / 3600
        
        by_project = {}
        for entry in entries:
            project = entry.get('project_name', 'No Project')
            if project not in by_project:
                by_project[project] = 0
            by_project[project] += entry['duration']
        
        return {
            'total_hours': round(total_hours, 2),
            'total_seconds': total_seconds,
            'by_project': {p: round(s/3600, 2) for p, s in by_project.items()},
            'entry_count': len([e for e in entries if e['duration'] > 0])
        }
```

### 2.3 Report Formatter (report_formatter.py)

**Key Methods:**
```python
class DailyReportFormatter:
    def __init__(self, config: Dict)
    
    def generate_html(self, report_data: Dict) -> str
        # Returns HTML email body
```

**HTML Structure:**
```html
<html>
  <head>
    <style>
      /* Email-safe CSS: inline styles, table-based layout */
      body { font-family: Arial, sans-serif; }
      .summary { background: #f0f0f0; padding: 20px; }
      .alert { color: red; font-weight: bold; }
    </style>
  </head>
  <body>
    <!-- 1. Header with date -->
    <!-- 2. Summary card (total hours, status) -->
    <!-- 3. Alert section (if over goal) -->
    <!-- 4. Project breakdown (table) -->
    <!-- 5. Detailed entries (expandable or table) -->
    <!-- 6. Insights/suggestions -->
    <!-- 7. Tomorrow preview (optional) -->
  </body>
</html>
```

---

## Phase 3: Integration & Scheduling (Days 4-5)

### 3.1 Entry Point (toggl_daily.py)

**Command-Line Interface:**
```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--generate', action='store_true', 
                       help='Generate report for today')
    parser.add_argument('--date', help='Specific date (YYYY-MM-DD)')
    parser.add_argument('--send-email', action='store_true',
                       help='Send email (default: no-email)')
    parser.add_argument('--validate', action='store_true',
                       help='Validate configuration')
    parser.add_argument('--schedule', action='store_true',
                       help='Start scheduler daemon')
    args = parser.parse_args()
    
    if args.generate:
        date = datetime.fromisoformat(args.date) if args.date else datetime.now()
        generate_and_send(date, send_email=args.send_email)
    
    elif args.validate:
        validate_setup()
    
    elif args.schedule:
        start_scheduler()
```

**Usage:**
```bash
# Generate for today (no email)
python src/toggl_daily.py --generate

# Generate and send email
python src/toggl_daily.py --generate --send-email

# Specific date
python src/toggl_daily.py --generate --date 2025-11-17 --send-email

# Validate setup
python src/toggl_daily.py --validate

# Start scheduler
python src/toggl_daily.py --schedule
```

### 3.2 Scheduler (toggl_scheduler.py)

**Implementation:**
```python
from schedule import Scheduler
import time

def scheduled_job():
    logger.info("Running scheduled daily report...")
    generate_and_send(datetime.now(), send_email=True)
    logger.info("Report complete")

def setup_schedule(config):
    scheduler = Scheduler()
    
    # Parse cron expression from config
    # "0 18 * * 1-5" = 6 PM weekdays
    cron_expr = config['toggl_daily_report']['schedule']
    
    # Setup job
    scheduler.every().day.at("18:00").do(scheduled_job)
    
    # Run forever
    while True:
        scheduler.run_pending()
        time.sleep(60)
```

---

## Phase 4: AWS Deployment (Days 6-7)

### 4.1 Lambda Handler (lambda_handler.py)

**Adapt from love-brittany-tracker:**
```python
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

from toggl_daily import generate_and_send, load_config, validate_configuration

def load_parameters_from_ssm():
    """Load API keys from AWS Parameter Store"""
    import boto3
    ssm = boto3.client('ssm')
    
    params = {
        'toggl_token': '/toggl-daily/api-token',
        'toggl_workspace': '/toggl-daily/workspace-id',
        'email': '/toggl-daily/recipient-email'
    }
    
    for key, param_name in params.items():
        try:
            response = ssm.get_parameter(Name=param_name, WithDecryption=True)
            os.environ[f'TOGGL_{key.upper()}'] = response['Parameter']['Value']
        except Exception as e:
            logger.warning(f"Could not load {param_name}: {e}")

def handler(event, context):
    """Lambda entry point - triggered by EventBridge daily"""
    logger.info("Starting Toggl Daily Report Lambda...")
    
    try:
        # Load secrets
        load_parameters_from_ssm()
        
        # Load config
        config = load_config()
        if not validate_configuration(config):
            raise ValueError("Config validation failed")
        
        # Generate report for today
        date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        generate_and_send(date, send_email=True)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Report sent successfully'})
        }
    except Exception as e:
        logger.error(f"Failed: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

### 4.2 EventBridge Configuration

**Deploy script (scripts/setup-eventbridge.sh):**
```bash
#!/bin/bash

RULE_NAME="toggl-daily-report"
FUNCTION_NAME="toggl-daily-report"
SCHEDULE="cron(0 23 ? * MON-FRI *)"  # 6 PM EST = 11 PM UTC

# Create rule
aws events put-rule \
    --name $RULE_NAME \
    --schedule-expression $SCHEDULE \
    --state ENABLED

# Add Lambda target
aws events put-targets \
    --rule $RULE_NAME \
    --targets "Id"="1","Arn"="arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}"

# Add Lambda permission
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id AllowEventBridge \
    --action 'lambda:InvokeFunction' \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:${AWS_REGION}:${ACCOUNT_ID}:rule/${RULE_NAME}"
```

---

## Testing Checklist

### Unit Tests
- [ ] Toggl API client returns correct format
- [ ] Summary calculation (hours, projects)
- [ ] Alert thresholds
- [ ] HTML generation (no broken tags)
- [ ] Date/timezone handling

### Integration Tests
- [ ] Read from Toggl API (with test token)
- [ ] Generate complete report
- [ ] Format as valid HTML
- [ ] Send email (to test address first)

### End-to-End Tests
- [ ] Local execution: `python src/toggl_daily.py --generate --send-email`
- [ ] Scheduler: `python src/toggl_scheduler.py` (run for 1 minute)
- [ ] Lambda: `aws lambda invoke --function-name toggl-daily-report response.json`
- [ ] Email delivery (check inbox)

---

## Estimated Timeline

| Phase | Task | Time |
|-------|------|------|
| 1 | Setup & scaffold | 2 hours |
| 2 | Toggl service | 4 hours |
| 2 | Report generator | 4 hours |
| 2 | Report formatter | 3 hours |
| 3 | Entry point & scheduler | 3 hours |
| 4 | AWS Lambda & EventBridge | 3 hours |
| Extras | Testing, docs, polish | 4 hours |
| **TOTAL** | | **~23 hours** |

---

## Key Differences from Love Brittany Tracker

| Aspect | Love Brittany | Toggl Daily |
|--------|---------------|-------------|
| Data Source | Calendar, Docs, Toggl | Toggl only |
| Report Frequency | 2x/week | Daily |
| Complexity | Multi-service aggregation | Single-service focus |
| Report Size | ~10 sections | ~5 sections |
| Alert Types | 9 activity types | 1-2 thresholds |

---

## File Structure Reference

```
toggl-daily-report/
├── README.md                      # Project documentation
├── config.yaml                    # Configuration template
├── .env.example                   # Environment variables
├── requirements.txt               # Python dependencies
├── lambda_handler.py              # AWS Lambda entry point
├── Dockerfile.lambda              # Docker for Lambda
│
├── src/
│   ├── toggl_daily.py            # Main entry point (CLI)
│   ├── toggl_service.py          # Toggl API client
│   ├── daily_report_generator.py # Report aggregation
│   ├── report_formatter.py       # HTML generation
│   ├── toggl_scheduler.py        # Local scheduler
│   └── email_sender.py           # Gmail integration (copied)
│
├── scripts/
│   ├── deploy-lambda-zip.sh      # Package & deploy
│   ├── setup-parameters.sh       # AWS Parameter Store
│   └── setup-eventbridge.sh      # EventBridge rule
│
├── docs/
│   ├── SETUP_GUIDE.md            # Installation & setup
│   ├── USAGE_GUIDE.md            # How to use
│   └── AWS_DEPLOYMENT.md         # Lambda deployment
│
├── tests/
│   ├── test_toggl_service.py
│   ├── test_report_generator.py
│   └── test_formatter.py
│
└── logs/
    └── toggl_daily.log           # (created at runtime)
```

---

## Next Steps

1. **Immediate:** Create the project structure
2. **Soon:** Implement toggl_service.py (hardest part)
3. **Then:** Build report generator and formatter
4. **Finally:** AWS Lambda deployment and testing

Good luck! You already have 80% of the architecture figured out from the Love Brittany Tracker.
