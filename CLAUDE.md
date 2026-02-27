# My-Workspace-TB- Monorepo

## Structure

- **apps/** — Python automation systems, Node.js tools (entry point:
  `src/<name>_main.py --validate|--generate`)
- **servers/** — MCP servers (TypeScript, `src/index.ts` → `dist/index.js`)
- **utils/** — Standalone scripts
- **docs/** — Workspace documentation

## Common Commands

```bash
npm run build              # Build all workspaces
npm test                   # Run all tests
npm run format             # Prettier format all TS/JS/JSON/MD
```

## Application Conventions

- Python entry points: `src/<name>_main.py` with `--validate` and `--generate`
  flags
- Config: `.env` or `config.yaml` per app; credentials in `credentials/`
  (gitignored)
- MCP servers: registered in `.mcp.json`, built with `npm run build`

## Pre-commit Hooks

- **Python** (`apps/`, `utils/`): black, isort, flake8 (max-line-length=127),
  bandit
- **TypeScript** (`servers/`): prettier

## Execution Model — ALWAYS FOLLOW

For any non-trivial task (more than a few-line fix), use this two-phase
approach:

1. **Plan (Opus — you)**: Analyze the codebase, design an exact implementation
   plan with specific file paths, diffs, and commands. Do not leave ambiguity.
2. **Execute (Sonnet agents)**: Launch Task tool agents with `model: "sonnet"`
   to carry out the plan. Use parallel agents for independent changes. Each
   agent must receive exact instructions — no design decisions.
   - **NEVER** set `model: "opus"` for any Task execution agent. Sonnet is the
     mandatory default. Only switch to Opus for execution if the user
     **explicitly** requests it in that message.
3. **Review (Opus — you)**: Check agent results, fix any issues yourself if
   needed.

Skip this only for trivial changes (typos, single-line fixes, quick questions).

## Commit Conventions

- Clear, descriptive messages focusing on what and why
- Include co-author footer for Claude-assisted commits

## Spec-Driven Development

For non-trivial features, use the spec-kit workflow: **specify → plan → tasks →
implement**. This formalizes the Plan phase with persistent spec artifacts in
`specs/`.

- **Start here**: `/spec-workflow <feature description>` — routes to the right
  phase
- **Constitution**: `.specify/memory/constitution.md` — workspace principles
  that guide all specs
- **Specs directory**: `specs/` at repo root (shared across apps)
- **Feature branches**: spec-kit creates numbered branches (e.g.,
  `001-feature-name`)

**When to use spec-kit**: New apps, major features, cross-app integrations,
ambiguous requirements. **When to skip**: Bug fixes, config changes, single-file
edits, clear scope (< 3 files).

**Caution**: `/speckit-plan` runs `update-agent-context.sh` which can modify
CLAUDE.md. Review changes after first use.

## Skills (invoke with `/skill-name`)

- `/new-mcp-server` — Scaffold a new MCP server
- `/deploy-lambda` — Deploy a Python app to AWS Lambda
- `/new-python-app` — Scaffold a new Python application
- `/test-and-build` — All build, test, format commands reference
- `/workspace-overview` — Full monorepo map with all apps, servers, and config
- `/spec-workflow` — Single entry point for spec-driven development lifecycle
- `/speckit-specify` — Create a feature spec from a description
- `/speckit-plan` — Generate implementation plan from a spec
- `/speckit-tasks` — Break a plan into actionable tasks
- `/speckit-implement` — Execute implementation tasks
- `/speckit-clarify` — Ask structured questions to de-risk ambiguity
- `/speckit-analyze` — Cross-artifact consistency check
- `/speckit-checklist` — Quality validation checklist
- `/speckit-constitution` — View/update workspace principles
- `/speckit-taskstoissues` — Convert tasks to GitHub issues

## Recent Changes

- 002-task-attachment-viewer: In-app image lightbox for Todoist task attachments
  on mobile (front-end only, `todoist_views.py`)
