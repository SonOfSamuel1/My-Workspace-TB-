#!/usr/bin/env python3
"""
Security Alert Notification System for My Workspace
Sends email and SMS alerts for critical security events
"""

import os
import json
import smtplib
import logging
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio not installed. SMS notifications disabled.")

try:
    import boto3
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    logger.warning("boto3 not installed. AWS CloudWatch integration disabled.")


class SecurityAlertNotifier:
    """
    Handles sending security alerts via multiple channels
    """

    def __init__(self, config_path: str = None):
        """Initialize the notifier with configuration"""
        self.config = self.load_config(config_path)
        self.alert_history = []
        self.rate_limits = {
            'email': {'count': 0, 'reset_time': time.time() + 3600},  # 10 per hour
            'sms': {'count': 0, 'reset_time': time.time() + 300}      # 1 per 5 minutes
        }

        # Initialize notification channels
        self._init_email()
        self._init_sms()
        self._init_cloudwatch()

    def load_config(self, config_path: str = None) -> Dict:
        """Load notification configuration"""
        default_config = {
            "email": {
                "enabled": True,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "from_email": os.getenv("ALERT_EMAIL_FROM", ""),
                "to_emails": [os.getenv("ALERT_EMAIL_TO", "terrance@goodportion.org")],
                "username": os.getenv("SMTP_USERNAME", ""),
                "password": os.getenv("SMTP_PASSWORD", "")
            },
            "sms": {
                "enabled": TWILIO_AVAILABLE,
                "account_sid": os.getenv("TWILIO_ACCOUNT_SID", ""),
                "auth_token": os.getenv("TWILIO_AUTH_TOKEN", ""),
                "from_number": os.getenv("TWILIO_FROM_NUMBER", ""),
                "to_numbers": [os.getenv("ESCALATION_PHONE", "+14077448449")]
            },
            "cloudwatch": {
                "enabled": AWS_AVAILABLE,
                "region": os.getenv("AWS_REGION", "us-east-1"),
                "log_group": "/aws/lambda/my-workspace-security",
                "metric_namespace": "MyWorkspace/Security"
            },
            "severity_levels": {
                "CRITICAL": ["email", "sms", "cloudwatch"],
                "HIGH": ["email", "cloudwatch"],
                "MEDIUM": ["cloudwatch"],
                "LOW": []
            },
            "rate_limits": {
                "email_per_hour": 10,
                "sms_per_5min": 1
            }
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    custom_config = json.load(f)
                    # Merge custom config with defaults
                    for key in custom_config:
                        if key in default_config:
                            if isinstance(default_config[key], dict):
                                default_config[key].update(custom_config[key])
                            else:
                                default_config[key] = custom_config[key]
            except Exception as e:
                logger.error(f"Failed to load custom config: {e}")

        return default_config

    def _init_email(self):
        """Initialize email client"""
        self.email_enabled = (
            self.config['email']['enabled'] and
            self.config['email']['from_email'] and
            self.config['email']['username'] and
            self.config['email']['password']
        )

        if not self.email_enabled:
            logger.warning("Email notifications disabled (missing credentials)")

    def _init_sms(self):
        """Initialize SMS client"""
        self.sms_enabled = (
            TWILIO_AVAILABLE and
            self.config['sms']['enabled'] and
            self.config['sms']['account_sid'] and
            self.config['sms']['auth_token']
        )

        if self.sms_enabled:
            try:
                self.twilio_client = TwilioClient(
                    self.config['sms']['account_sid'],
                    self.config['sms']['auth_token']
                )
                logger.info("SMS notifications enabled via Twilio")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio: {e}")
                self.sms_enabled = False
        else:
            logger.warning("SMS notifications disabled")

    def _init_cloudwatch(self):
        """Initialize CloudWatch client"""
        self.cloudwatch_enabled = AWS_AVAILABLE and self.config['cloudwatch']['enabled']

        if self.cloudwatch_enabled:
            try:
                self.cloudwatch_logs = boto3.client(
                    'logs',
                    region_name=self.config['cloudwatch']['region']
                )
                self.cloudwatch_metrics = boto3.client(
                    'cloudwatch',
                    region_name=self.config['cloudwatch']['region']
                )
                logger.info("CloudWatch integration enabled")
            except Exception as e:
                logger.error(f"Failed to initialize CloudWatch: {e}")
                self.cloudwatch_enabled = False
        else:
            logger.warning("CloudWatch integration disabled")

    def check_rate_limit(self, channel: str) -> bool:
        """Check if we're within rate limits"""
        current_time = time.time()

        if channel not in self.rate_limits:
            return True

        # Reset counter if time window expired
        if current_time > self.rate_limits[channel]['reset_time']:
            if channel == 'email':
                self.rate_limits[channel] = {
                    'count': 0,
                    'reset_time': current_time + 3600
                }
            elif channel == 'sms':
                self.rate_limits[channel] = {
                    'count': 0,
                    'reset_time': current_time + 300
                }

        # Check limit
        if channel == 'email' and self.rate_limits[channel]['count'] >= 10:
            logger.warning("Email rate limit exceeded")
            return False
        elif channel == 'sms' and self.rate_limits[channel]['count'] >= 1:
            logger.warning("SMS rate limit exceeded")
            return False

        return True

    def send_alert(self, severity: str, event_type: str, message: str,
                  details: Dict = None, app: str = None) -> bool:
        """
        Send security alert through configured channels

        Args:
            severity: CRITICAL, HIGH, MEDIUM, LOW
            event_type: Type of security event
            message: Alert message
            details: Additional event details
            app: Application name

        Returns:
            True if at least one notification was sent
        """
        # Prepare alert data
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "severity": severity,
            "event_type": event_type,
            "message": message,
            "app": app or "unknown",
            "details": details or {}
        }

        # Record in history
        self.alert_history.append(alert)

        # Determine channels based on severity
        channels = self.config['severity_levels'].get(severity, [])

        success = False

        # Send through each channel
        if 'email' in channels and self.email_enabled:
            if self.check_rate_limit('email'):
                success = self._send_email_alert(alert) or success
                self.rate_limits['email']['count'] += 1

        if 'sms' in channels and self.sms_enabled:
            if self.check_rate_limit('sms'):
                success = self._send_sms_alert(alert) or success
                self.rate_limits['sms']['count'] += 1

        if 'cloudwatch' in channels and self.cloudwatch_enabled:
            success = self._send_cloudwatch_alert(alert) or success

        # Log the alert
        self._log_alert(alert)

        return success

    def _send_email_alert(self, alert: Dict) -> bool:
        """Send email alert"""
        try:
            # Prepare email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert['severity']}] Security Alert: {alert['event_type']}"
            msg['From'] = self.config['email']['from_email']
            msg['To'] = ', '.join(self.config['email']['to_emails'])

            # Create HTML body
            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif;">
                <div style="background-color: {'#ff0000' if alert['severity'] == 'CRITICAL' else '#ff9900'};
                            color: white; padding: 10px; border-radius: 5px;">
                  <h2>Security Alert: {alert['severity']}</h2>
                </div>
                <div style="padding: 20px;">
                  <p><strong>Event Type:</strong> {alert['event_type']}</p>
                  <p><strong>Application:</strong> {alert['app']}</p>
                  <p><strong>Time:</strong> {alert['timestamp']}</p>
                  <p><strong>Message:</strong> {alert['message']}</p>

                  <h3>Details:</h3>
                  <pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px;">
{json.dumps(alert['details'], indent=2)}
                  </pre>

                  <hr>
                  <p style="color: #666; font-size: 12px;">
                    This is an automated security alert from My Workspace Security Framework.
                    <br>To adjust alert settings, modify security/alert-config.json
                  </p>
                </div>
              </body>
            </html>
            """

            # Attach HTML
            msg.attach(MIMEText(html_body, 'html'))

            # Send email
            with smtplib.SMTP(self.config['email']['smtp_server'],
                             self.config['email']['smtp_port']) as server:
                server.starttls()
                server.login(
                    self.config['email']['username'],
                    self.config['email']['password']
                )
                server.send_message(msg)

            logger.info(f"Email alert sent for {alert['event_type']}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

    def _send_sms_alert(self, alert: Dict) -> bool:
        """Send SMS alert"""
        try:
            # Prepare short message
            sms_text = (
                f"SECURITY ALERT [{alert['severity']}]\n"
                f"{alert['event_type']}\n"
                f"App: {alert['app']}\n"
                f"{alert['message'][:100]}"  # Limit message length
            )

            # Send to all configured numbers
            for to_number in self.config['sms']['to_numbers']:
                if to_number:
                    self.twilio_client.messages.create(
                        body=sms_text,
                        from_=self.config['sms']['from_number'],
                        to=to_number
                    )

            logger.info(f"SMS alert sent for {alert['event_type']}")
            return True

        except Exception as e:
            logger.error(f"Failed to send SMS alert: {e}")
            return False

    def _send_cloudwatch_alert(self, alert: Dict) -> bool:
        """Send alert to CloudWatch"""
        try:
            # Log to CloudWatch Logs
            log_event = {
                'timestamp': int(datetime.utcnow().timestamp() * 1000),
                'message': json.dumps(alert)
            }

            # Create log stream if needed
            log_stream = f"security-alerts-{datetime.utcnow().strftime('%Y%m%d')}"

            try:
                self.cloudwatch_logs.create_log_stream(
                    logGroupName=self.config['cloudwatch']['log_group'],
                    logStreamName=log_stream
                )
            except self.cloudwatch_logs.exceptions.ResourceAlreadyExistsException:
                pass  # Stream already exists

            # Put log event
            self.cloudwatch_logs.put_log_events(
                logGroupName=self.config['cloudwatch']['log_group'],
                logStreamName=log_stream,
                logEvents=[log_event]
            )

            # Put custom metric
            self.cloudwatch_metrics.put_metric_data(
                Namespace=self.config['cloudwatch']['metric_namespace'],
                MetricData=[
                    {
                        'MetricName': f"SecurityAlert_{alert['severity']}",
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow(),
                        'Dimensions': [
                            {'Name': 'Application', 'Value': alert['app']},
                            {'Name': 'EventType', 'Value': alert['event_type']}
                        ]
                    }
                ]
            )

            logger.info(f"CloudWatch alert sent for {alert['event_type']}")
            return True

        except Exception as e:
            logger.error(f"Failed to send CloudWatch alert: {e}")
            return False

    def _log_alert(self, alert: Dict):
        """Log alert to local file"""
        alert_log_dir = Path.home() / '.my-workspace-vault' / 'alerts'
        alert_log_dir.mkdir(parents=True, exist_ok=True)

        alert_file = alert_log_dir / f"alerts_{datetime.now().strftime('%Y%m%d')}.jsonl"

        with open(alert_file, 'a') as f:
            f.write(json.dumps(alert) + '\n')

        # Set secure permissions
        os.chmod(alert_file, 0o600)

    def get_alert_summary(self, hours: int = 24) -> Dict:
        """Get summary of recent alerts"""
        cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
        recent_alerts = [
            a for a in self.alert_history
            if datetime.fromisoformat(a['timestamp']).timestamp() > cutoff_time
        ]

        summary = {
            'total': len(recent_alerts),
            'by_severity': {},
            'by_type': {},
            'by_app': {}
        }

        for alert in recent_alerts:
            # Count by severity
            severity = alert['severity']
            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1

            # Count by type
            event_type = alert['event_type']
            summary['by_type'][event_type] = summary['by_type'].get(event_type, 0) + 1

            # Count by app
            app = alert['app']
            summary['by_app'][app] = summary['by_app'].get(app, 0) + 1

        return summary

    def test_notifications(self) -> Dict[str, bool]:
        """Test all notification channels"""
        results = {}

        # Test email
        if self.email_enabled:
            results['email'] = self._send_email_alert({
                'severity': 'TEST',
                'event_type': 'NOTIFICATION_TEST',
                'message': 'Testing email notifications',
                'app': 'test',
                'timestamp': datetime.utcnow().isoformat(),
                'details': {'test': True}
            })

        # Test SMS
        if self.sms_enabled:
            results['sms'] = self._send_sms_alert({
                'severity': 'TEST',
                'event_type': 'NOTIFICATION_TEST',
                'message': 'Testing SMS',
                'app': 'test',
                'timestamp': datetime.utcnow().isoformat(),
                'details': {}
            })

        # Test CloudWatch
        if self.cloudwatch_enabled:
            results['cloudwatch'] = self._send_cloudwatch_alert({
                'severity': 'TEST',
                'event_type': 'NOTIFICATION_TEST',
                'message': 'Testing CloudWatch',
                'app': 'test',
                'timestamp': datetime.utcnow().isoformat(),
                'details': {}
            })

        return results


def main():
    """CLI interface for alert notifier"""
    import argparse

    parser = argparse.ArgumentParser(description="Security Alert Notifier")
    parser.add_argument("action",
                       choices=["send", "test", "summary", "configure"],
                       help="Action to perform")
    parser.add_argument("--severity",
                       choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                       default="HIGH",
                       help="Alert severity")
    parser.add_argument("--event", help="Event type")
    parser.add_argument("--message", help="Alert message")
    parser.add_argument("--app", help="Application name")
    parser.add_argument("--config", help="Config file path")

    args = parser.parse_args()

    notifier = SecurityAlertNotifier(config_path=args.config)

    if args.action == "send":
        if not args.event or not args.message:
            print("Error: --event and --message required for send")
            return

        success = notifier.send_alert(
            severity=args.severity,
            event_type=args.event,
            message=args.message,
            app=args.app
        )
        print(f"Alert sent: {success}")

    elif args.action == "test":
        print("Testing notification channels...")
        results = notifier.test_notifications()
        for channel, success in results.items():
            status = "✓ SUCCESS" if success else "✗ FAILED"
            print(f"  {channel}: {status}")

    elif args.action == "summary":
        summary = notifier.get_alert_summary()
        print("Alert Summary (last 24 hours):")
        print(f"  Total: {summary['total']}")
        print("  By Severity:", summary['by_severity'])
        print("  By Type:", summary['by_type'])
        print("  By App:", summary['by_app'])

    elif args.action == "configure":
        # Generate sample configuration
        sample_config = {
            "email": {
                "enabled": True,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "from_email": "alerts@example.com",
                "to_emails": ["admin@example.com"],
                "username": "alerts@example.com",
                "password": "app-specific-password"
            },
            "sms": {
                "enabled": True,
                "to_numbers": ["+1234567890"]
            },
            "severity_levels": {
                "CRITICAL": ["email", "sms", "cloudwatch"],
                "HIGH": ["email", "cloudwatch"],
                "MEDIUM": ["cloudwatch"],
                "LOW": []
            }
        }

        config_path = args.config or "alert-config.json"
        with open(config_path, 'w') as f:
            json.dump(sample_config, f, indent=2)

        print(f"Sample configuration written to {config_path}")
        print("Edit this file with your actual credentials")


if __name__ == "__main__":
    main()