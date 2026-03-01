# My-Workspace-TB- Constitution

## Core Principles

### I. Automation-First

Every application runs headless and is Lambda-deployable. No interactive
prompts, no GUI dependencies. Entry points accept `--validate` and `--generate`
flags for testability. If it can't run in a cron job, it doesn't ship.

### II. Convention Over Configuration

Predictable patterns reduce cognitive load:

- Python entry points: `src/<name>_main.py`
- Config: `.env` or `config.yaml` per app; credentials in AWS Parameter Store
- MCP servers: `src/index.ts` → `dist/index.js`, registered in `.mcp.json`
- Deploy scripts: `scripts/deploy-lambda-zip.sh`

### III. Personal-Scale Simplicity

Single-user system. No multi-tenancy, no complex auth, no feature flags. AWS
Parameter Store for secrets. Direct Lambda invocations over API Gateway when
possible. YAGNI is law.

### IV. Observability

Every app supports `--validate` for health checks. CloudWatch logging for all
Lambda functions. Structured output (JSON) for machine consumption,
human-readable for manual runs.

### V. Spec-Driven Development

Non-trivial features follow the specify → plan → tasks → implement lifecycle.
Specs live in `specs/` at repo root. The Execution Model (Plan with Opus →
Execute with Sonnet agents → Review with Opus) governs implementation.

## Development Workflow

- **Pre-commit hooks**: Python (black, isort, flake8, bandit), TypeScript
  (prettier)
- **Branching**: Feature branches via spec-kit (`NNN-feature-name`), merge to
  main
- **Commits**: Clear messages with co-author footer for Claude-assisted work
- **Testing**: Validate flags, pytest for Python, vitest/jest for TypeScript

## Governance

This constitution guides all spec-kit decisions. When a spec conflicts with
these principles, the principles win. Amendments require updating both this file
and `CLAUDE.md`.

**Version**: 1.0.0 | **Ratified**: 2026-02-26 | **Last Amended**: 2026-02-26
