#!/usr/bin/env python3
"""
Bulk SMS Sender
Send SMS messages to multiple recipients from a CSV file
"""

import sys
import csv
from pathlib import Path
from typing import List, Dict
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.twilio_client import TwilioPersonalClient
from src.config import ConfigManager


class BulkSender:
    """Bulk SMS sending with rate limiting and error handling"""

    def __init__(self, delay_seconds: float = 1.0):
        """
        Initialize bulk sender

        Args:
            delay_seconds: Delay between messages to avoid rate limiting
        """
        self.client = TwilioPersonalClient()
        self.delay_seconds = delay_seconds
        self.results = []

    def load_recipients_from_csv(self, csv_path: str) -> List[Dict[str, str]]:
        """
        Load recipients from CSV file

        Expected CSV format:
        phone,name,custom_field
        +1234567890,John Doe,Value1
        +0987654321,Jane Smith,Value2

        Args:
            csv_path: Path to CSV file

        Returns:
            List of recipient dictionaries
        """
        recipients = []
        with open(csv_path, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if 'phone' in row:
                    recipients.append(row)
        return recipients

    def personalize_message(self, template: str, recipient: Dict[str, str]) -> str:
        """
        Personalize message template with recipient data

        Template can use {field_name} placeholders

        Args:
            template: Message template with placeholders
            recipient: Recipient data dictionary

        Returns:
            Personalized message
        """
        message = template
        for key, value in recipient.items():
            placeholder = f"{{{key}}}"
            message = message.replace(placeholder, value)
        return message

    def send_bulk_messages(
        self,
        recipients: List[Dict[str, str]],
        message_template: str,
        dry_run: bool = False
    ) -> Dict[str, any]:
        """
        Send messages to multiple recipients

        Args:
            recipients: List of recipient dictionaries
            message_template: Message template with optional placeholders
            dry_run: If True, don't actually send messages

        Returns:
            Summary of results
        """
        successful = 0
        failed = 0
        skipped = 0

        print(f"\n{'DRY RUN - ' if dry_run else ''}Sending messages to {len(recipients)} recipients...")
        print("-" * 50)

        for i, recipient in enumerate(recipients, 1):
            phone = recipient.get('phone')

            if not phone:
                print(f"[{i}/{len(recipients)}] ⚠️  Skipped - No phone number")
                skipped += 1
                continue

            # Validate phone number
            if not ConfigManager.validate_phone_number(phone):
                print(f"[{i}/{len(recipients)}] ⚠️  Skipped - Invalid phone: {phone}")
                skipped += 1
                continue

            # Personalize message
            message = self.personalize_message(message_template, recipient)

            if dry_run:
                print(f"[{i}/{len(recipients)}] 📝 Would send to {phone}: {message[:50]}...")
                successful += 1
            else:
                try:
                    result = self.client.send_sms(to=phone, body=message)
                    self.results.append({
                        'recipient': recipient,
                        'status': 'success',
                        'sid': result['sid']
                    })
                    print(f"[{i}/{len(recipients)}] ✅ Sent to {phone} (SID: {result['sid'][:8]}...)")
                    successful += 1

                    # Rate limiting
                    if i < len(recipients):
                        time.sleep(self.delay_seconds)

                except Exception as e:
                    self.results.append({
                        'recipient': recipient,
                        'status': 'failed',
                        'error': str(e)
                    })
                    print(f"[{i}/{len(recipients)}] ❌ Failed to {phone}: {e}")
                    failed += 1

        # Summary
        print("\n" + "=" * 50)
        print("BULK SEND SUMMARY")
        print("=" * 50)
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Skipped: {skipped}")
        print(f"📊 Total: {len(recipients)}")

        return {
            'successful': successful,
            'failed': failed,
            'skipped': skipped,
            'total': len(recipients),
            'results': self.results
        }

    def save_results_to_csv(self, output_path: str):
        """Save send results to CSV file"""
        with open(output_path, 'w', newline='', encoding='utf-8') as file:
            fieldnames = ['phone', 'name', 'status', 'sid', 'error']
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            writer.writeheader()
            for result in self.results:
                row = {
                    'phone': result['recipient'].get('phone', ''),
                    'name': result['recipient'].get('name', ''),
                    'status': result['status'],
                    'sid': result.get('sid', ''),
                    'error': result.get('error', '')
                }
                writer.writerow(row)

        print(f"\n📁 Results saved to: {output_path}")


# Example usage
if __name__ == "__main__":
    # Create example CSV file
    example_csv = Path(__file__).parent / "recipients_example.csv"

    # Create example CSV if it doesn't exist
    if not example_csv.exists():
        with open(example_csv, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['phone', 'name', 'event'])
            writer.writerow(['+1234567890', 'John Doe', 'Annual Meeting'])
            writer.writerow(['+0987654321', 'Jane Smith', 'Annual Meeting'])
            writer.writerow(['+1122334455', 'Bob Johnson', 'Annual Meeting'])
        print(f"Created example CSV: {example_csv}")

    # Example message template
    template = """Hi {name}!

This is a reminder about the {event} tomorrow at 2 PM.

Please confirm your attendance by replying YES or NO.

Thanks!"""

    # Initialize bulk sender
    sender = BulkSender(delay_seconds=1.0)

    # Load recipients
    recipients = sender.load_recipients_from_csv(example_csv)
    print(f"Loaded {len(recipients)} recipients from CSV")

    # Preview mode
    print("\nMessage Template:")
    print("-" * 40)
    print(template)
    print("-" * 40)

    # Ask for confirmation
    response = input("\nSend messages? (yes/dry-run/no): ").lower()

    if response == 'yes':
        results = sender.send_bulk_messages(recipients, template, dry_run=False)
        sender.save_results_to_csv(Path(__file__).parent / "send_results.csv")
    elif response == 'dry-run':
        results = sender.send_bulk_messages(recipients, template, dry_run=True)
    else:
        print("Cancelled.")