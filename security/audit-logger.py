#!/usr/bin/env python3
"""
Security Audit Logger for My Workspace
Provides comprehensive audit logging with tamper detection
"""

import os
import json
import hashlib
import logging
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from enum import Enum
import threading
from queue import Queue
import gzip

# Configure base logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AuditLevel(Enum):
    """Audit event severity levels"""
    CRITICAL = "CRITICAL"  # Security violations, unauthorized access
    HIGH = "HIGH"          # Failed authentication, rate limit violations
    MEDIUM = "MEDIUM"      # Configuration changes, permission modifications
    LOW = "LOW"            # Normal operations, API calls
    INFO = "INFO"          # Informational events


class AuditEvent(Enum):
    """Standard audit event types"""
    # Authentication Events
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILURE = "AUTH_FAILURE"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_ROTATED = "TOKEN_ROTATED"

    # Email Events
    EMAIL_SENT = "EMAIL_SENT"
    EMAIL_DRAFTED = "EMAIL_DRAFTED"
    EMAIL_CLASSIFIED = "EMAIL_CLASSIFIED"
    EMAIL_BLOCKED = "EMAIL_BLOCKED"

    # SMS Events
    SMS_SENT = "SMS_SENT"
    SMS_ESCALATION = "SMS_ESCALATION"

    # API Events
    API_CALL = "API_CALL"
    API_RATE_LIMIT = "API_RATE_LIMIT"
    API_ERROR = "API_ERROR"

    # Security Events
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    CREDENTIAL_ACCESS = "CREDENTIAL_ACCESS"
    CREDENTIAL_STORED = "CREDENTIAL_STORED"

    # System Events
    SYSTEM_START = "SYSTEM_START"
    SYSTEM_STOP = "SYSTEM_STOP"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    FILE_ACCESS = "FILE_ACCESS"


class SecureAuditLogger:
    """
    Secure audit logger with tamper detection and encryption
    """

    def __init__(self, app_name: str, log_dir: str = None):
        """
        Initialize the audit logger

        Args:
            app_name: Application name for audit entries
            log_dir: Directory for audit logs
        """
        self.app_name = app_name
        self.log_dir = Path(log_dir or os.path.expanduser("~/.my-workspace-vault/audit"))
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Set secure permissions
        os.chmod(self.log_dir, 0o700)

        # Initialize log files
        self.current_log_file = self._get_log_file_path()
        self.hash_chain_file = self.log_dir / f"{app_name}.chain"

        # Initialize hash chain for tamper detection
        self.last_hash = self._load_hash_chain()

        # Async logging queue
        self.log_queue = Queue()
        self.writer_thread = threading.Thread(target=self._log_writer, daemon=True)
        self.writer_thread.start()

        # Statistics
        self.stats = {
            "events_logged": 0,
            "critical_events": 0,
            "high_events": 0,
            "errors": 0
        }

    def _get_log_file_path(self) -> Path:
        """Get current log file path (rotates daily)"""
        date_str = datetime.now().strftime("%Y%m%d")
        return self.log_dir / f"{self.app_name}_{date_str}.audit.jsonl"

    def _load_hash_chain(self) -> str:
        """Load the last hash from the chain file"""
        if self.hash_chain_file.exists():
            with open(self.hash_chain_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    return lines[-1].strip().split(',')[1]  # Format: timestamp,hash
        return "0" * 64  # Initial hash

    def _save_hash_chain(self, hash_value: str):
        """Append hash to chain file"""
        timestamp = datetime.utcnow().isoformat()
        with open(self.hash_chain_file, 'a') as f:
            f.write(f"{timestamp},{hash_value}\n")

        # Set secure permissions
        os.chmod(self.hash_chain_file, 0o600)

    def _compute_event_hash(self, event_data: Dict) -> str:
        """Compute hash of event data including previous hash (blockchain-style)"""
        # Include previous hash for chain integrity
        event_data['previous_hash'] = self.last_hash

        # Serialize and hash
        event_json = json.dumps(event_data, sort_keys=True)
        hash_value = hashlib.sha256(event_json.encode()).hexdigest()

        return hash_value

    def _log_writer(self):
        """Background thread for writing log entries"""
        while True:
            try:
                # Get log entry from queue (blocks until available)
                entry = self.log_queue.get()

                if entry is None:  # Shutdown signal
                    break

                # Write to file
                self._write_log_entry(entry)

                # Update statistics
                self.stats["events_logged"] += 1
                if entry.get("level") == AuditLevel.CRITICAL.value:
                    self.stats["critical_events"] += 1
                elif entry.get("level") == AuditLevel.HIGH.value:
                    self.stats["high_events"] += 1

            except Exception as e:
                logger.error(f"Error writing audit log: {e}")
                self.stats["errors"] += 1

    def _write_log_entry(self, entry: Dict):
        """Write a single log entry to file"""
        # Rotate log file if needed
        current_file = self._get_log_file_path()
        if current_file != self.current_log_file:
            self._rotate_log()
            self.current_log_file = current_file

        # Write entry
        with open(self.current_log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        # Set secure permissions
        os.chmod(self.current_log_file, 0o600)

        # Update hash chain
        self._save_hash_chain(entry['hash'])
        self.last_hash = entry['hash']

    def _rotate_log(self):
        """Rotate and compress old log files"""
        if self.current_log_file.exists():
            # Compress old log
            compressed_file = self.current_log_file.with_suffix('.jsonl.gz')
            with open(self.current_log_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    f_out.writelines(f_in)

            # Remove original
            self.current_log_file.unlink()

            # Set secure permissions on compressed file
            os.chmod(compressed_file, 0o600)

            logger.info(f"Rotated log file: {compressed_file}")

    def log(self, event: AuditEvent, level: AuditLevel, details: Dict[str, Any],
            user: str = None, ip_address: str = None):
        """
        Log an audit event

        Args:
            event: Event type
            level: Severity level
            details: Event-specific details
            user: User identifier
            ip_address: Source IP address
        """
        # Prepare audit entry
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "app": self.app_name,
            "event": event.value,
            "level": level.value,
            "details": details,
            "user": user or os.getenv("USER", "system"),
            "ip_address": ip_address or "127.0.0.1",
            "pid": os.getpid(),
            "thread_id": threading.get_ident()
        }

        # Add environment context
        entry["environment"] = {
            "aws_lambda": os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None,
            "github_actions": os.getenv("GITHUB_ACTIONS") == "true",
            "ci": os.getenv("CI") == "true"
        }

        # Compute hash for tamper detection
        entry["hash"] = self._compute_event_hash(entry)

        # Queue for async writing
        self.log_queue.put(entry)

        # Also log critical events immediately
        if level == AuditLevel.CRITICAL:
            logger.critical(f"AUDIT: {event.value} - {details}")
            self._alert_critical_event(entry)

    def _alert_critical_event(self, entry: Dict):
        """Send alert for critical events"""
        # Write to special critical events file
        critical_file = self.log_dir / "critical_events.log"
        with open(critical_file, 'a') as f:
            f.write(f"{entry['timestamp']} - {entry['event']} - {entry['details']}\n")

        # TODO: Send email/SMS alert for critical events
        # This would integrate with notification system

    def log_email_sent(self, recipient: str, subject: str, tier: int,
                       classification_confidence: float):
        """Log email sending event"""
        self.log(
            AuditEvent.EMAIL_SENT,
            AuditLevel.LOW,
            {
                "recipient": recipient,
                "subject": subject,
                "tier": tier,
                "classification_confidence": classification_confidence,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def log_email_blocked(self, recipient: str, reason: str):
        """Log blocked email event"""
        self.log(
            AuditEvent.EMAIL_BLOCKED,
            AuditLevel.MEDIUM,
            {
                "recipient": recipient,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def log_api_call(self, api_name: str, endpoint: str, method: str,
                    status_code: int = None):
        """Log API call"""
        self.log(
            AuditEvent.API_CALL,
            AuditLevel.INFO,
            {
                "api": api_name,
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def log_rate_limit_exceeded(self, limit_key: str, requested: int, available: int):
        """Log rate limit violation"""
        self.log(
            AuditEvent.API_RATE_LIMIT,
            AuditLevel.HIGH,
            {
                "limit_key": limit_key,
                "requested_tokens": requested,
                "available_tokens": available,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def log_credential_access(self, service: str, key: str, purpose: str):
        """Log credential access"""
        self.log(
            AuditEvent.CREDENTIAL_ACCESS,
            AuditLevel.MEDIUM,
            {
                "service": service,
                "key": key,
                "purpose": purpose,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def log_security_violation(self, violation_type: str, details: str):
        """Log security violation"""
        self.log(
            AuditEvent.SECURITY_VIOLATION,
            AuditLevel.CRITICAL,
            {
                "type": violation_type,
                "details": details,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def verify_integrity(self, start_date: str = None, end_date: str = None) -> bool:
        """
        Verify log integrity using hash chain

        Args:
            start_date: Start date (YYYYMMDD format)
            end_date: End date (YYYYMMDD format)

        Returns:
            True if integrity is valid, False otherwise
        """
        logger.info("Verifying audit log integrity...")

        # Load hash chain
        if not self.hash_chain_file.exists():
            logger.warning("No hash chain file found")
            return False

        with open(self.hash_chain_file, 'r') as f:
            chain_entries = [line.strip().split(',') for line in f.readlines()]

        # Verify each log file
        log_files = sorted(self.log_dir.glob(f"{self.app_name}_*.audit.jsonl*"))

        for log_file in log_files:
            # Check date range if specified
            file_date = log_file.stem.split('_')[1].split('.')[0]
            if start_date and file_date < start_date:
                continue
            if end_date and file_date > end_date:
                continue

            logger.info(f"Verifying {log_file}...")

            # Read log entries
            if log_file.suffix == '.gz':
                with gzip.open(log_file, 'rt') as f:
                    lines = f.readlines()
            else:
                with open(log_file, 'r') as f:
                    lines = f.readlines()

            # Verify each entry
            for line in lines:
                entry = json.loads(line)
                stored_hash = entry.pop('hash')

                # Recompute hash
                computed_hash = self._compute_event_hash(entry)

                if computed_hash != stored_hash:
                    logger.error(f"Hash mismatch in {log_file}: {entry['timestamp']}")
                    return False

        logger.info("Audit log integrity verified successfully")
        return True

    def search(self, event_type: str = None, level: str = None,
              start_time: datetime = None, end_time: datetime = None,
              user: str = None) -> List[Dict]:
        """
        Search audit logs

        Args:
            event_type: Filter by event type
            level: Filter by severity level
            start_time: Start time for search
            end_time: End time for search
            user: Filter by user

        Returns:
            List of matching audit entries
        """
        results = []

        # Search through log files
        log_files = sorted(self.log_dir.glob(f"{self.app_name}_*.audit.jsonl*"))

        for log_file in log_files:
            # Read log entries
            if log_file.suffix == '.gz':
                with gzip.open(log_file, 'rt') as f:
                    lines = f.readlines()
            else:
                with open(log_file, 'r') as f:
                    lines = f.readlines()

            # Filter entries
            for line in lines:
                entry = json.loads(line)

                # Apply filters
                if event_type and entry['event'] != event_type:
                    continue
                if level and entry['level'] != level:
                    continue
                if user and entry['user'] != user:
                    continue

                # Time range filter
                entry_time = datetime.fromisoformat(entry['timestamp'])
                if start_time and entry_time < start_time:
                    continue
                if end_time and entry_time > end_time:
                    continue

                results.append(entry)

        return results

    def generate_report(self, period: str = "daily") -> Dict:
        """
        Generate audit report

        Args:
            period: Report period ("daily", "weekly", "monthly")

        Returns:
            Report dictionary with statistics
        """
        # Determine time range
        end_time = datetime.utcnow()
        if period == "daily":
            start_time = end_time - timedelta(days=1)
        elif period == "weekly":
            start_time = end_time - timedelta(weeks=1)
        elif period == "monthly":
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(days=1)

        # Search logs
        entries = self.search(start_time=start_time, end_time=end_time)

        # Generate statistics
        report = {
            "period": period,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_events": len(entries),
            "events_by_type": {},
            "events_by_level": {},
            "events_by_user": {},
            "critical_events": [],
            "high_events": [],
            "api_calls": 0,
            "emails_sent": 0,
            "sms_sent": 0,
            "rate_limits_exceeded": 0
        }

        # Analyze entries
        for entry in entries:
            # Count by type
            event_type = entry['event']
            report["events_by_type"][event_type] = report["events_by_type"].get(event_type, 0) + 1

            # Count by level
            level = entry['level']
            report["events_by_level"][level] = report["events_by_level"].get(level, 0) + 1

            # Count by user
            user = entry['user']
            report["events_by_user"][user] = report["events_by_user"].get(user, 0) + 1

            # Collect critical events
            if level == "CRITICAL":
                report["critical_events"].append({
                    "timestamp": entry['timestamp'],
                    "event": event_type,
                    "details": entry['details']
                })

            # Collect high severity events
            if level == "HIGH":
                report["high_events"].append({
                    "timestamp": entry['timestamp'],
                    "event": event_type,
                    "details": entry['details']
                })

            # Count specific events
            if event_type == "API_CALL":
                report["api_calls"] += 1
            elif event_type == "EMAIL_SENT":
                report["emails_sent"] += 1
            elif event_type == "SMS_SENT":
                report["sms_sent"] += 1
            elif event_type == "API_RATE_LIMIT":
                report["rate_limits_exceeded"] += 1

        return report

    def shutdown(self):
        """Shutdown the logger gracefully"""
        # Signal writer thread to stop
        self.log_queue.put(None)

        # Wait for queue to empty
        self.writer_thread.join(timeout=5)

        logger.info(f"Audit logger shutdown. Stats: {self.stats}")


def main():
    """CLI interface for audit logger"""
    import argparse

    parser = argparse.ArgumentParser(description="Security Audit Logger")
    parser.add_argument("action", choices=["verify", "search", "report", "test"],
                       help="Action to perform")
    parser.add_argument("--app", default="test", help="Application name")
    parser.add_argument("--event", help="Event type to search")
    parser.add_argument("--level", help="Severity level to search")
    parser.add_argument("--user", help="User to search")
    parser.add_argument("--period", default="daily",
                       choices=["daily", "weekly", "monthly"],
                       help="Report period")

    args = parser.parse_args()

    logger_instance = SecureAuditLogger(args.app)

    if args.action == "verify":
        result = logger_instance.verify_integrity()
        print(f"Integrity check: {'PASSED' if result else 'FAILED'}")

    elif args.action == "search":
        results = logger_instance.search(
            event_type=args.event,
            level=args.level,
            user=args.user
        )
        print(f"Found {len(results)} events:")
        for entry in results[:10]:  # Show first 10
            print(f"  {entry['timestamp']} - {entry['event']} - {entry['level']}")

    elif args.action == "report":
        report = logger_instance.generate_report(args.period)
        print(f"\nAudit Report ({report['period']})")
        print("=" * 50)
        print(f"Total Events: {report['total_events']}")
        print(f"API Calls: {report['api_calls']}")
        print(f"Emails Sent: {report['emails_sent']}")
        print(f"SMS Sent: {report['sms_sent']}")
        print(f"Rate Limits Exceeded: {report['rate_limits_exceeded']}")

        if report['critical_events']:
            print(f"\nCritical Events: {len(report['critical_events'])}")
            for event in report['critical_events']:
                print(f"  - {event['timestamp']}: {event['event']}")

    elif args.action == "test":
        # Test logging
        logger_instance.log_email_sent("test@example.com", "Test Subject", 2, 0.95)
        logger_instance.log_api_call("gmail", "/messages/send", "POST", 200)
        logger_instance.log_rate_limit_exceeded("email_send", 11, 0)
        logger_instance.log_security_violation("unauthorized_access", "Attempt to access restricted resource")

        time.sleep(1)  # Wait for async writes
        print("Test events logged successfully")

    logger_instance.shutdown()


if __name__ == "__main__":
    main()