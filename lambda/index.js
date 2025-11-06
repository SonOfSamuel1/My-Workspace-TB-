/**
 * AWS Lambda Handler for Autonomous Email Assistant
 *
 * This Lambda function replaces the GitHub Actions workflow and runs
 * the Claude Code CLI in headless mode to process emails.
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');

const writeFile = promisify(fs.writeFile);
const mkdir = promisify(fs.mkdir);

/**
 * Determine execution mode based on current hour (EST)
 */
function getExecutionMode() {
  const estDate = new Date().toLocaleString("en-US", { timeZone: "America/New_York" });
  const hour = new Date(estDate).getHours();

  if (hour === 7) return 'morning_brief';
  if (hour === 17) return 'eod_report';
  if (hour === 13) return 'midday_check';
  return 'hourly_process';
}

/**
 * Setup Gmail MCP credentials from environment variables
 */
async function setupGmailCredentials() {
  const gmailMcpDir = path.join('/tmp', '.gmail-mcp');
  const configDir = path.join('/tmp', '.config', 'claude');

  // Create directories
  await mkdir(gmailMcpDir, { recursive: true });
  await mkdir(configDir, { recursive: true });

  // Decode and write Gmail OAuth credentials
  const gmailOauthCreds = Buffer.from(
    process.env.GMAIL_OAUTH_CREDENTIALS,
    'base64'
  ).toString('utf-8');

  const gmailUserCreds = Buffer.from(
    process.env.GMAIL_CREDENTIALS,
    'base64'
  ).toString('utf-8');

  await writeFile(
    path.join(gmailMcpDir, 'gcp-oauth.keys.json'),
    gmailOauthCreds
  );

  await writeFile(
    path.join(gmailMcpDir, 'credentials.json'),
    gmailUserCreds
  );

  // Create MCP config
  const mcpConfig = {
    mcpServers: {
      gmail: {
        type: "stdio",
        command: "npx",
        args: ["@gongrzhe/server-gmail-autoauth-mcp"],
        env: {}
      }
    }
  };

  await writeFile(
    path.join(configDir, 'claude_code_config.json'),
    JSON.stringify(mcpConfig, null, 2)
  );

  return {
    gmailMcpDir,
    configPath: path.join(configDir, 'claude_code_config.json')
  };
}

/**
 * Build the Claude prompt for email processing
 */
function buildClaudePrompt(mode, hour) {
  return `You are Terrance Brandon's Executive Email Assistant, running autonomous hourly email management.

CURRENT CONTEXT:
- Execution Mode: ${mode}
- Current Hour (EST): ${hour}:00
- Test Mode: false

YOUR CONFIGURATION (from claude-agents/executive-email-assistant-config-terrance.md):
- Email: terrance@goodportion.org
- Delegation Level: Level 2 (Manage)
- Time Zone: EST
- Communication Style: Casual (Hi/Thanks), "Kind regards,", NO emojis
- Escalation: SMS to 407-744-8449 for Tier 1 urgent

OFF-LIMITS CONTACTS (Always Escalate as Tier 1):
- Family Members
- Darrell Coleman
- Paul Robertson
- Tatyana Brandon

LABELS SYSTEM:
1. Action Required - High-priority items needing decision
2. To Read - Information to review later
3. Waiting For - Awaiting external responses
4. Completed - Finished items
5. VIP - VIP contacts and always-escalate list
6. Meetings - Calendar/scheduling
7. Travel - Travel related
8. Expenses - Receipts, invoices
9. Newsletters - Subscriptions

TIER CLASSIFICATION:

TIER 1 (Escalate Immediately - SMS + Priority Email):
- Revenue-impacting emails from customers/prospects
- Strategic partnership opportunities
- Major donor communications
- Speaking/media opportunities
- Financial matters requiring approval
- Employee/HR issues
- Legal matters
- Emails from off-limits contacts
- Anything marked urgent/confidential

TIER 2 (Handle Independently):
- Meeting scheduling
- Newsletter subscriptions
- Vendor communications (routine)
- Follow-up reminders
- Information requests
- Administrative tasks
- Travel confirmations
- Expense receipts

TIER 3 (Draft for Approval):
- Meeting decline requests
- Strategic communications
- First-time contacts (seemingly important)
- Requires Terrance's expertise/voice

TIER 4 (Draft-Only, Never Send):
- HR/Employee performance matters
- Financial negotiations
- Legal matters
- Board communications
- Personal matters (health, family)

YOUR TASKS FOR THIS HOUR:

1. ACCESS GMAIL VIA MCP
   - Connect to terrance@goodportion.org inbox
   - Use Gmail MCP tools (should be available)

2. FETCH NEW EMAILS
   - Get emails received in the last hour
   - If this is first run today (7 AM), get overnight emails since 5 PM yesterday

3. PROCESS EACH EMAIL:
   - Read sender, subject, and content
   - Classify into Tier 1/2/3/4
   - Apply appropriate Gmail label
   - Take action based on tier:

     TIER 1:
     - Apply "Action Required" + "VIP" labels
     - Send SMS to ${process.env.ESCALATION_PHONE || '+14077448449'} with brief alert
     - Add to priority list for brief/report
     - DO NOT respond to email yet

     TIER 2:
     - Apply appropriate label (Meetings/Travel/Expenses/Newsletters)
     - Draft and SEND response if clear pattern exists
     - Archive if handled
     - Log action for EOD report

     TIER 3:
     - Apply "Action Required" label
     - Draft response but DO NOT send
     - Save draft in Gmail
     - Add to approval queue for brief/report

     TIER 4:
     - Apply "Action Required" label
     - DO NOT draft or send anything
     - Flag for Terrance's personal attention
     - Add to brief/report with sensitivity note

4. UPDATE "WAITING FOR" ITEMS:
   - Check emails with "Waiting For" label
   - If response received, move to appropriate category
   - If >3 days old, draft follow-up (add to approval queue)

5. GENERATE OUTPUT BASED ON MODE:

   IF MODE = "morning_brief" (7 AM):
   - Generate comprehensive morning brief
   - Include overnight email summary
   - List all Tier 1 escalations
   - List all Tier 3/4 items needing approval
   - Show updated "Waiting For" status
   - Send via email to terrance@goodportion.org
   - Subject: "Morning Brief - [Date]"

   IF MODE = "eod_report" (5 PM):
   - Generate comprehensive end-of-day report
   - Total emails processed today
   - Actions taken (Tier 2 handled)
   - Items awaiting approval (Tier 3/4)
   - Still waiting for responses
   - Tomorrow's priorities
   - Send via email to terrance@goodportion.org
   - Subject: "End of Day Report - [Date]"

   IF MODE = "midday_check" (1 PM):
   - Only send report if Tier 1 urgent items exist
   - Brief summary of urgent matters
   - Subject: "Midday Alert - Urgent Items"

   IF MODE = "hourly_process":
   - Process emails silently
   - Only send SMS for Tier 1 urgent items
   - No email report unless critical

6. ERROR HANDLING:
   - If Gmail MCP not available, log error and exit gracefully
   - If cannot access inbox, send alert to Terrance
   - If unsure about classification, default to Tier 3 (draft for approval)

IMPORTANT CONSTRAINTS:
- Never use emojis (Terrance hates them)
- Always identify as "Executive Email Assistant for Terrance Brandon"
- Sign responses with "Kind regards,"
- If meeting decline needed, draft but don't send (Tier 3)
- Be conservative with escalations during learning phase

BEGIN PROCESSING NOW.

Output your actions in this format:

## EMAIL PROCESSING SUMMARY
- Emails checked: [#]
- New emails found: [#]
- Tier 1 (escalated): [#]
- Tier 2 (handled): [#]
- Tier 3 (drafted): [#]
- Tier 4 (flagged): [#]

## ACTIONS TAKEN
[List each action taken]

## ESCALATIONS
[If any Tier 1 items, list them]

## MODE-SPECIFIC OUTPUT
[Morning brief / EOD report / Midday alert / Silent processing confirmation]`;
}

/**
 * Execute Claude Code CLI
 */
function executeClaudeCLI(prompt, configPath) {
  return new Promise((resolve, reject) => {
    const claude = spawn('claude', [
      '--print',
      '--dangerously-skip-permissions',
      '--mcp-config',
      configPath
    ], {
      env: {
        ...process.env,
        HOME: '/tmp',
        CLAUDE_CODE_OAUTH_TOKEN: process.env.CLAUDE_CODE_OAUTH_TOKEN,
        TWILIO_ACCOUNT_SID: process.env.TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN: process.env.TWILIO_AUTH_TOKEN,
        TWILIO_FROM_NUMBER: process.env.TWILIO_FROM_NUMBER,
        ESCALATION_PHONE: process.env.ESCALATION_PHONE || '+14077448449'
      }
    });

    let stdout = '';
    let stderr = '';

    // Send prompt to stdin
    claude.stdin.write(prompt);
    claude.stdin.end();

    claude.stdout.on('data', (data) => {
      stdout += data.toString();
      console.log('STDOUT:', data.toString());
    });

    claude.stderr.on('data', (data) => {
      stderr += data.toString();
      console.error('STDERR:', data.toString());
    });

    claude.on('close', (code) => {
      if (code === 0) {
        resolve({ stdout, stderr });
      } else {
        reject(new Error(`Claude CLI exited with code ${code}\nSTDERR: ${stderr}`));
      }
    });

    // Timeout after 9 minutes (Lambda has 10 min max, leave buffer)
    setTimeout(() => {
      claude.kill();
      reject(new Error('Claude CLI execution timeout'));
    }, 9 * 60 * 1000);
  });
}

/**
 * Main Lambda handler
 */
exports.handler = async (event, context) => {
  console.log('Email Assistant Lambda started');
  console.log('Event:', JSON.stringify(event, null, 2));

  try {
    // Get execution mode
    const mode = getExecutionMode();
    const estDate = new Date().toLocaleString("en-US", { timeZone: "America/New_York" });
    const hour = new Date(estDate).getHours();

    console.log(`Execution mode: ${mode}, Hour: ${hour}`);

    // Setup Gmail credentials
    console.log('Setting up Gmail MCP credentials...');
    const { configPath } = await setupGmailCredentials();
    console.log('Gmail credentials configured');

    // Build prompt
    const prompt = buildClaudePrompt(mode, hour);

    // Execute Claude Code CLI
    console.log('Executing Claude Code CLI...');
    const { stdout, stderr } = await executeClaudeCLI(prompt, configPath);

    console.log('Email processing completed successfully');

    return {
      statusCode: 200,
      body: JSON.stringify({
        success: true,
        mode,
        hour,
        output: stdout,
        timestamp: new Date().toISOString()
      })
    };

  } catch (error) {
    console.error('Error processing emails:', error);

    return {
      statusCode: 500,
      body: JSON.stringify({
        success: false,
        error: error.message,
        timestamp: new Date().toISOString()
      })
    };
  }
};
