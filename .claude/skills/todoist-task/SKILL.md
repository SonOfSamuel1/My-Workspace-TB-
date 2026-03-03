---
description:
  Fetch and complete a Todoist task when the user shares a Todoist task link
user_invocable: true
---

# Todoist Task Handler

When the user shares a Todoist task URL (e.g.
`https://app.todoist.com/app/task/<TASK_ID>`), follow this workflow:

## 1. Extract the Task ID

The task ID is the last path segment of the URL:

```
https://app.todoist.com/app/task/6g5MJfgjWQ4ggmVC
                                  ^^^^^^^^^^^^^^^^
                                  This is the task ID
```

## 2. Load the API Token

The Todoist API token is stored in a dotenv file:

```bash
grep TODOIST_API_TOKEN ~/Projects/todoist-daily-reviewer/.env
```

This returns: `TODOIST_API_TOKEN=<token_value>`

## 3. Fetch the Task Details

Use the **Todoist API v1** to get the task:

```bash
curl -s "https://api.todoist.com/api/v1/tasks/<TASK_ID>" \
  -H "Authorization: Bearer <TOKEN>" | python3 -m json.tool
```

The response contains:

- `content` — the task title / what needs to be done
- `description` — optional additional details
- `project_id` — which project the task belongs to
- `labels` — any labels on the task
- `priority` — 1 (normal) to 4 (urgent)
- `due` — due date info (if set)

## 4. Check for Attachments

If the task description or comments contain image URLs or file attachments,
fetch and display them so you can understand the full context of the task.

## 5. Open a Worktree

Create an isolated worktree for this task:

1. Slugify the task `content` into a worktree name: lowercase, replace
   non-alphanumeric chars with hyphens, collapse consecutive hyphens, truncate
   to 50 chars. Example: `"Fix login bug on mobile"` → `fix-login-bug-on-mobile`
2. Use the **`EnterWorktree`** tool with that slug as the `name` parameter.
3. Record the worktree name — you'll need it in step 7.

## 6. Update Label to "In Progress"

Mark the task as actively being worked on:

```bash
curl -s -X POST "https://api.todoist.com/api/v1/tasks/<TASK_ID>" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"labels": ["In Progress"]}'
```

This replaces any existing labels (e.g. "New Issue") with "In Progress".

## 7. Write Session ID & Worktree to Description

Append tracking metadata to the task description so the session can be resumed
later:

1. **Derive session ID**: Run `ls -t ~/.claude/projects/*/*.jsonl | head -1` and
   extract the UUID from the filename (the part before `.jsonl`).
2. **Preserve existing description** from the step 3 response.
3. **Update the task description** via the API. Use `python3` to safely
   construct the JSON body (handles special characters in existing description):

```bash
python3 -c "
import json, sys
existing = sys.argv[1]
session_id = sys.argv[2]
worktree = sys.argv[3]
sep = '\n\n' if existing.strip() else ''
new_desc = existing.rstrip() + sep + 'Claude Session: ' + session_id + '\nWorktree: ' + worktree
print(json.dumps({'description': new_desc}))
" "<EXISTING_DESCRIPTION>" "<SESSION_ID>" "<WORKTREE_NAME>" | \
curl -s -X POST "https://api.todoist.com/api/v1/tasks/<TASK_ID>" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d @-
```

## 8. Do the Work

Read the task `content` and `description` to understand what needs to be done.
Then complete the task — this is usually a code change in this workspace. All
work happens inside the worktree created in step 5.

## 9. Commit & Merge to Main

> **CRITICAL — DO NOT SKIP STEP 9c.** You MUST ask the user for explicit
> approval before closing the task or pushing to main. This applies even after
> context compaction or session continuation. If you are unsure whether you
> already asked, ask again.

### 9a. Commit all changes

Stage and commit all changes in the worktree with a descriptive message
referencing the task.

### 9b. Merge to main

1. Switch to `main` and pull latest:

   ```bash
   git checkout main && git pull origin main
   ```

2. Merge the feature branch:

   ```bash
   git merge <worktree-branch>
   ```

If merge conflicts occur, **inform the user** and leave the task open — do NOT
force-resolve or auto-close.

## 10. Deploy

> **Always merge to main BEFORE deploying.** Never deploy from a worktree branch
> — the deploy must run from the merged main branch.

If the task changed ActionOS or any other Railway-hosted app, deploy to Railway:

```bash
cd apps/ActionOS && railway up --service actionos --detach
```

If the task was a non-deployable change (docs, local scripts, etc.), skip this step.

## 11. Run Performance Check (ActionOS deploys only)

If the task changed any file in ActionOS (`app.py`, `lambda_handler.py`, or
anything under `src/`), **always** run `/perf-check` after the deploy
completes. Do not wait for the user to ask.

```
/perf-check
```

This measures TTFB and DCL for all 6 endpoints against established baselines
and confirms cache warming is working. If any endpoint FAILs, diagnose and fix
before proceeding to close the task.

If the task was a non-ActionOS change, skip this step.

## 13. Ask Before Closing & Pushing

**Always ask**: "Can I mark this task as complete on Todoist and push to main?"

Do **NOT** auto-close. Do **NOT** push to main. Wait for explicit user approval
for both actions.

## 14. Close and Push (if approved)

If the user approves:

1. Close the Todoist task:

   ```bash
   curl -s -X POST "https://api.todoist.com/api/v1/tasks/<TASK_ID>/close" \
     -H "Authorization: Bearer <TOKEN>"
   ```

   A successful close returns HTTP **204** (no content).

2. Push to remote:

   ```bash
   git push origin main
   ```

If the user does **not** approve, leave the task open and inform the user that
the task remains in "In Progress" status on Todoist.

## 15. Clean Up the Worktree

After the push succeeds, **always** remove the worktree and its branch. Run
these commands from the **outer repo root** (not the submodule):

```bash
cd "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace/My-Workspace-TB-"
git worktree remove --force .claude/worktrees/<WORKTREE-NAME>
git branch -d worktree-<WORKTREE-NAME>
```

Where `<WORKTREE-NAME>` is the slug recorded in Step 5 (e.g.
`fix-login-bug-on-mobile`).

> **Why this matters:** If the worktree directory is deleted by Claude Code
> session cleanup before you explicitly remove it, the Bash tool's stored CWD
> becomes invalid and all subsequent shell commands in the session will fail
> with "Working directory no longer exists." Running this step immediately
> after the push prevents that breakage.

If `git branch -d` fails because the branch was already merged, use `-D` to
force-delete:

```bash
git branch -D worktree-<WORKTREE-NAME>
```

## API Reference

| Endpoint                    | Method | Purpose                        |
| --------------------------- | ------ | ------------------------------ |
| `/api/v1/tasks/<id>`        | GET    | Fetch task details             |
| `/api/v1/tasks/<id>`        | POST   | **Update task** (labels, desc) |
| `/api/v1/tasks/<id>/close`  | POST   | Mark task complete             |
| `/api/v1/tasks/<id>/reopen` | POST   | Reopen a completed task        |
| `/api/v1/tasks`             | POST   | Create a new task              |

## Important Notes

- Always use API **v1** (`/api/v1/`). The v2 REST API (`/rest/v2/`) is
  deprecated and returns 410.
- The API token is a **personal token** — do not log or expose it in output.
- **Never auto-close** a task — always ask the user for explicit confirmation
  before closing.
- Always **preserve existing description** content when appending session and
  worktree metadata.
- Session ID is derived from the most recent `.jsonl` transcript file in the
  Claude projects directory.
- If merge conflicts occur, inform the user and leave the task open.
