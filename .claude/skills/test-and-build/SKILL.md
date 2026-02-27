---
description:
  Reference for all build, test, format, and clean commands in this workspace
disable-model-invocation: true
---

# Build, Test & Format Commands

## Root Level (npm workspaces)

```bash
npm run build                    # Build all workspaces (servers + email-assistant)
npm run build:servers            # Build all MCP servers only
npm test                         # Run tests across all workspaces
npm run test:servers             # Run MCP server tests only
npm run format                   # Format all TS/JS/JSON/MD files with Prettier
npm run format:check             # Check formatting without changes
npm run clean                    # Remove all node_modules and dist folders
```

## MCP Servers (TypeScript)

```bash
cd servers/<server-name>
npm install
npm run build                    # Compile TypeScript to dist/
npm run watch                    # Watch mode for development
npm run dev                      # Build and run server
npm start                        # Run compiled server
```

Build a specific server from root:

```bash
npm run build --workspace=servers/<server-name>
```

After building, restart Claude Code/Desktop to pick up changes.

## Python Applications

```bash
cd apps/<app-name>
pip install -r requirements.txt
python src/<main>.py --validate  # Validate configuration only
python src/<main>.py --generate  # Run full generation/report
```

## Email Assistant

```bash
npm run email-assistant:test         # Run Jest tests
npm run email-assistant:agent:start  # Start email agent
npm run email-assistant:agent:test   # Test email agent

# Or directly:
cd apps/autonomous-email-assistant
npm test                             # Run Jest tests
npm run test:coverage               # Coverage report
```

## Pre-commit Hooks

Runs automatically on `git commit`:

**Python** (`apps/`, `utils/`): black, isort, flake8 (max-line-length=127),
bandit **TypeScript/JS** (`servers/`): prettier

## Lambda Deployment

```bash
cd apps/<app-name>
./scripts/deploy-lambda-zip.sh
```
