#!/usr/bin/env python3
"""
Secure Credential Manager for My Workspace
Handles encrypted storage and retrieval of sensitive credentials
"""

import os
import json
import base64
import hashlib
import logging
import stat
from pathlib import Path
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import keyring
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecureCredentialManager:
    """
    Manages encrypted credentials with file permission hardening
    and audit logging capabilities
    """

    def __init__(self, vault_path: str = None):
        """Initialize the credential manager"""
        self.vault_path = Path(vault_path or os.path.expanduser("~/.my-workspace-vault"))
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self._set_secure_permissions(self.vault_path)

        self.credentials_file = self.vault_path / "credentials.enc"
        self.audit_log_file = self.vault_path / "audit.log"
        self.key_file = self.vault_path / ".key"

        # Initialize encryption key
        self.cipher = self._initialize_encryption()

        # Initialize audit logger
        self._setup_audit_logger()

    def _set_secure_permissions(self, path: Path):
        """Set secure file permissions (0600 for files, 0700 for directories)"""
        try:
            if path.is_file():
                # Owner read/write only (0600)
                os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            elif path.is_dir():
                # Owner read/write/execute only (0700)
                os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            logger.info(f"Set secure permissions on {path}")
        except Exception as e:
            logger.error(f"Failed to set permissions on {path}: {e}")
            raise

    def _initialize_encryption(self) -> Fernet:
        """Initialize or load encryption key"""
        if self.key_file.exists():
            # Load existing key from keyring
            key = self._load_encryption_key()
        else:
            # Generate new key and store securely
            key = self._generate_encryption_key()

        return Fernet(key)

    def _generate_encryption_key(self) -> bytes:
        """Generate a new encryption key"""
        # Get or create a master password (stored in system keyring)
        master_password = keyring.get_password("my-workspace", "master-key")
        if not master_password:
            # Generate a strong random password
            import secrets
            master_password = secrets.token_urlsafe(32)
            keyring.set_password("my-workspace", "master-key", master_password)
            logger.info("Generated new master encryption key")

        # Derive encryption key from master password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'my-workspace-salt-2024',  # Use a fixed salt for consistency
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

        # Store key reference (not the actual key)
        self.key_file.write_text("keyring:my-workspace:master-key")
        self._set_secure_permissions(self.key_file)

        return key

    def _load_encryption_key(self) -> bytes:
        """Load encryption key from secure storage"""
        master_password = keyring.get_password("my-workspace", "master-key")
        if not master_password:
            raise ValueError("Master key not found in keyring. Vault may be corrupted.")

        # Derive encryption key from master password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'my-workspace-salt-2024',
            iterations=100000,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

    def _setup_audit_logger(self):
        """Setup audit logging"""
        audit_handler = logging.FileHandler(self.audit_log_file)
        audit_handler.setLevel(logging.INFO)
        audit_formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        audit_handler.setFormatter(audit_formatter)

        self.audit_logger = logging.getLogger('audit')
        self.audit_logger.addHandler(audit_handler)
        self.audit_logger.setLevel(logging.INFO)

        # Secure the audit log
        if self.audit_log_file.exists():
            self._set_secure_permissions(self.audit_log_file)

    def _audit_log(self, action: str, details: Dict[str, Any]):
        """Log an audit event"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "details": details,
            "user": os.getenv("USER", "unknown"),
            "pid": os.getpid()
        }
        self.audit_logger.info(json.dumps(audit_entry))

    def store_credential(self, service: str, key: str, value: str,
                        rotate_days: int = 30, metadata: Dict = None):
        """
        Store a credential securely

        Args:
            service: Service name (e.g., 'gmail', 'ynab', 'todoist')
            key: Credential key (e.g., 'api_key', 'oauth_token')
            value: The actual credential value
            rotate_days: Days until rotation reminder
            metadata: Additional metadata to store
        """
        # Load existing credentials
        credentials = self._load_credentials()

        # Prepare credential entry
        entry = {
            "value": value,
            "created_at": datetime.utcnow().isoformat(),
            "rotate_by": (datetime.utcnow() + timedelta(days=rotate_days)).isoformat(),
            "metadata": metadata or {}
        }

        # Store credential
        if service not in credentials:
            credentials[service] = {}

        # Check if overwriting existing
        is_update = key in credentials[service]
        credentials[service][key] = entry

        # Save encrypted credentials
        self._save_credentials(credentials)

        # Audit log
        self._audit_log(
            "CREDENTIAL_STORED" if not is_update else "CREDENTIAL_UPDATED",
            {
                "service": service,
                "key": key,
                "rotate_days": rotate_days,
                "has_metadata": bool(metadata)
            }
        )

        logger.info(f"Stored credential for {service}:{key}")

    def get_credential(self, service: str, key: str) -> Optional[str]:
        """
        Retrieve a credential

        Args:
            service: Service name
            key: Credential key

        Returns:
            The credential value or None if not found
        """
        credentials = self._load_credentials()

        if service in credentials and key in credentials[service]:
            entry = credentials[service][key]

            # Check if rotation is needed
            rotate_by = datetime.fromisoformat(entry["rotate_by"])
            if datetime.utcnow() > rotate_by:
                logger.warning(f"Credential {service}:{key} needs rotation (expired {rotate_by})")

            # Audit log
            self._audit_log("CREDENTIAL_ACCESSED", {
                "service": service,
                "key": key
            })

            return entry["value"]

        return None

    def list_credentials(self) -> Dict[str, list]:
        """List all stored credentials (without values)"""
        credentials = self._load_credentials()
        result = {}

        for service, keys in credentials.items():
            result[service] = []
            for key, entry in keys.items():
                rotate_by = datetime.fromisoformat(entry["rotate_by"])
                needs_rotation = datetime.utcnow() > rotate_by

                result[service].append({
                    "key": key,
                    "created_at": entry["created_at"],
                    "rotate_by": entry["rotate_by"],
                    "needs_rotation": needs_rotation,
                    "metadata": entry.get("metadata", {})
                })

        return result

    def check_rotation_needed(self) -> list:
        """Check which credentials need rotation"""
        credentials = self._load_credentials()
        needs_rotation = []

        for service, keys in credentials.items():
            for key, entry in keys.items():
                rotate_by = datetime.fromisoformat(entry["rotate_by"])
                if datetime.utcnow() > rotate_by:
                    needs_rotation.append({
                        "service": service,
                        "key": key,
                        "expired_at": entry["rotate_by"],
                        "days_overdue": (datetime.utcnow() - rotate_by).days
                    })

        return needs_rotation

    def _load_credentials(self) -> Dict:
        """Load and decrypt credentials"""
        if not self.credentials_file.exists():
            return {}

        try:
            encrypted_data = self.credentials_file.read_bytes()
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return {}

    def _save_credentials(self, credentials: Dict):
        """Encrypt and save credentials"""
        try:
            json_data = json.dumps(credentials, indent=2)
            encrypted_data = self.cipher.encrypt(json_data.encode())

            # Write with secure permissions
            self.credentials_file.write_bytes(encrypted_data)
            self._set_secure_permissions(self.credentials_file)

        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            raise

    def migrate_from_env_file(self, env_file_path: str, service: str):
        """
        Migrate credentials from .env file to secure storage

        Args:
            env_file_path: Path to .env file
            service: Service name for these credentials
        """
        env_path = Path(env_file_path)
        if not env_path.exists():
            logger.warning(f"Environment file not found: {env_file_path}")
            return

        migrated = []
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")

                    # Determine rotation period based on key type
                    if 'token' in key.lower() or 'oauth' in key.lower():
                        rotate_days = 30
                    elif 'api' in key.lower() or 'key' in key.lower():
                        rotate_days = 90
                    else:
                        rotate_days = 180

                    self.store_credential(service, key, value, rotate_days)
                    migrated.append(key)

        if migrated:
            logger.info(f"Migrated {len(migrated)} credentials from {env_file_path}")
            self._audit_log("ENV_FILE_MIGRATED", {
                "service": service,
                "file": str(env_file_path),
                "keys_migrated": migrated
            })

            # Create backup of original .env file
            backup_path = env_path.with_suffix('.env.backup')
            env_path.rename(backup_path)
            logger.info(f"Original .env file backed up to {backup_path}")

    def export_for_lambda(self, service: str, output_file: str = None):
        """
        Export credentials for AWS Lambda deployment

        Args:
            service: Service to export credentials for
            output_file: Optional output file path
        """
        credentials = self._load_credentials()

        if service not in credentials:
            logger.warning(f"No credentials found for service: {service}")
            return None

        # Prepare export format for Lambda environment variables
        export_data = {}
        for key, entry in credentials[service].items():
            export_data[key] = entry["value"]

        if output_file:
            # Write as JSON for AWS Secrets Manager
            output_path = Path(output_file)
            output_path.write_text(json.dumps(export_data, indent=2))
            self._set_secure_permissions(output_path)
            logger.info(f"Exported credentials to {output_file}")

        return export_data

    def validate_permissions(self) -> Dict[str, bool]:
        """Validate that all credential files have correct permissions"""
        results = {}

        for path in [self.vault_path, self.credentials_file, self.audit_log_file, self.key_file]:
            if path.exists():
                stats = path.stat()
                mode = oct(stats.st_mode)[-3:]

                if path.is_file():
                    # Should be 600 (owner read/write only)
                    is_secure = mode == '600'
                else:
                    # Should be 700 (owner read/write/execute only)
                    is_secure = mode == '700'

                results[str(path)] = is_secure

                if not is_secure:
                    logger.warning(f"Insecure permissions on {path}: {mode}")
                    self._set_secure_permissions(path)

        return results


def main():
    """CLI interface for credential management"""
    import argparse

    parser = argparse.ArgumentParser(description="Secure Credential Manager")
    parser.add_argument("action", choices=["store", "get", "list", "migrate", "check-rotation", "validate"],
                       help="Action to perform")
    parser.add_argument("--service", help="Service name")
    parser.add_argument("--key", help="Credential key")
    parser.add_argument("--value", help="Credential value (for store)")
    parser.add_argument("--env-file", help="Path to .env file (for migrate)")
    parser.add_argument("--rotate-days", type=int, default=30, help="Days until rotation")
    parser.add_argument("--vault-path", help="Custom vault path")

    args = parser.parse_args()

    manager = SecureCredentialManager(vault_path=args.vault_path)

    if args.action == "store":
        if not all([args.service, args.key, args.value]):
            print("Error: --service, --key, and --value required for store")
            return
        manager.store_credential(args.service, args.key, args.value, args.rotate_days)
        print(f"Stored credential for {args.service}:{args.key}")

    elif args.action == "get":
        if not all([args.service, args.key]):
            print("Error: --service and --key required for get")
            return
        value = manager.get_credential(args.service, args.key)
        if value:
            print(value)
        else:
            print(f"Credential not found: {args.service}:{args.key}")

    elif args.action == "list":
        credentials = manager.list_credentials()
        for service, keys in credentials.items():
            print(f"\n{service}:")
            for key_info in keys:
                rotation_status = "⚠️ NEEDS ROTATION" if key_info["needs_rotation"] else "✓"
                print(f"  - {key_info['key']}: expires {key_info['rotate_by']} {rotation_status}")

    elif args.action == "migrate":
        if not all([args.env_file, args.service]):
            print("Error: --env-file and --service required for migrate")
            return
        manager.migrate_from_env_file(args.env_file, args.service)

    elif args.action == "check-rotation":
        needs_rotation = manager.check_rotation_needed()
        if needs_rotation:
            print("Credentials needing rotation:")
            for cred in needs_rotation:
                print(f"  - {cred['service']}:{cred['key']} (overdue by {cred['days_overdue']} days)")
        else:
            print("All credentials are up to date")

    elif args.action == "validate":
        results = manager.validate_permissions()
        print("Permission validation results:")
        for path, is_secure in results.items():
            status = "✓ SECURE" if is_secure else "⚠️ FIXED"
            print(f"  {path}: {status}")


if __name__ == "__main__":
    main()