# My Workspace - Personal Development Monorepo

A unified workspace for personal automation, productivity systems, and AI integration projects. This monorepo consolidates applications, MCP (Model Context Protocol) servers, utilities, and documentation.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5.x-blue.svg)](https://www.typescriptlang.org/)
[![MCP](https://img.shields.io/badge/MCP-1.0.4-green.svg)](https://modelcontextprotocol.io/)

## Overview

This repository brings together:

- **Applications** - Full-featured automation systems
- **MCP Servers** - AI assistant integrations for Gmail, Todoist, and YNAB
- **Utilities** - Standalone scripts for productivity workflows
- **Documentation** - Comprehensive guides and reference materials

## Quick Start

### Prerequisites

- **Node.js** 18+ (for MCP servers)
- **Python** 3.x (for applications and utilities)
- **Git** for version control
- **AWS CLI** (optional, for cloud deployments)

### Installation

```bash
# Clone the repository
git clone https://github.com/SonOfSamuel1/My-Workspace-TB-.git
cd My-Workspace-TB-

# Install MCP servers
cd servers/todoist-mcp-server && npm install && npm run build && cd ../..
cd servers/ynab-mcp-server && npm install && npm run build && cd ../..
cd servers/gmail-mcp-server && npm install && npm run build && cd ../..

# Install Python applications
cd apps/love-brittany-tracker && pip install -r requirements.txt && cd ../..
```

## Repository Structure

```
My-Workspace-TB-/
├── apps/                          # Full applications
│   ├── autonomous-email-assistant/ # AI-powered email management system
│   └── love-brittany-tracker/    # Relationship tracking automation
├── servers/                       # MCP server implementations
│   ├── gmail-mcp-server/         # Gmail integration for AI assistants
│   ├── todoist-mcp-server/       # Todoist task management
│   └── ynab-mcp-server/          # YNAB budget & transactions
├── utils/                         # Standalone utility scripts
│   └── todoist_p2_label_updater.py
├── docs/                          # Centralized documentation
└── CLAUDE.md                      # Detailed workspace guide
```

## Projects

### Applications

#### Autonomous Email Assistant
AI-powered email management system with Claude Code CLI and Gmail MCP integration.

- **Features**: 4-tier email classification, autonomous responses, OpenRouter reasoning models, web automation via Playwright
- **Modes**: Executive Assistant (hourly processing), Email Agent (autonomous actions)
- **Deployment**: GitHub Actions, AWS Lambda
- **Documentation**: [apps/autonomous-email-assistant/README.md](apps/autonomous-email-assistant/README.md)

#### Love Brittany Tracker
Automated relationship tracking system with bi-weekly HTML reports.

- **Features**: 9 activity categories, Google Calendar/Docs integration, Toggl tracking
- **Deployment**: AWS Lambda, Render, Docker
- **Documentation**: [apps/love-brittany-tracker/README.md](apps/love-brittany-tracker/README.md)

### MCP Servers

#### Gmail MCP Server
Enables AI assistants to read, search, and send Gmail messages.

- **Tools**: List messages, read content, send emails, search
- **Documentation**: [servers/gmail-mcp-server/README.md](servers/gmail-mcp-server/README.md)

#### Todoist MCP Server
Full Todoist task management integration.

- **Tools**: Create/update/complete tasks, manage projects, labels, filters
- **Documentation**: [servers/todoist-mcp-server/README.md](servers/todoist-mcp-server/README.md)

#### YNAB MCP Server
Budget and transaction management for You Need A Budget.

- **Tools**: Manage budgets, accounts, transactions, categories
- **Documentation**: [servers/ynab-mcp-server/README.md](servers/ynab-mcp-server/README.md)

### Utilities

- **todoist_p2_label_updater.py** - Automated Todoist P2 label management

## Technology Stack

| Category | Technologies |
|----------|-------------|
| **Languages** | Python 3.x, TypeScript, Bash |
| **APIs** | Google (Calendar, Docs, Gmail), Todoist, YNAB, Toggl |
| **Infrastructure** | AWS Lambda, EventBridge, Parameter Store |
| **Frameworks** | Model Context Protocol (MCP), FastMCP |

## Configuration

### Environment Variables

Each project uses `.env` files for configuration. Example files (`.env.example`) are provided in each project directory.

### MCP Server Setup

MCP servers can be configured in Claude Desktop or Claude Code:

```json
{
  "mcpServers": {
    "todoist": {
      "command": "node",
      "args": ["${workspaceFolder}/servers/todoist-mcp-server/dist/index.js"],
      "env": {
        "TODOIST_API_TOKEN": "your-token-here"
      }
    }
  }
}
```

See [docs/mcp-server-configurator.md](docs/mcp-server-configurator.md) for detailed setup.

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Comprehensive workspace guide (for AI assistants)
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines
- **[SECURITY.md](SECURITY.md)** - Security policies
- **Project-specific docs** - See individual README files

## Development

### Running Tests

```bash
# MCP servers
cd servers/todoist-mcp-server && npm test && cd ../..

# Python applications
cd apps/love-brittany-tracker && pytest && cd ../..
```

### Building Projects

```bash
# Build all MCP servers
npm run build --workspaces

# Build individual server
cd servers/todoist-mcp-server && npm run build
```

## Monorepo Benefits

- **Unified History** - Complete git history preserved for all projects
- **Shared Resources** - Common documentation patterns and utilities
- **Simplified Development** - Single clone for all related projects
- **Consistent Standards** - Standardized tooling and practices

## Git History

This monorepo preserves complete history from merged repositories:
- Original My Workspace repository
- Love Brittany tracker (merged via git subtree on 2025-11-16)
- Autonomous Email Assistant (merged via git subtree on 2025-11-18)

View complete history: `git log --all --graph`

## Contributing

This is a personal workspace, but follows professional standards:

1. Keep projects isolated in their directories
2. Maintain comprehensive documentation
3. Follow existing naming conventions
4. Preserve git history when adding projects

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## Security

- Never commit `.env` files or credentials
- Use AWS Parameter Store for cloud secrets
- Report security issues via [SECURITY.md](SECURITY.md)

## License

Individual projects may have their own licenses. See project directories for details.

## Contact

**Terrance Brandon**
GitHub: [@SonOfSamuel1](https://github.com/SonOfSamuel1)

---

**Last Updated**: 2025-11-18
**Monorepo Version**: 1.0

For detailed technical documentation optimized for AI assistants, see [CLAUDE.md](CLAUDE.md).
