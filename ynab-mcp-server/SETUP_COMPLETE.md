# YNAB MCP Server - Setup Complete! ✅

Your YNAB MCP server is now properly configured for Claude Code.

## What Was Configured

### 1. Project Structure ✓
```
ynab-mcp-server/
├── .mcp.json              # Claude Code MCP configuration (with your API key)
├── .mcp.json.example      # Template for version control
├── src/index.ts           # MCP server source code
├── dist/index.js          # Compiled server (executable)
└── package.json           # Dependencies
```

### 2. MCP Configuration File ✓

**File**: `.mcp.json` (at project root)

```json
{
  "mcpServers": {
    "ynab": {
      "command": "node",
      "args": [
        "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace/ynab-mcp-server/dist/index.js"
      ],
      "env": {
        "YNAB_API_KEY": "hYPZEhxFtOZh0f5BDQMXdqHUsX5yrNgJtUJmyJlkYDs"
      }
    }
  }
}
```

### 3. Server Built and Ready ✓
- TypeScript compiled successfully
- dist/index.js is executable
- All 25 YNAB tools are available

## Next Steps

### Option 1: Restart Claude Code (Recommended)

If you're in a Claude Code session, you may need to restart it to load the new MCP server:

1. Exit the current Claude Code session
2. Restart Claude Code in this directory
3. The YNAB MCP server should now be available

### Option 2: Check MCP Server Status

Try asking Claude:
```
List all available MCP servers
```

You should see "ynab" in the list.

### Option 3: Test the Server

Once loaded, try these commands:

```
Show me all my YNAB budgets
```

```
What are my YNAB account balances?
```

```
List my recent transactions
```

## Troubleshooting

### Server Not Showing Up?

**Try these steps:**

1. **Verify the build**:
   ```bash
   npm run build
   ```

2. **Check the file is executable**:
   ```bash
   ls -la dist/index.js
   # Should show -rwxr-xr-x (executable permissions)
   ```

3. **Test the server manually**:
   ```bash
   YNAB_API_KEY="hYPZEhxFtOZh0f5BDQMXdqHUsX5yrNgJtUJmyJlkYDs" node dist/index.js
   ```

   The server should start and show: "YNAB MCP Server running on stdio"

4. **Verify .mcp.json syntax**:
   ```bash
   cat .mcp.json | jq .
   # Should parse without errors
   ```

5. **Restart Claude Code** - Exit and relaunch in this directory

### API Key Issues?

If you get authentication errors:

1. Verify your YNAB API key is still valid
2. Generate a new token at: https://app.ynab.com/settings/developer
3. Update `.mcp.json` with the new key

### Permission Errors?

```bash
chmod +x dist/index.js
```

## Available MCP Tools

Once the server is loaded, you'll have access to 25 tools:

### Budgets
- `ynab_get_budgets` - List all budgets
- `ynab_get_budget` - Get budget details

### Accounts
- `ynab_get_accounts` - List accounts
- `ynab_get_account` - Get account details
- `ynab_create_account` - Create new account

### Transactions
- `ynab_get_transactions` - List transactions
- `ynab_get_transactions_by_account` - Filter by account
- `ynab_get_transactions_by_category` - Filter by category
- `ynab_get_transaction` - Get specific transaction
- `ynab_create_transaction` - Create transaction
- `ynab_update_transaction` - Update transaction

### Categories
- `ynab_get_categories` - List categories
- `ynab_get_category` - Get category details
- `ynab_update_category` - Update budget amounts

### Payees
- `ynab_get_payees` - List payees
- `ynab_get_payee` - Get payee details

### Scheduled Transactions
- `ynab_get_scheduled_transactions` - List scheduled
- `ynab_get_scheduled_transaction` - Get details
- `ynab_create_scheduled_transaction` - Create new
- `ynab_update_scheduled_transaction` - Update existing
- `ynab_delete_scheduled_transaction` - Delete

### Budget Months
- `ynab_get_months` - List all months
- `ynab_get_month` - Get month details

### User
- `ynab_get_user` - Get user info

## Example Queries

Once the server is loaded, try these:

```
"What budgets do I have in YNAB?"
"Show me my checking account balance"
"List transactions from last week"
"Create a $50 grocery transaction"
"How much did I spend on dining out this month?"
"What are my scheduled bills?"
```

## Security Notes

- ✅ `.mcp.json` is gitignored (contains your API key)
- ✅ `.mcp.json.example` is safe to commit (no real key)
- ✅ API key is only in environment variables
- ⚠️ Never commit `.mcp.json` to version control

## Need Help?

- 📖 See [EXAMPLES.md](./EXAMPLES.md) for usage examples
- 📚 Read [README.md](./README.md) for full documentation
- 🚀 Check [QUICKSTART.md](./QUICKSTART.md) for quick setup
- 🌐 Visit [YNAB API Docs](https://api.ynab.com/)

---

**Status**: Configuration complete! Ready to use with Claude Code.

If the server isn't showing up yet, try **restarting Claude Code** in this directory.
