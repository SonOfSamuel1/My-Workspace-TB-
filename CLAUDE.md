# My Workspace - Personal Development Monorepo

A unified workspace containing applications, MCP servers, utilities, and documentation for personal automation and productivity systems.

## Repository Structure

```
My Workspace/
├── apps/              # Full applications and automation systems
├── servers/           # MCP (Model Context Protocol) server implementations
├── utils/             # Standalone utility scripts and tools
├── docs/              # Centralized documentation and guides
└── CLAUDE.md          # This file
```

## Quick Navigation

### Applications (`apps/`)
- **[love-brittany-tracker](apps/love-brittany-tracker/README.md)** - Relationship tracking automation with bi-weekly reporting
- **[love-kaelin-tracker](apps/love-kaelin-tracker/README.md)** - Father-daughter development tracking with weekly reporting

### MCP Servers (`servers/`)
- **[gmail-mcp-server](servers/gmail-mcp-server/README.md)** - Gmail integration for AI assistants
- **[google-docs-mcp-server](servers/google-docs-mcp-server/README.md)** - Google Docs integration for creating, reading, and editing documents
- **[todoist-mcp-server](servers/todoist-mcp-server/README.md)** - Todoist task management integration
- **[ynab-mcp-server](servers/ynab-mcp-server/README.md)** - YNAB budget and transaction management

### Utilities (`utils/`)
- **todoist_p2_label_updater.py** - Automated Todoist label management

### Documentation (`docs/`)
- Technical guides, troubleshooting docs, and reference materials
- Financial ledgers and business documentation
- MCP server configuration guides

## Technology Stack

### Languages
- Python 3.x (Applications and utilities)
- TypeScript/Node.js (MCP servers)
- Bash (Automation scripts)

### Key Dependencies
- Google APIs (Calendar, Docs, Gmail)
- Todoist REST API v2
- YNAB API
- Model Context Protocol (MCP)

### Infrastructure
- AWS Lambda (Serverless functions)
- AWS Parameter Store (Secret management)
- AWS EventBridge (Scheduled triggers)

## Getting Started

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/SonOfSamuel1/My-Workspace-TB-.git
   cd "My Workspace"
   ```

2. **Set up applications** (see `apps/` directory READMEs)

3. **Configure MCP servers** (see `servers/` directory READMEs)

4. **Install Python utilities:**
   ```bash
   cd utils
   # Follow individual utility documentation
   ```

### Working with Applications

Each application in `apps/` is self-contained with its own:
- Dependencies (`requirements.txt`, `package.json`)
- Configuration files
- Documentation
- Setup scripts

Navigate to the specific application directory and follow its README.

### Working with MCP Servers

MCP servers enable AI assistants to interact with external services. Each server in `servers/` provides:
- API integration tools
- Configuration templates
- Setup instructions
- Usage examples

See individual server READMEs for configuration details.

## Development Workflow

### Adding New Projects

1. **Applications**: Place in `apps/<project-name>/`
2. **MCP Servers**: Place in `servers/<server-name>/`
3. **Utilities**: Place in `utils/`
4. **Documentation**: Place in `docs/`

### Git History

This monorepo preserves complete git history from all merged repositories:
- Original My Workspace repository
- Love Brittany relationship tracker (merged via git subtree)

Use `git log --all --graph` to view the complete history.

### Commit Standards

Commits follow the pattern:
- Clear, descriptive messages
- Context about what and why
- Co-authored with Claude Code when applicable

## Common Tasks

### Run Love Brittany Tracker
```bash
cd apps/love-brittany-tracker
python src/relationship_main.py --generate
```

### Run Love Kaelin Tracker
```bash
cd apps/love-kaelin-tracker
python src/kaelin_main.py --generate
```

### Build MCP Servers
```bash
cd servers/todoist-mcp-server
npm install
npm run build
```

### Update Todoist Labels
```bash
cd utils
python todoist_p2_label_updater.py
```

## Configuration Files

### Root Level
- `.mcp.json` - MCP server registry for Claude Code
- `.claude/` - Claude Code configuration

### Application Level
- Each app has its own `.env`, `config.yaml`, or similar
- Credential files stored in app-specific directories
- See individual READMEs for details

## Security Notes

### Credentials
- Never commit `.env` files or credentials
- Use `.gitignore` to exclude sensitive files
- AWS Parameter Store for cloud credentials
- Local credential files for development

### API Keys
- Todoist: Personal access tokens
- YNAB: Personal access tokens
- Google: OAuth2 credentials
- Store securely, never in version control

## Documentation

### Application Docs
- Located in respective `apps/<app-name>/docs/` directories
- Include setup guides, troubleshooting, and usage examples

### Workspace Docs
- Located in `docs/` at root level
- Technical guides, financial documents, reference materials

### README Files
- Each project has its own README.md
- Contains quick start, features, and configuration

## Monorepo Benefits

### Unified History
- All projects tracked in single repository
- Easy cross-project refactoring
- Simplified dependency management

### Shared Resources
- Common documentation patterns
- Reusable utilities
- Centralized credential management

### Simplified Development
- Single clone for all projects
- Easier to maintain consistency
- Better visibility into related systems

## Contributing

This is a personal workspace, but organizational principles include:
- Keep projects isolated in their directories
- Maintain clear documentation
- Preserve git history when adding projects
- Follow existing naming conventions

## Project Origins

### Merged Projects
- **Love Brittany Tracker** - Merged from standalone repository on 2025-11-16
  - Complete commit history preserved
  - Originally: App-Personal-Love-Brittany-Reporting

### Native Projects
- **MCP Servers** - Developed directly in this workspace
- **Utilities** - Created for workspace automation

## Support and Troubleshooting

### Application Issues
- Check application-specific documentation in `apps/<app-name>/docs/`
- Review logs (typically in `apps/<app-name>/logs/`)
- Run validation scripts if available

### MCP Server Issues
- Verify API tokens in `.env` files
- Check server build: `npm run build`
- Review Claude Code/Desktop configuration
- See `docs/mcp-server-configurator.md`

### General Issues
- Check git history: `git log`
- Review recent commits: `git log --oneline -10`
- Examine backups if needed

## License

Projects may have individual licenses - see respective LICENSE files in project directories.

## Contact

Repository Owner: Terrance Brandon
GitHub: @SonOfSamuel1

---

**Last Updated:** 2025-11-17
**Repository Structure Version:** 1.0
