# Email Automation Setup Guide

## Overview

This guide will help you set up autonomous hourly email management using Claude Code Max subscription via GitHub Actions.

**What it does:**
- Runs every hour from 7 AM to 5 PM EST (Monday-Friday)
- Processes emails from terrance@goodportion.org
- Categorizes into Tiers 1/2/3/4
- Handles routine emails automatically (Tier 2)
- Escalates urgent items via SMS (Tier 1)
- Sends morning briefs (7 AM) and EOD reports (5 PM)

**Cost:**
- GitHub Actions: FREE (well under 2,000 min/month limit)
- Claude Code Max: $100/month (you already pay this)
- **Total additional cost: $0**

---

## Step 1: Extract Claude Code OAuth Tokens

You need to get your Claude Code authentication tokens to use your Max subscription in GitHub Actions.

### Method A: Using `claude setup-token` (Recommended)

Open your terminal and run:
```bash
claude setup-token
```

This will:
1. Open your browser for authentication
2. Generate a long-lived token
3. Display the token information

Copy the following values:
- `access_token`
- `refresh_token`
- `expires_at`

### Method B: Extract from macOS Keychain

1. Open **Keychain Access** app
2. Search for "claude"
3. Double-click the entry
4. Check "Show password"
5. Enter your Mac password
6. Copy the JSON (contains `access_token`, `refresh_token`, `expires_at`)

---

## Step 2: Get Gmail OAuth Credentials

You already have Gmail MCP configured. Get the credentials:

```bash
# OAuth keys
cat ~/.gmail-mcp/gcp-oauth.keys.json

# Credentials (access tokens)
cat ~/.gmail-mcp/credentials.json
```

Copy the entire JSON contents of both files.

---

## Step 3: Configure GitHub Secrets

Go to your GitHub repository:
`https://github.com/YOUR_USERNAME/personal-workspace-1`

Navigate to: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

### Claude Code Authentication

**Secret Name:** `CLAUDE_CODE_OAUTH_TOKEN`
**Value:** [Paste the entire token from Step 1 - starts with `sk-ant-oat01-`]

Example: `sk-ant-oat01-LYgbMJvOnqV29qCcZu0RXfu9t...`

### Gmail MCP Authentication

**Secret Name:** `GMAIL_OAUTH_CREDENTIALS`
**Value:** [Paste entire contents of `~/.gmail-mcp/gcp-oauth.keys.json`]

**Secret Name:** `GMAIL_CREDENTIALS`
**Value:** [Paste entire contents of `~/.gmail-mcp/credentials.json`]

### Twilio for SMS Escalations (Optional but Recommended)

If you want SMS alerts for Tier 1 urgent emails:

**Secret Name:** `TWILIO_ACCOUNT_SID`
**Value:** [Your Twilio Account SID]

**Secret Name:** `TWILIO_AUTH_TOKEN`
**Value:** [Your Twilio Auth Token]

**Secret Name:** `TWILIO_FROM_NUMBER`
**Value:** [Your Twilio phone number in format +1234567890]

**Escalation phone is hardcoded:** +14077448449 (in workflow file)

---

## Step 4: Commit and Push Workflow

The workflow file is already created at:
`.github/workflows/hourly-email-management.yml`

Commit and push it:

```bash
cd /Users/terrancebrandon/personal-workspace-1
git add .github/workflows/hourly-email-management.yml
git add EMAIL-AUTOMATION-SETUP.md
git commit -m "Add hourly email automation via Claude Code Max"
git push origin main
```

---

## Step 5: Test the Workflow

Before enabling automatic scheduling, test manually:

1. Go to GitHub: **Actions** tab
2. Click **Hourly Email Management** workflow
3. Click **Run workflow** button
4. Select branch: `main`
5. Click **Run workflow**

Watch the logs to see if it processes emails correctly.

---

## Step 6: Monitor First Week

The workflow will now run automatically every hour from 7 AM - 5 PM EST on weekdays.

**Check logs:**
- Go to **Actions** tab in GitHub
- Click on any workflow run to see detailed logs
- Look for email processing summary

**You'll receive:**
- **7 AM:** Morning brief email
- **Hourly:** Silent processing (only SMS if urgent)
- **1 PM:** Midday alert (only if Tier 1 urgent items)
- **5 PM:** End-of-day report email

---

## Troubleshooting

### Workflow fails with "OAuth token expired"

**Fix:** Tokens expire after some time. Re-run Step 1 to get fresh tokens and update GitHub secrets.

### Gmail MCP not connecting

**Fix:** Verify `GMAIL_OAUTH_CREDENTIALS` and `GMAIL_CREDENTIALS` are correctly pasted (entire JSON).

### No emails being processed

**Fix:**
1. Check if workflow is running (Actions tab)
2. Verify schedule cron is correct for your timezone
3. Check workflow logs for errors

### Tier classification seems wrong

**Fix:** The agent learns over time. During first week, it may over-escalate (conservative). Provide feedback by manually adjusting labels in Gmail.

---

## Usage Limits

### GitHub Actions (Free Tier)
- **2,000 minutes/month** included
- Your usage: ~275 min/month (11 runs/day × 5 days × 5 min/run)
- **Well within limits** (13% usage)

### Claude Code Max ($100/month)
- **~225 messages per 5-hour session**
- Your usage: ~220 messages/day (11 hourly runs × ~20 messages)
- **Within limits** (sessions are 1 hour apart, no overlap)

---

## Customization

### Change Schedule

Edit `.github/workflows/hourly-email-management.yml`:

```yaml
schedule:
  - cron: "0 12-22 * * 1-5"  # Current: 7 AM - 5 PM EST, Mon-Fri

# Examples:
  - cron: "0 11-23 * * 1-5"  # 6 AM - 6 PM EST
  - cron: "0 12-22 * * *"    # 7 AM - 5 PM EST, Every day (including weekends)
  - cron: "0 */2 12-22 * * 1-5"  # Every 2 hours instead of hourly
```

### Change Email Processing Logic

The prompt is embedded in the workflow file. You can modify:
- Tier classification criteria
- Label application rules
- Response templates
- Brief/report formats

### Add More Actions

You can extend the workflow to:
- Create calendar events from emails
- Auto-respond to specific senders
- Forward certain emails to team members
- Log all emails to a database

---

## Security Notes

**GitHub Secrets are encrypted** - Your OAuth tokens and credentials are stored securely by GitHub.

**Access control:**
- Only you (repo owner) can view/edit secrets
- Workflow logs don't expose secret values
- Tokens can be revoked anytime

**Best practices:**
- Rotate tokens quarterly (re-run `claude setup-token`)
- Monitor workflow logs for suspicious activity
- Use 2FA on GitHub account

---

## Next Steps

1. ✅ Extract OAuth tokens (Step 1)
2. ✅ Configure GitHub secrets (Step 3)
3. ✅ Push workflow to GitHub (Step 4)
4. ✅ Test manually (Step 5)
5. ✅ Monitor first week (Step 6)

Once working smoothly, you can:
- Adjust tier classification based on learning
- Fine-tune schedules
- Add custom automations
- Reduce manual email time to <15 min/day

---

## Support

If you encounter issues:

1. Check GitHub Actions logs first
2. Verify all secrets are correctly configured
3. Test Gmail MCP locally: `npx @gongrzhe/server-gmail-autoauth-mcp`
4. Re-authenticate Claude Code: `claude setup-token`

**Happy automating!** 🚀

(Oops, no emojis - Terrance hates those)

Happy automating!
