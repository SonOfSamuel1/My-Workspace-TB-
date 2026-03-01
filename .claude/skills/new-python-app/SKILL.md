---
description: Scaffold a new Python application following workspace conventions
disable-model-invocation: true
---

# Create New Python Application

## Directory Structure

```
apps/<app-name>/
├── src/
│   ├── __init__.py
│   └── <name>_main.py          # Entry point with --validate/--generate flags
├── credentials/
│   └── credentials.json         # Google OAuth2 creds (gitignored)
├── docs/                        # App-specific documentation
├── scripts/
│   └── deploy-lambda-zip.sh     # If Lambda-deployed
├── requirements.txt
├── .env                         # Local config (gitignored)
├── .env.example                 # Config template (committed)
├── config.yaml                  # Optional YAML config
├── .gitignore
└── README.md
```

## Entry Point Convention

All Python apps use `src/<name>_main.py` with standard CLI flags:

```python
#!/usr/bin/env python3
"""<App Name> - Brief description."""

import argparse
import os
import sys

def validate_config():
    """Validate all configuration and credentials."""
    # Check env vars, API tokens, file paths
    print("Configuration valid.")

def generate():
    """Run the main application logic."""
    # Main business logic here
    pass

def main():
    parser = argparse.ArgumentParser(description="<App Name>")
    parser.add_argument("--validate", action="store_true", help="Validate configuration")
    parser.add_argument("--generate", action="store_true", help="Run generation/report")
    args = parser.parse_args()

    if args.validate:
        validate_config()
    elif args.generate:
        generate()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
```

## Naming Conventions

- **Directory**: `apps/<kebab-case-name>/` (e.g., `apps/weekly-budget-report/`)
- **Entry point**: `src/<snake_case_name>_main.py` (e.g.,
  `src/weekly_budget_main.py`)
- **Module files**: snake_case (e.g., `src/email_sender.py`)

## Google API Credentials

For apps using Google APIs (Calendar, Docs, Gmail):

1. Place OAuth2 credentials at `credentials/credentials.json`
2. Token file auto-generated as `credentials/token.pickle`
3. Add to `.gitignore`:

   ```
   credentials/
   *.pickle
   ```

## Pre-commit Hooks (automatic)

Python files in `apps/` are automatically checked on commit:

- **black** — code formatting
- **isort** — import sorting
- **flake8** — linting (max-line-length=127)
- **bandit** — security scanning

## .env.example template

```bash
# API Configuration
API_TOKEN=your_token_here
DEBUG=false

# Google API (if applicable)
GOOGLE_CREDENTIALS_PATH=credentials/credentials.json

# AWS (if Lambda-deployed)
AWS_REGION=us-east-1
```

## Quick start after scaffolding

```bash
cd apps/<app-name>
pip install -r requirements.txt
python src/<name>_main.py --validate
python src/<name>_main.py --generate
```
