# Utilities Directory

Standalone utility scripts and tools for automation and productivity.

## Available Utilities

### todoist_p2_label_updater.py
**Language:** Python
**Purpose:** Automated Todoist label management utility

**Description:**
Updates Todoist task labels based on priority levels. Useful for maintaining consistent labeling across projects and automating task organization workflows.

**Usage:**
```bash
cd utils
python todoist_p2_label_updater.py
```

**Configuration:**
- Requires Todoist API token
- Configure via environment variables or script parameters
- See script documentation for details

## Utility Guidelines

### What Belongs Here

Utilities are **standalone scripts or tools** that:
- Perform a specific, well-defined task
- Don't require complex project structure
- Can be run independently
- Are reusable across contexts

**Examples:**
- Data migration scripts
- Batch processing tools
- API automation scripts
- File conversion utilities
- System maintenance tools

### What Doesn't Belong Here

**Full applications** should go in `apps/`:
- Multi-file projects with dependencies
- Applications with persistent state
- Complex systems with multiple components
- Projects requiring dedicated documentation

**MCP servers** should go in `servers/`:
- Tools that expose MCP protocol interfaces
- Integration servers for AI assistants

## Adding New Utilities

### Single-File Utilities

For simple, standalone scripts:

```bash
# Create the utility file
touch utils/your_utility_name.py
# or
touch utils/your_utility_name.sh

# Make executable if needed
chmod +x utils/your_utility_name.sh
```

**Include in the file:**
- Docstring or header comment explaining purpose
- Usage instructions in comments
- Configuration documentation
- Error handling
- Example usage

### Multi-File Utilities

For utilities with dependencies:

```
utils/your-utility/
├── README.md              # Documentation
├── main.py or main.sh     # Entry point
├── requirements.txt       # Python dependencies (if needed)
├── .env.example          # Configuration template
└── lib/                  # Supporting modules
```

## Utility Template

### Python Utility Template

```python
#!/usr/bin/env python3
"""
Utility Name - Brief description

Usage:
    python utility_name.py [options]

Options:
    --option1    Description of option 1
    --option2    Description of option 2

Configuration:
    TODOIST_API_TOKEN    API token for Todoist
    # Add other env vars

Examples:
    python utility_name.py --option1 value

Author: Your Name
Created: YYYY-MM-DD
"""

import os
import sys

def main():
    """Main function."""
    # Implementation
    pass

if __name__ == "__main__":
    main()
```

### Bash Utility Template

```bash
#!/bin/bash
#
# Utility Name - Brief description
#
# Usage:
#   ./utility_name.sh [options]
#
# Options:
#   -o, --option1    Description of option 1
#   -v, --verbose    Enable verbose output
#
# Configuration:
#   Requires ENV_VAR to be set
#
# Examples:
#   ./utility_name.sh --option1 value
#
# Author: Your Name
# Created: YYYY-MM-DD

set -euo pipefail

# Main function
main() {
    # Implementation
    echo "Running utility..."
}

main "$@"
```

## Common Patterns

### API Integration Utilities

For utilities that interact with APIs:

1. **Authentication:**
   - Store API keys in environment variables
   - Use `.env` file for local development
   - Document required credentials

2. **Error Handling:**
   - Catch and log API errors
   - Provide clear error messages
   - Include retry logic for transient failures

3. **Rate Limiting:**
   - Respect API rate limits
   - Implement backoff strategies
   - Document API quotas

### Batch Processing Utilities

For utilities that process multiple items:

1. **Input Validation:**
   - Verify input files/data exist
   - Validate format and structure
   - Fail fast on invalid input

2. **Progress Reporting:**
   - Show progress for long operations
   - Log processed items
   - Report success/failure counts

3. **Idempotency:**
   - Safe to run multiple times
   - Skip already-processed items
   - Create checkpoints for resumption

### File Processing Utilities

For utilities that manipulate files:

1. **Backup:**
   - Create backups before modifications
   - Use timestamped backup names
   - Document backup location

2. **Validation:**
   - Check file permissions
   - Verify file formats
   - Handle missing files gracefully

3. **Atomic Operations:**
   - Write to temp file first
   - Move to final location on success
   - Clean up temp files on failure

## Development Best Practices

### Code Quality
- Follow language-specific style guides (PEP 8 for Python)
- Include type hints (Python 3.5+)
- Add docstrings to functions
- Keep functions focused and small

### Documentation
- Usage instructions in script header
- Configuration requirements
- Example commands
- Expected output format

### Error Handling
- Validate inputs
- Provide helpful error messages
- Exit with appropriate codes (0 = success, non-zero = error)
- Log errors for debugging

### Dependencies
- Minimize external dependencies
- Document all requirements
- Provide installation instructions
- Consider using standard library when possible

## Configuration Management

### Environment Variables

```python
import os

# Required configuration
API_TOKEN = os.environ.get("API_TOKEN")
if not API_TOKEN:
    raise ValueError("API_TOKEN environment variable required")

# Optional configuration with defaults
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "100"))
```

### Configuration Files

For utilities with complex configuration:

```python
import yaml

def load_config(config_path="config.yaml"):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

config = load_config()
```

### Command-Line Arguments

```python
import argparse

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Utility description")
    parser.add_argument("--input", required=True, help="Input file path")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    return parser.parse_args()

args = parse_args()
```

## Testing Utilities

### Manual Testing

1. **Test with valid input:**
   ```bash
   python utility.py --input valid_data.txt
   ```

2. **Test error handling:**
   ```bash
   python utility.py --input nonexistent.txt
   python utility.py  # Missing required argument
   ```

3. **Test edge cases:**
   - Empty input
   - Very large input
   - Special characters
   - Network failures (for API utilities)

### Automated Testing

For complex utilities, consider adding tests:

```python
# test_utility.py
import unittest
from utility import process_data

class TestUtility(unittest.TestCase):
    def test_valid_input(self):
        result = process_data("valid input")
        self.assertEqual(result, expected_output)

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            process_data("invalid input")

if __name__ == "__main__":
    unittest.main()
```

## Common Use Cases

### Todoist Automation
- Label management
- Bulk task updates
- Project organization
- Priority adjustments

### YNAB Automation
- Transaction categorization
- Budget report generation
- Account reconciliation
- Data export/import

### File Management
- Batch file renaming
- Format conversion
- Backup creation
- Archive maintenance

### Data Processing
- CSV manipulation
- JSON transformation
- Log analysis
- Report generation

## Scheduling Utilities

### Cron Jobs (macOS/Linux)

```bash
# Edit crontab
crontab -e

# Run utility daily at 9 AM
0 9 * * * cd /path/to/workspace/utils && python utility.py

# Run weekly on Monday at 8 PM
0 20 * * 1 /path/to/workspace/utils/utility.sh
```

### launchd (macOS)

Create a plist file for more complex scheduling:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yourname.utility</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/utils/utility.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
</dict>
</plist>
```

## Troubleshooting

### Permission Issues
```bash
# Make script executable
chmod +x utility.sh

# Check file permissions
ls -la utility.py
```

### Import Errors (Python)
```bash
# Check Python version
python --version

# Install dependencies
pip install -r requirements.txt

# Verify module installation
pip list
```

### Environment Variables Not Set
```bash
# Check if variable is set
echo $API_TOKEN

# Set temporarily
export API_TOKEN="your_token"

# Set permanently (add to ~/.bashrc or ~/.zshrc)
echo 'export API_TOKEN="your_token"' >> ~/.bashrc
```

## Resources

### Related Documentation
- [Main Workspace](../CLAUDE.md)
- [Applications](../apps/CLAUDE.md)
- [MCP Servers](../servers/CLAUDE.md)

### Python Resources
- [Python Official Documentation](https://docs.python.org/)
- [PEP 8 Style Guide](https://pep8.org/)
- [argparse Documentation](https://docs.python.org/3/library/argparse.html)

### Bash Resources
- [Bash Reference Manual](https://www.gnu.org/software/bash/manual/)
- [ShellCheck](https://www.shellcheck.net/) - Shell script analysis tool

### API Documentation
- [Todoist API](https://developer.todoist.com/)
- [YNAB API](https://api.ynab.com/)

---

**Directory Purpose:** Standalone utility scripts and automation tools
**Last Updated:** 2025-11-16
