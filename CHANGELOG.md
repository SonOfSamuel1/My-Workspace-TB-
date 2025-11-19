# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive repository improvements and infrastructure setup
- Root-level `.gitignore` for workspace-wide patterns
- Root-level `README.md` for GitHub discoverability
- Root-level `LICENSE` (MIT) for workspace licensing
- Root-level `package.json` for monorepo management with npm workspaces
- Complete testing infrastructure:
  - Vitest configuration for all MCP servers
  - Pytest configuration for Python applications
  - Example test files for all projects
- GitHub Actions CI/CD workflows:
  - MCP server testing workflow
  - Python application testing workflow
  - Linting workflow (TypeScript, Python, Markdown)
  - Security scanning workflow (npm audit, safety, TruffleHog, CodeQL)
- Pre-commit hooks configuration:
  - `.pre-commit-config.yaml` for Python projects
  - Husky hooks for JavaScript/TypeScript
  - Lint-staged for incremental linting
  - Secret detection with detect-secrets
  - Code formatting with Black, Prettier
  - Security scanning with Bandit
- Renovate configuration for automated dependency management
- Documentation files:
  - `CONTRIBUTING.md` with comprehensive contribution guidelines
  - `SECURITY.md` with security policies and best practices
  - `CHANGELOG.md` (this file)
- Missing LICENSE files for:
  - Gmail MCP Server
  - Love Brittany Tracker application
- `.env.example` for Gmail MCP Server
- `.mcp.json` configuration with all three MCP servers registered

### Changed
- Secured exposed YNAB API key in `.claude/mcp_config.json` (now uses environment variables)
- Updated `.claude/mcp_config.json` to use workspace-relative paths
- Enhanced all MCP server `package.json` files with test scripts and dependencies

### Fixed
- Security: Removed hardcoded API key from `.claude/mcp_config.json`

## [1.0.0] - 2025-11-16

### Added
- Initial monorepo structure with hierarchical organization
- Applications directory (`apps/`)
  - Love Brittany Tracker with complete codebase and documentation
- MCP Servers directory (`servers/`)
  - Todoist MCP Server (v1.0.0)
  - YNAB MCP Server (v1.0.0)
  - Gmail MCP Server (v1.0.0)
- Utilities directory (`utils/`)
  - Todoist P2 label updater script
- Documentation directory (`docs/`)
  - MCP server configuration guide
  - YNAB troubleshooting guide
  - Self-employment ledger
- Hierarchical CLAUDE.md documentation structure:
  - Root CLAUDE.md with workspace overview
  - Apps CLAUDE.md with application standards
  - Servers CLAUDE.md with MCP development guide
  - Utils CLAUDE.md with utility development patterns
  - Docs CLAUDE.md with documentation standards
- Monorepo merge report documenting repository consolidation

### Changed
- Reorganized from standalone repositories into unified monorepo structure
- Preserved complete git history from all merged repositories
- Standardized directory structure across all projects

## Love Brittany Tracker - [1.0.0] - 2025-11-16

### Added
- Bi-weekly relationship tracking automation
- Google Calendar integration for activity tracking
- Google Docs report generation with HTML formatting
- Email delivery via Gmail API
- Toggl time tracking integration
- 9 activity categories with configurable tracking
- AWS Lambda deployment support
- Render deployment support
- Docker containerization
- Comprehensive documentation (16+ markdown files)
- Deployment scripts and guides

## MCP Servers - [1.0.0] - 2025-11-16

### Todoist MCP Server
- Task creation and management
- Project organization
- Label and filter support
- Due date handling
- Priority levels
- Comments and collaboration

### YNAB MCP Server
- Budget retrieval and management
- Account operations
- Transaction creation and updates
- Category management
- Payee handling
- Bulk operations support

### Gmail MCP Server
- Message listing and retrieval
- Email sending with CC/BCC
- Advanced search with Gmail syntax
- Label management
- Thread operations
- Mark as read/unread
- Move to trash

## Infrastructure - [1.0.0] - 2025-11-16

### Added
- AWS Lambda deployment capabilities
- AWS Parameter Store integration for secrets
- AWS EventBridge scheduling support
- Render deployment configurations
- Docker containerization support

## [Pre-Monorepo] - Before 2025-11-16

### Individual Projects
- Love Brittany Tracker developed as standalone application
- MCP servers created for AI assistant integration
- Utility scripts developed for personal automation
- Documentation accumulated across projects

---

## Legend

- **Added**: New features or capabilities
- **Changed**: Changes to existing functionality
- **Deprecated**: Features that will be removed in future versions
- **Removed**: Features that have been removed
- **Fixed**: Bug fixes
- **Security**: Security-related changes

---

## Notes

### Versioning Strategy

- **Monorepo**: Follows semantic versioning at repository level
- **Individual Projects**: May have independent versioning
- **Breaking Changes**: Indicated by major version bumps

### Migration to Monorepo

On 2025-11-16, standalone repositories were merged using git subtree to preserve complete commit history. See `MONOREPO_MERGE_REPORT.md` for detailed merge documentation.

### Future Plans

- Expand test coverage across all projects
- Add integration tests for MCP servers
- Implement E2E testing for applications
- Add more automation utilities
- Create shared libraries for common functionality
- Expand MCP server capabilities

---

**Repository**: [My-Workspace-TB-](https://github.com/SonOfSamuel1/My-Workspace-TB-)
**Maintainer**: Terrance Brandon (@SonOfSamuel1)
