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

## 4. Do the Work

Read the task `content` and `description` to understand what needs to be done.
Then complete the task — this is usually a code change in this workspace.

## 5. Close the Task on Todoist

After completing the work, mark the task as done:

```bash
curl -s -X POST "https://api.todoist.com/api/v1/tasks/<TASK_ID>/close" \
  -H "Authorization: Bearer <TOKEN>"
```

A successful close returns HTTP **204** (no content).

## API Reference

| Endpoint                    | Method | Purpose                 |
| --------------------------- | ------ | ----------------------- |
| `/api/v1/tasks/<id>`        | GET    | Fetch task details      |
| `/api/v1/tasks/<id>/close`  | POST   | Mark task complete      |
| `/api/v1/tasks`             | POST   | Create a new task       |
| `/api/v1/tasks/<id>`        | POST   | Update a task           |
| `/api/v1/tasks/<id>/reopen` | POST   | Reopen a completed task |

## Important Notes

- Always use API **v1** (`/api/v1/`). The v2 REST API (`/rest/v2/`) is
  deprecated and returns 410.
- The API token is a **personal token** — do not log or expose it in output.
- Always confirm with the user before closing a task if the work required is
  ambiguous.
