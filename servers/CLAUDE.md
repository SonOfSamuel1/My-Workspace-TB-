# MCP Servers Directory

Model Context Protocol (MCP) server implementations that enable AI assistants to interact with external services and APIs.

## What is MCP?

The Model Context Protocol (MCP) is a standard for connecting AI assistants like Claude to external tools and data sources. MCP servers expose tools that AI assistants can use to perform actions or retrieve information.

## Available Servers

### gmail-mcp-server
**Path:** `servers/gmail-mcp-server/`
**Language:** TypeScript/Node.js
**Purpose:** Gmail integration for AI assistants

**Features:**
- Send emails
- Read messages
- Search inbox
- Manage labels and threads

**Setup:**
```bash
cd gmail-mcp-server
npm install
npm run build
```

**Documentation:** [README.md](gmail-mcp-server/README.md)

---

### todoist-mcp-server
**Path:** `servers/todoist-mcp-server/`
**Language:** TypeScript/Node.js
**Purpose:** Todoist task management integration

**Features:**
- Task CRUD operations
- Project management
- Section organization
- Comment system
- Label management
- Advanced filtering

**Setup:**
```bash
cd todoist-mcp-server
npm install
npm run build
```

**Configuration:** Requires Todoist API token in `.env`

**Documentation:**
- [README.md](todoist-mcp-server/README.md)
- [Examples](todoist-mcp-server/EXAMPLES.md)
- [Setup Guide](todoist-mcp-server/SETUP_CLAUDE_CODE.md)

---

### ynab-mcp-server
**Path:** `servers/ynab-mcp-server/`
**Language:** TypeScript/Node.js
**Purpose:** YNAB (You Need A Budget) integration

**Features:**
- Budget management
- Account operations
- Transaction CRUD
- Category updates
- Payee management
- Scheduled transactions
- Month budget views

**Setup:**
```bash
cd ynab-mcp-server
npm install
npm run build
```

**Configuration:** Requires YNAB API token in `.env` or `.mcp.json`

**Documentation:**
- [README.md](ynab-mcp-server/README.md)
- [Quick Start](ynab-mcp-server/QUICKSTART.md)
- [Examples](ynab-mcp-server/EXAMPLES.md)

## Server Architecture

### Typical Structure
```
server-name/
├── src/
│   └── index.ts           # Main server implementation
├── dist/                  # Compiled JavaScript
├── package.json           # Dependencies and scripts
├── tsconfig.json          # TypeScript configuration
├── .env.example           # Environment template
├── .gitignore
├── README.md
└── EXAMPLES.md            # Usage examples
```

### Common Components

**index.ts:**
- Server initialization
- Tool registration
- API client setup
- Request handlers
- Error handling

**package.json:**
- Dependencies (@modelcontextprotocol/sdk)
- Build scripts (tsc, watch)
- Development tools

**Configuration:**
- API tokens in .env
- MCP registration in .mcp.json or claude_desktop_config.json

## Configuration

### Claude Code (CLI)

Project-level configuration in `.mcp.json`:
```json
{
  "mcpServers": {
    "server-name": {
      "command": "node",
      "args": ["dist/index.js"],
      "env": {
        "API_KEY": "your_key_here"
      }
    }
  }
}
```

### Claude Desktop

Global configuration in `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):
```json
{
  "mcpServers": {
    "server-name": {
      "command": "node",
      "args": ["/absolute/path/to/server/dist/index.js"],
      "env": {
        "API_KEY": "your_key_here"
      }
    }
  }
}
```

## Development Workflow

### Initial Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure API credentials:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Build the server:**
   ```bash
   npm run build
   ```

4. **Test the server:**
   - Restart Claude Code/Desktop
   - Ask a test question using the server's tools

### Development Mode

```bash
# Watch for changes and rebuild
npm run watch

# Or build and run
npm run dev
```

### Available Scripts

Common npm scripts across servers:
- `npm run build` - Compile TypeScript
- `npm run watch` - Watch mode for development
- `npm run dev` - Build and run
- `npm start` - Run compiled server

## Adding New Servers

### Prerequisites
- Node.js and npm installed
- API access to target service
- MCP SDK knowledge

### Setup Steps

1. **Create server directory:**
   ```bash
   mkdir servers/new-server-mcp
   cd servers/new-server-mcp
   ```

2. **Initialize project:**
   ```bash
   npm init -y
   npm install @modelcontextprotocol/sdk
   npm install -D typescript @types/node
   ```

3. **Create tsconfig.json:**
   ```json
   {
     "compilerOptions": {
       "target": "ES2022",
       "module": "Node16",
       "moduleResolution": "Node16",
       "outDir": "./dist",
       "rootDir": "./src",
       "strict": true,
       "esModuleInterop": true,
       "skipLibCheck": true
     }
   }
   ```

4. **Implement server in src/index.ts**

5. **Add build scripts to package.json:**
   ```json
   {
     "scripts": {
       "build": "tsc",
       "watch": "tsc --watch",
       "dev": "npm run build && node dist/index.js",
       "start": "node dist/index.js"
     }
   }
   ```

6. **Create documentation:**
   - README.md with setup and usage
   - EXAMPLES.md with usage examples
   - .env.example for configuration template

### Server Template

Basic MCP server structure:
```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { ListToolsRequestSchema, CallToolRequestSchema } from "@modelcontextprotocol/sdk/types.js";

const server = new Server({
  name: "your-server",
  version: "1.0.0",
}, {
  capabilities: {
    tools: {},
  },
});

// Register tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "tool_name",
      description: "Tool description",
      inputSchema: {
        type: "object",
        properties: {
          // Define parameters
        },
      },
    },
  ],
}));

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  // Implement tool logic
});

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
```

## API Integration Best Practices

### Authentication
- Store API keys in environment variables
- Never commit credentials
- Use .env.example for templates
- Document API key acquisition process

### Error Handling
- Catch and format API errors clearly
- Provide helpful error messages
- Log errors for debugging
- Handle rate limits gracefully

### Rate Limiting
- Document API rate limits in README
- Implement retry logic if needed
- Cache responses when appropriate
- Warn users about quota consumption

### Data Handling
- Validate input parameters
- Sanitize user input
- Format output consistently
- Handle edge cases (null, empty, etc.)

## Testing

### Manual Testing

1. **Build the server:**
   ```bash
   npm run build
   ```

2. **Configure in Claude Code/Desktop**

3. **Test with natural language:**
   - "Show me my [service] data"
   - "Create a new [item]"
   - "Update [item] with [changes]"

### Debugging

**Check server is running:**
- Claude Code: Server loads automatically from `.mcp.json`
- Claude Desktop: Check configuration file path

**View logs:**
- Console output during development
- Claude Desktop: Check application logs

**Common issues:**
- API token invalid or missing
- Server not built (run `npm run build`)
- Incorrect path in configuration
- Missing environment variables

## Resources

### Documentation
- [MCP Documentation](https://modelcontextprotocol.io/)
- [MCP SDK on GitHub](https://github.com/modelcontextprotocol/sdk)
- [Workspace MCP Configuration Guide](../docs/mcp-server-configurator.md)

### API References
- [Todoist API](https://developer.todoist.com/rest/v2/)
- [YNAB API](https://api.ynab.com/)
- [Gmail API](https://developers.google.com/gmail/api)

### Related Directories
- [Main Workspace](../CLAUDE.md)
- [Applications](../apps/CLAUDE.md)
- [Utilities](../utils/CLAUDE.md)

## Troubleshooting

### Server Won't Start
1. Check build: `npm run build`
2. Verify path in configuration
3. Check for TypeScript errors
4. Ensure dependencies installed

### API Authentication Fails
1. Verify API key is correct
2. Check .env file exists and is loaded
3. Confirm API key has required permissions
4. Test API key with direct HTTP request

### Tools Not Appearing
1. Restart Claude Code/Desktop
2. Verify server in configuration
3. Check server is running (no errors in console)
4. Review server tool registration code

### For detailed troubleshooting:
- See [YNAB MCP Troubleshooting](../docs/YNAB_MCP_TROUBLESHOOTING.md)
- Check individual server READMEs
- Review MCP documentation

---

**Directory Purpose:** MCP server implementations for AI assistant integrations
**Last Updated:** 2025-11-16
