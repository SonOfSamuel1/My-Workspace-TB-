---
name: spec-workflow
description:
  Guide through the full spec-kit lifecycle for feature development. Single
  entry point for spec-driven development with monorepo-specific context. Routes
  to the appropriate spec-kit phase based on current state.
---

# Spec Workflow

## User Input

```text
$ARGUMENTS
```

## Overview

This skill is the single entry point for spec-driven development in
My-Workspace-TB-. It assesses where you are in the lifecycle and routes you to
the right phase.

## When to Use Spec-Kit vs Direct Implementation

**Use spec-kit** (`/spec-workflow`) for:

- New applications or major features spanning multiple files
- Cross-app integrations (e.g., connecting a Lambda to a new data source)
- Features where requirements are ambiguous or multi-step

**Skip spec-kit** (just implement directly) for:

- Single-file bug fixes or typo corrections
- Adding a config value or environment variable
- Routine dependency updates
- Changes with clear, unambiguous scope (< 3 files)

## Lifecycle Phases

### Phase 1: Specify (`/speckit-specify`)

Creates a feature branch and `specs/NNN-feature-name/spec.md` with requirements,
user stories, and acceptance criteria. **No implementation details.**

### Phase 2: Clarify (`/speckit-clarify`) — Optional

Ask structured questions to de-risk ambiguous areas before planning.

### Phase 3: Plan (`/speckit-plan`)

Generates `specs/NNN-feature-name/plan.md` with technical implementation plan.
Maps to the **Plan** phase of the Execution Model.

### Phase 4: Tasks (`/speckit-tasks`)

Breaks the plan into actionable task files. Maps to the **Execute** phase — each
task can be dispatched to a Sonnet agent.

### Phase 5: Analyze (`/speckit-analyze`) — Optional

Cross-artifact consistency check before implementation.

### Phase 6: Implement (`/speckit-implement`)

Executes the tasks. Use the Execution Model: Opus plans, Sonnet agents execute
in parallel, Opus reviews.

### Phase 7: Checklist (`/speckit-checklist`) — Optional

Quality validation checklist for the completed implementation.

## Routing Logic

When the user invokes `/spec-workflow`:

1. **If `$ARGUMENTS` contains a feature description** → Route to
   `/speckit-specify` with that description
2. **If on a feature branch (NNN-feature-name)**:
   - Check which artifacts exist in `specs/NNN-feature-name/`:
     - No `spec.md` → Something went wrong, re-run `/speckit-specify`
     - Has `spec.md` but no `plan.md` → Route to `/speckit-plan`
     - Has `plan.md` but no task files → Route to `/speckit-tasks`
     - Has tasks → Route to `/speckit-implement`
3. **If on main with no arguments** → List recent specs and ask what the user
   wants to work on

## Monorepo Context

When generating specs and plans, consider:

- **Which app does this feature belong to?** Check `apps/` for existing apps
- **Python or TypeScript?** Follow the conventions for the target app type
- **Entry points**: Python apps use `src/<name>_main.py`, MCP servers use
  `src/index.ts`
- **Deployment**: Lambda via `scripts/deploy-lambda-zip.sh`
- **Secrets**: AWS Parameter Store, never `.env` in production
- **Specs directory**: `specs/` at repo root (not per-app), since features may
  span apps
