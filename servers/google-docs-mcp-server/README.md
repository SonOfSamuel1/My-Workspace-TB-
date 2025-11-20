# Google Docs MCP Server

An MCP (Model Context Protocol) server that provides AI assistants with the ability to interact with Google Docs. This enables creating, reading, editing, and managing Google Docs through natural language.

## Features

### Document Operations
- **Create Documents** - Create new Google Docs with optional title and initial content
- **Read Documents** - Retrieve the full text content of any Google Doc
- **Update Documents** - Append or replace text in existing documents
- **List Documents** - Browse your Google Docs with search and filtering
- **Search Documents** - Find text within specific documents

### Advanced Editing
- **Insert Text** - Insert text at specific positions in a document
- **Delete Text** - Remove text ranges from documents
- **Batch Operations** - Perform multiple edits in a single request

## Installation

### Prerequisites
- Node.js 18+ and npm
- A Google Cloud Project with Google Docs API and Drive API enabled
- OAuth2 credentials from Google Cloud Console

### Setup Steps

1. **Clone and install dependencies:**
   ```bash
   cd servers/google-docs-mcp-server
   npm install
   ```

2. **Set up Google Cloud credentials:**

   a. Go to [Google Cloud Console](https://console.cloud.google.com/)

   b. Create a new project or select an existing one

   c. Enable the required APIs:
      - Google Docs API
      - Google Drive API

   d. Create OAuth 2.0 credentials:
      - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
      - Choose "Desktop app" as the application type
      - Download the credentials JSON file

   e. Save the downloaded file as `credentials.json` in the server directory:
      ```bash
      # Place it here:
      servers/google-docs-mcp-server/credentials.json
      ```

3. **Build the server:**
   ```bash
   npm run build
   ```

4. **Authorize the application:**
   ```bash
   node dist/auth.js
   ```

   This will:
   - Display an authorization URL
   - Ask you to visit the URL and grant permissions
   - Request the authorization code
   - Generate a `token.json` file

5. **Verify setup:**
   ```bash
   # The following files should now exist:
   # - credentials.json (your OAuth2 credentials)
   # - token.json (your access/refresh tokens)
   ```

## Configuration

### Environment Variables

Create a `.env` file (optional) to customize paths:

```env
# Optional: Custom paths for credentials and token
GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json
GOOGLE_TOKEN_PATH=/path/to/token.json
```

If not specified, the server looks for `credentials.json` and `token.json` in the server directory.

### MCP Configuration

Add to your Claude Code configuration (`.mcp.json`):

```json
{
  "mcpServers": {
    "google-docs": {
      "command": "node",
      "args": [
        "/absolute/path/to/servers/google-docs-mcp-server/dist/index.js"
      ]
    }
  }
}
```

Or for Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "google-docs": {
      "command": "node",
      "args": [
        "/Users/yourusername/path/to/servers/google-docs-mcp-server/dist/index.js"
      ]
    }
  }
}
```

## Available Tools

### create_document
Create a new Google Doc.

**Parameters:**
- `title` (string, optional) - Title of the document
- `content` (string, optional) - Initial text content

**Example:**
```
Create a new document titled "Project Notes" with the content "Meeting notes from today's discussion"
```

### get_document
Retrieve the content of a Google Doc.

**Parameters:**
- `documentId` (string, required) - The ID of the document

**Example:**
```
Get the content of document 1abc2def3ghi4jkl5mno6pqr
```

### update_document
Update a Google Doc by appending or replacing content.

**Parameters:**
- `documentId` (string, required) - The ID of the document
- `text` (string, required) - Text to add or replace
- `mode` (string, optional) - "append" or "replace" (default: "append")

**Example:**
```
Append "## Next Steps\n- Review code\n- Test features" to document 1abc2def3ghi4jkl5mno6pqr
```

### list_documents
List your Google Docs.

**Parameters:**
- `pageSize` (number, optional) - Number of documents to return (max 100, default 20)
- `query` (string, optional) - Search query (e.g., 'name contains "report"')

**Example:**
```
List all documents with "meeting" in the name
```

### search_in_document
Search for text within a document.

**Parameters:**
- `documentId` (string, required) - The ID of the document
- `searchText` (string, required) - Text to search for

**Example:**
```
Search for "TODO" in document 1abc2def3ghi4jkl5mno6pqr
```

### insert_text
Insert text at a specific position.

**Parameters:**
- `documentId` (string, required) - The ID of the document
- `text` (string, required) - Text to insert
- `index` (number, required) - Character index (1 = start of document)

**Example:**
```
Insert "DRAFT - " at the beginning of document 1abc2def3ghi4jkl5mno6pqr
```

### delete_text_range
Delete a range of text.

**Parameters:**
- `documentId` (string, required) - The ID of the document
- `startIndex` (number, required) - Start position
- `endIndex` (number, required) - End position

**Example:**
```
Delete characters 50 through 100 in document 1abc2def3ghi4jkl5mno6pqr
```

## Usage Examples

### With Claude Code

```
User: Create a new document called "Weekly Report" and add a header

Claude: I'll create that document for you.
[Uses create_document tool with title "Weekly Report" and content "# Weekly Report\n\n"]

User: List my recent documents

Claude: Here are your recent documents...
[Uses list_documents tool]

User: Get the content of the first document

Claude: [Uses get_document tool with the document ID]
```

### Finding Document IDs

Document IDs can be found in several ways:
1. From the URL: `https://docs.google.com/document/d/{DOCUMENT_ID}/edit`
2. Using the `list_documents` tool
3. From the response when creating a new document

## Development

### Build
```bash
npm run build
```

### Watch mode (auto-rebuild)
```bash
npm run watch
```

### Re-authorize
If you need to re-authorize (e.g., changed scopes):
```bash
rm token.json
node dist/auth.js
```

## Troubleshooting

### "Credentials file not found"
Make sure `credentials.json` exists in the server directory. Download it from Google Cloud Console.

### "Token file not found"
Run the authorization script: `node dist/auth.js`

### "Invalid credentials"
Your OAuth2 credentials may be incorrect. Re-download from Google Cloud Console.

### "Insufficient permissions"
The token may not have the right scopes. Delete `token.json` and re-authorize.

### "API not enabled"
Make sure you've enabled both:
- Google Docs API
- Google Drive API

In your Google Cloud Console project.

## Security Notes

### Credentials Management
- **Never commit `credentials.json` or `token.json` to version control**
- These files contain sensitive authentication data
- Add them to `.gitignore`

### OAuth2 Scopes
This server requests the following scopes:
- `https://www.googleapis.com/auth/documents` - Full access to Google Docs
- `https://www.googleapis.com/auth/drive.readonly` - Read-only access to Drive (for listing docs)

### Token Storage
- Tokens are stored locally in `token.json`
- Refresh tokens allow persistent access
- Tokens expire and are automatically refreshed

## File Structure

```
google-docs-mcp-server/
├── src/
│   ├── index.ts          # Main MCP server implementation
│   └── auth.ts           # OAuth2 authorization helper
├── dist/                 # Compiled JavaScript (generated)
├── credentials.json      # OAuth2 credentials (not in git)
├── token.json           # Access tokens (not in git)
├── package.json         # Dependencies and scripts
├── tsconfig.json        # TypeScript configuration
├── .env                 # Environment variables (optional)
└── README.md           # This file
```

## Integration with Other Tools

### With Love Brittany Tracker
The Google Docs server can be used alongside the Love Brittany Tracker app to:
- Export relationship reports to Google Docs
- Create formatted weekly summaries
- Store historical data in organized documents

### With Todoist MCP Server
Combine with Todoist to:
- Create task lists from document outlines
- Export completed tasks to a Google Doc
- Generate weekly task summaries

## API Reference

### Google Docs API v1
This server uses the [Google Docs API v1](https://developers.google.com/docs/api/reference/rest/v1/documents).

### Google Drive API v3
For listing documents, the server uses [Google Drive API v3](https://developers.google.com/drive/api/v3/reference).

## Contributing

This is part of a personal workspace, but improvements are welcome:
- Keep tools focused and well-documented
- Follow existing patterns from other MCP servers
- Test with both Claude Code and Claude Desktop

## License

MIT

## Support

For issues specific to this MCP server:
- Check the troubleshooting section above
- Review Google API documentation
- Ensure credentials are properly configured

For general MCP questions:
- See [Model Context Protocol documentation](https://modelcontextprotocol.io/)
- Check other MCP servers in `servers/` directory

---

**Author:** Terrance Brandon
**Repository:** [My-Workspace-TB-](https://github.com/SonOfSamuel1/My-Workspace-TB-)
**Last Updated:** 2025-11-17
