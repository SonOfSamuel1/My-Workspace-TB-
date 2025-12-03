#!/usr/bin/env python3
"""Quick test message sender"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.twilio_client import TwilioPersonalClient

# Send message
client = TwilioPersonalClient()
result = client.send_to_self("Test message from Claude Code! Your Twilio setup is working. Check your phone!")
print(f"Message sent! SID: {result['sid']}")
print(f"Status: {result['status']}")
print("Check your phone at 407-744-8449!")