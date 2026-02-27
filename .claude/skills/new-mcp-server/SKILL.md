---
description:
  Scaffold a new MCP server with TypeScript boilerplate, tsconfig, package.json,
  and registration
disable-model-invocation: true
---

# Create New MCP Server

## Directory Structure

```
servers/<server-name>/
├── src/
│   └── index.ts           # Main server implementation
├── dist/                  # Compiled JavaScript (gitignored)
├── package.json
├── tsconfig.json
├── .env.example
├── .gitignore
├── README.md
└── EXAMPLES.md
```

## Step 1: Create directory and initialize

```bash
mkdir -p servers/<server-name>/src
cd servers/<server-name>
npm init -y
npm install @modelcontextprotocol/sdk
npm install -D typescript @types/node
```

## Step 2: tsconfig.json

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

## Step 3: package.json scripts

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

## Step 4: src/index.ts template

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const server = new Server(
  {
    name: "<server-name>",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

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
  const { name, arguments: args } = request.params;
  switch (name) {
    case "tool_name":
      // Implement tool logic
      return { content: [{ type: "text", text: "result" }] };
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
});

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
```

## Step 5: Register in .mcp.json (project root)

```json
{
  "mcpServers": {
    "<server-name>": {
      "command": "node",
      "args": ["servers/<server-name>/dist/index.js"],
      "env": {
        "API_KEY": "<YOUR_API_KEY_HERE>"
      }
    }
  }
}
```

For Claude Desktop, add to
`~/Library/Application Support/Claude/claude_desktop_config.json` with absolute
paths.

## Step 6: Build and test

```bash
npm run build
# Restart Claude Code/Desktop, then test by asking Claude to use the tools
```

## Existing servers for reference

- `servers/gmail-mcp-server/` — Gmail (send, read, search, labels)
- `servers/todoist-mcp-server/` — Todoist (tasks, projects, sections, labels,
  filters)
- `servers/ynab-mcp-server/` — YNAB (budgets, accounts, transactions,
  categories)
