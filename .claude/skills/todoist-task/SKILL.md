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

## 9. Commit, Merge & Close

### 9a. Commit all changes

Stage and commit all changes in the worktree with a descriptive message
referencing the task.

### 9b. Merge to main

```bash
git checkout main && git merge <worktree-branch>
```

If merge conflicts occur, **inform the user** and leave the task open — do NOT
force-resolve or auto-close.

### 9c. Ask the user before closing

**Always ask**: "Can I mark this task as complete on Todoist?"

Do **NOT** auto-close. Wait for explicit user approval.

### 9d. Close (if approved)

If the user approves:

```bash
curl -s -X POST "https://api.todoist.com/api/v1/tasks/<TASK_ID>/close" \
  -H "Authorization: Bearer <TOKEN>"
```

A successful close returns HTTP **204** (no content).

If the user does **not** approve, leave the task open and inform the user that
the task remains in "In Progress" status on Todoist.

## 10. Merge to Main and Push

After closing the Todoist task, merge the worktree branch into `main` and push:

1. Commit any remaining changes on the current branch.
2. Switch to `main` and pull latest:

   ```bash
   git checkout main && git pull origin main
   ```

3. Merge the feature branch:

   ```bash
   git merge <worktree-branch> --no-edit
   ```

4. Push to remote:

   ```bash
   git push origin main
   ```

5. Confirm the merge and push succeeded before finishing.

If there are merge conflicts, stop and ask the user how to resolve them rather
than force-merging.

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
