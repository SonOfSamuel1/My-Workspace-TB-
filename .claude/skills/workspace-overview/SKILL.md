---
description:
  Full monorepo map — all apps, servers, utils, config files, tech stack, and
  conventions
disable-model-invocation: true
---

# Workspace Overview

**Repository**: My-Workspace-TB- (github.com/SonOfSamuel1/My-Workspace-TB-)
**Owner**: Terrance Brandon (@SonOfSamuel1)

## Monorepo Structure

```
My-Workspace-TB-/
├── apps/                  # Full applications and automation systems
├── servers/               # MCP server implementations (TypeScript)
├── utils/                 # Standalone utility scripts
├── docs/                  # Workspace-level documentation
├── scripts/               # Workspace-level scripts
├── .mcp.json              # MCP server registry for Claude Code
├── .pre-commit-config.yaml
├── package.json           # npm workspaces config
└── CLAUDE.md
```

## Applications (apps/)

| App                           | Type    | Purpose                                      |
| ----------------------------- | ------- | -------------------------------------------- |
| ActionOS                      | —       | Action management system                     |
| amazon-ynab-reconciler        | Python  | Amazon/YNAB transaction reconciliation       |
| autonomous-email-assistant    | Node.js | AI-powered email management                  |
| cc-session-tracker            | —       | Claude Code session tracking                 |
| eight-sleep-jailbreak         | —       | Eight Sleep integration                      |
| factor75-meal-selector        | —       | Factor75 meal selection                      |
| fireflies-meeting-notes       | —       | Fireflies.ai meeting notes integration       |
| gmail-email-actions           | —       | Gmail action automation                      |
| homeschool-events-gwinnett    | —       | Homeschool event aggregation                 |
| jt-teaching-newsletter        | Python  | Teaching newsletter generation (SES)         |
| love-brittany-tracker         | Python  | Relationship tracking with bi-weekly reports |
| obsidian-bibleref-linker      | —       | Obsidian Bible reference linker              |
| todoist-actions-web           | —       | Todoist web actions                          |
| todoist-coding-digest         | —       | Todoist coding task digest                   |
| todoist-inbox-digest          | —       | Todoist inbox digest                         |
| todoist-inbox-manager         | —       | Todoist inbox management                     |
| weekly-github-trending-report | —       | Weekly GitHub trending report                |
| ynab-dashboard                | —       | YNAB budget dashboard                        |
| ynab-transaction-reviewer     | Python  | YNAB transaction review system               |

## MCP Servers (servers/)

| Server             | Purpose                                                     |
| ------------------ | ----------------------------------------------------------- |
| gmail-mcp-server   | Gmail integration (send, read, search, labels)              |
| todoist-mcp-server | Todoist task management (tasks, projects, sections, labels) |
| ynab-mcp-server    | YNAB budget management (budgets, accounts, transactions)    |

## Utilities (utils/)

- `todoist_p2_label_updater.py` — Automated Todoist label management

## Technology Stack

- **Languages**: Python 3.x, TypeScript/Node.js, Bash
- **APIs**: Google (Calendar, Docs, Gmail), Todoist REST API v2, YNAB API, MCP
  SDK
- **Infrastructure**: AWS Lambda, Parameter Store, EventBridge, CloudWatch
- **Testing**: Jest (Node.js), --validate flags (Python)
- **Formatting**: black + isort + flake8 (Python), prettier (TypeScript)

## Key Config Files

| File                      | Purpose                                    |
| ------------------------- | ------------------------------------------ |
| `.mcp.json`               | MCP server registry for Claude Code        |
| `.pre-commit-config.yaml` | Git hooks (black, isort, flake8, prettier) |
| `.lintstagedrc.json`      | Staged file formatting                     |
| `package.json`            | npm workspaces config                      |

## Security Rules

- Never commit `.env` files or credentials
- Use `.gitignore` to exclude sensitive files
- AWS Parameter Store for cloud credentials
- Google OAuth2 credentials in `credentials/` directories (gitignored)
- API keys: Todoist (personal tokens), YNAB (personal tokens), Google (OAuth2)

## Commit Conventions

- Clear, descriptive messages focusing on what and why
- Co-authored with Claude Code: `Co-Authored-By: Claude <noreply@anthropic.com>`
