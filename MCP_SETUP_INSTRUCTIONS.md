# MCP Server Setup Instructions

## ✅ What Has Been Fixed

1. **Agent Files**: Fixed all 3 agent files in `~/.claude/agents/` by adding proper YAML frontmatter with required `name` field
2. **Environment Files**: Created `.env` files for all MCP servers (todoist, ynab, gmail)
3. **Configuration**: Updated `.mcp.json` with absolute paths and placeholder API tokens

## 🔴 What Still Needs to Be Done

### 1. Build the MCP Servers

The TypeScript compilation was taking too long, so you'll need to build them manually:

```bash
# Build Todoist MCP Server
cd servers/todoist-mcp-server
npm run build

# Build YNAB MCP Server
cd servers/ynab-mcp-server
npm run build

# Build Gmail MCP Server
cd servers/gmail-mcp-server
npm run build
```

Each build should create a `dist/` directory with the compiled JavaScript files.

### 2. Add Your API Tokens

You need to add your actual API tokens to the `.mcp.json` file:

#### Todoist API Token
1. Go to: https://todoist.com/app/settings/integrations/developer
2. Copy your API token
3. In `.mcp.json`, replace `ADD_YOUR_TODOIST_API_TOKEN_HERE` with your actual token

#### YNAB API Key
1. Go to: https://app.ynab.com/settings/developer
2. Create a new Personal Access Token
3. Copy the token
4. In `.mcp.json`, replace `ADD_YOUR_YNAB_API_KEY_HERE` with your actual token

#### Gmail Setup
1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Create a project or select an existing one
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop application type)
5. Download the credentials JSON file
6. Save it as `~/.gmail-mcp-credentials.json`
7. After building the Gmail server, run:
   ```bash
   cd servers/gmail-mcp-server
   npm run auth
   ```
8. Follow the OAuth flow to generate `~/.gmail-mcp-token.json`

### 3. Restart Claude Code

After completing the above steps:
```bash
# Restart Claude Code to reload the configuration
# The MCP servers should then be available
```

## 📁 Files Created/Modified

### Created Files:
- `/servers/todoist-mcp-server/.env` - Todoist environment configuration
- `/servers/ynab-mcp-server/.env` - YNAB environment configuration
- `/servers/gmail-mcp-server/.env` - Gmail environment configuration
- This instructions file

### Modified Files:
- `~/.claude/agents/executive-email-assistant-config-terrance.md` - Added YAML frontmatter
- `~/.claude/agents/README.md` - Added YAML frontmatter
- `~/.claude/agents/executive-email-assistant.md` - Added YAML frontmatter
- `.mcp.json` - Updated with absolute paths and placeholder tokens

## 🔍 Verification Steps

After completing the setup:

1. **Check builds completed**:
   ```bash
   ls -la servers/todoist-mcp-server/dist/
   ls -la servers/ynab-mcp-server/dist/
   ls -la servers/gmail-mcp-server/dist/
   ```

2. **Verify API tokens are in place**:
   ```bash
   grep "ADD_YOUR" .mcp.json
   # Should return nothing if all tokens are replaced
   ```

3. **Test in Claude Code**:
   - Restart Claude Code
   - Try a command like "Show me my Todoist tasks"
   - Check if the MCP server responds

## ⚠️ Notes

- The Comet server connection failure is normal if Comet browser isn't running
- The husky warning during npm install can be ignored
- If builds fail, check for TypeScript errors in the source files
- Gmail requires OAuth setup which is more complex than simple API tokens

## 📚 Additional Resources

- [Todoist API Documentation](https://developer.todoist.com/rest/v2/)
- [YNAB API Documentation](https://api.ynab.com/)
- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [MCP Documentation](https://modelcontextprotocol.io/)

---
Created: 2025-11-26
Status: Partial completion - manual steps required