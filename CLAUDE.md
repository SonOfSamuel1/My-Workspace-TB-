# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

### Root Level (npm workspaces)
```bash
npm run build                    # Build all workspaces (servers + email-assistant)
npm run build:servers            # Build all MCP servers only
npm test                         # Run tests across all workspaces
npm run test:servers             # Run MCP server tests only
npm run format                   # Format all TS/JS/JSON/MD files with Prettier
npm run format:check             # Check formatting without changes
npm run clean                    # Remove all node_modules and dist folders
```

### MCP Servers (TypeScript)
```bash
cd servers/<server-name>
npm install
npm run build                    # Compile TypeScript to dist/
npm run watch                    # Watch mode for development
npm run dev                      # Build and run server
npm start                        # Run compiled server
```

### Python Applications
```bash
cd apps/<app-name>
pip install -r requirements.txt
python src/<main>.py --validate  # Validate configuration
python src/<main>.py --generate  # Run generation/report
```

### Autonomous Email Assistant
```bash
npm run email-assistant:test         # Run email assistant tests
npm run email-assistant:agent:start  # Start email agent
npm run email-assistant:agent:test   # Test email agent
```

## Architecture

### Monorepo Structure
- **apps/**: Self-contained applications (Python automation systems, Node.js tools)
- **servers/**: MCP (Model Context Protocol) servers (TypeScript/Node.js)
- **utils/**: Standalone utility scripts
- **docs/**: Workspace-level documentation

### Application Patterns

**Python Applications** (love-brittany-tracker, weekly-budget-report, ynab-transaction-reviewer):
- Entry point: `src/<name>_main.py`
- Google API credentials: `credentials/credentials.json`
- Config: `.env` or `config.yaml`
- AWS Lambda deployment via `scripts/deploy-lambda-zip.sh`

**MCP Servers** (TypeScript):
- Single file: `src/index.ts`
- Compiled output: `dist/index.js`
- Registered in `.mcp.json` or Claude Desktop config
- Uses `@modelcontextprotocol/sdk`

**Node.js Applications** (autonomous-email-assistant, ynab-transaction-reviewer/web):
- Jest for testing
- Often deployed to AWS Lambda or have Next.js web components

### Key Configuration Files
- `.mcp.json` - MCP server registry for Claude Code
- `.pre-commit-config.yaml` - Git hooks (black, isort, flake8 for Python; prettier for TS/JS)
- `.lintstagedrc.json` - Staged file formatting
- `package.json` - npm workspaces config

### Pre-commit Hooks
Python files in `apps/` and `utils/` are automatically formatted with:
- black (formatting)
- isort (import sorting)
- flake8 (linting, max-line-length=127)
- bandit (security)

TypeScript/JS files in `servers/` use prettier.

## Testing

### MCP Servers
```bash
# Build first, then restart Claude Code/Desktop to test
npm run build --workspace=servers/ynab-mcp-server
# Test by asking Claude to use the server's tools
```

### Python Applications
Most Python apps have `--validate` flags to test configuration without running full operations.

### Email Assistant
```bash
cd apps/autonomous-email-assistant
npm test                         # Run Jest tests
npm run test:coverage           # Coverage report
```

## AWS Lambda Deployment

Python applications with Lambda deployment have:
```
app/
├── lambda_handler.py           # Lambda entry point
├── scripts/deploy-lambda-zip.sh
└── requirements-lambda.txt     # Lambda-specific deps
```

Deploy: `./scripts/deploy-lambda-zip.sh`

## MCP Server Development

Template for new MCP servers:
```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server({ name: "your-server", version: "1.0.0" }, {
  capabilities: { tools: {} }
});

// Register tools with server.setRequestHandler()
const transport = new StdioServerTransport();
await server.connect(transport);
```

tsconfig.json pattern:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "moduleResolution": "Node16",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true
  }
}
```

## Commit Conventions

Commits in this repo are typically co-authored with Claude Code. When committing:
- Clear, descriptive messages focusing on what and why
- Include co-author footer for Claude-assisted commits
