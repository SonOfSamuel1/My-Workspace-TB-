"""
Twilio Personal - SMS automation for personal use
"""

from .twilio_client import TwilioPersonalClient
from .config import TwilioConfig, ConfigManager, get_config

__version__ = "1.0.0"
__all__ = ["TwilioPersonalClient", "TwilioConfig", "ConfigManager", "get_config"]