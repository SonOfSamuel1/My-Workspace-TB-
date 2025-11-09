# 🚀 Deploy Your Email Assistant NOW

Follow these steps in order. Each step takes ~2-5 minutes.

---

## ✅ Pre-Deployment Checklist

Before you begin, verify you have:

- [x] Claude Code CLI installed (`claude --version` works)
- [x] Gmail MCP credentials at `~/.gmail-mcp/`
- [x] GitHub CLI installed (`gh --version` works)
- [ ] GitHub repository created
- [ ] Claude Code OAuth token ready
- [ ] (Optional) OpenRouter API key for Email Agent
- [ ] (Optional) Twilio credentials for SMS alerts

---

## Step 1: Get Your Claude Code Token (2 minutes)

```bash
# Generate your authentication token
claude setup-token
```

**Copy the token** - it starts with `sk-ant-oat01-...`

You'll need this in Step 3.

---

## Step 2: Create/Verify GitHub Repository (2 minutes)

### Option A: Create New Repository

```bash
# Create private repository
gh repo create App--Internal-Business--Autonomous-Email-Assistant \
  --private \
  --source=. \
  --remote=origin \
  --description "Autonomous email management system with Claude Code"

# Push code
git add .
git commit -m "feat: Email assistant ready for deployment"
git push -u origin main
```

### Option B: Use Existing Repository

```bash
# Verify remote is set
git remote -v

# If no remote, add it
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git

# Push code
git add .
git commit -m "feat: Email assistant ready for deployment"
git push -u origin main
```

---

## Step 3: Configure GitHub Secrets (3 minutes)

### Automated Setup (Recommended)

```bash
# Run the setup script - it will prompt you for everything
./scripts/setup-github-secrets.sh
```

The script will ask for:

1. **Claude Code OAuth Token** (from Step 1)
   - Paste your `sk-ant-oat01-...` token

2. **Gmail credentials** (auto-detected from `~/.gmail-mcp/`)
   - Automatically encoded and uploaded

3. **Twilio credentials** (optional - press Enter to skip)
   - Only if you want SMS alerts for urgent emails

4. **OpenRouter API Key** (optional - press Enter to skip)
   - Only if you want Email Agent autonomous actions
   - Get free $5 credit at [openrouter.ai](https://openrouter.ai)

---

## Step 4: Test the Workflow (3 minutes)

```bash
# Trigger a test run (no actual emails sent)
gh workflow run "Hourly Email Management" --field test_mode=true

# Watch the progress
gh run watch

# This will take 2-3 minutes to complete
```

**What to look for:**

✅ Workflow starts successfully
✅ Claude Code CLI installs
✅ Gmail MCP credentials load
✅ MCP configuration validates
✅ Claude processes the prompt
✅ Workflow completes without errors

**If successful, you'll see:**

```
✓ Setup Node.js
✓ Install Claude Code
✓ Install Gmail MCP Server
✓ Setup Gmail MCP credentials
✓ Verify MCP Setup
✓ Process Emails with Claude Code
✓ Upload Processing Log
```

---

## Step 5: Verify Deployment (2 minutes)

Check that everything is configured:

```bash
# View workflow status
gh run list --workflow="Hourly Email Management" --limit 5

# Check secrets are set
gh secret list

# Expected secrets:
# CLAUDE_CODE_OAUTH_TOKEN
# GMAIL_OAUTH_CREDENTIALS
# GMAIL_CREDENTIALS
# (Optional) TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER
# (Optional) OPENROUTER_API_KEY
```

---

## Step 6: Wait for First Real Run

Your email assistant is now deployed! It will run automatically:

**Schedule (Eastern Time, Monday-Friday):**

- **7:00 AM** - Morning brief with overnight emails
- **8:00 AM - 4:00 PM** - Hourly processing (silent)
- **1:00 PM** - Midday check (only if urgent)
- **5:00 PM** - End-of-day report

**What happens next:**

1. At 7 AM tomorrow, you'll receive a **Morning Brief** email
2. Throughout the day, urgent emails trigger **SMS alerts** (if Twilio configured)
3. Routine emails are **handled automatically** (Tier 2)
4. Important emails are **drafted for approval** (Tier 3)
5. At 5 PM, you'll receive an **End-of-Day Report**

---

## 🎉 You're Live!

### Immediate Next Steps

**1. Test manually right now (optional):**

```bash
# Trigger immediate run in production mode
gh workflow run "Hourly Email Management"

# Watch it run
gh run watch
```

**2. Monitor your first runs:**

```bash
# View recent workflow runs
gh run list --limit 5

# Download processing logs
gh run download

# View detailed logs
gh run view --log
```

**3. Set up notifications:**

- Go to repository → Settings → Notifications
- Enable email alerts for workflow failures
- Get notified if anything goes wrong

---

## 📊 What to Expect

### First Week (Learning Phase)

**Goal:** Verify classification accuracy

- [ ] Check morning briefs daily
- [ ] Review Tier 2 auto-responses
- [ ] Approve/edit Tier 3 drafts
- [ ] Confirm Tier 1 escalations are appropriate
- [ ] Adjust off-limits contacts if needed

**Expected:**
- Some mis-classifications (this is normal!)
- Conservative escalations (Tier 3 > Tier 2)
- Request for clarification on edge cases

**Action:**
- Update [claude-agents/executive-email-assistant.md](claude-agents/executive-email-assistant.md) with edge cases
- Add examples to improve accuracy
- Refine tier definitions

### Week 2-4 (Tuning Phase)

**Goal:** Optimize for your patterns

- [ ] Identify common email types
- [ ] Create response templates
- [ ] Trust Tier 2 autonomous handling
- [ ] Batch-approve Tier 3 drafts
- [ ] Monitor EOD reports

**Expected:**
- Increasing accuracy (>90%)
- Fewer manual interventions needed
- Consistent classification patterns

**Action:**
- Add auto-response templates
- Expand Tier 2 autonomous scenarios
- Fine-tune communication style

### Month 2+ (Autopilot Phase)

**Goal:** Minimal supervision

- [ ] Trust the system
- [ ] Review only escalations
- [ ] Approve drafts in batches
- [ ] Weekly accuracy check
- [ ] Monthly rule refinement

**Expected:**
- >95% classification accuracy
- 50-70% emails handled autonomously
- Significant time saved
- Inbox stays organized

---

## 🛠️ Quick Reference

### Check Workflow Status

```bash
gh run list --workflow="Hourly Email Management"
```

### View Logs

```bash
gh run view --log
```

### Trigger Manual Run

```bash
gh workflow run "Hourly Email Management"
```

### Update Secrets

```bash
gh secret set CLAUDE_CODE_OAUTH_TOKEN -b"new-token"
```

### Disable Workflow (Emergency)

```bash
gh workflow disable "Hourly Email Management"
```

### Re-enable Workflow

```bash
gh workflow enable "Hourly Email Management"
```

---

## ⚠️ Troubleshooting

### Workflow Fails Immediately

**Symptom:** Red X on workflow run

**Check:**
```bash
# View error logs
gh run view --log | grep -i error

# Common issues:
# - Invalid Claude token → Re-run: claude setup-token
# - Expired Gmail credentials → Re-encode and update secrets
# - Missing secrets → Run: gh secret list
```

### No Morning Brief Received

**Symptom:** 7 AM passed, no email

**Check:**
```bash
# Was workflow triggered?
gh run list --created $(date +%Y-%m-%d)

# If no runs, check schedule is enabled
gh workflow view "Hourly Email Management"
```

**Solution:**
- Trigger manually: `gh workflow run "Hourly Email Management"`
- Check spam folder
- Verify Gmail MCP credentials

### MCP Not Loading

**Symptom:** "Gmail MCP tools not available"

**Solution:**
```bash
# Re-encode and update secrets
cat ~/.gmail-mcp/gcp-oauth.keys.json | base64 | gh secret set GMAIL_OAUTH_CREDENTIALS
cat ~/.gmail-mcp/credentials.json | base64 | gh secret set GMAIL_CREDENTIALS
```

---

## 💡 Pro Tips

### Reduce Noise

If you're getting too many notifications:

1. Edit [.github/workflows/hourly-email-management.yml](.github/workflows/hourly-email-management.yml)
2. Change morning brief to only include escalations
3. Reduce EOD report detail level
4. Only send midday check for critical items

### Speed Up Processing

If >50 emails/hour:

1. Increase timeout: `timeout-minutes: 15`
2. Switch to AWS Lambda for better performance
3. Add parallel processing for batches

### Save Money

1. Use DeepSeek R1 (not OpenAI o1) - 100x cheaper
2. Disable Email Agent if not needed
3. Skip SMS (use email escalations only)
4. Reduce schedule to business hours only

---

## 📞 Getting Help

1. **Check logs first:**
   ```bash
   gh run view --log
   ```

2. **Review documentation:**
   - [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md) - Full deployment guide
   - [CLAUDE.md](CLAUDE.md) - Development guide
   - [EMAIL-AGENT.md](EMAIL-AGENT.md) - Email Agent docs

3. **Test locally:**
   ```bash
   npm run agent:test
   claude --debug --mcp-config ~/.config/claude/claude_code_config.json
   ```

---

## ✨ You Did It!

Your autonomous email assistant is now:

✅ Deployed to GitHub Actions
✅ Running hourly during business hours
✅ Classifying emails into 4 tiers
✅ Handling routine emails automatically
✅ Escalating urgent items via SMS (if configured)
✅ Drafting responses for approval
✅ Sending morning briefs and EOD reports

**Enjoy your newly organized inbox!** 📧✨

---

**Next:** Wait for your first morning brief tomorrow at 7 AM EST, or trigger a manual run now:

```bash
gh workflow run "Hourly Email Management"
gh run watch
```
