"""
Credential validation and secure loading utilities.

Provides functions to validate that required credentials are present
and properly formatted before attempting to use them.
"""

import os
import logging
from typing import Dict, Optional
from pathlib import Path

from exceptions import CredentialError

logger = logging.getLogger(__name__)


def validate_credentials(
    require_amazon: bool = False,
    require_gmail: bool = False,
    require_ynab: bool = True
) -> Dict[str, bool]:
    """
    Validate that required credentials are present and properly formatted.

    Args:
        require_amazon: Whether Amazon credentials are required
        require_gmail: Whether Gmail credentials are required
        require_ynab: Whether YNAB credentials are required (default True)

    Returns:
        Dict mapping credential names to validation status

    Raises:
        CredentialError: If any required credentials are missing or invalid
    """
    results = {}
    errors = []

    # YNAB API key validation
    ynab_key = os.getenv('YNAB_API_KEY')
    if require_ynab:
        if not ynab_key:
            errors.append("YNAB_API_KEY environment variable not set")
            results['ynab'] = False
        elif len(ynab_key) < 20:
            errors.append("YNAB_API_KEY appears invalid (too short)")
            results['ynab'] = False
        else:
            results['ynab'] = True
            logger.debug("YNAB API key validated")
    else:
        results['ynab'] = bool(ynab_key)

    # Amazon credentials validation
    amazon_email = os.getenv('AMAZON_EMAIL')
    amazon_password = os.getenv('AMAZON_PASSWORD')
    if require_amazon:
        if not amazon_email:
            errors.append("AMAZON_EMAIL environment variable not set")
            results['amazon_email'] = False
        elif '@' not in amazon_email:
            errors.append("AMAZON_EMAIL does not appear to be a valid email address")
            results['amazon_email'] = False
        else:
            results['amazon_email'] = True

        if not amazon_password:
            errors.append("AMAZON_PASSWORD environment variable not set")
            results['amazon_password'] = False
        else:
            results['amazon_password'] = True

        results['amazon'] = results.get('amazon_email', False) and results.get('amazon_password', False)
    else:
        results['amazon'] = bool(amazon_email and amazon_password)

    # Gmail credentials validation
    if require_gmail:
        gmail_creds_path = os.getenv('GMAIL_CREDENTIALS_PATH')
        gmail_token_path = os.getenv('GMAIL_TOKEN_PATH')

        if not gmail_creds_path:
            errors.append("GMAIL_CREDENTIALS_PATH environment variable not set")
            results['gmail_credentials'] = False
        elif not Path(gmail_creds_path).exists():
            errors.append(f"Gmail credentials file not found: {gmail_creds_path}")
            results['gmail_credentials'] = False
        else:
            results['gmail_credentials'] = True

        # Token is optional initially (created during auth flow)
        if gmail_token_path and Path(gmail_token_path).exists():
            results['gmail_token'] = True
        else:
            results['gmail_token'] = False
            logger.info("Gmail token not found - will need to authenticate")

        results['gmail'] = results.get('gmail_credentials', False)
    else:
        gmail_creds_path = os.getenv('GMAIL_CREDENTIALS_PATH')
        results['gmail'] = bool(gmail_creds_path and Path(gmail_creds_path).exists())

    # Raise error if any required credentials are missing
    if errors:
        error_message = "; ".join(errors)
        logger.error(f"Credential validation failed: {error_message}")
        raise CredentialError(error_message)

    logger.info(f"Credentials validated: {results}")
    return results


def mask_credential(credential: str, visible_chars: int = 4) -> str:
    """
    Mask a credential for safe logging.

    Args:
        credential: The credential to mask
        visible_chars: Number of characters to show at the start

    Returns:
        Masked credential string (e.g., "abcd********")
    """
    if not credential:
        return "***"
    if len(credential) <= visible_chars:
        return "*" * len(credential)
    return credential[:visible_chars] + "*" * (len(credential) - visible_chars)


def get_credential_summary() -> Dict[str, str]:
    """
    Get a summary of configured credentials (masked for safety).

    Returns:
        Dict with credential names and their masked values or status
    """
    summary = {}

    # YNAB
    ynab_key = os.getenv('YNAB_API_KEY')
    summary['YNAB_API_KEY'] = mask_credential(ynab_key) if ynab_key else "NOT SET"

    # Amazon
    amazon_email = os.getenv('AMAZON_EMAIL')
    summary['AMAZON_EMAIL'] = amazon_email if amazon_email else "NOT SET"

    amazon_password = os.getenv('AMAZON_PASSWORD')
    summary['AMAZON_PASSWORD'] = "SET" if amazon_password else "NOT SET"

    amazon_otp = os.getenv('AMAZON_OTP_SECRET')
    summary['AMAZON_OTP_SECRET'] = "SET" if amazon_otp else "NOT SET"

    # Gmail
    gmail_creds = os.getenv('GMAIL_CREDENTIALS_PATH')
    if gmail_creds:
        exists = Path(gmail_creds).exists()
        summary['GMAIL_CREDENTIALS'] = f"{'EXISTS' if exists else 'MISSING'}: {gmail_creds}"
    else:
        summary['GMAIL_CREDENTIALS'] = "NOT SET"

    gmail_token = os.getenv('GMAIL_TOKEN_PATH')
    if gmail_token:
        exists = Path(gmail_token).exists()
        summary['GMAIL_TOKEN'] = f"{'EXISTS' if exists else 'MISSING'}: {gmail_token}"
    else:
        summary['GMAIL_TOKEN'] = "NOT SET"

    return summary


def validate_aws_credentials() -> bool:
    """
    Validate AWS credentials are available (for Lambda deployment).

    Returns:
        True if AWS credentials are configured
    """
    # Check for AWS environment variables or IAM role
    has_env_creds = bool(
        os.getenv('AWS_ACCESS_KEY_ID') and
        os.getenv('AWS_SECRET_ACCESS_KEY')
    )

    # In Lambda, credentials come from IAM role
    has_lambda_role = bool(os.getenv('AWS_LAMBDA_FUNCTION_NAME'))

    # Check for AWS profile
    has_profile = bool(os.getenv('AWS_PROFILE'))

    if has_env_creds or has_lambda_role or has_profile:
        logger.debug("AWS credentials validated")
        return True

    logger.warning("No AWS credentials found")
    return False


if __name__ == "__main__":
    # Test credential validation
    logging.basicConfig(level=logging.INFO)

    print("\n" + "=" * 50)
    print("CREDENTIAL SUMMARY")
    print("=" * 50)

    summary = get_credential_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 50)
    print("VALIDATION RESULTS")
    print("=" * 50)

    try:
        results = validate_credentials(
            require_amazon=False,
            require_gmail=False,
            require_ynab=True
        )
        for key, valid in results.items():
            status = "VALID" if valid else "MISSING/INVALID"
            print(f"  {key}: {status}")
    except CredentialError as e:
        print(f"  ERROR: {e}")

    print("=" * 50)
