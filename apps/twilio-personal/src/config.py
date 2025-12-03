"""
Twilio Configuration Manager
Handles loading and validation of Twilio credentials and settings
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from dataclasses import dataclass


@dataclass
class TwilioConfig:
    """Twilio configuration container"""
    account_sid: str
    auth_token: str
    phone_number: Optional[str] = None
    personal_number: Optional[str] = None
    messaging_service_sid: Optional[str] = None
    email: Optional[str] = None


class ConfigManager:
    """Manages Twilio configuration loading and validation"""

    def __init__(self, env_path: Optional[Path] = None):
        """
        Initialize configuration manager

        Args:
            env_path: Optional path to .env file
        """
        if env_path:
            load_dotenv(env_path)
        else:
            # Load from default location
            env_file = Path(__file__).parent.parent / '.env'
            if env_file.exists():
                load_dotenv(env_file)
            else:
                load_dotenv()  # Try to load from current directory

    def load_config(self) -> TwilioConfig:
        """
        Load Twilio configuration from environment variables

        Returns:
            TwilioConfig object with loaded values

        Raises:
            ValueError: If required configuration is missing
        """
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')

        if not account_sid or not auth_token:
            raise ValueError(
                "Missing required Twilio credentials. "
                "Please set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN "
                "in your .env file or environment variables."
            )

        return TwilioConfig(
            account_sid=account_sid,
            auth_token=auth_token,
            phone_number=os.getenv('TWILIO_PHONE_NUMBER'),
            personal_number=os.getenv('MY_PERSONAL_NUMBER'),
            messaging_service_sid=os.getenv('TWILIO_MESSAGING_SERVICE_SID'),
            email=os.getenv('TWILIO_EMAIL', 'twilio.everglade@mymailgpt.com')
        )

    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """
        Validate phone number format

        Args:
            phone: Phone number to validate

        Returns:
            True if valid format, False otherwise
        """
        # Basic validation - must start with + and have 10-15 digits
        import re
        pattern = r'^\+[1-9]\d{9,14}$'
        return bool(re.match(pattern, phone.replace(' ', '').replace('-', '')))


# Convenience function for quick config loading
def get_config() -> TwilioConfig:
    """Get Twilio configuration with default settings"""
    manager = ConfigManager()
    return manager.load_config()