# Quick Start Guide

Get started with the YNAB MCP Server in 3 minutes!

## Prerequisites

- Node.js 18+ installed
- A YNAB account with an API token

## Step 1: Get Your YNAB API Token

1. Go to https://app.ynab.com
2. Navigate to **Account Settings** → **Developer Settings**
3. Click **New Token**
4. Copy your Personal Access Token

## Step 2: Build the Project

```bash
npm install
npm run build
```

## Step 3: Configure Your API Key

The project is already configured for Claude Code! Just update the API key:

**Option A: Edit the config file**

Open `.mcp.json` and replace the API key:

```json
{
  "mcpServers": {
    "ynab": {
      "command": "node",
      "args": ["dist/index.js"],
      "env": {
        "YNAB_API_KEY": "your_actual_api_key_here"
      }
    }
  }
}
```

**Option B: Use environment variable**

```bash
export YNAB_API_KEY="your_actual_api_key_here"
```

Then update `.mcp.json` to use the environment variable:

```json
{
  "mcpServers": {
    "ynab": {
      "command": "node",
      "args": ["dist/index.js"],
      "env": {
        "YNAB_API_KEY": "${YNAB_API_KEY}"
      }
    }
  }
}
```

## Step 4: Test It Out

If you're using Claude Code CLI in this directory, the MCP server should automatically load!

Try these commands:

```
Show me all my YNAB budgets
```

```
What are my account balances?
```

```
Show me transactions from last week
```

```
How much did I spend on groceries this month?
```

## Common Issues

### "YNAB_API_KEY environment variable is required"

Make sure your API key is properly set in `.claude/mcp_config.json`.

### "404 Not Found" or "401 Unauthorized"

Check that your API token is valid and hasn't expired. Generate a new one if needed.

### "Rate limit exceeded"

YNAB limits you to 200 API requests per hour. Wait a bit before trying again.

## Next Steps

- Check out [EXAMPLES.md](./EXAMPLES.md) for more usage examples
- Read the full [README.md](./README.md) for complete documentation
- Visit the [YNAB API docs](https://api.ynab.com/) for API details

## Understanding YNAB Amounts

YNAB uses "milliunits" for all monetary values:

- 1000 milliunits = $1.00
- 50000 milliunits = $50.00
- -25000 milliunits = -$25.00 (expense)

Claude will automatically handle this conversion for you!

## Need Help?

- The MCP server returns detailed error messages
- Check the [YNAB API documentation](https://api.ynab.com/)
- Review [EXAMPLES.md](./EXAMPLES.md) for usage patterns

Happy budgeting!
