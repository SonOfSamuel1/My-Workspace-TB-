"""
S3 Cache Service for YNAB API responses

Caches API responses in S3 to avoid rate limiting.
Default TTL: 12 hours
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default cache TTL in hours
DEFAULT_CACHE_TTL_HOURS = 12

# S3 bucket name
CACHE_BUCKET = os.getenv('YNAB_CACHE_BUCKET', 'ynab-reviewer-cache')


class CacheService:
    """S3-based caching service for YNAB API responses"""

    def __init__(self, bucket_name: str = None, ttl_hours: int = None):
        """
        Initialize cache service

        Args:
            bucket_name: S3 bucket name for cache storage
            ttl_hours: Cache TTL in hours (default: 12)
        """
        self.bucket_name = bucket_name or CACHE_BUCKET
        self.ttl_hours = ttl_hours or DEFAULT_CACHE_TTL_HOURS
        self.s3 = boto3.client('s3')
        self._enabled = True

    def disable(self):
        """Disable caching (useful for force refresh)"""
        self._enabled = False

    def enable(self):
        """Enable caching"""
        self._enabled = True

    def _get_cache_key(self, key: str) -> str:
        """Generate S3 object key for cache entry"""
        return f"cache/{key}.json"

    def get(self, key: str) -> Optional[Any]:
        """
        Get cached data if valid

        Args:
            key: Cache key (e.g., 'categories', 'accounts', 'transactions-2024-01-15')

        Returns:
            Cached data if valid, None otherwise
        """
        if not self._enabled:
            logger.info(f"Cache disabled, skipping get for {key}")
            return None

        cache_key = self._get_cache_key(key)

        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=cache_key)
            data = json.loads(response['Body'].read().decode('utf-8'))

            # Check if cache is still valid
            cached_at = datetime.fromisoformat(data.get('cached_at', '1970-01-01T00:00:00'))
            expires_at = cached_at + timedelta(hours=self.ttl_hours)

            if datetime.utcnow() < expires_at:
                logger.info(f"Cache HIT for {key} (cached at {cached_at}, expires at {expires_at})")
                return data.get('payload')
            else:
                logger.info(f"Cache EXPIRED for {key} (cached at {cached_at}, expired at {expires_at})")
                return None

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.info(f"Cache MISS for {key} (not found)")
            else:
                logger.warning(f"Cache error for {key}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Cache error for {key}: {e}")
            return None

    def set(self, key: str, data: Any) -> bool:
        """
        Store data in cache

        Args:
            key: Cache key
            data: Data to cache (must be JSON serializable)

        Returns:
            True if successful, False otherwise
        """
        if not self._enabled:
            logger.info(f"Cache disabled, skipping set for {key}")
            return False

        cache_key = self._get_cache_key(key)

        try:
            cache_entry = {
                'cached_at': datetime.utcnow().isoformat(),
                'ttl_hours': self.ttl_hours,
                'payload': data
            }

            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=cache_key,
                Body=json.dumps(cache_entry, default=str),
                ContentType='application/json'
            )

            logger.info(f"Cache SET for {key}")
            return True

        except Exception as e:
            logger.warning(f"Failed to cache {key}: {e}")
            return False

    def invalidate(self, key: str) -> bool:
        """
        Invalidate (delete) a cache entry

        Args:
            key: Cache key to invalidate

        Returns:
            True if successful, False otherwise
        """
        cache_key = self._get_cache_key(key)

        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=cache_key)
            logger.info(f"Cache INVALIDATED for {key}")
            return True
        except Exception as e:
            logger.warning(f"Failed to invalidate cache {key}: {e}")
            return False

    def invalidate_all(self) -> bool:
        """
        Invalidate all cache entries

        Returns:
            True if successful, False otherwise
        """
        try:
            # List all objects in cache prefix
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='cache/'
            )

            if 'Contents' not in response:
                logger.info("No cache entries to invalidate")
                return True

            # Delete all cache objects
            objects = [{'Key': obj['Key']} for obj in response['Contents']]
            self.s3.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': objects}
            )

            logger.info(f"Cache INVALIDATED ALL ({len(objects)} entries)")
            return True

        except Exception as e:
            logger.warning(f"Failed to invalidate all cache: {e}")
            return False


# Singleton instance
_cache_instance: Optional[CacheService] = None


def get_cache() -> CacheService:
    """Get or create cache service singleton"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService()
    return _cache_instance
