# YNAB MCP Server Troubleshooting Guide

## Quick Check: Is the Server Connected?

Run this command in your terminal:
```bash
cd "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace"
claude mcp list
```

You should see:
```
ynab: node ... - ✓ Connected
```

If you see this but the server still isn't available in Claude Code, **reload the VS Code/Cursor window** (Cmd+Shift+P → "Reload Window").

---

## Common Issues & Solutions

### Issue 1: Server Not Showing in MCP List

**Symptom:** `claude mcp list` doesn't show the YNAB server

**Solution:**
```bash
# Navigate to workspace
cd "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace"

# Add the server with API key
claude mcp add --transport stdio ynab \
  --env YNAB_API_KEY=hYPZEhxFtOZh0f5BDQMXdqHUsX5yrNgJtUJmyJlkYDs \
  -- node "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace/ynab-mcp-server/dist/index.js"
```

### Issue 2: Server Shows as Disconnected

**Symptom:** `claude mcp list` shows `❌ Disconnected` or errors

**Diagnosis Steps:**

1. **Test the server manually:**
   ```bash
   cd "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace/ynab-mcp-server"

   echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}' | \
   YNAB_API_KEY="hYPZEhxFtOZh0f5BDQMXdqHUsX5yrNgJtUJmyJlkYDs" node dist/index.js
   ```

   **Expected output:**
   ```
   YNAB MCP Server running on stdio
   {"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"ynab-mcp-server","version":"1.0.0"}},"jsonrpc":"2.0","id":1}
   ```

2. **Check if the built files exist:**
   ```bash
   ls -la "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace/ynab-mcp-server/dist/index.js"
   ```

   If missing, rebuild:
   ```bash
   cd "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace/ynab-mcp-server"
   npm run build
   ```

3. **Verify Node.js is available:**
   ```bash
   which node
   node --version
   ```

### Issue 3: Wrong Configuration File

**Symptom:** Configuration exists but server won't connect

Claude Code uses **different configuration scopes**:

- **Local scope** (recommended): Stored in `~/.claude.json`, private to you
- **Project scope**: Stored in `.mcp.json` at workspace root, shared with team

**Check which scope has the config:**
```bash
cd "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace"
claude mcp get ynab
```

**If server exists in multiple scopes, remove duplicates:**
```bash
# Remove from both scopes first
claude mcp remove ynab -s local
claude mcp remove ynab -s project

# Re-add to local scope (recommended for API keys)
claude mcp add --transport stdio ynab \
  --env YNAB_API_KEY=hYPZEhxFtOZh0f5BDQMXdqHUsX5yrNgJtUJmyJlkYDs \
  -- node "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace/ynab-mcp-server/dist/index.js"
```

### Issue 4: Missing API Key Environment Variable

**Symptom:** Server connects but tools fail with authentication errors

**Check current configuration:**
```bash
claude mcp get ynab
```

Look for the `env` section with `YNAB_API_KEY`.

**Fix:** Remove and re-add with the API key (see Issue 1 solution above)

### Issue 5: Server Works in CLI but Not in Claude Code

**Symptom:** `claude mcp list` shows connected, but tools aren't available in the UI

**Solutions:**

1. **Reload VS Code/Cursor window:**
   - Press `Cmd+Shift+P`
   - Type "Reload Window"
   - Press Enter

2. **Restart the application completely:**
   - Quit VS Code/Cursor
   - Reopen it

3. **Reset project approval choices:**
   ```bash
   claude mcp reset-project-choices
   ```
   Then reload the window.

---

## Configuration Reference

### Correct Local Configuration

Location: `~/.claude.json` (in the `projects` section for your workspace)

```json
{
  "projects": {
    "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace": {
      "mcpServers": {
        "ynab": {
          "type": "stdio",
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
  }
}
```

### Available YNAB Tools (24 total)

When properly connected, you'll have access to:

**Budgets:**
- `ynab_get_budgets` - Get all budgets
- `ynab_get_budget` - Get specific budget details

**Accounts:**
- `ynab_get_accounts` - Get all accounts
- `ynab_get_account` - Get specific account
- `ynab_create_account` - Create new account

**Categories:**
- `ynab_get_categories` - Get all categories
- `ynab_get_category` - Get specific category
- `ynab_update_category` - Update category budget/goals

**Transactions:**
- `ynab_get_transactions` - Get all transactions
- `ynab_get_transactions_by_account` - Get account transactions
- `ynab_get_transactions_by_category` - Get category transactions
- `ynab_get_transaction` - Get specific transaction
- `ynab_create_transaction` - Create new transaction
- `ynab_update_transaction` - Update existing transaction

**Payees:**
- `ynab_get_payees` - Get all payees
- `ynab_get_payee` - Get specific payee

**Scheduled Transactions:**
- `ynab_get_scheduled_transactions` - Get all scheduled transactions
- `ynab_get_scheduled_transaction` - Get specific scheduled transaction
- `ynab_create_scheduled_transaction` - Create scheduled transaction
- `ynab_update_scheduled_transaction` - Update scheduled transaction
- `ynab_delete_scheduled_transaction` - Delete scheduled transaction

**Months:**
- `ynab_get_months` - Get all budget months
- `ynab_get_month` - Get specific month data

**User:**
- `ynab_get_user` - Get authenticated user info

---

## Verification Checklist

Use this checklist to verify everything is working:

- [ ] `claude mcp list` shows `ynab: ... - ✓ Connected`
- [ ] Manual server test returns proper JSON-RPC response
- [ ] `dist/index.js` file exists and is executable
- [ ] Node.js is installed and accessible via `which node`
- [ ] API key is present in configuration (`claude mcp get ynab`)
- [ ] VS Code/Cursor window has been reloaded after any config changes
- [ ] `ListMcpResourcesTool` shows ynab server in Claude Code session

---

## Emergency Reset

If nothing else works, completely remove and reinstall:

```bash
# Navigate to workspace
cd "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace"

# Remove from all scopes
claude mcp remove ynab -s local 2>/dev/null || true
claude mcp remove ynab -s project 2>/dev/null || true

# Rebuild the server (if needed)
cd ynab-mcp-server
npm install
npm run build
cd ..

# Re-add with full configuration
claude mcp add --transport stdio ynab \
  --env YNAB_API_KEY=hYPZEhxFtOZh0f5BDQMXdqHUsX5yrNgJtUJmyJlkYDs \
  -- node "/Users/terrancebrandon/Desktop/Code Projects (Official)/My Workspace/ynab-mcp-server/dist/index.js"

# Verify
claude mcp list

# Reload VS Code/Cursor window
# Cmd+Shift+P → "Reload Window"
```

---

## Additional Resources

- **MCP Documentation:** https://code.claude.com/docs/en/mcp.md
- **Claude CLI Help:** Run `claude mcp --help`
- **Server Source:** `ynab-mcp-server/src/index.ts`
- **YNAB API Docs:** https://api.ynab.com/

---

**Last Updated:** 2025-11-16
**YNAB API Key Location:** Stored in `~/.claude.json` under project-specific `mcpServers.ynab.env`
