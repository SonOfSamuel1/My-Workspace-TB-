#!/usr/bin/env python3
"""
Daily Reminder Script
Send yourself daily reminders via SMS
Can be scheduled with cron or task scheduler
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.twilio_client import TwilioPersonalClient


def send_daily_reminder():
    """Send a daily reminder SMS to personal number"""
    client = TwilioPersonalClient()

    # Get current day and date
    today = datetime.now()
    day_name = today.strftime("%A")
    date_str = today.strftime("%B %d, %Y")

    # Customize your reminder message
    reminders = {
        "Monday": "Start the week strong! Review your weekly goals.",
        "Tuesday": "Stay focused on your priorities today.",
        "Wednesday": "Midweek check-in: Are you on track with your goals?",
        "Thursday": "Almost there! Keep pushing forward.",
        "Friday": "Wrap up the week and plan for relaxation.",
        "Saturday": "Enjoy your weekend! Time for personal projects.",
        "Sunday": "Rest, recharge, and prepare for the week ahead."
    }

    message = f"""Good morning! 📅 {date_str}

{reminders.get(day_name, "Have a great day!")}

Daily checklist:
• Review calendar
• Check priority tasks
• Stay hydrated
• Take breaks

Sent via Twilio Personal"""

    try:
        result = client.send_to_self(body=message)
        print(f"✓ Daily reminder sent successfully! SID: {result['sid']}")
        return True
    except Exception as e:
        print(f"✗ Failed to send daily reminder: {e}")
        return False


if __name__ == "__main__":
    send_daily_reminder()