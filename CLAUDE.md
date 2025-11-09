# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an autonomous email management system that runs via GitHub Actions or AWS Lambda. It uses Claude Code CLI with Gmail MCP to process emails hourly during business hours, classify them into tiers, handle routine tasks autonomously, and escalate urgent items via SMS.

The system has two primary modes:
1. **Executive Assistant Mode**: Autonomous email processing with 4-tier classification (Escalate/Handle/Draft/Flag)
2. **Email Agent Mode**: Dedicated agent email address that uses OpenRouter reasoning models to execute autonomous actions via tools (Playwright, Calendar, Data)

## Development Commands

### Testing
```bash
# Run all tests
npm test

# Watch mode
npm run test:watch

# Coverage report
npm run test:coverage

# Test email agent specifically
npm run agent:test
```

### Email Agent
```bash
# Start the email agent system
npm run agent:start

# Test agent with sample requests
npm run agent:test
```

### Local Development
```bash
# Test Claude Code locally with MCP
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
claude --print --mcp-config ~/.config/claude/claude_code_config.json

# Debug mode with MCP
claude --debug --mcp-config ~/.config/claude/claude_code_config.json
```

### GitHub Actions
```bash
# Trigger workflow manually
gh workflow run "Hourly Email Management"

# View workflow logs
gh run list --workflow="Hourly Email Management"
```

### AWS Lambda
```bash
# Deploy Lambda function
cd lambda && ./setup-lambda.sh

# View Lambda logs
aws logs tail /aws/lambda/email-assistant-processor --follow

# Test Lambda function
aws lambda invoke --function-name email-assistant-processor response.json
```

## Architecture

### Two-System Design

**1. Executive Assistant (Main System)**
- Runs hourly via GitHub Actions or AWS Lambda
- Uses Claude Code CLI + Gmail MCP
- Processes all incoming emails
- 4-tier classification: Escalate (Tier 1), Handle (Tier 2), Draft (Tier 3), Flag (Tier 4)
- Autonomous actions for Tier 2, drafts for Tier 3, SMS escalation for Tier 1
- No external dependencies besides Claude Code subscription

**2. Email Agent (Autonomous Action System)**
- Triggered when dedicated agent email is CC'd or directly emailed
- Uses OpenRouter reasoning models (DeepSeek R1, OpenAI o1, Gemini 2.0)
- Three tools: Playwright (web automation), Calendar, Data processing
- Safety checks with approval workflow for sensitive actions
- Independent from main system, can be disabled

### Data Flow

```
Email arrives → Gmail MCP → Claude Code CLI → Classification (Tier 1-4)
                                              ↓
                          Tier 1: SMS Escalation + Label
                          Tier 2: Auto-handle + Send response
                          Tier 3: Draft for approval
                          Tier 4: Flag only, never send
```

For Email Agent:
```
Email to agent@ → Understanding (OpenRouter) → Safety Check → Execute Tools → Send Response
```

### Key Files

- [.github/workflows/hourly-email-management.yml](.github/workflows/hourly-email-management.yml) - GitHub Actions workflow, defines execution modes (morning_brief, eod_report, midday_check, hourly_process)
- [claude-agents/executive-email-assistant.md](claude-agents/executive-email-assistant.md) - Main agent specification defining tier classification rules, delegation levels, communication protocols
- [claude-agents/executive-email-assistant-config-terrance.md](claude-agents/executive-email-assistant-config-terrance.md) - User-specific config (email, timezone, off-limits contacts, communication style)
- [lib/email-agent.js](lib/email-agent.js) - Email Agent core system with OpenRouter integration
- [lib/email-agent-setup.js](lib/email-agent-setup.js) - Email Agent initialization and monitoring
- [lib/email-autopilot.js](lib/email-autopilot.js) - Autonomous decision making engine
- [lib/tools/playwright-tool.js](lib/tools/playwright-tool.js) - Web automation tool for agent
- [lib/tools/calendar-tool.js](lib/tools/calendar-tool.js) - Calendar management tool
- [lib/tools/data-tool.js](lib/tools/data-tool.js) - Data processing tool
- [config/email-agent-config.js](config/email-agent-config.js) - Email agent configuration (OpenRouter, safety, tools)

### Gmail MCP Integration

The system requires Gmail MCP server (`@gongrzhe/server-gmail-autoauth-mcp`) configured in `~/.config/claude/claude_code_config.json`. Credentials are stored in `~/.gmail-mcp/` directory:
- `gcp-oauth.keys.json` - OAuth client credentials from Google Cloud Console
- `credentials.json` - User token after OAuth flow

In GitHub Actions, these are base64-encoded and stored as secrets to avoid JSON escaping issues.

### Execution Modes

The workflow determines mode based on EST hour:
- **morning_brief** (7 AM): Overnight email summary, escalations, approval queue
- **eod_report** (5 PM): Full day summary, actions taken, pending items
- **midday_check** (1 PM): Only sends if Tier 1 urgent items exist
- **hourly_process** (all other hours): Silent processing, SMS for Tier 1 only

## Important Patterns

### Tier Classification Logic

The most critical aspect of this system is correct tier classification. Read [claude-agents/executive-email-assistant.md](claude-agents/executive-email-assistant.md) carefully to understand the classification rules.

**Key principle**: Be conservative during learning phase. If unsure, default to Tier 3 (draft for approval) rather than Tier 2 (autonomous send).

**Off-limits contacts** (defined in user config) ALWAYS get Tier 1 treatment regardless of content.

### Email Agent Request Processing

Email Agent uses a reasoning model to understand requests and decompose them into tool actions. The flow is:
1. Parse email content and extract intent
2. Determine if action is required (informational vs. actionable)
3. Safety check: Is this auto-approved or does it need approval?
4. Execute tool chain (can be multiple steps: navigate → extract → process)
5. Send structured response with reasoning, actions taken, and results

See [lib/email-agent.js](lib/email-agent.js) for implementation.

### Safety Checks

Email Agent has configurable safety mode (enabled by default). Actions are categorized:
- **Auto-approve**: Information retrieval, status checks, calendar views
- **Require approval**: Financial transactions, data deletion, external API calls, bulk email sends

Configure in [config/email-agent-config.js](config/email-agent-config.js).

### Tool Usage

Email Agent tools are designed to be composable:
- **Playwright**: Navigate, click, fill forms, extract data, take screenshots
- **Calendar**: Create events, check availability, list events, cancel
- **Data**: Analyze text, extract structured data, format data

Each tool validates parameters and handles errors gracefully.

## Configuration Files

### GitHub Secrets Required

For GitHub Actions deployment:
- `CLAUDE_CODE_OAUTH_TOKEN` - From `claude setup-token`
- `GMAIL_OAUTH_CREDENTIALS` - Base64-encoded `~/.gmail-mcp/gcp-oauth.keys.json`
- `GMAIL_CREDENTIALS` - Base64-encoded `~/.gmail-mcp/credentials.json`
- `TWILIO_ACCOUNT_SID` - Optional, for SMS escalation
- `TWILIO_AUTH_TOKEN` - Optional
- `TWILIO_FROM_NUMBER` - Optional

For Email Agent:
- `AGENT_EMAIL` - Dedicated agent email address
- `OPENROUTER_API_KEY` - From openrouter.ai dashboard
- `REASONING_MODEL` - Optional, defaults to `deepseek/deepseek-r1`

### Environment Variables

Set in `.env` for local development:
```bash
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
AGENT_EMAIL=assistant@yourdomain.com
OPENROUTER_API_KEY=sk-or-v1-...
REASONING_MODEL=deepseek/deepseek-r1
LOG_LEVEL=info
```

## Testing Strategy

When modifying the system:

1. **Test classification logic locally** - Use `claude --print` with sample email prompts
2. **Test Email Agent** - Run `npm run agent:test` to verify tool integration
3. **Manual workflow trigger** - Use GitHub Actions manual trigger before pushing changes
4. **Monitor action logs** - Check GitHub Actions artifacts for processing logs
5. **Review action history** - For Email Agent, check `emailAgentSetup.getActionHistory()`

## Common Modifications

### Adding New Gmail Labels

Edit [scripts/create-gmail-labels.js](scripts/create-gmail-labels.js) and run locally with Gmail MCP configured.

### Changing Classification Rules

Edit [claude-agents/executive-email-assistant.md](claude-agents/executive-email-assistant.md), commit, and the next workflow run will use updated rules.

### Adjusting Schedule

Edit [.github/workflows/hourly-email-management.yml](.github/workflows/hourly-email-management.yml) cron expression. Remember it's in UTC (EST + 5 hours).

### Adding Custom Email Agent Tools

Create new tool in `lib/tools/`, follow the pattern from existing tools (constructor with `name` and `description`, `register()` method, `execute()` method). Register in [lib/email-agent-setup.js](lib/email-agent-setup.js).

### Configuring OpenRouter Models

Available reasoning models in [config/email-agent-config.js](config/email-agent-config.js):
- `deepseek/deepseek-r1` - Default, fast, cost-effective
- `openai/o1` - Most advanced, expensive
- `openai/o1-mini` - Balanced
- `google/gemini-2.0-flash-thinking-exp` - Fast experimental

Set `fallbackModel` for resilience if primary fails.

## Cost Considerations

**Claude Code Max**: $100/month (existing subscription requirement)

**GitHub Actions**: Free tier includes 2,000 minutes/month. This workflow uses ~30 min/month.

**AWS Lambda** (optional): ~$2-5/month for hourly execution

**OpenRouter** (Email Agent only):
- DeepSeek R1: $0.14 per 1M input tokens, $0.28 per 1M output (recommended)
- OpenAI o1: $15 per 1M input, $60 per 1M output
- Set `maxTokens` in config to control costs

**Twilio SMS** (optional): ~$0.0075 per message

## Debugging

### Gmail MCP Not Loading
```bash
# Check config
cat ~/.config/claude/claude_code_config.json

# Verify credentials
cat ~/.gmail-mcp/credentials.json | jq '.'

# Test MCP server
npx @gongrzhe/server-gmail-autoauth-mcp
```

### Workflow Failures
Check GitHub Actions logs for:
- Invalid OAuth token (re-run `claude setup-token`)
- Expired Gmail credentials (re-authorize)
- Malformed base64 secrets (re-encode)

### Email Agent Not Processing
```javascript
const status = emailAgentSetup.getStatus();
console.log('Initialized:', status.initialized);
console.log('Tools:', status.statistics.availableTools);
```

### OpenRouter API Errors
- Invalid API key: Check `.env`
- Rate limit: Reduce polling frequency
- Model unavailable: Switch to fallback model

## Security Notes

- Never commit `.env` files or credential JSON files
- All secrets stored as GitHub encrypted secrets
- Base64 encoding prevents JSON escaping issues in GitHub Actions
- Headless mode (`--dangerously-skip-permissions`) is required for automation but only used in controlled GitHub Actions/Lambda environment
- Email Agent safety mode prevents dangerous actions without approval
- Playwright tool can be restricted to `allowedDomains` in config
