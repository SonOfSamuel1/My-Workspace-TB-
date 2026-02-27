"""Web Push notification service for ActionOS.

Handles VAPID key loading, subscription storage in SSM, and sending
push notifications via pywebpush.

SSM parameters used:
  /action-dashboard/vapid-public-key   - base64url-encoded uncompressed P-256 public key
  /action-dashboard/vapid-private-key  - PEM-encoded private key
  /action-dashboard/push-subscription  - JSON push subscription (single-user)
"""

import json
import logging
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

_SSM_PUB = "/action-dashboard/vapid-public-key"
_SSM_PRIV = "/action-dashboard/vapid-private-key"
_SSM_SUB = "/action-dashboard/push-subscription"

_ssm = boto3.client("ssm", region_name="us-east-1")

_VAPID_CLAIMS = {"sub": "mailto:admin@actionos.app"}


def _put_param(name: str, value: str, secure: bool = False) -> None:
    _ssm.put_parameter(
        Name=name,
        Value=value,
        Type="SecureString" if secure else "String",
        Overwrite=True,
    )


def _get_param(name: str, decrypt: bool = True) -> Optional[str]:
    try:
        r = _ssm.get_parameter(Name=name, WithDecryption=decrypt)
        return r["Parameter"]["Value"]
    except _ssm.exceptions.ParameterNotFound:
        return None
    except Exception as e:
        logger.error(f"SSM get {name}: {e}")
        return None


# ---------------------------------------------------------------------------
# VAPID key management
# ---------------------------------------------------------------------------


def generate_and_store_vapid_keys() -> dict:
    """Generate a fresh VAPID key pair and store it in SSM.

    Returns {'public_key': '...', 'private_key_pem': '...'}.
    Call this once via the setup script or notify_test if keys are missing.
    """
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    # Uncompressed public key (65 bytes: 0x04 || x || y) → base64url
    pub_bytes = public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    pub_b64 = base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode()

    priv_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()

    _put_param(_SSM_PUB, pub_b64, secure=False)
    _put_param(_SSM_PRIV, priv_pem, secure=True)
    logger.info("Generated and stored new VAPID keys")
    return {"public_key": pub_b64, "private_key_pem": priv_pem}


def get_vapid_public_key() -> Optional[str]:
    """Return the VAPID public key (base64url), generating keys if missing."""
    key = _get_param(_SSM_PUB, decrypt=False)
    if not key:
        data = generate_and_store_vapid_keys()
        key = data["public_key"]
    return key


def get_vapid_private_key() -> Optional[str]:
    return _get_param(_SSM_PRIV, decrypt=True)


# ---------------------------------------------------------------------------
# Subscription storage
# ---------------------------------------------------------------------------


def store_subscription(subscription: dict) -> bool:
    """Persist a push subscription JSON to SSM. Returns True on success."""
    try:
        _put_param(_SSM_SUB, json.dumps(subscription), secure=False)
        logger.info(
            f"Stored push subscription endpoint: {subscription.get('endpoint', '')[:60]}"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to store push subscription: {e}")
        return False


def get_subscription() -> Optional[dict]:
    """Load the stored push subscription. Returns None if not found."""
    raw = _get_param(_SSM_SUB, decrypt=False)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Send push notification
# ---------------------------------------------------------------------------


def send_push(title: str, body: str, url: str = "/") -> bool:
    """Send a push notification to the stored subscription.

    Returns True on success, False if no subscription or send failed.
    """
    subscription = get_subscription()
    if not subscription:
        logger.info("No push subscription stored — skipping push")
        return False

    private_key = get_vapid_private_key()
    if not private_key:
        logger.warning("No VAPID private key — cannot send push")
        return False

    try:
        import base64

        from cryptography.hazmat.primitives import serialization
        from pywebpush import webpush

        # Convert PEM to raw base64url 32-byte key (pywebpush expects this)
        if "BEGIN" in private_key:
            pkey = serialization.load_pem_private_key(
                private_key.encode(), password=None
            )
            raw = pkey.private_numbers().private_value.to_bytes(32, "big")
            private_key = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

        payload = json.dumps({"title": title, "body": body, "url": url})
        webpush(
            subscription_info=subscription,
            data=payload,
            vapid_private_key=private_key,
            vapid_claims=dict(_VAPID_CLAIMS),
        )
        logger.info(f"Push sent: {title}")
        return True
    except Exception as e:
        logger.error(f"Push send failed: {e}")
        return False
