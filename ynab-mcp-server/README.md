# YNAB MCP Server

A Model Context Protocol (MCP) server that provides integration with the YNAB (You Need A Budget) API. This server allows AI assistants like Claude to interact with your YNAB budgets, accounts, transactions, and more.

## Features

- **Budget Management**: Retrieve all budgets and detailed budget information
- **Accounts**: View and create accounts
- **Transactions**: Create, update, and query transactions across budgets, accounts, and categories
- **Categories**: View categories and update budgeted amounts
- **Payees**: Retrieve payee information
- **Scheduled Transactions**: Manage recurring transactions
- **Month Budgets**: View budget data by month
- **Delta Requests**: Efficiently sync only changed data

## Installation

1. Clone or download this repository
2. Install dependencies:

```bash
npm install
```

3. Build the TypeScript code:

```bash
npm run build
```

## Configuration

### Get Your YNAB API Token

1. Log in to YNAB at https://app.ynab.com
2. Go to Account Settings → Developer Settings
3. Click "New Token" and create a Personal Access Token
4. Copy your token (it will look like: `hYPZEhxFtOZh0f5BDQMXdqHUsX5yrNgJtUJmyJlkYDs`)

### Configure for Claude Code (CLI)

This repository is already configured for Claude Code! The configuration is in `.mcp.json` at the project root.

To use it:

1. Make sure you've built the project: `npm run build`
2. The MCP server is automatically available when you use Claude Code in this directory
3. Try asking: "Show me all my YNAB budgets"

If you cloned this repo, copy the example config and add your API key:

```bash
cp .mcp.json.example .mcp.json
# Edit .mcp.json and replace "your_ynab_api_key_here" with your actual key
```

The `.mcp.json` file format:

```json
{
  "mcpServers": {
    "ynab": {
      "command": "node",
      "args": ["dist/index.js"],
      "env": {
        "YNAB_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

### Configure for Claude Desktop

Add the server to your Claude Desktop configuration file:

**MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

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

After updating the configuration, restart Claude Desktop.

## Available Tools

### Budgets
- `ynab_get_budgets` - Get all budgets
- `ynab_get_budget` - Get detailed budget information

### Accounts
- `ynab_get_accounts` - Get all accounts for a budget
- `ynab_get_account` - Get a specific account
- `ynab_create_account` - Create a new account

### Categories
- `ynab_get_categories` - Get all categories
- `ynab_get_category` - Get a specific category
- `ynab_update_category` - Update category budget or goal for a month

### Transactions
- `ynab_get_transactions` - Get all transactions
- `ynab_get_transactions_by_account` - Get transactions for an account
- `ynab_get_transactions_by_category` - Get transactions for a category
- `ynab_get_transaction` - Get a specific transaction
- `ynab_create_transaction` - Create a new transaction
- `ynab_update_transaction` - Update an existing transaction

### Payees
- `ynab_get_payees` - Get all payees
- `ynab_get_payee` - Get a specific payee

### Scheduled Transactions
- `ynab_get_scheduled_transactions` - Get all scheduled transactions
- `ynab_get_scheduled_transaction` - Get a specific scheduled transaction
- `ynab_create_scheduled_transaction` - Create a new scheduled transaction
- `ynab_update_scheduled_transaction` - Update a scheduled transaction
- `ynab_delete_scheduled_transaction` - Delete a scheduled transaction

### Budget Months
- `ynab_get_months` - Get all budget months
- `ynab_get_month` - Get a specific month's budget data

### User
- `ynab_get_user` - Get authenticated user information

## Usage Examples

Once configured with Claude Desktop, you can ask Claude to:

- "Show me all my YNAB budgets"
- "What are my checking account transactions from last month?"
- "Create a transaction for $50 at Starbucks in my Coffee category"
- "How much did I budget for groceries this month?"
- "Show me all my scheduled transactions"
- "What's my current account balance?"

## Important Notes

### Amount Format
YNAB uses "milliunits" for all monetary amounts:
- **1000 milliunits = $1.00**
- **-25000 milliunits = -$25.00 (outflow)**
- **100000 milliunits = $100.00 (inflow)**

When creating or updating transactions, multiply dollar amounts by 1000.

### Date Format
All dates should be in ISO 8601 format: `YYYY-MM-DD`
- Example: `2025-01-15`

### Rate Limiting
The YNAB API has a rate limit of **200 requests per hour** per access token.

### Delta Requests
Many endpoints support `last_knowledge_of_server` parameter to only fetch changed data, reducing API calls and improving performance.

## Development

### Build
```bash
npm run build
```

### Watch Mode
```bash
npm run watch
```

### Run Directly
```bash
YNAB_API_KEY="your_token_here" npm start
```

## API Reference

For detailed YNAB API documentation, visit: https://api.ynab.com/

## License

MIT

## Support

For issues with this MCP server, please create an issue in the repository.

For YNAB API questions, refer to the official YNAB API documentation.
