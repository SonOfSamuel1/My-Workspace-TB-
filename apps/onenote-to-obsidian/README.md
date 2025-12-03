# OneNote to Obsidian Migration Tool

A Python tool to migrate your Microsoft OneNote notebooks to an Obsidian vault, converting content to Markdown format while preserving structure, images, and metadata.

## Features

- **Full Notebook Migration** - Migrate all notebooks or select specific ones
- **Structure Preservation** - Maintains notebook/section/page hierarchy as folders
- **Content Conversion** - Converts OneNote HTML to clean Obsidian-compatible Markdown
- **Image Handling** - Downloads and embeds images with Obsidian syntax
- **Metadata Preservation** - Optional YAML frontmatter with creation dates
- **Internal Links** - Converts OneNote links to Obsidian wiki links
- **Tables Support** - Converts HTML tables to Markdown tables
- **Dry Run Mode** - Preview migration without writing files
- **Progress Tracking** - Detailed logging and migration statistics

## Quick Start

```bash
# Navigate to project
cd apps/onenote-to-obsidian

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Configure Azure credentials (see Setup section)
# Edit .env with your AZURE_CLIENT_ID

# Validate setup
python src/migration_main.py --validate

# List your notebooks
python src/migration_main.py --list

# Dry run (see what will be migrated)
python src/migration_main.py --migrate --dry-run

# Perform migration
python src/migration_main.py --migrate
```

## Setup

### Prerequisites

1. **Python 3.8+** installed
2. **Microsoft account** with OneNote notebooks
3. **Azure AD application** for API access (free)

### Step 1: Create Azure AD Application

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Configure the application:
   - **Name**: `OneNote Migration Tool`
   - **Supported account types**:
     - For personal OneNote: `Personal Microsoft accounts only`
     - For work/school: `Accounts in any organizational directory and personal Microsoft accounts`
   - **Redirect URI**: Leave blank (we use device code flow)
5. Click **Register**
6. Copy the **Application (client) ID**

### Step 2: Configure API Permissions

1. In your app registration, go to **API permissions**
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Select **Delegated permissions**
5. Add these permissions:
   - `Notes.Read` - Read user notebooks
   - `Notes.Read.All` - Read all notebooks user has access to
   - `User.Read` - Sign in and read user profile
6. Click **Add permissions**
7. If using a work/school account, click **Grant admin consent** (may require admin)

### Step 3: Configure Environment

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Azure Client ID:
   ```
   AZURE_CLIENT_ID=your-application-client-id
   AZURE_TENANT_ID=common
   ```

   **Note**: Use `common` for personal accounts, or your organization's tenant ID for work/school accounts.

### Step 4: Validate Setup

```bash
python src/migration_main.py --validate
```

This will:
- Check your configuration
- Authenticate with Microsoft (opens browser for device code)
- List your accessible notebooks

## Usage

### List Notebooks

See all notebooks available for migration:

```bash
python src/migration_main.py --list
```

### Migrate All Notebooks

```bash
python src/migration_main.py --migrate
```

### Migrate Specific Notebook

```bash
python src/migration_main.py --migrate --notebook "My Notebook"
```

### Dry Run (Preview)

See what would be migrated without writing files:

```bash
python src/migration_main.py --migrate --dry-run
```

### Custom Vault Location

```bash
python src/migration_main.py --migrate --vault ~/Documents/MyObsidianVault
```

### Skip Existing Pages

Don't overwrite pages that already exist:

```bash
python src/migration_main.py --migrate --skip-existing
```

## Configuration

Edit `config.yaml` to customize the migration:

```yaml
migration:
  # Output vault location
  vault_path: "./output/obsidian-vault"

  # Attachments folder name
  attachments_folder: "attachments"

  # Create index files for notebooks/sections
  create_index_files: true

  # Preserve original timestamps
  preserve_timestamps: true

  # Skip existing pages
  skip_existing: false

  # Download embedded images
  download_images: true

  # Include YAML frontmatter
  include_metadata: true
```

## Project Structure

```
onenote-to-obsidian/
├── src/
│   ├── migration_main.py     # Main entry point and CLI
│   ├── onenote_service.py    # Microsoft Graph API integration
│   ├── content_converter.py  # HTML to Markdown conversion
│   └── obsidian_writer.py    # Vault file management
├── output/                    # Default vault output location
├── logs/                      # Migration logs
├── credentials/               # Token cache (auto-created)
├── config.yaml               # Configuration
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
└── README.md                 # This file
```

## Output Structure

The tool creates an Obsidian vault with this structure:

```
obsidian-vault/
├── .obsidian/                    # Obsidian config folder
├── attachments/                  # All images and files
├── Notebook 1/
│   ├── Notebook 1.md            # Notebook index
│   ├── Section A/
│   │   ├── Section A.md         # Section index
│   │   ├── Page 1.md
│   │   └── Page 2.md
│   └── Section B/
│       └── ...
├── Notebook 2/
│   └── ...
└── _migration_log.md            # Migration statistics
```

## Markdown Conversion

The tool converts OneNote content to Obsidian-compatible Markdown:

| OneNote Element | Obsidian Output |
|----------------|-----------------|
| Headings | `# Heading 1`, `## Heading 2`, etc. |
| Bold | `**text**` |
| Italic | `*text*` |
| Strikethrough | `~~text~~` |
| Links | `[text](url)` |
| Internal links | `[[Page Name]]` |
| Images | `![[attachments/image.png]]` |
| Tables | Markdown tables |
| Code | `` `code` `` or code blocks |
| Lists | `- item` or `1. item` |
| Blockquotes | `> quote` |

## Frontmatter

Each page includes YAML frontmatter with metadata:

```yaml
---
title: "Page Title"
created: 2024-01-15T10:30:00Z
modified: 2024-02-20T14:45:00Z
source: OneNote
onenote_id: 0-abc123def456
---
```

## Troubleshooting

### Authentication Issues

**"AADSTS7000218: Invalid request - no client_id"**
- Ensure `AZURE_CLIENT_ID` is set in your `.env` file
- Check the client ID is correct (no extra spaces or quotes)

**"AADSTS50011: Reply URL does not match"**
- This tool uses device code flow, no redirect URI needed
- If you added one, try removing it from Azure portal

**"Consent Required" or "Need Admin Approval"**
- For personal accounts: You'll be prompted to consent
- For work/school: Admin may need to grant consent first

### Migration Issues

**"No notebooks found"**
- Verify you have notebooks in your OneNote account
- Check you're signing in with the correct account
- Ensure API permissions are granted

**Images not downloading**
- Check your internet connection
- Some images may require re-authentication
- Try running with `--skip-existing` to retry failed pages

**Timeout errors**
- Large notebooks may take time
- Try migrating one notebook at a time with `--notebook`

### Common Fixes

1. **Clear token cache**:
   ```bash
   rm -rf credentials/token_cache.json
   ```

2. **Check logs**:
   ```bash
   tail -f logs/migration.log
   ```

3. **Verify permissions in Azure**:
   - Go to Azure Portal > Your App > API permissions
   - Ensure all permissions have green checkmarks

## Limitations

- **Ink/drawing content**: OneNote ink drawings are not fully supported
- **Embedded files**: Some file types may not migrate
- **OneNote for Windows 10**: Some features from the Windows 10 app may not be accessible via API
- **Rate limits**: Microsoft Graph API has rate limits; large migrations may need pauses

## Development

### Adding New Features

1. **Content conversion**: Modify `content_converter.py`
2. **API access**: Modify `onenote_service.py`
3. **File output**: Modify `obsidian_writer.py`
4. **CLI options**: Modify `migration_main.py`

### Running Tests

```bash
# Run validation
python src/migration_main.py --validate

# Test with dry run
python src/migration_main.py --migrate --dry-run
```

## Security Notes

- **Token storage**: Authentication tokens are cached locally in `credentials/`
- **Never commit**: The `.env` file and `credentials/` folder should never be committed
- **Revoke access**: You can revoke the app's access from your Microsoft account settings

## License

Part of the My Workspace monorepo. See repository LICENSE.

## Contact

Repository Owner: Terrance Brandon
GitHub: @SonOfSamuel1

---

**Last Updated:** 2025-12-03
**Version:** 1.0.0
**Status:** Ready for Use
