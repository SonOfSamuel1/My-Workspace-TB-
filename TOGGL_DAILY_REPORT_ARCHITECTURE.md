# Toggl Daily Report System - Architecture Analysis
## Patterns from Love Brittany Tracker Application

**Analysis Date:** 2025-11-17
**Source:** `/home/user/My-Workspace-TB-/apps/love-brittany-tracker`

---

## 1. OVERALL PROJECT STRUCTURE

### Directory Layout
```
love-brittany-tracker/
├── src/                          # Core application logic
│   ├── relationship_main.py       # Entry point & orchestrator
│   ├── relationship_tracker.py    # Data aggregation & analysis
│   ├── relationship_report.py     # Report generation
│   ├── relationship_scheduler.py  # Local scheduling
│   ├── calendar_service.py        # Google Calendar integration
│   ├── docs_service.py            # Google Docs integration
│   ├── toggl_service.py           # Toggl Track integration
│   └── email_sender.py            # Gmail integration
├── docs/                          # User documentation
├── scripts/                       # Deployment scripts
├── config.yaml                    # Configuration (YAML)
├── .env.example                   # Environment template
├── lambda_handler.py              # AWS Lambda entry point
├── requirements.txt               # Python dependencies
├── Dockerfile.lambda              # Container definition
└── README.md                      # Main documentation
```

### Key Pattern: Separation of Concerns
- **Services Layer:** Handle external API integrations
- **Business Logic Layer:** Data aggregation and analysis
- **Orchestration Layer:** Coordinate services and generate output
- **Delivery Layer:** Send reports via email

---

## 2. CONFIGURATION MANAGEMENT

### YAML Configuration (`config.yaml`)
Centralized configuration with sensible defaults:

```yaml
# Main sections:
- sync:             # Toggl-to-Calendar sync settings
- calendar:         # Event formatting
- filters:          # Which entries to include/exclude
- logging:          # Log levels and file paths
- cache:            # Response caching (TTL, directory)
- webhook:          # Optional real-time updates
- metrics:          # Performance tracking
- relationship_tracking:  # Report-specific settings
```

### Environment Variables (`.env`)
- **API Credentials:** `TOGGL_API_TOKEN`, `TOGGL_WORKSPACE_ID`
- **Google Auth:** `GOOGLE_CREDENTIALS_FILE`, `GOOGLE_TOKEN_FILE`
- **Identifiers:** Document IDs, Calendar IDs, Email addresses
- **Feature Flags:** Enable/disable integrations

### Pattern: Config + Env Override
Configuration is layered:
1. Load defaults from `config.yaml`
2. Override with environment variables if present (for Lambda/Docker)
3. Validate all required settings before execution

---

## 3. API INTEGRATION ARCHITECTURE

### Three-Tier Service Pattern

#### Tier 1: Authentication Layer
Each service handles OAuth2/token management independently:

```python
class CalendarService:
    def authenticate(self):
        # Load token from pickle
        if not creds or not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())  # Refresh token
            else:
                flow = InstalledAppFlow.from_client_secrets_file(...)
                creds = flow.run_local_server(port=0)  # New OAuth2 flow
        pickle.dump(creds, token)  # Save for next run
```

**Key Points:**
- Tokens stored in pickle format (binary, secure)
- Auto-refresh when expired
- Graceful fallback to interactive login

#### Tier 2: API Request Layer
Each service wraps API calls with error handling:

```python
class TogglService:
    def get_time_entries(self, start_date, end_date):
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return self._format_time_entry(entry)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error: {str(e)}")
            return None
```

**Key Points:**
- Authentication headers constructed once (basic auth for Toggl)
- Error handling with logging
- Return formatted data structures

#### Tier 3: Data Formatting Layer
Services normalize API responses to consistent formats:

```python
def _format_time_entry(self, entry):
    return {
        'id': entry['id'],
        'description': entry['description'],
        'project_name': entry['project']['name'],
        'start': entry['start'],
        'duration_seconds': entry['duration'],
        'tags': entry.get('tags', [])
    }
```

### Service Patterns Used

| Service | API | Auth | Key Methods | Data Format |
|---------|-----|------|-------------|------------|
| CalendarService | Google Calendar | OAuth2 | `get_events()`, `create_event()` | Event dict with start/end datetime |
| DocsService | Google Docs | OAuth2 | `get_document_content()` | Plain text with section markers |
| TogglService | Toggl Track | Basic Auth | `get_time_entries()`, `get_current_entry()` | Entry dict with duration_seconds |
| EmailSender | Gmail | OAuth2 | `send_html_email()` | Formatted email (MIME) |

---

## 4. DATA AGGREGATION PATTERN

### RelationshipTracker: Multi-Source Data Collection

The `relationship_tracker.py` module exemplifies how to aggregate data:

```python
class RelationshipTracker:
    def generate_report(self) -> Dict:
        report = {
            'date_nights': self._check_date_nights(),       # Calendar
            'gifts': self._check_gifts(),                   # Google Docs
            'letters': self._check_letters(),               # Google Docs
            'action_plan_reviews': self._check_action_plan_reviews(),  # Docs
            'daily_gaps': self._check_daily_gaps(),         # Calendar
            'toggl_stats': self._get_toggl_statistics(),    # Toggl
            'journal_entries': self._check_journal_entries(),  # Docs
            'alerts': self._generate_alerts(report)         # Computed
        }
        return report
```

### Key Patterns:
1. **Parallel Data Collection:** Each check method is independent
2. **Consistent Return Format:** All methods return Dict with specific keys
3. **Error Resilience:** Missing data doesn't crash, returns empty/default
4. **Computed Alerts:** Generated after all data collected

### Example: Date Night Check
```python
def _check_date_nights(self):
    # 1. Query Calendar API for date range
    events = self.calendar_service.get_events(
        start_date=now,
        end_date=now + timedelta(days=365),
        search_terms=['date night', 'date', 'romantic dinner']
    )
    
    # 2. For each event, check for babysitter
    for event in events:
        babysitter = self._check_babysitter_for_date(event)
        
    # 3. Check for reservations
    has_reservation = self._check_reservation(event)
    
    # 4. Return aggregated data
    return {
        'total_scheduled': len(date_nights),
        'date_nights': date_nights,
        'missing_months': missing_months,
        'coverage_percent': (12 - len(missing_months)) / 12 * 100
    }
```

---

## 5. DOCUMENT PARSING PATTERN

### Structured Data Extraction from Google Docs

The system parses human-readable Google Doc sections:

```
[GIFTS]
□ Date: 2025-11-10 | Diamond earrings
□ Date: 2025-08-15 | Spa weekend
□ Date: YYYY-MM-DD | (placeholder not counted)

[LETTERS]
□ Date: 2025-11-05 | Handwritten letter in book
☑ Date: 2025-10-20 | Letter about dreams

[ACTION PLAN REVIEWS]
□ Date: 2025-11-01 | Quarterly review completed
```

### Parsing Logic
```python
def _parse_section(self, doc_content: str, section_name: str):
    entries = []
    
    # Find section markers
    section_marker = f"[{section_name}]"
    section_start = doc_content.index(section_marker)
    section_end = doc_content.find('[', section_start + 1)
    section_content = doc_content[section_start:section_end]
    
    # Parse lines: □ Date: YYYY-MM-DD | Details
    for line in section_content.split('\n'):
        if 'Date:' in line:
            date_part = line.split('Date:')[1].split('|')[0].strip()
            details = line.split('|', 1)[1].strip() if '|' in line else ''
            
            # Validate date format
            try:
                datetime.strptime(date_part, '%Y-%m-%d')
                entries.append({
                    'date': date_part,
                    'details': details,
                    'completed': '☑' in line
                })
            except ValueError:
                continue  # Skip invalid dates
    
    return entries
```

### Key Insights:
- **Simple Format:** Human-friendly, not machine-only syntax
- **Date Validation:** Filters out placeholders (YYYY-MM-DD)
- **Completed Tracking:** Uses checkbox symbols (☑ vs □)
- **Details Extraction:** Pipe-separated for structured data

---

## 6. REPORT GENERATION PATTERN

### HTML Report Builder

The `relationship_report.py` generates email-ready HTML:

```python
class RelationshipReportGenerator:
    def generate_html_report(self, report_data: Dict) -> str:
        # 1. Calculate health score
        health_score = self._calculate_health_score(report_data)
        
        # 2. Build modular sections
        html_parts = [
            self._get_html_header(),
            self._get_executive_summary(health_score, report_data),
            self._get_critical_alerts(report_data['alerts']),
            self._get_date_nights_section(report_data['date_nights']),
            self._get_gifts_section(report_data['gifts']),
            self._get_toggl_section(report_data['toggl_stats']),
            self._get_html_footer()
        ]
        
        return '\n'.join(html_parts)
```

### Health Score Calculation
```python
def _calculate_health_score(self, report_data: Dict) -> int:
    score = 100
    
    # Deductions
    critical_alerts = [a for a in report_data['alerts'] if a['level'] == 'critical']
    score -= len(critical_alerts) * 10  # -10 per critical
    
    warning_alerts = [a for a in report_data['alerts'] if a['level'] == 'warning']
    score -= len(warning_alerts) * 5   # -5 per warning
    
    # Bonuses
    date_coverage = report_data['date_nights'].get('coverage_percent', 0)
    if date_coverage >= 90:
        score += 5
    
    toggl_hours = report_data['toggl_stats'].get('total_hours', 0)
    if toggl_hours >= 10:
        score += 5
    
    return max(0, min(100, score))  # Clamp 0-100
```

### Alert Generation
```python
def _generate_alerts(self, report: Dict) -> List[Dict]:
    alerts = []
    
    # Check each metric
    if report['gifts']['is_overdue']:
        alerts.append({
            'level': 'critical',
            'category': 'Gifts',
            'message': f"Overdue by {days_overdue} days",
            'action': 'Purchase and give unexpected gift soon'
        })
    
    return alerts
```

---

## 7. SCHEDULING PATTERNS

### Local Scheduling (Python `schedule` library)
```python
def setup_schedule(config: dict):
    schedules = config.get('relationship_tracking', {}).get('schedule', [
        '0 19 * * 6',   # Saturday 7pm EST
        '30 18 * * 3'   # Wednesday 6:30pm EST
    ])
    
    for schedule_cron in schedules:
        # Parse cron and schedule job
        schedule.every().at(time_str).do(scheduled_report_job)
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)
```

### AWS Lambda Scheduling (EventBridge)
```
EventBridge Rule:
├── Schedule: cron(0 9 ? * SUN *)  # Sunday 9 AM UTC = 4 AM EST
├── Target: Lambda Function
└── IAM Permission: events.amazonaws.com can invoke function
```

### Key Differences:
| Method | Pros | Cons |
|--------|------|------|
| Local Schedule | Simple, no infrastructure | Requires always-on server |
| EventBridge | Serverless, reliable, cheap | Need AWS account |
| Cron (system) | Standard Unix approach | Less flexible |

---

## 8. AWS DEPLOYMENT ARCHITECTURE

### Serverless Stack
```
┌─────────────────────────────────────────┐
│         EventBridge Rule                │
│     (Sunday 4 AM EST = 9 AM UTC)        │
└────────────────┬────────────────────────┘
                 │ Trigger
                 ▼
┌─────────────────────────────────────────┐
│      AWS Lambda Function                │
│    - Runtime: Python 3.9                │
│    - Memory: 512 MB                     │
│    - Timeout: 900 seconds               │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌────────┐ ┌──────────────┐ ┌─────────┐
│ SSM    │ │ CloudWatch   │ │ /tmp    │
│Param   │ │ Logs         │ │Storage  │
│Store   │ │              │ │(Creds)  │
└────────┘ └──────────────┘ └─────────┘
```

### Credential Management in Lambda
```python
def load_credentials_from_parameters():
    """Load from AWS Systems Manager Parameter Store"""
    cred_mapping = {
        '/love-brittany/credentials': '/tmp/credentials/credentials.json',
        '/love-brittany/token': '/tmp/credentials/token.pickle'
    }
    
    for param_name, file_path in cred_mapping.items():
        param_value = get_parameter(param_name)
        
        # Decode base64 for binary files
        if file_path.endswith('.pickle'):
            decoded_value = base64.b64decode(param_value)
            with open(file_path, 'wb') as f:
                f.write(decoded_value)
```

### Lambda Handler Pattern
```python
def weekly_report_handler(event: Dict, context: Any) -> Dict:
    """Lambda entry point"""
    try:
        # 1. Load secrets from Parameter Store
        load_credentials_from_parameters()
        load_api_keys_from_parameters()
        
        # 2. Set environment for execution
        os.environ['GOOGLE_CREDENTIALS_FILE'] = '/tmp/credentials/credentials.json'
        os.environ['GOOGLE_TOKEN_FILE'] = '/tmp/credentials/token.pickle'
        
        # 3. Load and validate config
        config = load_config()
        if not validate_configuration(config):
            raise ValueError("Configuration validation failed")
        
        # 4. Generate report
        generate_report(config, send_email=True)
        
        return {'statusCode': 200, 'body': 'Success'}
    except Exception as e:
        logger.error(f"Failed: {str(e)}", exc_info=True)
        return {'statusCode': 500, 'body': f'Error: {str(e)}'}
```

### Deployment Scripts
- `deploy-lambda-zip.sh` - Package Python dependencies + code into ZIP
- `setup-parameters.sh` - Upload credentials to Parameter Store
- `setup-eventbridge.sh` - Create EventBridge rule
- `test-lambda.sh` - Manual invocation for testing

---

## 9. ERROR HANDLING & VALIDATION

### Configuration Validation
```python
def validate_configuration(config: dict) -> bool:
    required_env_vars = [
        'RELATIONSHIP_TRACKING_DOC_ID',
        'RELATIONSHIP_REPORT_EMAIL',
        'GOOGLE_CREDENTIALS_FILE',
        'TOGGL_API_TOKEN'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing: {', '.join(missing_vars)}")
        return False
    
    if not config.get('relationship_tracking', {}).get('enabled'):
        logger.warning("Tracking disabled in config")
        return False
    
    return True
```

### Service Validation
```python
def validate_setup():
    """Pre-flight check before running"""
    checks = [
        ("Calendar", lambda: CalendarService().validate_credentials()),
        ("Docs", lambda: docs_service.get_document_metadata(doc_id)),
        ("Toggl", lambda: TogglService().validate_credentials()),
        ("Gmail", lambda: EmailSender().validate_credentials()),
    ]
    
    for service_name, check_func in checks:
        if not check_func():
            print(f"❌ {service_name} validation failed")
            return False
    
    print("✅ All validations passed!")
    return True
```

### Logging Strategy
```python
def setup_logging(config: dict):
    log_config = config.get('logging', {})
    
    logging.basicConfig(
        level=getattr(logging, log_config.get('level', 'INFO')),
        format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        handlers=[
            logging.FileHandler(log_config.get('file', 'logs/relationship.log')),
            logging.StreamHandler(sys.stdout)
        ]
    )
```

---

## 10. KEY PATTERNS FOR TOGGL DAILY REPORT SYSTEM

### Recommended Architecture

```python
# 1. SERVICE LAYER
class TogglDailyService:
    """Fetch Toggl data for specific date"""
    def get_daily_entries(self, date: datetime) -> List[Dict]
    def get_project_summary(self, date: datetime) -> Dict
    def get_billable_hours(self, date: datetime) -> float

class CalendarDailyService:
    """Get calendar context for the day"""
    def get_daily_events(self, date: datetime) -> List[Dict]
    def get_focus_blocks(self, date: datetime) -> List[Dict]

# 2. BUSINESS LOGIC LAYER
class DailyReportGenerator:
    """Aggregate and analyze daily data"""
    def generate_daily_report(self, date: datetime) -> Dict:
        return {
            'date': date.isoformat(),
            'entries': self.toggl.get_daily_entries(date),
            'summary': self._calculate_summary(),
            'insights': self._generate_insights(),
            'alerts': self._check_thresholds()
        }

# 3. REPORT LAYER
class DailyReportFormatter:
    """Create HTML email"""
    def generate_html(self, report_data: Dict) -> str:
        # Sections:
        # - Daily Summary (total hours, projects)
        # - Time Breakdown (pie chart data)
        # - Detailed Entries (table)
        # - Insights (patterns, suggestions)
        # - Tomorrow Preview

# 4. DELIVERY LAYER
class DailyReportEmailer:
    """Send email at specified time"""
    def send_daily_report(self, email: str, report_html: str) -> bool
```

### Configuration Pattern
```yaml
toggl_daily_report:
  enabled: true
  schedule: "0 18 * * 1-5"  # 6 PM weekdays
  timezone: "America/New_York"
  
  # Report settings
  email:
    recipient: "user@example.com"
    subject_template: "Daily Report - {date}"
    include_insights: true
  
  # Data collection
  lookback_hours: 24
  include_running_entries: false
  
  # Display options
  min_duration_minutes: 1
  group_by_project: true
  
  # Thresholds
  alert_threshold_hours: 8  # Alert if > 8 hours
  goal_hours: 8
```

### Entry Points
```python
# Local execution
python src/toggl_daily.py --generate --date 2025-11-17

# Scheduled daemon
python src/toggl_scheduler.py

# AWS Lambda
aws lambda invoke --function-name toggl-daily-report response.json

# Docker
docker run toggl-daily-reporter
```

---

## 11. DEPENDENCIES & TECH STACK

### Key Libraries Used
```
# Google APIs
google-api-python-client==2.108.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.0

# HTTP
requests==2.31.0

# Configuration
PyYAML==6.0.1
python-dotenv==1.0.0

# Scheduling
schedule==1.2.0
APScheduler (alternative)

# Date/Time
python-dateutil==2.8.2
pytz==2023.3

# Logging
colorlog==6.8.0

# Web (if using webhook)
Flask==3.0.0

# AWS (optional)
boto3 (for Parameter Store)
```

### For Toggl Daily Report
```
# Add to requirements:
requests==2.31.0  (for Toggl API)
pydantic==2.0.0  (for data validation)
jinja2==3.1.0  (for HTML templating - better than string concatenation)
```

---

## 12. TESTING & VALIDATION APPROACH

### Test Pyramid
```
                    E2E Tests (full reports)
                   /                    \
                 Integration Tests (API + report)
               /                            \
            Unit Tests (each service/method)
```

### Key Test Areas
1. **Configuration Loading** - YAML parsing, env var override
2. **API Integration** - Mock API responses, test error cases
3. **Data Parsing** - Document section extraction
4. **Report Generation** - HTML generation, formatting
5. **Email Sending** - MIME formatting, attachment handling
6. **Scheduling** - Cron parsing, timezone handling

### Validation Script Pattern
```python
# setup_wizard.sh / validate.py
echo "Testing Google Calendar..."
CalendarService().validate_credentials()

echo "Testing Toggl API..."
TogglService().validate_credentials()

echo "Testing Gmail..."
EmailSender().validate_credentials()

echo "Testing configuration..."
validate_configuration(load_config())

echo "All systems ready!"
```

---

## 13. MONITORING & LOGGING

### Log Levels Used
- **ERROR:** Failed API calls, validation failures, exceptions
- **WARNING:** Missing optional data, deprecated configurations
- **INFO:** Normal operation, report generated, email sent
- **DEBUG:** API request details, data parsing steps

### CloudWatch Integration (Lambda)
- Automatically captured: stdout, stderr
- Manual logging: `logger.info()` statements
- View: `aws logs tail /aws/lambda/function-name --follow`

### Local Logging
```python
# Creates logs/relationship.log
logging.basicConfig(
    handlers=[
        logging.FileHandler('logs/relationship.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
```

---

## 14. QUICK REFERENCE: APPLYING TO TOGGL DAILY REPORTS

### 1. Start with Structure
```
toggl-daily-report/
├── src/
│   ├── toggl_daily.py           (entry point + orchestrator)
│   ├── toggl_data_service.py    (API integration)
│   ├── daily_report_generator.py (aggregation)
│   └── report_formatter.py       (HTML generation)
├── config.yaml
├── .env.example
├── requirements.txt
└── README.md
```

### 2. Key Implementation Priorities
1. **Toggl API Integration** - Get time entries for a date
2. **Data Aggregation** - Summarize by project, tags, duration
3. **HTML Report** - Clean, readable format
4. **Email Delivery** - Gmail API
5. **Scheduling** - Daily at 6 PM (or after-hours)
6. **AWS Deployment** - Lambda + EventBridge

### 3. Reusable Code from Love Brittany
- `email_sender.py` - Can use as-is (Gmail API)
- `calendar_service.py` - Can adapt for context/meetings
- Logging setup pattern
- Configuration loading pattern
- Lambda handler pattern
- AWS Parameter Store credential loading

### 4. New Code Needed
- Toggl API client (simpler than Google APIs)
- Daily aggregation logic
- HTML report formatter (similar but simpler)
- Insights/suggestions engine

---

## SUMMARY

The Love Brittany Tracker exemplifies a **well-architected data aggregation and reporting system** with these strengths:

✅ **Clear Separation of Concerns** - Services, business logic, orchestration, delivery
✅ **Flexible Configuration** - YAML + environment variables, easy to customize
✅ **Robust Error Handling** - Validation, logging, graceful degradation
✅ **Multiple Deployment Options** - Local scheduler, AWS Lambda, Docker
✅ **Credential Security** - Parameter Store for sensitive data, pickle for OAuth tokens
✅ **Maintainable Code** - Well-documented, modular, easy to extend
✅ **User-Friendly Output** - Beautiful HTML emails with health scores and alerts

These patterns are **directly applicable** to building a Toggl Daily Report system with minimal adaptation.
