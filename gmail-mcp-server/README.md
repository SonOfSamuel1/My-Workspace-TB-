# Gmail MCP Server

A Model Context Protocol (MCP) server that provides Gmail integration for Claude and other MCP clients. This server allows you to read, send, search, and manage Gmail messages through the MCP protocol.

## Features

- **List Messages**: Retrieve messages from your inbox or specific labels
- **Read Messages**: Get full message content including headers and body
- **Send Emails**: Send emails with support for CC and BCC
- **Search Messages**: Search using Gmail's powerful search syntax
- **Manage Labels**: Get all Gmail labels
- **Thread Management**: Retrieve complete email threads
- **Message Actions**: Mark as read/unread, move to trash

## Prerequisites

- Node.js 18 or higher
- A Google Cloud Platform account
- Gmail API enabled

## Setup Instructions

### 1. Create Google Cloud Project and Enable Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

### 2. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Configure the OAuth consent screen if prompted:
   - Choose "External" user type
   - Fill in required fields (app name, user support email, developer email)
   - Add scopes: `gmail.readonly`, `gmail.send`, `gmail.modify`
   - Add your email as a test user
4. Create OAuth client ID:
   - Application type: "Desktop app"
   - Name: "Gmail MCP Server" (or any name you prefer)
5. Download the credentials JSON file

### 3. Install the MCP Server

```bash
cd gmail-mcp-server
npm install
npm run build
```

### 4. Set Up Authentication

1. Save your downloaded credentials file as `~/.gmail-mcp-credentials.json`:
   ```bash
   mv ~/Downloads/client_secret_*.json ~/.gmail-mcp-credentials.json
   ```

2. Run the authentication script:
   ```bash
   npm run auth
   ```

3. Follow the prompts:
   - A URL will be displayed
   - Open the URL in your browser
   - Sign in with your Google account
   - Grant the requested permissions
   - Copy the authorization code
   - Paste the code back into the terminal

4. The authentication token will be saved to `~/.gmail-mcp-token.json`

### 5. Configure Claude Desktop

Add the server to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "gmail": {
      "command": "node",
      "args": [
        "/absolute/path/to/gmail-mcp-server/dist/index.js"
      ]
    }
  }
}
```

Replace `/absolute/path/to/gmail-mcp-server` with the actual path to the gmail-mcp-server directory.

### 6. Restart Claude Desktop

After updating the configuration, restart Claude Desktop to load the Gmail MCP server.

## Available Tools

### `gmail_list_messages`

List email messages from Gmail.

**Parameters:**
- `maxResults` (optional): Maximum number of messages to return (default: 10, max: 100)
- `labelIds` (optional): Array of label IDs to filter by (e.g., `["INBOX", "UNREAD"]`)

**Example:**
```
List my 20 most recent emails
```

### `gmail_get_message`

Get the full content of a specific email message.

**Parameters:**
- `messageId` (required): The ID of the message to retrieve

**Example:**
```
Show me the full content of message ID 18c2f4b3a8e1d9f7
```

### `gmail_send_email`

Send an email via Gmail.

**Parameters:**
- `to` (required): Recipient email address
- `subject` (required): Email subject
- `body` (required): Email body (plain text)
- `cc` (optional): CC email addresses (comma-separated)
- `bcc` (optional): BCC email addresses (comma-separated)

**Example:**
```
Send an email to john@example.com with subject "Meeting Tomorrow" and body "Hi John, Let's meet at 2pm."
```

### `gmail_search_messages`

Search for messages using Gmail search syntax.

**Parameters:**
- `query` (required): Gmail search query
- `maxResults` (optional): Maximum number of messages to return (default: 10, max: 100)

**Example:**
```
Search for unread emails from john@example.com
```

**Search Query Examples:**
- `from:someone@example.com` - Emails from specific sender
- `subject:meeting` - Emails with "meeting" in subject
- `is:unread` - Unread emails
- `has:attachment` - Emails with attachments
- `after:2024/01/01` - Emails after a specific date
- `label:important` - Emails with specific label

### `gmail_get_labels`

Get all labels in the Gmail account.

**Example:**
```
Show me all my Gmail labels
```

### `gmail_get_thread`

Get all messages in an email thread.

**Parameters:**
- `threadId` (required): The ID of the thread to retrieve

**Example:**
```
Show me all messages in thread 18c2f4b3a8e1d9f7
```

### `gmail_trash_message`

Move a message to trash.

**Parameters:**
- `messageId` (required): The ID of the message to trash

**Example:**
```
Move message 18c2f4b3a8e1d9f7 to trash
```

### `gmail_mark_as_read`

Mark a message as read.

**Parameters:**
- `messageId` (required): The ID of the message to mark as read

**Example:**
```
Mark message 18c2f4b3a8e1d9f7 as read
```

### `gmail_mark_as_unread`

Mark a message as unread.

**Parameters:**
- `messageId` (required): The ID of the message to mark as unread

**Example:**
```
Mark message 18c2f4b3a8e1d9f7 as unread
```

## Troubleshooting

### "Credentials file not found"

Make sure you've saved your OAuth credentials to `~/.gmail-mcp-credentials.json`.

### "Token file not found"

Run `npm run auth` to authenticate and generate the token file.

### "Invalid grant" error

Your refresh token may have expired. Delete `~/.gmail-mcp-token.json` and run `npm run auth` again.

### "Insufficient permissions"

Make sure you've added all required scopes when creating your OAuth consent screen:
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.send`
- `https://www.googleapis.com/auth/gmail.modify`

### Gmail API quota limits

The Gmail API has usage quotas. If you encounter quota errors:
- Check your quota usage in Google Cloud Console
- Request a quota increase if needed
- Implement rate limiting in your usage

## Development

### Build

```bash
npm run build
```

### Watch mode

```bash
npm run watch
```

### Re-authenticate

```bash
npm run auth
```

## Security Notes

- Keep your credentials file (`~/.gmail-mcp-credentials.json`) secure and never commit it to version control
- The token file (`~/.gmail-mcp-token.json`) contains your access tokens - keep it secure
- Only grant access to trusted applications
- Regularly review your Google account's authorized applications

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
