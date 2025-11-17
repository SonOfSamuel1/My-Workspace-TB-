# Code Pattern Reference - Love Brittany to Toggl Daily Report

Quick lookup for copying and adapting key patterns.

---

## 1. SERVICE LAYER - Authentication Pattern

### Google APIs (OAuth2)
```python
# Source: calendar_service.py, docs_service.py, email_sender.py
# Pattern: Load token, refresh if needed, create service

import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

class GoogleService:
    def authenticate(self):
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # Refresh or create new
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
        
        # Save for next run
        with open(self.token_file, 'wb') as token:
            pickle.dump(creds, token)
        
        self.service = build('service_name', 'v1', credentials=creds)
```

### Toggl API (Basic Auth)
```python
# Source: toggl_service.py
# Pattern: Simple HTTP with Base64 auth

from base64 import b64encode
import requests

class TogglService:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.track.toggl.com/api/v9"
        
        # Setup auth header
        auth_string = f"{api_token}:api_token"
        auth_b64 = b64encode(auth_string.encode()).decode()
        self.headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json'
        }
    
    def get_time_entries(self, start_date, end_date):
        params = {
            'start_date': start_date.isoformat() + 'Z',
            'end_date': end_date.isoformat() + 'Z'
        }
        response = requests.get(
            f"{self.base_url}/me/time_entries",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def validate_credentials(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/me",
                headers=self.headers
            )
            return response.status_code == 200
        except:
            return False
```

---

## 2. DATA AGGREGATION PATTERN

### Multi-Source Aggregation Template
```python
# Source: relationship_tracker.py
# Pattern: Collect from multiple sources, return consistent format

class DataAggregator:
    def generate_report(self) -> Dict:
        report = {
            'timestamp': datetime.now(self.timezone).isoformat(),
            'source1_data': self._get_data_from_source1(),  # Service A
            'source2_data': self._get_data_from_source2(),  # Service B
            'source3_data': self._get_data_from_source3(),  # Service C
            'computed_alerts': self._generate_alerts(...)   # Analysis
        }
        return report
    
    def _get_data_from_source1(self) -> Dict:
        """Aggregate data from Service A"""
        logger.info("Fetching data from Service A...")
        try:
            raw_data = self.service_a.fetch()
            processed = self._process_source1(raw_data)
            return {
                'status': 'success',
                'data': processed,
                'last_update': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Service A failed: {e}")
            return {
                'status': 'error',
                'data': [],
                'error': str(e)
            }
    
    def _generate_alerts(self, report: Dict) -> List[Dict]:
        """Generate alerts based on report data"""
        alerts = []
        
        # Check each metric
        if some_condition(report):
            alerts.append({
                'level': 'critical',
                'category': 'Category Name',
                'message': 'Human-readable message',
                'action': 'What to do about it'
            })
        
        return alerts
```

### Toggl Daily Report Adaptation
```python
# Simplified for single-source data

class DailyReportGenerator:
    def generate_report(self, date: datetime) -> Dict:
        """Generate daily report for specific date"""
        start = date.replace(hour=0, minute=0, second=0)
        end = date.replace(hour=23, minute=59, second=59)
        
        logger.info(f"Generating report for {date.date()}...")
        
        # Fetch data
        entries = self.toggl.get_time_entries(start, end)
        
        # Process
        summary = self._calculate_summary(entries)
        insights = self._generate_insights(entries)
        alerts = self._check_thresholds(summary)
        
        return {
            'date': date.isoformat(),
            'entries': entries,
            'summary': summary,
            'insights': insights,
            'alerts': alerts
        }
    
    def _calculate_summary(self, entries: List[Dict]) -> Dict:
        """Summarize time entries"""
        total_seconds = sum(e['duration'] for e in entries if e['duration'] > 0)
        
        by_project = {}
        for entry in entries:
            proj = entry.get('project_name', 'Unassigned')
            by_project[proj] = by_project.get(proj, 0) + entry['duration']
        
        return {
            'total_hours': round(total_seconds / 3600, 2),
            'by_project': {p: round(s/3600, 2) for p, s in by_project.items()},
            'entries_count': len(entries)
        }
```

---

## 3. CONFIGURATION PATTERN

### Config Layering
```python
# Source: relationship_main.py
# Pattern: YAML config + environment variable override

import os
import yaml
from pathlib import Path

def load_config() -> dict:
    """Load config.yaml"""
    config_path = Path('config.yaml')
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config

def load_environment():
    """Load .env file into os.environ"""
    env_path = Path('.env')
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

def generate_report(config: dict):
    """Use config with env override"""
    # From config
    recipient = config['relationship_tracking']['email']['recipient']
    
    # Override with env var if present
    recipient = os.getenv('RELATIONSHIP_REPORT_EMAIL', recipient)
```

### For Toggl Daily Report
```python
# config.yaml structure
toggl_daily_report:
  enabled: true
  schedule: "0 18 * * 1-5"  # 6 PM weekdays
  timezone: "America/New_York"
  
  email:
    recipient: "${TOGGL_REPORT_EMAIL}"  # Or use env override
    subject_template: "Daily Report - {date}"
  
  toggl:
    api_token: "${TOGGL_API_TOKEN}"
    workspace_id: "${TOGGL_WORKSPACE_ID}"
  
  thresholds:
    alert_over_hours: 10
    goal_hours: 8

# Loading pattern
config = load_config()
report_config = config['toggl_daily_report']

# Environment override
report_config['email']['recipient'] = os.getenv(
    'TOGGL_REPORT_EMAIL',
    report_config['email']['recipient']
)
```

---

## 4. HTML REPORT GENERATION PATTERN

### Email-Safe HTML Template
```python
# Source: relationship_report.py
# Pattern: String concatenation with inline CSS and tables

def generate_html_report(self, data: Dict) -> str:
    """Generate email-safe HTML"""
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; }}
            .header {{ background: #f0f0f0; padding: 20px; text-align: center; }}
            .summary {{ background: #e8f5e9; padding: 20px; margin: 20px 0; }}
            .alert {{ background: #ffebee; border-left: 4px solid #c62828; padding: 10px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background: #f5f5f5; padding: 10px; text-align: left; }}
            td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Daily Time Report</h1>
                <p>{data['date']}</p>
            </div>
            
            <div class="summary">
                <h2>Summary</h2>
                <p><strong>Total Hours:</strong> {data['summary']['total_hours']}h</p>
                <p><strong>Entries:</strong> {data['summary']['entries_count']}</p>
            </div>
            
            {self._render_alerts(data['alerts'])}
            {self._render_projects_table(data['summary']['by_project'])}
            
        </div>
    </body>
    </html>
    """
    
    return html

def _render_alerts(self, alerts: List[Dict]) -> str:
    """Render alert section"""
    if not alerts:
        return ""
    
    html = '<div class="alerts">'
    for alert in alerts:
        html += f'<div class="alert"><strong>{alert["level"].upper()}</strong>: {alert["message"]}</div>'
    html += '</div>'
    return html

def _render_projects_table(self, by_project: Dict) -> str:
    """Render project breakdown table"""
    html = '<h2>Projects</h2><table><tr><th>Project</th><th>Hours</th></tr>'
    for project, hours in by_project.items():
        html += f'<tr><td>{project}</td><td>{hours}h</td></tr>'
    html += '</table>'
    return html
```

---

## 5. ENTRY POINT WITH ARGUMENT PARSING

### CLI Pattern
```python
# Source: relationship_main.py
# Pattern: argparse for multiple commands

import argparse

def main():
    parser = argparse.ArgumentParser(
        description='Love Brittany Action Plan Tracker'
    )
    
    parser.add_argument(
        '--generate',
        action='store_true',
        help='Generate and send relationship tracking report'
    )
    
    parser.add_argument(
        '--no-email',
        action='store_true',
        help='Generate report but do not send email'
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate setup and configuration'
    )
    
    args = parser.parse_args()
    
    # Load config first
    config = load_config()
    setup_logging(config)
    load_environment()
    
    if args.validate:
        sys.exit(0 if validate_setup() else 1)
    
    elif args.generate:
        if not validate_configuration(config):
            sys.exit(1)
        send_email = not args.no_email
        generate_report(config, send_email=send_email)
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
```

### For Toggl Daily Report
```python
# src/toggl_daily.py

def main():
    parser = argparse.ArgumentParser(description='Toggl Daily Report')
    
    parser.add_argument(
        '--generate',
        action='store_true',
        help='Generate daily report'
    )
    
    parser.add_argument(
        '--date',
        help='Report date (YYYY-MM-DD), defaults to today'
    )
    
    parser.add_argument(
        '--send-email',
        action='store_true',
        help='Send email (default: no-email)'
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate configuration'
    )
    
    parser.add_argument(
        '--schedule',
        action='store_true',
        help='Start scheduler daemon'
    )
    
    args = parser.parse_args()
    
    config = load_config()
    setup_logging(config)
    load_environment()
    
    if args.generate:
        date = datetime.fromisoformat(args.date) if args.date else datetime.now()
        generate_and_send(date, send_email=args.send_email)
    
    elif args.validate:
        validate_setup()
    
    elif args.schedule:
        start_scheduler()
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
```

---

## 6. VALIDATION PATTERN

### Pre-flight Checks
```python
# Source: relationship_main.py
# Pattern: Check all dependencies before execution

def validate_configuration(config: dict) -> bool:
    """Validate required config present"""
    logger = logging.getLogger(__name__)
    
    required_env_vars = [
        'TOGGL_API_TOKEN',
        'TOGGL_WORKSPACE_ID',
        'TOGGL_REPORT_EMAIL'
    ]
    
    missing = [v for v in required_env_vars if not os.getenv(v)]
    
    if missing:
        logger.error(f"Missing env vars: {', '.join(missing)}")
        return False
    
    if not config.get('toggl_daily_report', {}).get('enabled'):
        logger.warning("Toggl daily report disabled")
        return False
    
    logger.info("Configuration validation passed")
    return True

def validate_setup():
    """Interactive validation of all services"""
    print("\n" + "="*60)
    print("TOGGL DAILY REPORT - SETUP VALIDATION")
    print("="*60 + "\n")
    
    try:
        # Load config
        print("📋 Loading configuration...")
        config = load_config()
        print("✅ Config loaded")
        
        # Load environment
        print("🔐 Loading environment variables...")
        load_environment()
        print("✅ Environment loaded")
        
        # Validate config
        print("✔️  Validating configuration...")
        if not validate_configuration(config):
            print("❌ Configuration validation failed")
            return False
        print("✅ Configuration valid")
        
        # Test Toggl
        print("⏱️  Testing Toggl connection...")
        toggl = TogglService()
        if toggl.validate_credentials():
            print("✅ Toggl connection successful")
        else:
            print("❌ Toggl connection failed")
            return False
        
        # Test Gmail
        print("📧 Testing Gmail connection...")
        email = EmailSender()
        if email.validate_credentials():
            print("✅ Gmail connection successful")
        else:
            print("❌ Gmail connection failed")
            return False
        
        print("\n" + "="*60)
        print("✅ ALL VALIDATIONS PASSED!")
        print("="*60 + "\n")
        
        return True
    
    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        print(f"\n❌ Validation failed: {str(e)}\n")
        return False
```

---

## 7. LOGGING SETUP

### Logger Configuration
```python
# Source: relationship_main.py
# Pattern: Centralized logging to file + stdout

import logging
import sys
from pathlib import Path

def setup_logging(config: dict):
    """Configure logging based on config"""
    log_config = config.get('logging', {})
    
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_format = log_config.get(
        'format',
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    log_file = log_config.get('file', 'logs/toggl_daily.log')
    
    # Create logs directory
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Suppress verbose third-party loggers
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

# Usage in modules
logger = logging.getLogger(__name__)

logger.info("Processing started")
logger.warning("Low on data")
logger.error("API failed", exc_info=True)
logger.debug("Detailed processing info")
```

---

## 8. AWS LAMBDA PATTERN

### Lambda Handler
```python
# Source: lambda_handler.py
# Pattern: Load secrets from Parameter Store, run function, return status

import json
import logging
import os
import sys
from typing import Dict, Any, Optional

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_parameter(parameter_name: str) -> Optional[str]:
    """Retrieve from AWS Systems Manager Parameter Store"""
    try:
        import boto3
        ssm = boto3.client('ssm')
        response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        logger.error(f"Failed to get {parameter_name}: {e}")
        return None

def load_parameters():
    """Load API keys from Parameter Store"""
    toggl_token = get_parameter('/toggl-daily/api-token')
    if toggl_token:
        os.environ['TOGGL_API_TOKEN'] = toggl_token
        logger.info("Loaded TOGGL_API_TOKEN")

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point"""
    logger.info("="*60)
    logger.info("TOGGL DAILY REPORT LAMBDA - Starting")
    logger.info("="*60)
    
    try:
        # Load secrets
        logger.info("Loading secrets from Parameter Store...")
        load_parameters()
        
        # Load config
        logger.info("Loading configuration...")
        config = load_config()
        
        # Override log path for Lambda
        if 'logging' not in config:
            config['logging'] = {}
        config['logging']['file'] = '/tmp/toggl_daily.log'
        
        setup_logging(config)
        
        # Validate
        logger.info("Validating configuration...")
        if not validate_configuration(config):
            raise ValueError("Configuration validation failed")
        
        # Generate report
        logger.info("Generating report...")
        from datetime import datetime
        date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        generate_and_send(date, send_email=True)
        
        logger.info("="*60)
        logger.info("✓ Report sent successfully")
        logger.info("="*60)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Success'})
        }
    
    except Exception as e:
        logger.error(f"Failed: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

---

## 9. SENDING EMAILS

### Email Sender
```python
# Source: email_sender.py
# Pattern: OAuth2 auth to Gmail, MIME formatting

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
from googleapiclient.discovery import build

class EmailSender:
    def __init__(self, credentials_path: str, token_path: str):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
    
    def authenticate(self) -> None:
        """OAuth2 authentication (see Google OAuth pattern above)"""
        # Load or refresh credentials, then:
        self.service = build('gmail', 'v1', credentials=creds)
    
    def send_html_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        from_email: Optional[str] = None
    ) -> bool:
        """Send HTML email"""
        if not self.service:
            self.authenticate()
        
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['To'] = to
            message['Subject'] = subject
            
            # Add HTML part
            message.attach(MIMEText(html_content, 'html'))
            
            # Send via Gmail API
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode()
            
            self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"Email sent to {to}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
```

---

## 10. KEY DIFFERENCES FOR TOGGL REPORT

| Feature | Love Brittany | Toggl Daily |
|---------|---------------|-------------|
| Complexity | High (9 data sources) | Low (1 data source) |
| Time complexity | Parse docs, search calendar | Simple API call |
| Report sections | 10+ | 4-5 |
| Frequency | 2x/week | Daily |
| Config options | 50+ | 15+ |
| Code reuse | Email, Calendar services | Email, logging |

**Simplification opportunity:** You don't need Google Calendar integration for Toggl Daily Report unless you want to add context about meetings/focus time. Just Toggl API + Email.

---

## Quick Copy-Paste Checklist

### From Love Brittany, Copy As-Is:
- [ ] `src/email_sender.py` - No changes needed
- [ ] Logging setup pattern - Just rename functions
- [ ] Configuration validation pattern - Adapt for your config keys
- [ ] Entry point structure - Keep argparse approach
- [ ] Lambda handler structure - Adapt parameter names

### From Love Brittany, Adapt:
- [ ] Service layer - Toggl is simpler (no OAuth)
- [ ] Data aggregation - Simpler (one source)
- [ ] HTML report generation - Adapt sections/styling
- [ ] Scheduler - Same pattern, different cron time

### New Code:
- [ ] TogglService.get_time_entries() - Read Toggl API docs
- [ ] DailyReportGenerator._calculate_summary() - Aggregation logic
- [ ] Report formatting - Custom HTML for your needs

