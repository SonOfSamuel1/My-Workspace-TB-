#!/usr/bin/env python3
"""
Main entry point for OneNote to Obsidian Migration Tool.

This script orchestrates the migration of OneNote notebooks
to an Obsidian vault, converting content to Markdown format.
"""
import os
import sys
import logging
import yaml
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Use python-dotenv for proper .env loading
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

from onenote_service import OneNoteService
from content_converter import ContentConverter
from obsidian_writer import ObsidianWriter


def setup_logging(config: dict):
    """Setup logging configuration."""
    log_config = config.get('logging', {})

    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = log_config.get('file', 'logs/migration.log')

    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def load_config() -> dict:
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent.parent / 'config.yaml'

    if not config_path.exists():
        # Return default configuration
        return {
            'migration': {
                'enabled': True,
                'vault_path': './output/obsidian-vault',
                'attachments_folder': 'attachments',
                'create_index_files': True,
                'preserve_timestamps': True,
                'skip_existing': False,
                'download_images': True,
                'include_metadata': True
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/migration.log'
            }
        }

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config


def load_environment():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent / '.env'

    if not env_path.exists():
        logging.warning(
            "Environment file '.env' not found. "
            "Using environment variables only."
        )
        return

    # Use python-dotenv if available
    if HAS_DOTENV:
        load_dotenv(env_path)
        logging.info("Environment loaded using python-dotenv")
        return

    # Fallback to manual parsing
    logging.info("python-dotenv not available, using manual .env parsing")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                os.environ[key.strip()] = value


def validate_configuration() -> bool:
    """
    Validate that required configuration is present.

    Returns:
        True if valid, False otherwise
    """
    logger = logging.getLogger(__name__)

    # Check required environment variables
    required_vars = ['AZURE_CLIENT_ID']
    optional_vars = ['AZURE_TENANT_ID', 'AZURE_CLIENT_SECRET']

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please update your .env file with these values")
        print("\nTo get Azure credentials:")
        print("1. Go to https://portal.azure.com")
        print("2. Register a new application in Azure Active Directory")
        print("3. Add Microsoft Graph API permissions: Notes.Read, Notes.Read.All")
        print("4. Copy the Application (client) ID to AZURE_CLIENT_ID")
        return False

    logger.info("Configuration validation passed")
    return True


def list_notebooks():
    """List all available OneNote notebooks."""
    logger = logging.getLogger(__name__)

    try:
        print("\n" + "="*60)
        print("DISCOVERING ONENOTE NOTEBOOKS")
        print("="*60 + "\n")

        onenote = OneNoteService()

        if not onenote.authenticate():
            print("\n Authentication failed")
            return

        notebooks = onenote.get_notebooks()

        if not notebooks:
            print("No notebooks found.")
            return

        print(f"Found {len(notebooks)} notebook(s):\n")

        for i, notebook in enumerate(notebooks, 1):
            print(f"{i}. {notebook['displayName']}")
            print(f"   ID: {notebook['id']}")
            print(f"   Created: {notebook.get('createdDateTime', 'Unknown')}")

            # Get sections
            sections = onenote.get_sections(notebook['id'])
            if sections:
                print(f"   Sections ({len(sections)}):")
                for section in sections:
                    print(f"     - {section['displayName']}")

            # Get section groups
            groups = onenote.get_section_groups(notebook['id'])
            if groups:
                print(f"   Section Groups ({len(groups)}):")
                for group in groups:
                    print(f"     - {group['displayName']}")

            print()

        print("="*60)
        print("Use --migrate to migrate all notebooks, or")
        print("--notebook <name> to migrate a specific notebook")
        print("="*60 + "\n")

    except Exception as e:
        logger.error(f"Error listing notebooks: {e}", exc_info=True)
        print(f"\n Error: {e}")


def migrate_notebooks(
    config: dict,
    notebook_filter: str = None,
    dry_run: bool = False
):
    """
    Migrate OneNote notebooks to Obsidian.

    Args:
        config: Configuration dictionary
        notebook_filter: Optional notebook name to filter
        dry_run: If True, don't actually write files
    """
    logger = logging.getLogger(__name__)

    try:
        migration_config = config.get('migration', {})
        vault_path = os.path.expanduser(
            migration_config.get('vault_path', './output/obsidian-vault')
        )

        print("\n" + "="*60)
        print("ONENOTE TO OBSIDIAN MIGRATION")
        print("="*60)
        print(f"\nVault path: {vault_path}")
        if dry_run:
            print("Mode: DRY RUN (no files will be written)")
        if notebook_filter:
            print(f"Filter: {notebook_filter}")
        print()

        # Initialize services
        logger.info("Initializing OneNote service...")
        onenote = OneNoteService()

        if not onenote.authenticate():
            print("\n Authentication failed")
            return

        # Initialize converter
        converter = ContentConverter({
            'image_folder': migration_config.get('attachments_folder', 'attachments'),
            'download_images': migration_config.get('download_images', True),
            'include_metadata': migration_config.get('include_metadata', True),
            'preserve_timestamps': migration_config.get('preserve_timestamps', True)
        })

        # Initialize writer
        writer = ObsidianWriter(
            vault_path=vault_path,
            onenote_service=onenote,
            config={
                'attachments_folder': migration_config.get('attachments_folder', 'attachments'),
                'create_index_files': migration_config.get('create_index_files', True),
                'preserve_timestamps': migration_config.get('preserve_timestamps', True),
                'skip_existing': migration_config.get('skip_existing', False),
                'dry_run': dry_run
            }
        )

        # Initialize vault
        if not writer.initialize_vault():
            print("\n Failed to initialize vault")
            return

        # Get notebooks
        logger.info("Fetching notebook structure...")
        print("Fetching notebook structure...")

        notebooks = onenote.get_all_notebooks_with_structure()

        if not notebooks:
            print("No notebooks found.")
            return

        # Filter if specified
        if notebook_filter:
            notebooks = [
                nb for nb in notebooks
                if notebook_filter.lower() in nb['displayName'].lower()
            ]
            if not notebooks:
                print(f"No notebooks matching '{notebook_filter}' found.")
                return

        print(f"\nMigrating {len(notebooks)} notebook(s)...\n")

        # Process each notebook
        for notebook in notebooks:
            print(f"\n Processing: {notebook['displayName']}")
            writer.write_notebook(notebook, converter)

        # Write migration log
        writer.write_migration_log()

        # Print summary
        print(writer.get_stats_summary())

        if dry_run:
            print("\nThis was a DRY RUN. No files were actually written.")
            print("Remove --dry-run to perform the actual migration.\n")
        else:
            print(f"\nMigration complete! Your Obsidian vault is at:")
            print(f"  {vault_path}")
            print("\nTo use with Obsidian:")
            print("1. Open Obsidian")
            print("2. Click 'Open folder as vault'")
            print(f"3. Select: {vault_path}")
            print()

    except Exception as e:
        logger.error(f"Migration error: {e}", exc_info=True)
        print(f"\n Error: {e}")


def validate_setup():
    """Validate that all services are properly configured."""
    print("\n" + "="*60)
    print("ONENOTE TO OBSIDIAN SETUP VALIDATION")
    print("="*60 + "\n")

    try:
        # Check environment variables
        print(" Checking environment variables...")

        client_id = os.getenv('AZURE_CLIENT_ID')
        if not client_id:
            print(" Missing AZURE_CLIENT_ID")
            print("\nTo configure Azure AD app:")
            print("1. Go to https://portal.azure.com")
            print("2. Navigate to Azure Active Directory > App registrations")
            print("3. Click 'New registration'")
            print("4. Name it 'OneNote Migration Tool'")
            print("5. Select 'Personal Microsoft accounts only' for personal OneNote")
            print("   Or 'Accounts in any organizational directory' for work/school")
            print("6. Set Redirect URI to 'http://localhost' (for device code flow)")
            print("7. Copy the Application (client) ID")
            print("\n8. Go to 'API permissions'")
            print("9. Add Microsoft Graph permissions:")
            print("   - Notes.Read (Delegated)")
            print("   - Notes.Read.All (Delegated)")
            print("   - User.Read (Delegated)")
            print("10. Grant admin consent if required")
            return False

        print(f" AZURE_CLIENT_ID: {client_id[:8]}...")

        tenant_id = os.getenv('AZURE_TENANT_ID', 'common')
        print(f" AZURE_TENANT_ID: {tenant_id}")

        # Test OneNote connection
        print("\n Testing OneNote connection...")

        onenote = OneNoteService()

        if onenote.validate_credentials():
            print(" OneNote connection successful!")

            # List notebooks
            notebooks = onenote.get_notebooks()
            print(f" Found {len(notebooks)} notebook(s)")

            for nb in notebooks[:3]:
                print(f"   - {nb['displayName']}")

            if len(notebooks) > 3:
                print(f"   ... and {len(notebooks) - 3} more")

        else:
            print(" OneNote connection failed")
            return False

        print("\n" + "="*60)
        print(" ALL VALIDATIONS PASSED!")
        print("="*60)

        print("\nNext steps:")
        print("1. Run: python src/migration_main.py --list")
        print("2. Run: python src/migration_main.py --migrate --dry-run")
        print("3. Run: python src/migration_main.py --migrate\n")

        return True

    except Exception as e:
        print(f"\n Validation failed: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='OneNote to Obsidian Migration Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Validate setup:
    python src/migration_main.py --validate

  List all notebooks:
    python src/migration_main.py --list

  Dry run migration (no files written):
    python src/migration_main.py --migrate --dry-run

  Migrate all notebooks:
    python src/migration_main.py --migrate

  Migrate specific notebook:
    python src/migration_main.py --migrate --notebook "My Notebook"

  Migrate to custom vault location:
    python src/migration_main.py --migrate --vault ~/Documents/MyVault
        """
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate setup and configuration'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available OneNote notebooks'
    )

    parser.add_argument(
        '--migrate',
        action='store_true',
        help='Perform the migration'
    )

    parser.add_argument(
        '--notebook',
        type=str,
        help='Filter to specific notebook name (partial match)'
    )

    parser.add_argument(
        '--vault',
        type=str,
        help='Path to Obsidian vault (overrides config)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without writing files'
    )

    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip pages that already exist in the vault'
    )

    args = parser.parse_args()

    # Change to project directory
    os.chdir(Path(__file__).parent.parent)

    # Load config
    config = load_config()

    # Setup logging
    setup_logging(config)

    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("Starting OneNote to Obsidian Migration Tool")
    logger.info("="*60)

    # Load environment
    load_environment()

    # Override config from args
    if args.vault:
        config.setdefault('migration', {})['vault_path'] = args.vault

    if args.skip_existing:
        config.setdefault('migration', {})['skip_existing'] = True

    if args.validate:
        if not validate_configuration():
            sys.exit(1)
        sys.exit(0 if validate_setup() else 1)

    elif args.list:
        if not validate_configuration():
            sys.exit(1)
        list_notebooks()

    elif args.migrate:
        if not validate_configuration():
            sys.exit(1)
        migrate_notebooks(
            config,
            notebook_filter=args.notebook,
            dry_run=args.dry_run
        )

    else:
        parser.print_help()
        print("\nQuick start:")
        print("  1. Set up Azure AD app and add AZURE_CLIENT_ID to .env")
        print("  2. Run: python src/migration_main.py --validate")
        print("  3. Run: python src/migration_main.py --migrate")


if __name__ == '__main__':
    main()
