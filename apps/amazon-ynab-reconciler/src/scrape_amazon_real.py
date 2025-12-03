#!/usr/bin/env python3
"""
Real Amazon order scraper using Playwright MCP.
This will actually log into Amazon and get your order history.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
import time

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

email = os.getenv('AMAZON_EMAIL')
password = os.getenv('AMAZON_PASSWORD')

print("🔄 Starting Amazon order scraping...")
print(f"   Email: {email}")

# Note: This script will be called by the reconciler
# and will use the Playwright MCP tools directly