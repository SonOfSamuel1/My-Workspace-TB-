"""
Twilio Client Wrapper
Provides simplified interface for common Twilio operations
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from .config import TwilioConfig, get_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TwilioPersonalClient:
    """Wrapper for Twilio operations tailored for personal use"""

    def __init__(self, config: Optional[TwilioConfig] = None):
        """
        Initialize Twilio client

        Args:
            config: Optional TwilioConfig object. If not provided, loads from environment
        """
        self.config = config or get_config()
        self.client = Client(self.config.account_sid, self.config.auth_token)
        logger.info(f"Initialized Twilio client for account: {self.config.account_sid[:8]}...")

    def send_sms(
        self,
        to: str,
        body: str,
        from_number: Optional[str] = None,
        media_url: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send an SMS message

        Args:
            to: Recipient phone number (E.164 format)
            body: Message body
            from_number: Sender number (uses config default if not specified)
            media_url: Optional list of media URLs for MMS

        Returns:
            Dictionary with message details

        Raises:
            TwilioRestException: If message sending fails
        """
        from_number = from_number or self.config.phone_number

        if not from_number:
            raise ValueError("No sender phone number configured. Set TWILIO_PHONE_NUMBER in .env")

        try:
            message_params = {
                'body': body,
                'from_': from_number,
                'to': to
            }

            if media_url:
                message_params['media_url'] = media_url

            message = self.client.messages.create(**message_params)

            result = {
                'sid': message.sid,
                'to': message.to,
                'from': message.from_,
                'body': message.body,
                'status': message.status,
                'date_created': message.date_created.isoformat() if message.date_created else None,
                'direction': message.direction,
                'price': message.price,
                'price_unit': message.price_unit
            }

            logger.info(f"SMS sent successfully. SID: {message.sid}")
            return result

        except TwilioRestException as e:
            logger.error(f"Failed to send SMS: {e}")
            raise

    def send_to_self(self, body: str, media_url: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send an SMS to your personal number

        Args:
            body: Message body
            media_url: Optional list of media URLs for MMS

        Returns:
            Dictionary with message details
        """
        if not self.config.personal_number:
            raise ValueError("Personal number not configured. Set MY_PERSONAL_NUMBER in .env")

        return self.send_sms(
            to=self.config.personal_number,
            body=body,
            media_url=media_url
        )

    def get_message_history(
        self,
        limit: int = 20,
        to: Optional[str] = None,
        from_number: Optional[str] = None,
        date_sent_after: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve message history

        Args:
            limit: Maximum number of messages to retrieve
            to: Filter by recipient number
            from_number: Filter by sender number
            date_sent_after: Filter messages sent after this date

        Returns:
            List of message dictionaries
        """
        filters = {}
        if to:
            filters['to'] = to
        if from_number:
            filters['from_'] = from_number
        if date_sent_after:
            filters['date_sent_after'] = date_sent_after

        try:
            messages = self.client.messages.list(limit=limit, **filters)

            result = []
            for msg in messages:
                result.append({
                    'sid': msg.sid,
                    'to': msg.to,
                    'from': msg.from_,
                    'body': msg.body,
                    'status': msg.status,
                    'direction': msg.direction,
                    'date_sent': msg.date_sent.isoformat() if msg.date_sent else None,
                    'price': msg.price
                })

            logger.info(f"Retrieved {len(result)} messages")
            return result

        except TwilioRestException as e:
            logger.error(f"Failed to retrieve message history: {e}")
            raise

    def get_phone_numbers(self) -> List[Dict[str, Any]]:
        """
        Get all phone numbers associated with the account

        Returns:
            List of phone number details
        """
        try:
            numbers = self.client.incoming_phone_numbers.list()

            result = []
            for num in numbers:
                result.append({
                    'sid': num.sid,
                    'phone_number': num.phone_number,
                    'friendly_name': num.friendly_name,
                    'capabilities': {
                        'voice': num.capabilities.voice,
                        'sms': num.capabilities.sms,
                        'mms': num.capabilities.mms
                    },
                    'date_created': num.date_created.isoformat() if num.date_created else None
                })

            logger.info(f"Retrieved {len(result)} phone numbers")
            return result

        except TwilioRestException as e:
            logger.error(f"Failed to retrieve phone numbers: {e}")
            raise

    def get_account_balance(self) -> Dict[str, Any]:
        """
        Get account balance information

        Returns:
            Dictionary with balance details
        """
        try:
            account = self.client.api.accounts(self.config.account_sid).fetch()

            return {
                'status': account.status,
                'type': account.type,
                'friendly_name': account.friendly_name,
                'date_created': account.date_created.isoformat() if account.date_created else None
            }

        except TwilioRestException as e:
            logger.error(f"Failed to retrieve account info: {e}")
            raise

    def verify_configuration(self) -> Dict[str, bool]:
        """
        Verify that the Twilio configuration is valid

        Returns:
            Dictionary with verification results
        """
        results = {
            'account_valid': False,
            'phone_number_valid': False,
            'personal_number_set': False,
            'can_send_sms': False
        }

        try:
            # Verify account
            account = self.client.api.accounts(self.config.account_sid).fetch()
            results['account_valid'] = account.status == 'active'

            # Check if phone number is configured
            if self.config.phone_number:
                # Verify the phone number exists in account
                numbers = self.get_phone_numbers()
                for num in numbers:
                    if num['phone_number'] == self.config.phone_number:
                        results['phone_number_valid'] = True
                        results['can_send_sms'] = num['capabilities']['sms']
                        break

            # Check personal number
            results['personal_number_set'] = bool(self.config.personal_number)

            logger.info(f"Configuration verification results: {results}")
            return results

        except Exception as e:
            logger.error(f"Configuration verification failed: {e}")
            return results