#!/usr/bin/env python3
"""
Rate Limiter for My Workspace Applications
Implements token bucket algorithm for API rate limiting
"""

import time
import json
import os
from pathlib import Path
from threading import Lock
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter with persistence
    """

    def __init__(self, storage_path: str = None):
        """Initialize the rate limiter"""
        self.storage_path = Path(storage_path or os.path.expanduser("~/.my-workspace-vault/rate_limits.json"))
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.buckets = {}
        self.locks = {}
        self.load_state()

    def load_state(self):
        """Load rate limit state from disk"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    for key, bucket_data in data.items():
                        self.buckets[key] = TokenBucket(
                            capacity=bucket_data['capacity'],
                            refill_rate=bucket_data['refill_rate'],
                            tokens=bucket_data.get('tokens', bucket_data['capacity']),
                            last_refill=datetime.fromisoformat(bucket_data['last_refill'])
                        )
                        self.locks[key] = Lock()
            except Exception as e:
                logger.error(f"Failed to load rate limit state: {e}")

    def save_state(self):
        """Save rate limit state to disk"""
        try:
            data = {}
            for key, bucket in self.buckets.items():
                data[key] = {
                    'capacity': bucket.capacity,
                    'refill_rate': bucket.refill_rate,
                    'tokens': bucket.tokens,
                    'last_refill': bucket.last_refill.isoformat()
                }

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

            # Set secure permissions
            os.chmod(self.storage_path, 0o600)
        except Exception as e:
            logger.error(f"Failed to save rate limit state: {e}")

    def configure_limit(self, key: str, capacity: int, refill_rate: float, period: str = "second"):
        """
        Configure a rate limit

        Args:
            key: Unique identifier for this limit (e.g., "email_sends")
            capacity: Maximum number of tokens in the bucket
            refill_rate: Number of tokens to refill per period
            period: Time period for refill ("second", "minute", "hour")
        """
        # Convert refill rate to per-second
        if period == "minute":
            refill_rate = refill_rate / 60
        elif period == "hour":
            refill_rate = refill_rate / 3600
        elif period == "day":
            refill_rate = refill_rate / 86400

        self.buckets[key] = TokenBucket(capacity, refill_rate)
        self.locks[key] = Lock()
        self.save_state()

        logger.info(f"Configured rate limit: {key} (capacity={capacity}, refill={refill_rate}/s)")

    def check_and_consume(self, key: str, tokens: int = 1, wait: bool = False) -> bool:
        """
        Check if operation is allowed and consume tokens

        Args:
            key: Rate limit key
            tokens: Number of tokens to consume
            wait: If True, wait for tokens to become available

        Returns:
            True if operation is allowed, False otherwise
        """
        if key not in self.buckets:
            logger.warning(f"Rate limit not configured for key: {key}")
            return True  # Allow if not configured

        with self.locks[key]:
            bucket = self.buckets[key]

            if wait:
                # Wait for tokens to become available
                while not bucket.consume(tokens):
                    wait_time = bucket.time_until_tokens(tokens)
                    if wait_time > 0:
                        time.sleep(min(wait_time, 1))  # Check every second
            else:
                # Try to consume tokens
                if bucket.consume(tokens):
                    self.save_state()
                    return True
                else:
                    logger.warning(f"Rate limit exceeded for {key}: {tokens} tokens requested, {bucket.tokens:.2f} available")
                    return False

        return False

    def get_remaining(self, key: str) -> Optional[float]:
        """Get remaining tokens for a key"""
        if key not in self.buckets:
            return None

        with self.locks[key]:
            bucket = self.buckets[key]
            bucket.refill()
            return bucket.tokens

    def reset(self, key: str):
        """Reset a rate limit to full capacity"""
        if key in self.buckets:
            with self.locks[key]:
                self.buckets[key].reset()
                self.save_state()

    def get_status(self) -> Dict:
        """Get status of all rate limits"""
        status = {}
        for key, bucket in self.buckets.items():
            with self.locks[key]:
                bucket.refill()
                status[key] = {
                    'tokens': bucket.tokens,
                    'capacity': bucket.capacity,
                    'refill_rate': bucket.refill_rate,
                    'percentage': (bucket.tokens / bucket.capacity) * 100
                }
        return status


class TokenBucket:
    """
    Token bucket implementation for rate limiting
    """

    def __init__(self, capacity: int, refill_rate: float, tokens: float = None,
                 last_refill: datetime = None):
        """
        Initialize a token bucket

        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
            tokens: Current tokens (default: capacity)
            last_refill: Last refill time
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = tokens if tokens is not None else capacity
        self.last_refill = last_refill or datetime.now()

    def refill(self):
        """Refill tokens based on elapsed time"""
        now = datetime.now()
        elapsed = (now - self.last_refill).total_seconds()

        # Calculate tokens to add
        tokens_to_add = elapsed * self.refill_rate

        # Add tokens up to capacity
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def consume(self, tokens: int) -> bool:
        """
        Try to consume tokens

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if successful, False if not enough tokens
        """
        self.refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def time_until_tokens(self, tokens: int) -> float:
        """
        Calculate time until enough tokens are available

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds until tokens are available
        """
        self.refill()

        if self.tokens >= tokens:
            return 0

        tokens_needed = tokens - self.tokens
        seconds_needed = tokens_needed / self.refill_rate

        return seconds_needed

    def reset(self):
        """Reset bucket to full capacity"""
        self.tokens = self.capacity
        self.last_refill = datetime.now()


class ApplicationRateLimiter:
    """
    Pre-configured rate limiter for My Workspace applications
    """

    def __init__(self, app_name: str):
        """Initialize with app-specific limits"""
        self.app_name = app_name
        self.limiter = RateLimiter()

        # Configure application-specific limits
        if app_name == "autonomous-email-assistant":
            self._configure_email_assistant_limits()
        elif app_name == "weekly-budget-report":
            self._configure_budget_report_limits()
        elif app_name in ["love-brittany-tracker", "love-kaelin-tracker"]:
            self._configure_love_tracker_limits()

    def _configure_email_assistant_limits(self):
        """Configure limits for Autonomous Email Assistant"""
        # Email sending: 10 per hour
        self.limiter.configure_limit("email_send", capacity=10, refill_rate=10, period="hour")

        # SMS sending: 1 per 5 minutes
        self.limiter.configure_limit("sms_send", capacity=1, refill_rate=1/5, period="minute")

        # Gmail API: 250 per second (Google's limit)
        self.limiter.configure_limit("gmail_api", capacity=250, refill_rate=250, period="second")

        # Claude Code API: 30 per minute
        self.limiter.configure_limit("claude_api", capacity=30, refill_rate=30, period="minute")

        # Email classification: 100 per minute
        self.limiter.configure_limit("email_classify", capacity=100, refill_rate=100, period="minute")

    def _configure_budget_report_limits(self):
        """Configure limits for Weekly Budget Report"""
        # Report generation: 1 per day
        self.limiter.configure_limit("report_generate", capacity=1, refill_rate=1, period="day")

        # YNAB API: 200 per hour (YNAB's limit)
        self.limiter.configure_limit("ynab_api", capacity=200, refill_rate=200, period="hour")

        # Email sending: 5 per hour
        self.limiter.configure_limit("email_send", capacity=5, refill_rate=5, period="hour")

    def _configure_love_tracker_limits(self):
        """Configure limits for Love Tracker applications"""
        # Report generation: 2 per week
        self.limiter.configure_limit("report_generate", capacity=2, refill_rate=2/7, period="day")

        # Google Docs API: 60 per minute
        self.limiter.configure_limit("docs_api", capacity=60, refill_rate=60, period="minute")

        # Calendar API: 60 per minute
        self.limiter.configure_limit("calendar_api", capacity=60, refill_rate=60, period="minute")

        # Toggl API: 120 per minute
        self.limiter.configure_limit("toggl_api", capacity=120, refill_rate=120, period="minute")

    def can_send_email(self, count: int = 1) -> bool:
        """Check if email sending is allowed"""
        return self.limiter.check_and_consume("email_send", count)

    def can_send_sms(self) -> bool:
        """Check if SMS sending is allowed"""
        return self.limiter.check_and_consume("sms_send", 1)

    def can_make_api_call(self, api_name: str, count: int = 1) -> bool:
        """Check if API call is allowed"""
        key = f"{api_name}_api"
        return self.limiter.check_and_consume(key, count)

    def can_generate_report(self) -> bool:
        """Check if report generation is allowed"""
        return self.limiter.check_and_consume("report_generate", 1)

    def wait_for_email(self, count: int = 1):
        """Wait until email sending is allowed"""
        self.limiter.check_and_consume("email_send", count, wait=True)

    def wait_for_sms(self):
        """Wait until SMS sending is allowed"""
        self.limiter.check_and_consume("sms_send", 1, wait=True)

    def get_status(self) -> Dict:
        """Get rate limit status"""
        return self.limiter.get_status()

    def reset_all(self):
        """Reset all rate limits (use with caution)"""
        for key in self.limiter.buckets.keys():
            self.limiter.reset(key)


def main():
    """CLI interface for rate limiter"""
    import argparse

    parser = argparse.ArgumentParser(description="Rate Limiter for My Workspace")
    parser.add_argument("action", choices=["status", "test", "reset", "configure"],
                       help="Action to perform")
    parser.add_argument("--app", help="Application name")
    parser.add_argument("--key", help="Rate limit key")
    parser.add_argument("--capacity", type=int, help="Bucket capacity")
    parser.add_argument("--rate", type=float, help="Refill rate")
    parser.add_argument("--period", choices=["second", "minute", "hour", "day"],
                       default="second", help="Refill period")

    args = parser.parse_args()

    if args.action == "status":
        if args.app:
            limiter = ApplicationRateLimiter(args.app)
            status = limiter.get_status()
            print(f"Rate limit status for {args.app}:")
            for key, info in status.items():
                print(f"  {key}:")
                print(f"    Tokens: {info['tokens']:.2f}/{info['capacity']}")
                print(f"    Available: {info['percentage']:.1f}%")
                print(f"    Refill: {info['refill_rate']:.2f}/sec")
        else:
            print("Please specify --app")

    elif args.action == "test":
        if args.app:
            limiter = ApplicationRateLimiter(args.app)

            # Test email sending
            print("Testing email rate limit...")
            for i in range(12):
                if limiter.can_send_email():
                    print(f"  Email {i+1}: ✓ Allowed")
                else:
                    print(f"  Email {i+1}: ✗ Blocked (rate limit)")
                time.sleep(0.1)

            # Test SMS sending
            print("\nTesting SMS rate limit...")
            for i in range(3):
                if limiter.can_send_sms():
                    print(f"  SMS {i+1}: ✓ Allowed")
                else:
                    print(f"  SMS {i+1}: ✗ Blocked (wait 5 minutes)")
                time.sleep(1)

        else:
            print("Please specify --app")

    elif args.action == "reset":
        if args.app:
            limiter = ApplicationRateLimiter(args.app)
            limiter.reset_all()
            print(f"Reset all rate limits for {args.app}")
        else:
            print("Please specify --app")

    elif args.action == "configure":
        if all([args.key, args.capacity, args.rate]):
            limiter = RateLimiter()
            limiter.configure_limit(args.key, args.capacity, args.rate, args.period)
            print(f"Configured rate limit: {args.key}")
        else:
            print("Please specify --key, --capacity, and --rate")


if __name__ == "__main__":
    main()