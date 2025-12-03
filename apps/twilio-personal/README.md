# Twilio Personal - SMS Automation for Personal Use

A comprehensive Python application for managing Twilio SMS operations for personal use, including automated reminders, alerts, and bulk messaging capabilities.

## Features

- **SMS Messaging**: Send SMS messages to any phone number
- **Self Notifications**: Quickly send notifications to your personal number
- **Message History**: View and search through message history
- **Phone Number Management**: List and manage Twilio phone numbers
- **Bulk Messaging**: Send personalized messages to multiple recipients
- **Alert System**: System monitoring and alert notifications
- **Daily Reminders**: Automated daily reminder messages
- **CLI Interface**: Rich command-line interface with colored output

## Installation

1. **Navigate to the app directory:**
   ```bash
   cd "apps/twilio-personal"
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your Twilio credentials:**

   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your Twilio credentials:
   ```env
   TWILIO_ACCOUNT_SID=your_account_sid_here
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_PHONE_NUMBER=+1234567890  # Your Twilio phone number
   MY_PERSONAL_NUMBER=+1234567890   # Your verified personal number
   TWILIO_EMAIL=twilio.everglade@mymailgpt.com
   ```

   You can find your Account SID and Auth Token in the [Twilio Console](https://console.twilio.com).

## Quick Start

### Using the CLI

The CLI provides an easy way to interact with Twilio:

```bash
# Run the setup wizard
python src/cli.py setup

# Verify your configuration
python src/cli.py verify

# Send an SMS
python src/cli.py send -t "+1234567890" -b "Hello from Twilio!"

# Send to yourself
python src/cli.py send-self -b "Personal reminder"

# View message history
python src/cli.py history --limit 10 --days 7

# List phone numbers
python src/cli.py numbers

# Check account info
python src/cli.py balance
```

### Using the Python API

```python
from src.twilio_client import TwilioPersonalClient

# Initialize client
client = TwilioPersonalClient()

# Send SMS
result = client.send_sms(
    to="+1234567890",
    body="Hello from Python!"
)

# Send to yourself
result = client.send_to_self("Personal notification")

# Get message history
messages = client.get_message_history(limit=10)

# Verify configuration
status = client.verify_configuration()
```

## Example Scripts

### Daily Reminder
Set up automated daily reminders:

```bash
python examples/daily_reminder.py
```

Schedule with cron (runs every day at 8 AM):
```bash
0 8 * * * cd /path/to/twilio-personal && python examples/daily_reminder.py
```

### Alert System
Send system alerts and notifications:

```python
from examples.alert_system import AlertSystem

alert = AlertSystem()

# Send various alerts
alert.system_startup_alert()
alert.backup_complete_alert("backup.tar.gz", "2.3GB")
alert.disk_space_alert(85.5)
alert.error_alert("Database connection failed", "MySQL")
```

### Bulk Messaging
Send personalized messages to multiple recipients:

```bash
python examples/bulk_sender.py
```

Create a CSV file with recipients:
```csv
phone,name,event
+1234567890,John Doe,Annual Meeting
+0987654321,Jane Smith,Annual Meeting
```

## Project Structure

```
twilio-personal/
├── src/
│   ├── __init__.py        # Package initialization
│   ├── config.py          # Configuration management
│   ├── twilio_client.py   # Main Twilio client wrapper
│   └── cli.py             # Command-line interface
├── examples/
│   ├── daily_reminder.py  # Daily reminder automation
│   ├── alert_system.py    # System alert notifications
│   └── bulk_sender.py     # Bulk SMS messaging
├── .env.example           # Environment variables template
├── .gitignore            # Git ignore rules
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Configuration

### Required Environment Variables

- `TWILIO_ACCOUNT_SID`: Your Twilio Account SID
- `TWILIO_AUTH_TOKEN`: Your Twilio Auth Token

### Optional Environment Variables

- `TWILIO_PHONE_NUMBER`: Your Twilio phone number for sending SMS
- `MY_PERSONAL_NUMBER`: Your personal phone number for notifications
- `TWILIO_MESSAGING_SERVICE_SID`: Messaging Service SID (if using)
- `TWILIO_EMAIL`: Email associated with your Twilio account

## Security Notes

- **Never commit `.env` files** to version control
- Store credentials securely
- Use environment variables for production deployments
- Regularly rotate your Auth Token
- Monitor your Twilio usage to detect unauthorized access

## Twilio Account Setup

1. **Create a Twilio Account:**
   - Sign up at [twilio.com](https://www.twilio.com/try-twilio)
   - Verify your email and phone number

2. **Get a Phone Number:**
   - Navigate to Phone Numbers > Manage > Buy a Number
   - Choose a number with SMS capabilities
   - Note the phone number for your `.env` file

3. **Find Your Credentials:**
   - Go to the [Twilio Console](https://console.twilio.com)
   - Account SID and Auth Token are on the dashboard
   - Copy these to your `.env` file

4. **Verify Personal Numbers:**
   - For trial accounts, verify numbers at Phone Numbers > Verified Caller IDs
   - Add your personal phone number for testing

## Rate Limits and Best Practices

- **Message Queue**: Twilio queues messages automatically
- **Rate Limiting**: Default 1-second delay between bulk messages
- **Error Handling**: Automatic retry logic for failed messages
- **Logging**: All operations are logged for debugging

## Troubleshooting

### Common Issues

1. **Authentication Error:**
   - Verify Account SID and Auth Token are correct
   - Check that credentials are properly loaded from `.env`

2. **Phone Number Not Found:**
   - Ensure phone number is in E.164 format (+1234567890)
   - Verify the number is purchased in your Twilio account

3. **Message Not Delivered:**
   - Check recipient number is verified (for trial accounts)
   - Ensure sufficient account balance
   - Review Twilio Console for error details

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration with Other Apps

This Twilio app can be integrated with other applications in the workspace:

- **Love Brittany/Kaelin Trackers**: Send relationship reminders
- **Weekly Budget Report**: SMS notifications for budget alerts
- **Todoist Integration**: Task completion notifications

## Future Enhancements

- [ ] WhatsApp integration
- [ ] Voice call support
- [ ] MMS (picture messaging) support
- [ ] Two-way SMS handling (webhooks)
- [ ] SMS templates management
- [ ] Usage analytics and reporting
- [ ] AWS Lambda deployment option

## Support

For Twilio-specific issues:
- [Twilio Documentation](https://www.twilio.com/docs/sms)
- [Twilio Console](https://console.twilio.com)
- [Twilio Support](https://support.twilio.com)

## License

This project is for personal use. Ensure compliance with Twilio's terms of service and applicable messaging regulations.

---

**Created:** 2024
**Last Updated:** 2024
**Version:** 1.0.0