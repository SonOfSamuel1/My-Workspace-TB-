# Email Assistant Deployment Guide

## Quick Deployment Checklist

- [ ] Claude Code CLI installed and authenticated
- [ ] Gmail MCP credentials configured
- [ ] GitHub repository created
- [ ] GitHub CLI (`gh`) installed and authenticated
- [ ] GitHub Secrets configured
- [ ] Workflow tested manually
- [ ] System deployed and running

---

## Prerequisites

### 1. Install Required Tools

```bash
# Install Claude Code CLI (if not already installed)
npm install -g @anthropic-ai/claude-code

# Install GitHub CLI
brew install gh  # macOS
# OR
# Download from https://cli.github.com/

# Authenticate GitHub CLI
gh auth login
```

### 2. Get Claude Code OAuth Token

```bash
# Generate your Claude Code token
claude setup-token

# Copy the token (starts with sk-ant-oat01-)
# You'll need this for GitHub Secrets
```

### 3. Set Up Gmail MCP (Already Done ✓)

Your Gmail MCP is already configured at:
- `~/.gmail-mcp/gcp-oauth.keys.json`
- `~/.gmail-mcp/credentials.json`

If you need to reconfigure:
```bash
# Install Gmail MCP server
npm install -g @gongrzhe/server-gmail-autoauth-mcp

# Configure in Claude Code
# Add to ~/.config/claude/claude_code_config.json
```

---

## Deployment Option 1: GitHub Actions (Recommended)

### Step 1: Push Code to GitHub

```bash
# If repository doesn't exist yet
gh repo create App--Internal-Business--Autonomous-Email-Assistant --private --source=. --remote=origin

# Commit your changes
git add .
git commit -m "feat: Email assistant ready for deployment"
git push -u origin main
```

### Step 2: Configure GitHub Secrets

**Automated Setup (Easiest):**

```bash
# Run the setup script
./scripts/setup-github-secrets.sh
```

The script will guide you through setting up:
1. `CLAUDE_CODE_OAUTH_TOKEN` - Your Claude Code token
2. `GMAIL_OAUTH_CREDENTIALS` - Automatically encoded from your local setup
3. `GMAIL_CREDENTIALS` - Automatically encoded from your local setup
4. `TWILIO_ACCOUNT_SID` - (Optional) For SMS escalations
5. `TWILIO_AUTH_TOKEN` - (Optional)
6. `TWILIO_FROM_NUMBER` - (Optional)
7. `OPENROUTER_API_KEY` - (Optional) For Email Agent

**Manual Setup (Alternative):**

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add each secret manually:

```bash
# Required secrets:
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-YOUR-TOKEN-HERE
GMAIL_OAUTH_CREDENTIALS=$(cat ~/.gmail-mcp/gcp-oauth.keys.json | base64)
GMAIL_CREDENTIALS=$(cat ~/.gmail-mcp/credentials.json | base64)

# Optional secrets (for SMS escalations):
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_FROM_NUMBER=+1234567890

# Optional secret (for Email Agent):
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### Step 3: Test the Workflow

**Manual Trigger:**

```bash
# Test in test mode (no actual emails sent)
gh workflow run "Hourly Email Management" --field test_mode=true

# Monitor the run
gh run watch

# Or view in browser
gh run list --workflow="Hourly Email Management"
```

**Check Workflow Status:**

```bash
# List recent runs
gh run list --limit 5

# View detailed logs
gh run view --log

# Download artifacts (processing logs)
gh run download
```

### Step 4: Verify Deployment

1. **Check that workflow is scheduled:**
   - Go to repository → Actions → "Hourly Email Management"
   - Should show scheduled runs

2. **Verify first run:**
   - Wait for next scheduled time (hourly from 7 AM - 5 PM EST, weekdays)
   - Or trigger manually for immediate test

3. **Monitor email processing:**
   - Check your email for morning brief (7 AM EST)
   - Check for end-of-day report (5 PM EST)
   - Verify SMS alerts if Twilio is configured

---

## Deployment Option 2: AWS Lambda

### Step 1: Set Up Lambda Environment

```bash
# Navigate to Lambda directory
cd lambda

# Make setup script executable
chmod +x setup-lambda.sh

# Run setup (requires AWS CLI configured)
./setup-lambda.sh
```

### Step 2: Configure Environment Variables

In AWS Lambda Console → Configuration → Environment variables:

```bash
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-YOUR-TOKEN
GMAIL_OAUTH_CREDENTIALS=<base64 encoded>
GMAIL_CREDENTIALS=<base64 encoded>
TWILIO_ACCOUNT_SID=<optional>
TWILIO_AUTH_TOKEN=<optional>
TWILIO_FROM_NUMBER=<optional>
OPENROUTER_API_KEY=<optional>
ESCALATION_PHONE=+14077448449
```

### Step 3: Set Up EventBridge Schedule

```bash
# Create schedule for hourly execution
aws events put-rule \
  --name email-assistant-hourly \
  --schedule-expression "cron(0 12-22 ? * MON-FRI *)" \
  --state ENABLED

# Add Lambda as target
aws events put-targets \
  --rule email-assistant-hourly \
  --targets "Id"="1","Arn"="arn:aws:lambda:REGION:ACCOUNT:function:email-assistant-processor"
```

### Step 4: Test Lambda Function

```bash
# Test locally with Docker
docker build -t email-assistant .
docker run -e CLAUDE_CODE_OAUTH_TOKEN=$CLAUDE_CODE_OAUTH_TOKEN email-assistant

# Test on AWS
aws lambda invoke \
  --function-name email-assistant-processor \
  --payload '{"mode": "hourly_process"}' \
  response.json

# View logs
aws logs tail /aws/lambda/email-assistant-processor --follow
```

---

## Configuration

### Execution Schedule

The system runs on this schedule (Eastern Time):

| Time | Mode | Behavior |
|------|------|----------|
| 7:00 AM | `morning_brief` | Overnight email summary + escalations |
| 8:00 AM - 12:00 PM | `hourly_process` | Silent processing, SMS for urgent only |
| 1:00 PM | `midday_check` | Only sends if urgent items exist |
| 2:00 PM - 4:00 PM | `hourly_process` | Silent processing |
| 5:00 PM | `eod_report` | Full day summary + pending approvals |

**To modify schedule:**

Edit [.github/workflows/hourly-email-management.yml](.github/workflows/hourly-email-management.yml#L5):

```yaml
schedule:
  - cron: "0 12-22 * * 1-5"  # Current: 7 AM - 5 PM EST, Mon-Fri
  # Change to:
  - cron: "0 13-23 * * 1-5"  # 8 AM - 6 PM EST
  - cron: "*/30 12-22 * * 1-5"  # Every 30 minutes
```

**Note:** GitHub Actions uses UTC, so add 5 hours to EST times.

### Email Classification Rules

Tier classification is defined in [claude-agents/executive-email-assistant.md](claude-agents/executive-email-assistant.md).

**To customize:**

1. Edit classification rules in the agent spec
2. Commit changes
3. Next workflow run will use updated rules

### User-Specific Configuration

Your personal preferences are in [claude-agents/executive-email-assistant-config-terrance.md](claude-agents/executive-email-assistant-config-terrance.md).

**To modify:**

- Email address
- Timezone
- Off-limits contacts
- Communication style
- Delegation level

### Email Agent Configuration

Email Agent settings are in [config/email-agent-config.js](config/email-agent-config.js).

**Key settings:**

```javascript
module.exports = {
  agentEmail: process.env.AGENT_EMAIL || 'assistant@yourdomain.com',

  openRouter: {
    reasoningModel: 'deepseek/deepseek-r1',  // Change model here
    maxTokens: 4000  // Adjust for cost control
  },

  safety: {
    enabled: true,  // Disable for auto-approve all actions
    requireApproval: [/* List of action types requiring approval */]
  },

  tools: {
    playwright: { enabled: true },
    calendar: { enabled: true },
    data: { enabled: true }
  }
};
```

---

## Testing

### Local Testing

Before deploying, test locally:

```bash
# Test Email Agent
npm run agent:test

# Run interactive demo
node scripts/demo-agent.js

# Test with Claude Code + Gmail MCP
claude --print --mcp-config ~/.config/claude/claude_code_config.json
```

### GitHub Actions Testing

```bash
# Manual trigger with test mode
gh workflow run "Hourly Email Management" --field test_mode=true

# Watch the run
gh run watch

# View logs
gh run view --log

# Check for errors
gh run list --workflow="Hourly Email Management" --limit 5
```

### Verification Checklist

After deployment:

- [ ] Morning brief arrives at 7 AM EST
- [ ] Hourly processing runs silently
- [ ] Tier 1 emails trigger SMS (if Twilio configured)
- [ ] Tier 2 emails get automatic responses
- [ ] Tier 3 emails have drafts created
- [ ] End-of-day report arrives at 5 PM EST
- [ ] Gmail labels are applied correctly
- [ ] Email Agent responds when CC'd (if configured)

---

## Monitoring

### View Processing Logs

**GitHub Actions:**

```bash
# List recent runs
gh run list --limit 10

# Download artifacts
gh run download <run-id>

# View specific run logs
gh run view <run-id> --log
```

**AWS Lambda:**

```bash
# Tail live logs
aws logs tail /aws/lambda/email-assistant-processor --follow

# Get recent logs
aws logs tail /aws/lambda/email-assistant-processor --since 1h

# Filter errors
aws logs filter-pattern /aws/lambda/email-assistant-processor "ERROR"
```

### Email Agent Statistics

If Email Agent is enabled:

```javascript
const emailAgentSetup = require('./lib/email-agent-setup');

// Get status
const status = emailAgentSetup.getStatus();
console.log('Total actions:', status.statistics.totalActions);
console.log('Success rate:', status.statistics.successRate);

// View history
const history = emailAgentSetup.getActionHistory(20);
history.forEach(action => {
  console.log('Email:', action.email.subject);
  console.log('Intent:', action.understanding.intent);
  console.log('Success:', action.execution?.overallSuccess);
});
```

### Health Checks

Monitor these indicators:

1. **Workflow success rate** - Should be >95%
2. **Email processing time** - Should complete in <5 minutes
3. **Classification accuracy** - Review flagged items weekly
4. **False escalations** - Adjust rules if too many Tier 1

---

## Troubleshooting

### Common Issues

**Issue: Workflow fails with "Invalid credentials"**

**Solution:**
```bash
# Re-encode credentials
cat ~/.gmail-mcp/gcp-oauth.keys.json | base64 | gh secret set GMAIL_OAUTH_CREDENTIALS
cat ~/.gmail-mcp/credentials.json | base64 | gh secret set GMAIL_CREDENTIALS
```

**Issue: Gmail MCP not loading**

**Solution:**
- Check that credentials are base64 encoded correctly
- Verify JSON is valid: `jq '.' ~/.gmail-mcp/credentials.json`
- Re-authenticate if token expired: `npx @gongrzhe/server-gmail-autoauth-mcp`

**Issue: Claude Code token expired**

**Solution:**
```bash
# Generate new token
claude setup-token

# Update secret
gh secret set CLAUDE_CODE_OAUTH_TOKEN -b"<new-token>"
```

**Issue: Workflow times out**

**Solution:**
- Increase timeout in workflow: `timeout-minutes: 15`
- Reduce batch size in processing
- Check for stuck API calls

**Issue: Email Agent not processing**

**Solution:**
- Verify `OPENROUTER_API_KEY` is set
- Check `AGENT_EMAIL` matches expected address
- Enable debug logging: `LOG_LEVEL=debug`

**Issue: SMS not sending**

**Solution:**
- Verify all Twilio secrets are set
- Check Twilio account balance
- Validate phone number format: `+1234567890`

---

## Cost Monitoring

### GitHub Actions

**Free tier:** 2,000 minutes/month

**This workflow usage:**
- ~2 minutes per run
- ~11 runs per weekday (7 AM - 5 PM hourly)
- ~22 weekdays per month
- **Total: ~480 minutes/month** (well within free tier)

### AWS Lambda

**Pricing:**
- $0.20 per 1M requests
- $0.0000166667 per GB-second

**Estimated cost:**
- ~242 invocations/month (11/day × 22 days)
- 1 GB memory, 30 second average duration
- **Total: ~$2-5/month**

### Claude Code Max

**Required:** Active subscription ($100/month)

### OpenRouter (Email Agent only)

**DeepSeek R1 pricing:**
- Input: $0.14 per 1M tokens
- Output: $0.28 per 1M tokens

**Estimated cost (100 agent requests/day):**
- ~3,000 requests/month
- Average 1,000 tokens per request
- **Total: ~$6-15/month**

### Twilio SMS (optional)

**Pricing:** ~$0.0075 per SMS

**Estimated cost (5 urgent escalations/day):**
- ~100 SMS/month
- **Total: ~$0.75/month**

### **Total Monthly Cost**

- **GitHub Actions:** $0 (free tier)
- **Claude Code Max:** $100 (existing subscription)
- **OpenRouter:** $6-15 (if Email Agent enabled)
- **Twilio:** $0.75 (if SMS enabled)

**Grand Total: $100-116/month**

---

## Security Best Practices

### Credential Management

✅ **Do:**
- Store credentials as GitHub Secrets
- Use base64 encoding to prevent JSON escaping
- Rotate tokens quarterly
- Use `--dangerously-skip-permissions` only in automated environments
- Enable safety mode for Email Agent

❌ **Don't:**
- Commit `.env` files
- Share OAuth tokens publicly
- Use personal tokens in shared repositories
- Disable safety checks in production

### Access Control

- Keep repository private
- Limit who can modify GitHub Secrets
- Use branch protection for `main`
- Review action logs regularly
- Monitor off-limits contact list

### Audit Trail

All actions are logged:
- GitHub Actions artifacts (30-day retention)
- Email Agent action history
- Gmail labels track all decisions
- SMS alerts for escalations

---

## Scaling and Optimization

### Handle More Emails

If processing >50 emails/hour:

1. Increase workflow timeout: `timeout-minutes: 15`
2. Add parallel processing in handler
3. Consider AWS Lambda for better performance
4. Batch similar actions together

### Reduce Costs

1. **Use DeepSeek R1** instead of OpenAI o1 (100x cheaper)
2. **Set token limits** in Email Agent config
3. **Reduce polling frequency** if low email volume
4. **Disable Email Agent** if not needed

### Improve Accuracy

1. **Review weekly** - Check classification accuracy
2. **Adjust rules** - Update tier definitions based on patterns
3. **Add examples** - Include edge cases in agent spec
4. **User feedback loop** - Mark incorrect classifications

---

## Next Steps After Deployment

### Week 1: Learning Phase

- [ ] Monitor all classifications
- [ ] Review Tier 2 auto-responses
- [ ] Verify Tier 3 drafts before sending
- [ ] Confirm Tier 1 escalations are appropriate
- [ ] Adjust off-limits contacts if needed

### Week 2-4: Tuning

- [ ] Identify classification patterns
- [ ] Update tier rules for edge cases
- [ ] Refine auto-response templates
- [ ] Add common scenarios to agent spec
- [ ] Optimize for your communication style

### Month 2+: Autopilot

- [ ] Trust Tier 2 autonomous handling
- [ ] Review only Tier 1 escalations
- [ ] Approve Tier 3 drafts in batches
- [ ] Monitor EOD reports for issues
- [ ] Quarterly review of action logs

---

## Support and Maintenance

### Regular Maintenance

**Monthly:**
- Review classification accuracy
- Check for expired credentials
- Update Gmail labels if needed
- Review Email Agent action history

**Quarterly:**
- Rotate Claude Code token
- Update dependencies: `npm update`
- Review and adjust tier rules
- Audit off-limits contacts

**Annually:**
- Renew Claude Code subscription
- Review cost optimization
- Update OpenRouter models
- Refresh Gmail OAuth credentials

### Getting Help

1. **Check documentation:**
   - [CLAUDE.md](CLAUDE.md) - Development guide
   - [EMAIL-AGENT.md](EMAIL-AGENT.md) - Email Agent docs
   - [QUICKSTART.md](QUICKSTART.md) - Quick start guide

2. **Review logs:**
   - GitHub Actions artifacts
   - Email Agent action history
   - Gmail label activity

3. **Test locally:**
   - Run `npm run agent:test`
   - Use `claude --debug`
   - Check MCP server status

4. **Community resources:**
   - Claude Code documentation
   - Gmail MCP server repo
   - OpenRouter docs

---

## Rollback Procedure

If something goes wrong:

### Disable Workflow

```bash
# Disable GitHub Actions workflow
gh workflow disable "Hourly Email Management"
```

### Revert to Previous Version

```bash
# Revert last commit
git revert HEAD
git push

# Or rollback to specific version
git reset --hard <commit-hash>
git push --force
```

### Emergency Stop

```bash
# Delete all GitHub Secrets
gh secret list | awk '{print $1}' | xargs -I {} gh secret delete {}

# Or disable individual secrets
gh secret delete CLAUDE_CODE_OAUTH_TOKEN
```

### Resume Normal Operation

```bash
# Re-enable workflow
gh workflow enable "Hourly Email Management"

# Test before enabling
gh workflow run "Hourly Email Management" --field test_mode=true
```

---

## Success Criteria

Your deployment is successful when:

✅ Morning brief arrives consistently at 7 AM EST
✅ Hourly processing completes in <5 minutes
✅ Tier 1 escalations are accurate (>90%)
✅ Tier 2 responses match your voice
✅ Tier 3 drafts need minimal editing
✅ No false positives in Tier 4
✅ EOD report provides useful summary
✅ Email Agent (if enabled) executes tasks correctly
✅ SMS alerts (if enabled) trigger appropriately
✅ Gmail labels organize inbox effectively

---

**You're ready to deploy! Run the setup script to begin:**

```bash
./scripts/setup-github-secrets.sh
```
