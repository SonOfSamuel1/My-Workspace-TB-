# Claude Code Setup Guide

## Quick Start

Your Todoist MCP server is configured and ready to use with Claude Code! Follow these steps:

### 1. Get Your Todoist API Token

1. Go to [Todoist Settings → Integrations → Developer](https://todoist.com/app/settings/integrations/developer)
2. Copy your API token

### 2. Configure the API Token

Edit the `.env` file in this directory and replace the placeholder:

```bash
TODOIST_API_TOKEN=paste_your_actual_token_here
```

**Important**: Keep your API token secure and never commit the `.env` file to version control (it's already in `.gitignore`).

### 3. Restart Claude Code

After adding your token, restart Claude Code to load the MCP server.

### 4. Verify It's Working

Try one of these commands in Claude Code:

- "Show me all my Todoist projects"
- "Create a task 'Test MCP integration' due today"
- "List all my tasks"

## Configuration Details

The MCP server is configured in `.claude/mcp_config.json`:

```json
{
  "mcpServers": {
    "todoist": {
      "command": "node",
      "args": [
        "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace/todoist-mcp-server/dist/index.js"
      ],
      "env": {
        "TODOIST_API_TOKEN": "${TODOIST_API_TOKEN}"
      }
    }
  }
}
```

The server automatically loads your API token from the `.env` file.

## Available Features

- **25 Tools** for complete Todoist management
- **Task Management**: Create, update, complete, delete tasks
- **Project Organization**: Manage projects and subprojects
- **Sections**: Organize tasks within projects
- **Labels**: Tag and filter tasks
- **Comments**: Collaborate on tasks and projects

## Next Steps

1. Check out [EXAMPLES.md](EXAMPLES.md) for detailed usage examples
2. Read [README.md](README.md) for complete documentation
3. Start managing your tasks with natural language!

## Troubleshooting

### "Authentication failed" error
- Verify your API token is correct in `.env`
- Make sure there are no extra spaces or quotes around the token
- Check that the token hasn't expired

### MCP server not loading
- Ensure you've restarted Claude Code after editing `.env`
- Verify `npm run build` completed successfully
- Check that `dist/index.js` exists

### Need to rebuild?
```bash
npm run build
```

## Example Commands to Try

**Create a task:**
```
Create a Todoist task "Review documentation" with priority 3 due tomorrow at 2pm
```

**List tasks:**
```
Show me all my Todoist tasks due today
```

**Create a project:**
```
Create a new Todoist project called "Personal Goals" with blue color
```

**Complete a task:**
```
Complete Todoist task with ID [task_id]
```

**Get projects:**
```
List all my Todoist projects
```

**Filter tasks:**
```
Show me all high priority Todoist tasks
```

---

That's it! You're ready to manage your Todoist tasks directly through Claude Code.
