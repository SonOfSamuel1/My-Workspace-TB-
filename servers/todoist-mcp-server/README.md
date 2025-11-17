# Todoist MCP Server

A Model Context Protocol (MCP) server that provides integration with the Todoist API, allowing Claude and other MCP clients to manage tasks, projects, sections, comments, and labels.

## Features

- **Task Management**: Create, read, update, complete, reopen, and delete tasks
- **Project Management**: Manage projects and subprojects
- **Section Management**: Organize tasks within projects using sections
- **Comment System**: Add and manage comments on tasks and projects
- **Label Management**: Create and apply labels to tasks
- **Advanced Filtering**: Filter tasks by project, section, label, or custom filters

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd todoist-mcp-server
```

2. Install dependencies:
```bash
npm install
```

3. Build the project:
```bash
npm run build
```

## Configuration

### Get Your Todoist API Token

1. Log in to [Todoist](https://todoist.com)
2. Go to Settings → Integrations → Developer
3. Copy your API token

### Set Up Environment Variables

Create a `.env` file in the project root:

```bash
TODOIST_API_TOKEN=your_todoist_api_token_here
```

Or export it in your shell:

```bash
export TODOIST_API_TOKEN=your_todoist_api_token_here
```

### Configure Claude Code

The MCP configuration is already set up in `.claude/mcp_config.json`. Just add your API token to the `.env` file:

1. Edit the `.env` file in the project root
2. Replace `your_todoist_api_token_here` with your actual token
3. Restart Claude Code to load the MCP server

### Configure Claude Desktop (Alternative)

Add this to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "todoist": {
      "command": "node",
      "args": ["/absolute/path/to/todoist-mcp-server/dist/index.js"],
      "env": {
        "TODOIST_API_TOKEN": "your_todoist_api_token_here"
      }
    }
  }
}
```

## Available Tools

### Tasks

- `todoist_get_tasks` - Get all active tasks with optional filters
- `todoist_get_task` - Get a specific task by ID
- `todoist_create_task` - Create a new task
- `todoist_update_task` - Update an existing task
- `todoist_close_task` - Mark a task as complete
- `todoist_reopen_task` - Reopen a completed task
- `todoist_delete_task` - Delete a task

### Projects

- `todoist_get_projects` - Get all projects
- `todoist_get_project` - Get a specific project
- `todoist_create_project` - Create a new project
- `todoist_update_project` - Update a project
- `todoist_delete_project` - Delete a project

### Sections

- `todoist_get_sections` - Get all sections
- `todoist_create_section` - Create a new section
- `todoist_update_section` - Update a section
- `todoist_delete_section` - Delete a section

### Comments

- `todoist_get_comments` - Get comments for a task or project
- `todoist_create_comment` - Add a comment
- `todoist_update_comment` - Update a comment
- `todoist_delete_comment` - Delete a comment

### Labels

- `todoist_get_labels` - Get all labels
- `todoist_create_label` - Create a new label
- `todoist_update_label` - Update a label
- `todoist_delete_label` - Delete a label

## Usage Examples

See [EXAMPLES.md](EXAMPLES.md) for detailed usage examples.

### Quick Examples

**Create a task:**
```
Create a task "Review pull requests" with priority 3 due tomorrow
```

**List today's tasks:**
```
Show me all tasks due today
```

**Complete a task:**
```
Mark task [task_id] as complete
```

**Create a project:**
```
Create a new project called "Q1 Goals"
```

## Development

### Scripts

- `npm run build` - Compile TypeScript to JavaScript
- `npm run watch` - Watch for changes and recompile
- `npm run dev` - Build and run the server
- `npm start` - Run the compiled server

### Project Structure

```
todoist-mcp-server/
├── src/
│   └── index.ts          # Main server implementation
├── dist/                 # Compiled JavaScript (generated)
├── package.json
├── tsconfig.json
├── .env.example
├── .gitignore
├── README.md
└── EXAMPLES.md
```

## API Reference

This server uses the [Todoist REST API v2](https://developer.todoist.com/rest/v2/). All API calls are authenticated using your Todoist API token.

### Priority Levels

- `1` - Normal (default)
- `2` - Medium
- `3` - High
- `4` - Urgent

### Filter Examples

- `today` - Tasks due today
- `tomorrow` - Tasks due tomorrow
- `overdue` - Overdue tasks
- `p1` - Priority 1 (urgent) tasks
- `@label_name` - Tasks with a specific label
- `#project_name` - Tasks in a specific project

## Troubleshooting

### API Token Issues

If you get authentication errors:
1. Verify your API token is correct
2. Make sure the token is properly set in the environment variable
3. Check that there are no extra spaces or quotes in the token

### Connection Issues

If Claude Desktop can't connect:
1. Verify the path to `dist/index.js` is absolute and correct
2. Make sure you've run `npm run build`
3. Check the Claude Desktop logs for error messages

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT

## Support

For issues and questions:
- Check the [Todoist API documentation](https://developer.todoist.com/rest/v2/)
- Open an issue in this repository
- Refer to the [MCP documentation](https://modelcontextprotocol.io/)
