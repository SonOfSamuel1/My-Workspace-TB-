/**
 * AWS Lambda Handler for Autonomous Email Assistant - IMPROVED VERSION
 *
 * This improved version includes:
 * - Retry logic with exponential backoff
 * - Structured logging
 * - Input validation
 * - Error handling and recovery
 * - Health checks
 * - Cost tracking
 *
 * To use: Rename this file to index.js after review
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');

const logger = require('./lib/logger');
const { validateEnvironment, validateExecutionMode, sanitizeForLogging } = require('./lib/config-validator');
const { executeWithRetry, RetryConditions } = require('./lib/retry');
const { EmailAssistantError, ErrorCodes, handleError } = require('./lib/error-handler');
const { selectModel, analyzeEmailComplexity } = require('./lib/model-router');

// HTML email generation and sending
const EmailSummaryGenerator = require('../lib/email-summary-generator');
const SESEmailSender = require('../lib/ses-email-sender');

const writeFile = promisify(fs.writeFile);
const mkdir = promisify(fs.mkdir);

// Initialize logger with Lambda context
let contextLogger = logger;

// Initialize email sender and generator
const emailGenerator = new EmailSummaryGenerator({
  dashboardUrl: process.env.DASHBOARD_URL || 'https://email-assistant.yourdomain.com/dashboard',
  userEmail: process.env.USER_EMAIL || 'terrance@goodportion.org'
});

const emailSender = new SESEmailSender({
  region: process.env.AWS_REGION || 'us-east-1',
  senderEmail: process.env.SES_SENDER_EMAIL || 'brandonhome.appdev@gmail.com'
});

/**
 * Parse JSON from Claude's output (handles ```json code blocks)
 */
function parseClaudeOutput(stdout) {
  try {
    // Extract JSON from markdown code blocks
    const jsonMatch = stdout.match(/```json\s*([\s\S]*?)\s*```/);
    if (jsonMatch && jsonMatch[1]) {
      return JSON.parse(jsonMatch[1].trim());
    }

    // Try parsing the entire output as JSON (fallback)
    return JSON.parse(stdout.trim());
  } catch (error) {
    contextLogger.warn('Failed to parse JSON from Claude output, using fallback', {
      error: error.message,
      outputPreview: stdout.substring(0, 500)
    });

    // Return a minimal fallback structure
    return {
      todayStats: { totalProcessed: 0, escalations: 0, handled: 0, drafts: 0, flagged: 0 },
      actionsTaken: [],
      tier1Escalations: [],
      tier3Pending: [],
      pendingForTomorrow: [],
      insights: [],
      topSenders: [],
      summary: stdout.substring(0, 1000) // Use raw output as summary
    };
  }
}

/**
 * Send formatted HTML email report based on execution mode
 */
async function sendFormattedReport(mode, processingResults, hour) {
  const userEmail = process.env.USER_EMAIL || 'terrance@goodportion.org';

  try {
    let emailContent;

    if (mode === 'morning_brief') {
      // Morning brief email
      emailContent = await emailGenerator.generateMorningBrief({
        overnight: {
          totalEmails: processingResults.todayStats?.totalProcessed || 0,
          handled: processingResults.todayStats?.handled || 0,
          escalations: processingResults.todayStats?.escalations || 0,
          drafts: processingResults.todayStats?.drafts || 0
        },
        tier1Escalations: processingResults.tier1Escalations || [],
        tier3Pending: processingResults.tier3Pending || [],
        tier2Handled: processingResults.actionsTaken?.filter(a => a.type === 'handled') || [],
        stats: {
          responseTime: processingResults.avgResponseTime,
          accuracy: processingResults.accuracy
        },
        agentActivity: {
          processed: processingResults.todayStats?.agentProcessed || 0
        }
      });
    } else if (mode === 'eod_report') {
      // End of day report
      emailContent = await emailGenerator.generateEODReport({
        todayStats: processingResults.todayStats || {},
        actionsTaken: processingResults.actionsTaken || [],
        pendingForTomorrow: processingResults.pendingForTomorrow || [],
        costs: processingResults.costs || { total: 0 },
        insights: processingResults.insights || [],
        topSenders: processingResults.topSenders || []
      });
    } else if (mode === 'midday_check' && processingResults.tier1Escalations?.length > 0) {
      // Midday urgent items alert
      emailContent = await emailGenerator.generateMiddayCheck(processingResults.tier1Escalations);
    } else {
      // Silent processing mode - no email needed
      contextLogger.info('Silent processing mode - skipping email report');
      return null;
    }

    if (!emailContent) {
      contextLogger.info('No email content generated (may be intentional for midday with no urgent items)');
      return null;
    }

    // Send the email via SES
    const result = await emailSender.sendHtmlEmail({
      to: userEmail,
      subject: emailContent.subject,
      htmlContent: emailContent.html,
      textContent: emailContent.plainText
    });

    contextLogger.info('HTML email report sent successfully', {
      mode,
      subject: emailContent.subject,
      messageId: result.messageId
    });

    return result;
  } catch (error) {
    contextLogger.error('Failed to send HTML email report', {
      mode,
      error: error.message
    });

    // Don't throw - email failure shouldn't fail the whole Lambda
    return null;
  }
}

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
  const startTime = Date.now();
  contextLogger.info('Setting up Gmail MCP credentials');

  try {
    const gmailMcpDir = path.join('/tmp', '.gmail-mcp');
    const configDir = path.join('/tmp', '.config', 'claude');

    // Create directories
    await mkdir(gmailMcpDir, { recursive: true });
    await mkdir(configDir, { recursive: true });
    contextLogger.debug('Created credential directories', { gmailMcpDir, configDir });

    // Decode and write Gmail OAuth credentials
    const gmailOauthCreds = Buffer.from(
      process.env.GMAIL_OAUTH_CREDENTIALS,
      'base64'
    ).toString('utf-8');

    const gmailUserCreds = Buffer.from(
      process.env.GMAIL_CREDENTIALS,
      'base64'
    ).toString('utf-8');

    // Validate JSON before writing
    try {
      JSON.parse(gmailOauthCreds);
      JSON.parse(gmailUserCreds);
    } catch (jsonError) {
      throw new EmailAssistantError(
        'Invalid Gmail credentials JSON',
        ErrorCodes.INVALID_CONFIG,
        false
      );
    }

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

    const duration = Date.now() - startTime;
    contextLogger.info('Gmail credentials configured successfully', {
      durationMs: duration
    });

    return {
      gmailMcpDir,
      configPath: path.join(configDir, 'claude_code_config.json')
    };
  } catch (error) {
    contextLogger.error('Failed to setup Gmail credentials', { error: error.message });
    throw error;
  }
}

/**
 * Build the Claude prompt for email processing
 * TODO: Replace with PromptBuilder once available
 */
function buildClaudePrompt(mode, hour, selectedModel) {
  contextLogger.debug('Building Claude prompt', { mode, hour, model: selectedModel?.displayName });

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
- Escalation: SMS to ${process.env.ESCALATION_PHONE || '+14077448449'} for Tier 1 urgent

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
   - Take action based on tier

4. UPDATE "WAITING FOR" ITEMS:
   - Check emails with "Waiting For" label
   - If response received, move to appropriate category
   - If >3 days old, draft follow-up

5. GENERATE OUTPUT BASED ON MODE

6. ERROR HANDLING:
   - If Gmail MCP not available, log error and exit gracefully
   - If cannot access inbox, send alert
   - If unsure about classification, default to Tier 3

IMPORTANT CONSTRAINTS:
- Never use emojis
- Always identify as "Executive Email Assistant for Terrance Brandon"
- Sign responses with "Kind regards,"
- Be conservative with escalations

BEGIN PROCESSING NOW.

CRITICAL: Output your results as a JSON object wrapped in \`\`\`json code blocks.
This JSON will be parsed programmatically to generate HTML email reports.

\`\`\`json
{
  "todayStats": {
    "totalProcessed": 0,
    "escalations": 0,
    "handled": 0,
    "drafts": 0,
    "flagged": 0,
    "agentProcessed": 0
  },
  "actionsTaken": [
    {
      "timestamp": "ISO timestamp",
      "emailId": "Gmail message ID",
      "subject": "Email subject",
      "from": "sender@email.com",
      "type": "escalated|handled|drafted|archived|flagged"
    }
  ],
  "tier1Escalations": [
    {
      "id": "Gmail message ID",
      "from": "sender@email.com",
      "subject": "Email subject",
      "timestamp": "ISO timestamp",
      "preview": "First 100 chars of email body",
      "reason": "Why this was escalated"
    }
  ],
  "tier3Pending": [
    {
      "id": "Gmail message ID",
      "from": "sender@email.com",
      "subject": "Email subject",
      "timestamp": "ISO timestamp",
      "draftPreview": "First 100 chars of draft response"
    }
  ],
  "pendingForTomorrow": [
    {
      "subject": "Email subject",
      "from": "sender@email.com",
      "followUpDate": "ISO date if scheduled"
    }
  ],
  "insights": [
    {
      "type": "pattern|performance|cost|recommendation|success|warning",
      "message": "Insight description"
    }
  ],
  "topSenders": [
    {
      "email": "sender@email.com",
      "count": 5,
      "averageTier": "Tier 2"
    }
  ],
  "summary": "Brief text summary for plain text fallback"
}
\`\`\`

Fill in actual values from your email processing. Use empty arrays [] if no items for a category.`;
}

/**
 * Execute Claude Code CLI with retry logic
 */
async function executeClaudeCLI(prompt, configPath, selectedModel) {
  const startTime = Date.now();

  return new Promise((resolve, reject) => {
    contextLogger.info('Executing Claude Code CLI', {
      promptLength: prompt.length,
      configPath,
      model: selectedModel?.displayName,
      estimatedCost: `$${selectedModel?.cost.toFixed(4)}`
    });

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
        ESCALATION_PHONE: process.env.ESCALATION_PHONE || '+14077448449',
        OPENROUTER_MODEL: selectedModel?.name || ''
      }
    });

    let stdout = '';
    let stderr = '';

    // Send prompt to stdin
    claude.stdin.write(prompt);
    claude.stdin.end();

    claude.stdout.on('data', (data) => {
      const chunk = data.toString();
      stdout += chunk;
      contextLogger.debug('Claude CLI stdout', { length: chunk.length });
    });

    claude.stderr.on('data', (data) => {
      const chunk = data.toString();
      stderr += chunk;
      contextLogger.warn('Claude CLI stderr', { content: chunk });
    });

    claude.on('close', (code) => {
      const duration = Date.now() - startTime;

      if (code === 0) {
        contextLogger.info('Claude CLI completed successfully', {
          durationMs: duration,
          stdoutLength: stdout.length,
          stderrLength: stderr.length
        });
        resolve({ stdout, stderr, duration });
      } else {
        contextLogger.error('Claude CLI exited with error', {
          code,
          durationMs: duration,
          stderr: stderr.substring(0, 500)
        });
        reject(new EmailAssistantError(
          `Claude CLI exited with code ${code}`,
          ErrorCodes.CLAUDE_CLI_FAILED,
          true // Potentially recoverable
        ));
      }
    });

    claude.on('error', (error) => {
      contextLogger.error('Claude CLI spawn error', { error: error.message });
      reject(new EmailAssistantError(
        `Failed to spawn Claude CLI: ${error.message}`,
        ErrorCodes.CLAUDE_CLI_FAILED,
        true
      ));
    });

    // Timeout after 9 minutes (Lambda has 10 min max, leave buffer)
    const timeout = setTimeout(() => {
      contextLogger.error('Claude CLI execution timeout');
      claude.kill('SIGTERM');

      // Force kill after 5 seconds if not terminated
      setTimeout(() => {
        if (!claude.killed) {
          claude.kill('SIGKILL');
        }
      }, 5000);

      reject(new EmailAssistantError(
        'Claude CLI execution timeout',
        ErrorCodes.TIMEOUT,
        true
      ));
    }, 9 * 60 * 1000);

    // Clear timeout on completion
    claude.once('close', () => clearTimeout(timeout));
  });
}

/**
 * Execute Claude CLI with retry logic
 */
async function executeClaudeWithRetry(prompt, configPath, selectedModel) {
  return executeWithRetry(
    () => executeClaudeCLI(prompt, configPath, selectedModel),
    {
      maxRetries: 3,
      initialDelay: 2000,
      maxDelay: 30000,
      backoffMultiplier: 2,
      onRetry: (attempt, error) => {
        contextLogger.warn('Retrying Claude CLI execution', {
          attempt,
          error: error.message,
          model: selectedModel?.displayName
        });
      }
    }
  );
}

/**
 * Send health check notification
 */
async function sendHealthCheck(status, stats) {
  contextLogger.info('Sending health check', { status, stats });

  // In production, this would send an email via SES or SNS
  // For now, just log it
  const healthReport = {
    timestamp: new Date().toISOString(),
    status,
    stats: sanitizeForLogging(stats)
  };

  if (status === 'healthy') {
    contextLogger.info('System health check: HEALTHY', healthReport);
  } else {
    contextLogger.error('System health check: UNHEALTHY', healthReport);
  }
}

/**
 * Main Lambda handler
 */
exports.handler = async (event, context) => {
  const startTime = Date.now();

  // Initialize logger with Lambda context
  contextLogger = logger.child({
    requestId: context.requestId,
    functionName: context.functionName,
    functionVersion: context.functionVersion
  });

  contextLogger.info('Email Assistant Lambda started', {
    event: sanitizeForLogging(event),
    remainingTimeMs: context.getRemainingTimeInMillis()
  });

  try {
    // Step 1: Validate environment
    contextLogger.info('Step 1: Validating environment');
    validateEnvironment();

    // Step 2: Get execution mode
    const mode = getExecutionMode();
    const estDate = new Date().toLocaleString("en-US", { timeZone: "America/New_York" });
    const hour = new Date(estDate).getHours();

    contextLogger.info('Step 2: Determined execution mode', { mode, hour });
    validateExecutionMode(mode);

    // Step 3: Setup Gmail credentials
    contextLogger.info('Step 3: Setting up Gmail MCP credentials');
    const { configPath } = await setupGmailCredentials();

    // Step 3.5: Select AI model based on email complexity
    // For now, use a mock email object. In production, this would analyze actual emails from inbox
    contextLogger.info('Step 3.5: Selecting AI model');
    const mockEmail = {
      id: 'batch',
      subject: `${mode} - Batch email processing`,
      body: 'Processing multiple emails in batch',
      from: 'system@lambda'
    };
    const selectedModel = selectModel(mockEmail);
    contextLogger.info('Model selected', {
      model: selectedModel.displayName,
      tier: selectedModel.tier,
      cost: `$${selectedModel.cost.toFixed(4)}`
    });

    // Step 4: Build prompt
    contextLogger.info('Step 4: Building Claude prompt');
    const prompt = buildClaudePrompt(mode, hour, selectedModel);

    // Step 5: Execute Claude Code CLI with retry
    contextLogger.info('Step 5: Executing Claude Code CLI');
    const { stdout, stderr, duration } = await executeClaudeWithRetry(prompt, configPath, selectedModel);

    // Step 5.5: Parse Claude's JSON output
    contextLogger.info('Step 5.5: Parsing Claude output as JSON');
    const processingResults = parseClaudeOutput(stdout);
    contextLogger.info('Parsed processing results', {
      emailsProcessed: processingResults.todayStats?.totalProcessed || 0,
      escalations: processingResults.tier1Escalations?.length || 0,
      insights: processingResults.insights?.length || 0
    });

    // Step 5.6: Send formatted HTML email report (for morning_brief, eod_report, midday_check modes)
    contextLogger.info('Step 5.6: Sending formatted HTML email report');
    const emailResult = await sendFormattedReport(mode, processingResults, hour);
    if (emailResult) {
      contextLogger.info('HTML email sent', { messageId: emailResult.messageId });
    }

    // Step 6: Send health check (daily at 5 PM)
    if (mode === 'eod_report') {
      await sendHealthCheck('healthy', {
        lastRun: new Date().toISOString(),
        mode,
        success: true,
        durationMs: duration,
        emailSent: !!emailResult
      });
    }

    const totalDuration = Date.now() - startTime;
    contextLogger.info('Email processing completed successfully', {
      totalDurationMs: totalDuration,
      mode,
      hour,
      htmlEmailSent: !!emailResult
    });

    return {
      statusCode: 200,
      body: JSON.stringify({
        success: true,
        mode,
        hour,
        durationMs: totalDuration,
        model: {
          name: selectedModel.displayName,
          tier: selectedModel.tier,
          cost: selectedModel.cost
        },
        processingResults: {
          totalProcessed: processingResults.todayStats?.totalProcessed || 0,
          escalations: processingResults.todayStats?.escalations || 0,
          handled: processingResults.todayStats?.handled || 0,
          drafts: processingResults.todayStats?.drafts || 0
        },
        htmlEmailSent: !!emailResult,
        timestamp: new Date().toISOString()
      })
    };

  } catch (error) {
    const totalDuration = Date.now() - startTime;

    contextLogger.error('Lambda execution failed', {
      error: error.message,
      code: error.code,
      stack: error.stack,
      totalDurationMs: totalDuration
    });

    // Attempt error recovery
    try {
      await handleError(error, {
        lambdaContext: context,
        event: sanitizeForLogging(event)
      });
    } catch (recoveryError) {
      contextLogger.error('Error recovery failed', {
        error: recoveryError.message
      });
    }

    // Send health check failure
    await sendHealthCheck('unhealthy', {
      lastRun: new Date().toISOString(),
      success: false,
      error: error.message,
      durationMs: totalDuration
    });

    return {
      statusCode: 500,
      body: JSON.stringify({
        success: false,
        error: error.message,
        code: error.code,
        timestamp: new Date().toISOString()
      })
    };
  }
};
