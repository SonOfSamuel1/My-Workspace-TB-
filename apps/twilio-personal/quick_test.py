#!/usr/bin/env python3
import os
import logging
logging.getLogger().setLevel(logging.ERROR)

from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

# Twilio setup from environment variables
account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
from_number = os.environ.get('TWILIO_FROM_NUMBER', '+16789905007')
to_number = os.environ.get('TWILIO_TO_NUMBER', '+14077448449')

# Create client and send
client = Client(account_sid, auth_token)

message = client.messages.create(
    body="Test message from Claude Code! Your Twilio is working perfectly. Have a great day!",
    from_=from_number,
    to=to_number
)

print(f"✅ Message sent!")
print(f"SID: {message.sid}")
print(f"To: {to_number}")
print("Check your phone!")