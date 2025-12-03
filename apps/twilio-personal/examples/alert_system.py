#!/usr/bin/env python3
"""
Alert System
Send SMS alerts for various system events or monitoring
"""

import sys
from pathlib import Path
from datetime import datetime
import socket
import platform

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.twilio_client import TwilioPersonalClient


class AlertSystem:
    """System for sending various types of alerts via SMS"""

    def __init__(self):
        self.client = TwilioPersonalClient()
        self.hostname = socket.gethostname()
        self.system = platform.system()

    def send_alert(self, alert_type: str, message: str, priority: str = "normal"):
        """
        Send an alert via SMS

        Args:
            alert_type: Type of alert (error, warning, info, success)
            message: Alert message
            priority: Alert priority (low, normal, high, critical)
        """
        # Priority emojis
        priority_icons = {
            "low": "ℹ️",
            "normal": "📌",
            "high": "⚠️",
            "critical": "🚨"
        }

        # Alert type emojis
        type_icons = {
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "success": "✅"
        }

        icon = priority_icons.get(priority, "📌")
        type_icon = type_icons.get(alert_type, "📨")

        timestamp = datetime.now().strftime("%H:%M:%S")

        alert_message = f"""{icon} {priority.upper()} ALERT {icon}

{type_icon} Type: {alert_type.upper()}
🖥️ System: {self.hostname} ({self.system})
🕐 Time: {timestamp}

{message}

--
Twilio Alert System"""

        try:
            result = self.client.send_to_self(body=alert_message)
            print(f"✓ Alert sent! SID: {result['sid']}")
            return True
        except Exception as e:
            print(f"✗ Failed to send alert: {e}")
            return False

    def system_startup_alert(self):
        """Send alert when system starts up"""
        return self.send_alert(
            alert_type="info",
            message="System has started successfully. All services operational.",
            priority="normal"
        )

    def backup_complete_alert(self, backup_name: str, size: str):
        """Send alert when backup completes"""
        return self.send_alert(
            alert_type="success",
            message=f"Backup completed successfully!\nName: {backup_name}\nSize: {size}",
            priority="normal"
        )

    def disk_space_alert(self, usage_percent: float):
        """Send alert for disk space issues"""
        priority = "high" if usage_percent > 90 else "normal"
        return self.send_alert(
            alert_type="warning",
            message=f"Disk space usage: {usage_percent:.1f}%\nConsider cleaning up files.",
            priority=priority
        )

    def error_alert(self, error_message: str, service_name: str = "Unknown"):
        """Send alert for errors"""
        return self.send_alert(
            alert_type="error",
            message=f"Service: {service_name}\nError: {error_message}",
            priority="high"
        )

    def custom_alert(self, message: str, **kwargs):
        """Send a custom alert with your own message"""
        alert_type = kwargs.get('alert_type', 'info')
        priority = kwargs.get('priority', 'normal')
        return self.send_alert(alert_type, message, priority)


# Example usage
if __name__ == "__main__":
    alert_system = AlertSystem()

    # Example: Send various alerts
    examples = [
        ("System startup", lambda: alert_system.system_startup_alert()),
        ("Backup complete", lambda: alert_system.backup_complete_alert("daily_backup_2024.tar.gz", "2.3 GB")),
        ("Disk space warning", lambda: alert_system.disk_space_alert(85.5)),
        ("Custom alert", lambda: alert_system.custom_alert(
            "Your scheduled task has completed successfully!",
            alert_type="success",
            priority="normal"
        ))
    ]

    print("Alert System Examples")
    print("-" * 40)

    for name, func in examples:
        response = input(f"\nSend {name} alert? (y/n): ").lower()
        if response == 'y':
            func()
        else:
            print(f"Skipped {name}")

    print("\n✓ Alert system demonstration complete!")