#!/usr/bin/env python3
"""
Webhook Server for Real-time Toggl Sync

This module provides a webhook endpoint for receiving Toggl Track webhooks
to enable real-time synchronization of time entries.
"""

import os
import sys
import json
import logging
import hmac
import hashlib
from datetime import datetime
from flask import Flask, request, jsonify
from sync_service import SyncService


app = Flask(__name__)
logger = logging.getLogger(__name__)

# Global sync service instance
sync_service = None


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify webhook signature.

    Args:
        payload: Request payload bytes
        signature: Signature from header
        secret: Webhook secret

    Returns:
        True if signature is valid, False otherwise
    """
    if not secret or not signature:
        return False

    # Compute expected signature
    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'toggl-calendar-sync'
    })


@app.route('/toggl-webhook', methods=['POST'])
def toggl_webhook():
    """
    Toggl webhook endpoint.

    Receives notifications about time entry changes and triggers sync.
    """
    try:
        # Get webhook secret
        webhook_secret = os.getenv('WEBHOOK_SECRET')

        # Verify signature if secret is configured
        if webhook_secret:
            signature = request.headers.get('X-Webhook-Signature', '')
            if not verify_webhook_signature(request.data, signature, webhook_secret):
                logger.warning("Invalid webhook signature")
                return jsonify({'error': 'Invalid signature'}), 401

        # Parse payload
        payload = request.json
        logger.info(f"Received webhook: {json.dumps(payload, indent=2)}")

        # Extract event information
        # Toggl webhook payload structure:
        # {
        #   "event": "time_entry.created" | "time_entry.updated" | "time_entry.deleted",
        #   "time_entry": { ... }
        # }
        event_type = payload.get('event')
        time_entry_data = payload.get('time_entry', {})

        if not event_type or not time_entry_data:
            logger.warning("Invalid webhook payload")
            return jsonify({'error': 'Invalid payload'}), 400

        # Get time entry ID
        entry_id = time_entry_data.get('id')
        if not entry_id:
            logger.warning("No entry ID in webhook payload")
            return jsonify({'error': 'No entry ID'}), 400

        # Handle different event types
        if event_type == 'time_entry.created':
            logger.info(f"New time entry created: {entry_id}")
            handle_entry_created(time_entry_data)

        elif event_type == 'time_entry.updated':
            logger.info(f"Time entry updated: {entry_id}")
            handle_entry_updated(time_entry_data)

        elif event_type == 'time_entry.deleted':
            logger.info(f"Time entry deleted: {entry_id}")
            handle_entry_deleted(time_entry_data)

        else:
            logger.warning(f"Unknown event type: {event_type}")
            return jsonify({'error': 'Unknown event type'}), 400

        return jsonify({
            'status': 'success',
            'event': event_type,
            'entry_id': entry_id
        })

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


def handle_entry_created(time_entry_data: dict):
    """
    Handle time entry creation.

    Args:
        time_entry_data: Time entry data from webhook
    """
    try:
        # Fetch full entry details from Toggl
        entry_id = time_entry_data.get('id')
        entry = sync_service.toggl.get_time_entry_by_id(entry_id)

        if entry:
            # Sync to calendar
            event_id = sync_service.sync_time_entry(entry)
            if event_id:
                logger.info(f"Successfully synced new entry {entry_id} to calendar event {event_id}")
            else:
                logger.warning(f"Failed to sync entry {entry_id}")
        else:
            logger.warning(f"Could not fetch entry {entry_id} from Toggl")

    except Exception as e:
        logger.error(f"Error handling entry creation: {str(e)}", exc_info=True)


def handle_entry_updated(time_entry_data: dict):
    """
    Handle time entry update.

    Args:
        time_entry_data: Time entry data from webhook
    """
    try:
        # Fetch full entry details from Toggl
        entry_id = time_entry_data.get('id')
        entry = sync_service.toggl.get_time_entry_by_id(entry_id)

        if entry:
            # Sync to calendar (will update existing event)
            event_id = sync_service.sync_time_entry(entry)
            if event_id:
                logger.info(f"Successfully updated calendar event {event_id} for entry {entry_id}")
            else:
                logger.warning(f"Failed to update entry {entry_id}")
        else:
            logger.warning(f"Could not fetch entry {entry_id} from Toggl")

    except Exception as e:
        logger.error(f"Error handling entry update: {str(e)}", exc_info=True)


def handle_entry_deleted(time_entry_data: dict):
    """
    Handle time entry deletion.

    Args:
        time_entry_data: Time entry data from webhook
    """
    try:
        entry_id = str(time_entry_data.get('id'))

        # Remove from calendar and sync state
        if sync_service.unsync_entry(entry_id):
            logger.info(f"Successfully removed calendar event for deleted entry {entry_id}")
        else:
            logger.warning(f"Could not remove entry {entry_id} (may not have been synced)")

    except Exception as e:
        logger.error(f"Error handling entry deletion: {str(e)}", exc_info=True)


def setup_logging():
    """Setup logging configuration."""
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'webhook.log')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main entry point for webhook server."""
    global sync_service

    setup_logging()

    # Initialize sync service
    logger.info("Initializing sync service...")
    sync_service = SyncService()

    # Validate services
    if not sync_service.validate_services():
        logger.error("Failed to validate services")
        return 1

    # Get configuration
    port = int(os.getenv('WEBHOOK_PORT', 8080))
    webhook_enabled = os.getenv('WEBHOOK_ENABLED', 'false').lower() == 'true'

    if not webhook_enabled:
        logger.warning("Webhook server is disabled in configuration")
        return 0

    # Start server
    logger.info(f"Starting webhook server on port {port}...")
    logger.info("Webhook endpoint: POST /toggl-webhook")
    logger.info("Health check: GET /health")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
