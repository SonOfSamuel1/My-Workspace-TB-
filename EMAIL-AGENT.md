# Email Agent System

## Overview

The Email Agent is a dedicated email address that you can CC or directly email to trigger intelligent autonomous actions. It uses OpenRouter reasoning models to understand your requests and can execute complex tasks using tools like Playwright for web automation, calendar management, and data processing.

## How It Works

```
┌─────────────────┐
│  Email Arrives  │
│  to Agent       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Understanding  │◄─── OpenRouter Reasoning Model
│  Request        │     (DeepSeek R1, OpenAI o1, etc.)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Safety Check   │◄─── Financial, Legal, Sensitive
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Execute        │◄─── Playwright, Calendar, Data
│  Actions        │     Tools
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Send Response  │
│  Email          │
└─────────────────┘
```

## Features

### 🤖 Intelligent Understanding
- Uses OpenRouter reasoning models (DeepSeek R1, OpenAI o1, Gemini 2.0)
- Understands natural language requests
- Extracts intent, actions, and parameters
- Provides reasoning for decisions

### 🛠️ Autonomous Tools

**Playwright Tool** (Web Automation)
- Navigate to websites
- Click buttons and links
- Fill out forms
- Extract data from pages
- Take screenshots
- Wait for elements
- Scroll pages
- Submit forms

**Calendar Tool**
- Create calendar events
- Check availability
- List upcoming events
- Cancel events

**Data Tool**
- Analyze text
- Extract structured data
- Format data
- Perform calculations

### 🔒 Safety Features
- Safety mode with approval workflow
- Auto-approve patterns for low-risk actions
- Financial impact checks
- Legal risk detection
- Sensitive content filtering
- Recipient validation
- Action history tracking

## Setup

### 1. Install Dependencies

```bash
npm install
```

New dependencies added:
- `playwright` ^1.40.1 - Web automation
- `axios` ^1.6.2 - HTTP client for OpenRouter API

### 2. Configure Environment Variables

Add to your `.env` file:

```env
# Email Agent Configuration
AGENT_EMAIL=assistant@yourdomain.com
OPENROUTER_API_KEY=sk-or-v1-...

# Optional: Specify reasoning model (defaults to deepseek/deepseek-r1)
REASONING_MODEL=deepseek/deepseek-r1

# Optional: Fallback model if primary fails
FALLBACK_MODEL=anthropic/claude-3.5-sonnet
```

### 3. Set Up Agent Email Address

**Option A: Gmail Alias**
1. Go to Gmail Settings → Accounts and Import
2. Add email alias: `assistant@yourdomain.com`
3. Configure forwarding to your main inbox

**Option B: Dedicated Gmail Account**
1. Create new Gmail account: `assistant@yourdomain.com`
2. Enable Gmail API access
3. Configure OAuth credentials

**Option C: Custom Domain**
1. Set up email forwarding from `assistant@yourdomain.com`
2. Forward to your monitored inbox
3. Configure MCP to filter by TO/CC address

### 4. Configure OpenRouter

1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Get your API key from the dashboard
3. Add credits to your account
4. Set `OPENROUTER_API_KEY` in `.env`

### 5. Initialize the Agent

```javascript
const emailAgentSetup = require('./lib/email-agent-setup');

async function start() {
  // Initialize agent
  const result = await emailAgentSetup.initialize();
  console.log(`Agent ready: ${result.agentEmail}`);
  console.log(`Tools: ${result.capabilities.tools.join(', ')}`);

  // Start monitoring (if using polling)
  await emailAgentSetup.startMonitoring(gmailClient);
}

start();
```

## Configuration

### config/email-agent-config.js

```javascript
module.exports = {
  // Agent email address
  agentEmail: process.env.AGENT_EMAIL || 'assistant@yourdomain.com',

  // OpenRouter configuration
  openRouter: {
    apiKey: process.env.OPENROUTER_API_KEY,
    reasoningModel: process.env.REASONING_MODEL || 'deepseek/deepseek-r1',
    fallbackModel: 'anthropic/claude-3.5-sonnet',
    timeout: 30000,
    maxTokens: 4000
  },

  // Safety settings
  safety: {
    enabled: true,
    requireApproval: [
      'financial_transaction',
      'delete_data',
      'send_email_external',
      'modify_calendar'
    ],
    autoApprove: [
      'check status',
      'get information',
      'read data',
      'view calendar'
    ],
    maxActionsPerEmail: 10,
    sensitiveKeywords: ['password', 'credit card', 'ssn', 'confidential']
  },

  // Tool configuration
  tools: {
    playwright: {
      enabled: true,
      headless: true,
      timeout: 30000,
      maxPages: 5,
      allowedDomains: [] // Empty = all domains allowed
    },
    calendar: {
      enabled: true,
      provider: 'google', // google, outlook, caldav
      defaultDuration: 30
    },
    data: {
      enabled: true,
      maxDataSize: 10 * 1024 * 1024, // 10MB
      allowedFormats: ['json', 'csv', 'xml', 'txt']
    }
  },

  // Monitoring settings
  monitoring: {
    pollInterval: 60000, // 1 minute
    maxEmailsPerCycle: 10,
    retryAttempts: 3
  }
};
```

## Usage Examples

### Example 1: Check Website Status

**Email:**
```
To: assistant@yourdomain.com
Subject: Check website status

Can you navigate to example.com and tell me if it's up and what the main heading says?
```

**Agent Response:**
```
Hi,

I've processed your request.

**What I understood:**
Check website status for example.com

**Actions taken:**
✅ Navigate to example.com
✅ Extract page data

Website is up. Main heading: "Example Domain"
Page loaded successfully in 1.2 seconds.

**Status:** All actions completed successfully.

Best regards,
Your Email Assistant
```

### Example 2: Calendar Check

**Email:**
```
To: assistant@yourdomain.com
Subject: What's on my calendar today?

Can you check my calendar and let me know what meetings I have today?
```

**Agent Response:**
```
Hi,

I've processed your request.

**What I understood:**
Check calendar for today's meetings

**Actions taken:**
✅ List calendar events for 2025-11-07

You have 3 meetings today:
- 9:00 AM - Team Standup (30 min)
- 2:00 PM - Client Review (1 hour)
- 4:30 PM - Project Planning (45 min)

**Status:** All actions completed successfully.

Best regards,
Your Email Assistant
```

### Example 3: Form Automation

**Email:**
```
To: assistant@yourdomain.com
Subject: Fill out contact form

Go to example.com/contact and fill out the form with:
- Name: John Doe
- Email: john@example.com
- Message: Please send me information about your services
```

**Agent Response (with Safety Check):**
```
Hi,

I need your approval to proceed with the following actions:

**What I understood:**
Fill out contact form on example.com/contact

**Planned actions:**
- Navigate to example.com/contact using playwright
- Fill form field 'name' with 'John Doe'
- Fill form field 'email' with 'john@example.com'
- Fill form field 'message' with 'Please send me information about your services'
- Submit form

**Safety level:** medium

Please reply with "APPROVE" to proceed or "DENY" to cancel.

Best regards,
Your Email Assistant
```

### Example 4: Data Analysis

**Email:**
```
To: assistant@yourdomain.com
Subject: Analyze sales data

Can you analyze this text and extract key metrics?

Sales Report Q4 2024:
- Total Revenue: $1.2M
- New Customers: 45
- Retention Rate: 92%
```

**Agent Response:**
```
Hi,

I've processed your request.

**What I understood:**
Extract and analyze sales metrics from Q4 2024 report

**Actions taken:**
✅ Analyze text data
✅ Extract key metrics

**Extracted Metrics:**
- Total Revenue: $1,200,000
- New Customers: 45
- Retention Rate: 92%
- Period: Q4 2024

**Analysis:**
Strong quarter with high retention. Revenue growth indicates healthy business.

**Status:** All actions completed successfully.

Best regards,
Your Email Assistant
```

## Available Reasoning Models

OpenRouter provides access to multiple reasoning models:

| Model | Provider | Strengths | Cost |
|-------|----------|-----------|------|
| deepseek/deepseek-r1 | DeepSeek | Fast, cost-effective, great reasoning | Low |
| openai/o1 | OpenAI | Advanced reasoning, high accuracy | High |
| openai/o1-mini | OpenAI | Balanced speed and reasoning | Medium |
| google/gemini-2.0-flash-thinking-exp | Google | Fast thinking, experimental | Medium |
| anthropic/claude-3.5-sonnet | Anthropic | Reliable, well-rounded | Medium-High |

Configure in `config/email-agent-config.js`:

```javascript
openRouter: {
  reasoningModel: 'deepseek/deepseek-r1', // Primary model
  fallbackModel: 'anthropic/claude-3.5-sonnet' // Backup if primary fails
}
```

## Testing

### Run Test Script

```bash
npm run agent:test
```

This will:
1. Initialize the agent
2. Test information request handling
3. Test web automation request
4. Display agent statistics
5. Show action history

### Manual Testing

```javascript
const emailAgentSetup = require('./lib/email-agent-setup');

async function testManually() {
  // Initialize
  await emailAgentSetup.initialize();

  // Test email
  const testEmail = {
    id: 'test1',
    from: 'user@example.com',
    to: 'assistant@yourdomain.com',
    subject: 'Test request',
    body: 'Can you navigate to example.com and tell me the page title?',
    date: new Date().toISOString()
  };

  // Process
  const result = await emailAgentSetup.processSingleEmail(testEmail);

  console.log('Result:', result);

  // Cleanup
  await emailAgentSetup.shutdown();
}

testManually();
```

## Integration with Main Email System

### Option 1: CC the Agent

In your main email handler (`handler.js`), detect when the agent is CC'd:

```javascript
async function handleEmail(email) {
  const agentEmail = config.agentEmail;

  // Check if agent is CC'd
  const isAgentCCd = email.cc?.some(cc =>
    cc.toLowerCase().includes(agentEmail.toLowerCase())
  );

  if (isAgentCCd) {
    // Process with agent
    const agentResult = await emailAgentSetup.processSingleEmail(email);

    if (agentResult.processed) {
      logger.info('Agent handled email', { emailId: email.id });
      return agentResult;
    }
  }

  // Regular email processing
  return await processEmailNormally(email);
}
```

### Option 2: Direct Agent Emails

Filter emails sent directly to the agent:

```javascript
async function handleEmail(email) {
  const agentEmail = config.agentEmail;

  // Check if email is directly to agent
  const isDirectToAgent = email.to?.toLowerCase().includes(agentEmail.toLowerCase());

  if (isDirectToAgent) {
    // Only agent processes this
    return await emailAgentSetup.processSingleEmail(email);
  }

  // Regular email processing
  return await processEmailNormally(email);
}
```

### Option 3: Hybrid Approach

```javascript
async function handleEmail(email) {
  const agentEmail = config.agentEmail;

  const isDirectToAgent = email.to?.toLowerCase().includes(agentEmail.toLowerCase());
  const isAgentCCd = email.cc?.some(cc =>
    cc.toLowerCase().includes(agentEmail.toLowerCase())
  );

  if (isDirectToAgent) {
    // Direct email: Agent handles exclusively
    return await emailAgentSetup.processSingleEmail(email);
  } else if (isAgentCCd) {
    // CC'd: Agent assists, but don't send duplicate responses
    const agentResult = await emailAgentSetup.processSingleEmail(email);

    // Return agent result but suppress auto-response
    agentResult.suppressResponse = true;
    return agentResult;
  }

  // Regular email processing
  return await processEmailNormally(email);
}
```

## Security Considerations

### 1. API Key Protection
- Never commit `.env` files
- Use environment variables in production
- Rotate API keys regularly

### 2. Tool Restrictions
```javascript
tools: {
  playwright: {
    allowedDomains: ['example.com', 'trusted-site.com'],
    blockedKeywords: ['admin', 'delete', 'drop table']
  }
}
```

### 3. Approval Workflow
```javascript
safety: {
  requireApproval: [
    'financial_transaction',
    'delete_data',
    'send_email_external',
    'modify_database'
  ]
}
```

### 4. Action Limits
```javascript
safety: {
  maxActionsPerEmail: 10,
  maxToolExecutionTime: 60000, // 1 minute
  maxConcurrentActions: 3
}
```

## Monitoring and Debugging

### Check Agent Status

```javascript
const status = emailAgentSetup.getStatus();

console.log('Initialized:', status.initialized);
console.log('Monitoring:', status.monitoring);
console.log('Total Actions:', status.statistics.totalActions);
console.log('Success Rate:', status.statistics.successRate);
console.log('Enabled Tools:', status.statistics.availableTools);
```

### View Action History

```javascript
const history = emailAgentSetup.getActionHistory(10); // Last 10 actions

history.forEach(action => {
  console.log('Email:', action.email.subject);
  console.log('Intent:', action.understanding.intent);
  console.log('Actions:', action.execution?.results?.length || 0);
  console.log('Success:', action.execution?.overallSuccess ? 'Yes' : 'No');
  console.log('---');
});
```

### Enable Debug Logging

```javascript
// In config/email-agent-config.js
module.exports = {
  logging: {
    level: 'debug', // debug, info, warn, error
    enableRequestLogging: true,
    enableToolLogging: true
  }
};
```

## Cost Management

### OpenRouter Pricing (approximate)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|----------------------|
| deepseek/deepseek-r1 | $0.14 | $0.28 |
| openai/o1 | $15.00 | $60.00 |
| openai/o1-mini | $3.00 | $12.00 |
| gemini-2.0-flash-thinking | $0.10 | $0.40 |
| claude-3.5-sonnet | $3.00 | $15.00 |

### Cost Optimization Tips

1. **Use DeepSeek R1 for most tasks** - 100x cheaper than OpenAI o1
2. **Set token limits** - Prevent runaway costs
3. **Cache common prompts** - Reduce API calls
4. **Monitor usage** - Track costs in real-time

```javascript
openRouter: {
  maxTokens: 2000, // Limit response size
  temperature: 0.7,  // Lower = more deterministic (less cost)
  cachePrompts: true // Enable prompt caching
}
```

## Troubleshooting

### Agent Not Processing Emails

**Check:**
1. Is `AGENT_EMAIL` configured correctly?
2. Is `OPENROUTER_API_KEY` set?
3. Is the agent initialized? (`emailAgentSetup.initialized === true`)
4. Are emails reaching the agent address?

**Debug:**
```javascript
const status = emailAgentSetup.getStatus();
console.log('Status:', status);
```

### OpenRouter API Errors

**Common Issues:**
- Invalid API key → Check `.env` file
- Rate limit exceeded → Reduce request frequency
- Model not available → Switch to fallback model

**Solution:**
```javascript
// Add error handling
try {
  const result = await emailAgentSetup.processSingleEmail(email);
} catch (error) {
  if (error.message.includes('rate limit')) {
    // Wait and retry
    await new Promise(resolve => setTimeout(resolve, 5000));
    return await emailAgentSetup.processSingleEmail(email);
  }
  throw error;
}
```

### Playwright Timeouts

**Issue:** Web pages take too long to load

**Solution:**
```javascript
tools: {
  playwright: {
    timeout: 60000, // Increase to 60 seconds
    waitUntil: 'domcontentloaded' // Don't wait for all resources
  }
}
```

### Safety Checks Blocking Actions

**Issue:** Too many actions require approval

**Solution:**
```javascript
safety: {
  autoApprove: [
    'check status',
    'get information',
    'read data',
    'view calendar',
    'navigate website' // Add more auto-approve patterns
  ]
}
```

## Advanced Usage

### Custom Tools

Create your own tools:

```javascript
// lib/tools/my-custom-tool.js
class MyCustomTool {
  constructor() {
    this.name = 'my_custom_tool';
    this.description = 'Does something custom';
  }

  register(agent) {
    agent.registerTool(this.name, this);
  }

  async execute(parameters) {
    // Your custom logic here
    return {
      success: true,
      result: 'Custom action completed'
    };
  }
}

module.exports = new MyCustomTool();
```

Register in `lib/email-agent-setup.js`:

```javascript
const myCustomTool = require('./tools/my-custom-tool');

// In initialize()
if (config.tools.myCustom?.enabled) {
  myCustomTool.register(emailAgent);
}
```

### Multi-Step Workflows

The agent can chain multiple actions:

**Email:**
```
Navigate to example.com, extract the contact email,
then create a calendar event to follow up in 2 days.
```

**Agent Understanding:**
```json
{
  "intent": "Multi-step workflow",
  "requiresAction": true,
  "actions": [
    {
      "type": "navigate",
      "tool": "playwright",
      "parameters": { "url": "example.com" }
    },
    {
      "type": "extract",
      "tool": "playwright",
      "parameters": { "selector": "[href^='mailto:']" }
    },
    {
      "type": "create_event",
      "tool": "calendar",
      "parameters": {
        "title": "Follow up with example.com",
        "date": "2025-11-09",
        "duration": 30
      }
    }
  ]
}
```

### Conditional Logic

The reasoning model can make decisions:

**Email:**
```
Check if example.com is up. If it's down, send me an alert.
If it's up, check the response time and let me know if it's slower than 2 seconds.
```

The model will reason through the conditional logic and execute the appropriate actions.

## Best Practices

### 1. Be Specific in Requests
✅ Good: "Navigate to example.com/pricing and extract the price for the Pro plan"
❌ Bad: "Check pricing"

### 2. Use Safety Checks for Sensitive Actions
Always require approval for:
- Financial transactions
- Data deletion
- External communications
- System modifications

### 3. Monitor Action History
Regularly review what the agent is doing:
```javascript
const history = emailAgentSetup.getActionHistory(50);
// Analyze patterns, identify issues
```

### 4. Set Appropriate Timeouts
```javascript
tools: {
  playwright: {
    timeout: 30000, // 30 seconds for most pages
    slowPages: {
      'heavy-site.com': 60000 // 60 seconds for specific sites
    }
  }
}
```

### 5. Use Template Responses
For common requests, create templates:
```javascript
autoResponseTemplates: {
  'website_status': 'Website {url} is {status}. Response time: {time}ms',
  'calendar_check': 'You have {count} meetings today: {list}'
}
```

## FAQ

**Q: Can the agent access my entire inbox?**
A: Only emails sent TO or CC'd to the agent email address are processed.

**Q: What happens if OpenRouter is down?**
A: The agent will attempt to use the fallback model. If both fail, an error response is sent.

**Q: Can I use multiple agent email addresses?**
A: Yes, initialize multiple agent instances with different configurations.

**Q: How do I disable specific tools?**
A: Set `enabled: false` in the tool configuration.

**Q: Is there a limit to how many actions per email?**
A: Yes, default is 10 actions per email (configurable via `maxActionsPerEmail`).

**Q: Can the agent learn from my feedback?**
A: Not currently, but action history is recorded for future ML implementation.

**Q: What about email attachments?**
A: The agent can read attachment metadata. Processing attachment contents is planned for future versions.

## Roadmap

- [ ] Attachment content processing
- [ ] Learning from user feedback
- [ ] Multi-agent collaboration
- [ ] Voice command integration
- [ ] Mobile app for approvals
- [ ] Advanced workflow builder
- [ ] Custom reasoning model fine-tuning
- [ ] Real-time action streaming
- [ ] Integration with more tools (Slack, GitHub, etc.)

## Support

For issues and questions:
- Review this documentation
- Check the troubleshooting section
- Review action history for debugging
- Enable debug logging for detailed insights

## License

MIT License - See LICENSE file for details
