# Comet MCP Server

An MCP (Model Context Protocol) server that enables Claude Code to control and interact with the Comet browser through macOS desktop automation. This server uses AppleScript and the Accessibility API to send prompts, extract responses, and perform browser automation tasks without requiring browser DevTools or Playwright.

## Features

- **Send Prompts**: Send text prompts to Comet's assistant and retrieve responses
- **Browser Navigation**: Navigate to URLs within Comet
- **Content Extraction**: Extract text from the current page or assistant responses
- **Batch Processing**: Execute multiple prompts sequentially
- **Research Mode**: Conduct research with follow-up questions
- **Screenshot Capture**: Take screenshots of the Comet window
- **Session Management**: Clear conversations and check browser health

## Prerequisites

- macOS (required for AppleScript automation)
- Node.js 18 or higher
- Comet browser installed
- Accessibility permissions enabled for Terminal/VS Code

## Installation

1. Navigate to the server directory:
```bash
cd servers/comet-mcp-server
```

2. Install dependencies:
```bash
npm install
```

3. Build the TypeScript code:
```bash
npm run build
```

## Configuration

### Enable Accessibility Permissions

For the automation to work, you need to grant accessibility permissions:

1. Open **System Preferences** → **Security & Privacy** → **Privacy** → **Accessibility**
2. Add and enable the application you're running the server from:
   - Terminal.app (if using terminal)
   - Visual Studio Code (if using VS Code terminal)
   - Claude Code (if using Claude Code)

### Environment Variables

You can configure the server behavior using environment variables:

- `RESPONSE_TIMEOUT` - Maximum time to wait for responses (default: 30000ms)
- `STABILIZATION_TIME` - Time to wait for response to stabilize (default: 1000ms)
- `MAX_RETRIES` - Maximum retry attempts for operations (default: 3)
- `USE_CLIPBOARD_FALLBACK` - Use clipboard for text extraction (default: true)

## MCP Registration

Add the server to your `.claude/mcp.json` file:

```json
{
  "mcpServers": {
    "comet": {
      "command": "node",
      "args": ["servers/comet-mcp-server/dist/index.js"],
      "env": {
        "RESPONSE_TIMEOUT": "30000",
        "STABILIZATION_TIME": "1000",
        "MAX_RETRIES": "3",
        "USE_CLIPBOARD_FALLBACK": "true"
      }
    }
  }
}
```

## Available Tools

### comet_send_prompt
Send a prompt to Comet's assistant.

**Parameters:**
- `prompt` (string, required): The prompt text to send
- `wait_for_response` (boolean, optional): Whether to wait for response (default: true)

**Example:**
```typescript
await comet_send_prompt({
  prompt: "What is machine learning?",
  wait_for_response: true
});
```

### comet_wait_response
Wait for and extract the current response from Comet.

**Parameters:** None

### comet_navigate
Navigate to a URL in Comet browser.

**Parameters:**
- `url` (string, required): The URL to navigate to

**Example:**
```typescript
await comet_navigate({
  url: "https://example.com"
});
```

### comet_extract_page
Extract text content from the current page.

**Parameters:** None

### comet_screenshot
Take a screenshot of the Comet window.

**Parameters:**
- `filename` (string, optional): Filename for the screenshot (default: "comet-screenshot.png")

### comet_batch_prompts
Send multiple prompts sequentially.

**Parameters:**
- `prompts` (string[], required): Array of prompts to send

**Example:**
```typescript
await comet_batch_prompts({
  prompts: [
    "What is AI?",
    "How does machine learning work?",
    "What are neural networks?"
  ]
});
```

### comet_research_topic
Research a topic with follow-up questions.

**Parameters:**
- `topic` (string, required): The main topic to research
- `follow_up_questions` (string[], optional): Follow-up questions to ask

**Example:**
```typescript
await comet_research_topic({
  topic: "quantum computing",
  follow_up_questions: [
    "What are the main challenges?",
    "What companies are leading in this field?"
  ]
});
```

### comet_clear
Clear the current conversation in Comet.

**Parameters:** None

### comet_health_check
Check if Comet is running and responsive.

**Parameters:** None

### comet_type_text
Type text at the current cursor position.

**Parameters:**
- `text` (string, required): The text to type

### comet_press_enter
Press the Enter key in Comet.

**Parameters:** None

## Usage Examples

### Basic Research Workflow
```javascript
// 1. Send a research prompt
const response = await comet_send_prompt({
  prompt: "Research the latest developments in renewable energy"
});

// 2. Ask follow-up questions
const followUp = await comet_send_prompt({
  prompt: "What are the most promising technologies?"
});

// 3. Take a screenshot for reference
await comet_screenshot({
  filename: "renewable-energy-research.png"
});
```

### Web Navigation and Content Extraction
```javascript
// 1. Navigate to a website
await comet_navigate({
  url: "https://news.ycombinator.com"
});

// 2. Extract page content
const content = await comet_extract_page();

// 3. Ask Comet to summarize
await comet_send_prompt({
  prompt: "Summarize the top stories on this page"
});
```

### Batch Processing
```javascript
// Process multiple queries
const responses = await comet_batch_prompts({
  prompts: [
    "What is the capital of France?",
    "What is the population?",
    "What are the main landmarks?"
  ]
});
```

## Troubleshooting

### Common Issues

1. **"Comet is not responding"**
   - Ensure Comet browser is installed and can be launched
   - Check that Comet appears in Applications folder
   - Try launching Comet manually first

2. **"Cannot extract text"**
   - Verify Accessibility permissions are granted
   - Try enabling the clipboard fallback method
   - Check that Comet window is not minimized

3. **"AppleScript execution failed"**
   - Ensure Terminal/VS Code has Accessibility permissions
   - Check System Preferences → Security & Privacy → Privacy
   - Restart the application after granting permissions

4. **"Response timeout"**
   - Increase `RESPONSE_TIMEOUT` environment variable
   - Check if Comet is processing the request (loading indicator)
   - Ensure stable internet connection

### Debug Mode

To see detailed logs, run the server directly:

```bash
node servers/comet-mcp-server/dist/index.js
```

Logs will appear in stderr, which helps with debugging.

## Development

### Project Structure
```
comet-mcp-server/
├── src/
│   ├── index.ts              # MCP server entry point
│   ├── comet-client.ts       # Comet automation client
│   ├── applescript-bridge.ts # AppleScript execution wrapper
│   └── utils/
│       ├── wait.ts           # Waiting and polling utilities
│       └── parser.ts         # Response parsing utilities
├── applescript/              # AppleScript automation files
│   ├── activate-comet.scpt
│   ├── send-prompt.scpt
│   ├── extract-text.scpt
│   └── navigate-url.scpt
├── dist/                     # Compiled JavaScript
├── package.json
├── tsconfig.json
└── README.md
```

### Building

```bash
# Development build with watch mode
npm run dev

# Production build
npm run build

# Clean build artifacts
npm run clean
```

### Testing

Test the server manually:

```bash
# 1. Build the server
npm run build

# 2. Test directly
node dist/index.js

# 3. Or use with Claude Code after registering in mcp.json
```

### Extending

To add new tools:

1. Add AppleScript files in `applescript/` directory
2. Add methods to `CometClient` class
3. Define new tools in `index.ts` TOOLS array
4. Add tool handlers in the switch statement

## Limitations

- **macOS Only**: Uses AppleScript, which is macOS-specific
- **UI Dependent**: Relies on Comet's UI structure; may break with updates
- **No Network Inspection**: Cannot intercept network requests like Playwright
- **Sequential Processing**: Operations are sequential, not parallel
- **Text Extraction**: May require clipboard fallback if Accessibility API fails

## Security Considerations

- **Accessibility Permissions**: Grants significant system access
- **Clipboard Access**: May access clipboard contents when fallback is enabled
- **No Credential Storage**: Does not store or manage Comet credentials
- **Local Execution Only**: Runs locally, no remote access

## License

MIT

## Contributing

This is part of a personal monorepo. For issues or improvements:
1. Test changes thoroughly with Comet browser
2. Update AppleScript files carefully
3. Maintain backwards compatibility
4. Document any UI dependencies

## Support

For issues or questions:
- Check the troubleshooting section
- Review AppleScript files for UI dependencies
- Test with Accessibility Inspector to verify element paths

---

**Author:** Terrance Brandon
**Version:** 1.0.0
**Last Updated:** November 2024