# Email Agent Quick Start Guide

## 🚀 See the Agent in Action (3 minutes)

### Option 1: Interactive Demo (Recommended)

Run the interactive demo to see how the agent processes different types of requests:

```bash
# 1. Run the demo (works without any setup)
node scripts/demo-agent.js
```

This will show you:
- ✅ Simple information requests
- ✅ Web automation with Playwright
- ✅ Data processing and analysis
- ✅ Agent statistics and history

**Note:** The demo runs in mock mode without an API key. To see real AI reasoning, continue to Option 2.

---

### Option 2: Live Agent with OpenRouter (5 minutes)

Test the agent with real AI reasoning using OpenRouter:

#### Step 1: Get OpenRouter API Key

1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up (free $5 credit for new accounts)
3. Get your API key from the dashboard

#### Step 2: Configure Environment

Create a `.env` file in the project root:

```bash
# Required for live agent
OPENROUTER_API_KEY=sk-or-v1-YOUR-KEY-HERE

# Optional customization
AGENT_EMAIL=assistant@yourdomain.com
REASONING_MODEL=deepseek/deepseek-r1
LOG_LEVEL=info
```

#### Step 3: Run the Test

```bash
# Run the full test suite
npm run agent:test

# Or run the interactive demo with real AI
node scripts/demo-agent.js
```

---

### Option 3: Manual Testing

Send a test email programmatically:

```javascript
const emailAgentSetup = require('./lib/email-agent-setup');

async function test() {
  // Initialize
  await emailAgentSetup.initialize();

  // Send test request
  const result = await emailAgentSetup.processSingleEmail({
    id: 'test1',
    from: 'you@example.com',
    to: 'assistant@yourdomain.com',
    subject: 'Test request',
    body: 'Can you check if example.com is up?',
    date: new Date().toISOString()
  });

  console.log('Result:', result);

  // Cleanup
  await emailAgentSetup.shutdown();
}

test();
```

---

## 📧 What the Agent Can Do

### 1. **Information Requests**
```
Subject: Quick question
Body: What time is it in New York?

Agent Response: Provides current time using data processing tool
```

### 2. **Web Automation**
```
Subject: Website check
Body: Navigate to example.com and tell me if it's up

Agent Response: Uses Playwright to visit site and report status
```

### 3. **Calendar Management**
```
Subject: Meeting tomorrow
Body: Create a calendar event for 2 PM tomorrow titled "Team Standup"

Agent Response: Uses calendar tool to create the event
```

### 4. **Data Analysis**
```
Subject: Sales data
Body: Analyze this sales report and extract key metrics: [data]

Agent Response: Uses data tool to parse and analyze
```

### 5. **Multi-Step Workflows**
```
Subject: Research competitor
Body: Navigate to competitor.com, extract their pricing, and create a comparison table

Agent Response: Chains multiple tools to complete the task
```

---

## 🔧 Available Tools

| Tool | Description | Example Use |
|------|-------------|-------------|
| **Playwright** | Web automation | Navigate sites, fill forms, extract data, screenshots |
| **Calendar** | Event management | Create/list/cancel events, check availability |
| **Data** | Processing | Analyze text, extract metrics, format data |

---

## 🛡️ Safety Features

The agent includes built-in safety checks:

- **Auto-approve patterns** - Low-risk actions like "check status" run automatically
- **Approval required** - High-risk actions like "delete data" require explicit approval
- **Domain restrictions** - Can block specific domains (banks, payment processors)
- **Action limits** - Maximum actions per email to prevent runaway processes
- **Audit trail** - All actions logged with full history

Configure in `config/email-agent-config.js`

---

## 💰 Cost Estimates

Using OpenRouter with DeepSeek R1 (recommended):

- **Input:** $0.14 per 1M tokens
- **Output:** $0.28 per 1M tokens

Typical costs:
- Simple request (check status): ~$0.0001
- Web automation (navigate + extract): ~$0.0005
- Complex workflow (5 steps): ~$0.002

**Monthly estimate** (100 requests/day): ~$6-15

For comparison, OpenAI o1 is 100x more expensive.

---

## 🔗 Integration with Main System

To integrate the Email Agent with your existing email management:

### In your main handler:

```javascript
const emailAgentSetup = require('./lib/email-agent-setup');
const config = require('./config/email-agent-config');

async function handleEmail(email) {
  // Check if agent is CC'd or directly addressed
  const isAgentEmail =
    email.to?.includes(config.agentEmail) ||
    email.cc?.some(cc => cc.includes(config.agentEmail));

  if (isAgentEmail) {
    // Let agent handle it
    return await emailAgentSetup.processSingleEmail(email);
  }

  // Regular email processing
  return await processEmailNormally(email);
}
```

---

## 📊 Monitoring

Check agent status:

```javascript
const status = emailAgentSetup.getStatus();
console.log('Total actions:', status.statistics.totalActions);
console.log('Success rate:', status.statistics.successRate);
console.log('Available tools:', status.statistics.availableTools);
```

View action history:

```javascript
const history = emailAgentSetup.getActionHistory(10);
history.forEach(action => {
  console.log('Intent:', action.understanding.intent);
  console.log('Success:', action.execution?.overallSuccess);
  console.log('Time:', action.timestamp);
});
```

---

## 🐛 Troubleshooting

### Agent not initializing

**Issue:** `OpenRouter API key is required`

**Solution:** Set `OPENROUTER_API_KEY` in `.env` file

---

### Playwright errors

**Issue:** `Browser not found`

**Solution:** Install Playwright browsers:
```bash
npx playwright install
```

---

### OpenRouter API errors

**Issue:** `Rate limit exceeded`

**Solution:**
- Reduce request frequency
- Switch to higher tier plan
- Use DeepSeek R1 (cheaper than GPT-4)

---

### Tool execution timeouts

**Issue:** `Timeout waiting for page`

**Solution:** Increase timeout in `config/email-agent-config.js`:
```javascript
tools: {
  playwright: {
    timeout: 60000  // 60 seconds
  }
}
```

---

## 🎯 Next Steps

1. ✅ Run `node scripts/demo-agent.js` to see the agent in action
2. ✅ Get OpenRouter API key for live testing
3. ✅ Configure agent email address
4. ✅ Test with your own requests
5. ✅ Integrate with Gmail MCP for production use
6. ✅ Deploy to GitHub Actions or AWS Lambda

For full deployment guide, see [README.md](README.md)

---

## 📚 Additional Resources

- **Email Agent Documentation:** [EMAIL-AGENT.md](EMAIL-AGENT.md)
- **Configuration Guide:** [config/email-agent-config.js](config/email-agent-config.js)
- **API Reference:** [lib/email-agent.js](lib/email-agent.js)
- **Tool Documentation:** [lib/tools/](lib/tools/)

---

**Questions?** Check the troubleshooting section in [EMAIL-AGENT.md](EMAIL-AGENT.md)
