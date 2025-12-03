/**
 * AWS Lambda Handler with Full Database Integration
 * Version 4.0 - Complete with Approval Queue and State Persistence
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');

// Core modules
const logger = require('../lib/logger');
const { validateEnvironment, validateExecutionMode, sanitizeForLogging } = require('../lib/config-validator');
const { executeWithRetry, RetryConditions } = require('../lib/retry');
const { EmailAssistantError, ErrorCodes, handleError } = require('../lib/error-handler');

// Email Agent modules
const EmailAgentSetup = require('../lib/email-agent-setup');
const EmailPoller = require('../lib/email-poller');

// Database modules
const ApprovalQueueManager = require('../lib/database/approval-queue');
const EmailStateManager = require('../lib/database/email-state');

// Additional modules
const EnhancedEmailDeduplication = require('../lib/enhanced-deduplication');
const threadDetector = require('../lib/thread-detector');
const MonitoringSystem = require('../lib/monitoring-system');
const EmailSummaryGenerator = require('../lib/email-summary-generator');

const writeFile = promisify(fs.writeFile);
const mkdir = promisify(fs.mkdir);

// Initialize components
let contextLogger = logger;
let emailAgent = null;
let poller = null;
let deduplicator = null;
let approvalQueue = null;
let emailState = null;
let monitoring = null;
let summaryGenerator = null;

/**
 * Lambda Handler
 */
exports.handler = async (event, context) => {
  const startTime = Date.now();

  // Initialize context logger
  contextLogger = logger.child({
    requestId: context.requestId,
    functionName: context.functionName,
    functionVersion: context.functionVersion
  });

  contextLogger.info('Lambda execution started', {
    event: sanitizeForLogging(event),
    remainingTimeMs: context.getRemainingTimeInMillis()
  });

  try {
    // Step 1: Validate environment
    validateEnvironment();

    // Step 2: Initialize database connections
    await initializeDatabaseConnections();

    // Step 3: Initialize monitoring
    monitoring = new MonitoringSystem();
    await monitoring.initialize();

    // Step 4: Initialize deduplication
    deduplicator = new EnhancedEmailDeduplication({
      storePath: '/tmp/email-deduplication.json',
      maxAge: 86400000 // 24 hours
    });
    await deduplicator.initialize();

    // Step 5: Initialize summary generator
    summaryGenerator = new EmailSummaryGenerator({
      dashboardUrl: process.env.DASHBOARD_URL || 'https://email-assistant.yourdomain.com',
      companyName: 'Executive Assistant System'
    });

    // Step 6: Determine execution mode
    const mode = event.mode || getExecutionMode();
    validateExecutionMode(mode);

    contextLogger.info('Execution mode determined', { mode });

    // Step 7: Setup credentials
    const { gmailMcpDir, configPath } = await setupGmailCredentials();

    // Step 8: Initialize Email Agent if enabled
    let agentEnabled = false;
    if (process.env.ENABLE_EMAIL_AGENT === 'true') {
      agentEnabled = await initializeEmailAgent();
    }

    // Step 9: Process emails based on mode
    const result = await processEmailsWithDatabase(mode, configPath, agentEnabled);

    // Step 10: Handle approval queue if needed
    if (mode === 'morning_brief' || mode === 'eod_report') {
      await processApprovalQueue(result);
    }

    // Step 11: Send summary email if appropriate
    if (shouldSendSummary(mode, result)) {
      await sendSummaryEmail(mode, result);
    }

    // Step 12: Track metrics
    await monitoring.trackExecution({
      mode,
      emailsProcessed: result.emailsProcessed,
      escalations: result.escalations,
      autoHandled: result.autoHandled,
      draftsCreated: result.draftsCreated,
      duration: Date.now() - startTime,
      costs: result.costs
    });

    // Step 13: Generate response
    const response = {
      statusCode: 200,
      body: JSON.stringify({
        success: true,
        mode,
        processed: result.emailsProcessed || 0,
        agentProcessed: result.agentEmailsProcessed || 0,
        escalations: result.escalations || 0,
        autoHandled: result.autoHandled || 0,
        draftsCreated: result.draftsCreated || 0,
        pendingApprovals: result.pendingApprovals || 0,
        duration: Date.now() - startTime,
        costs: result.costs,
        message: result.message || 'Email processing completed successfully'
      })
    };

    contextLogger.info('Lambda execution completed successfully', {
      duration: Date.now() - startTime,
      response: response.body
    });

    return response;

  } catch (error) {
    const duration = Date.now() - startTime;

    const errorResponse = handleError(error, contextLogger);

    // Track error
    if (monitoring) {
      await monitoring.trackError({
        error: error.message,
        stack: error.stack,
        mode: event.mode || getExecutionMode(),
        duration
      });
    }

    // Check if we should send to DLQ
    if (shouldSendToDLQ(error, event)) {
      await sendToDLQ(event, error);
    }

    return {
      statusCode: errorResponse.statusCode,
      body: JSON.stringify({
        success: false,
        error: errorResponse.message,
        code: errorResponse.code,
        mode: event.mode || getExecutionMode(),
        duration,
        retryable: errorResponse.retryable
      })
    };
  } finally {
    // Cleanup
    await cleanup();
  }
};

/**
 * Initialize database connections
 */
async function initializeDatabaseConnections() {
  contextLogger.info('Initializing database connections');

  // Initialize approval queue
  approvalQueue = new ApprovalQueueManager({
    tableName: process.env.STATE_TABLE || 'email-assistant-state',
    region: process.env.AWS_REGION || 'us-east-1'
  });

  // Initialize email state
  emailState = new EmailStateManager({
    tableName: process.env.STATE_TABLE || 'email-assistant-state',
    region: process.env.AWS_REGION || 'us-east-1'
  });

  contextLogger.info('Database connections initialized');
}

/**
 * Initialize Email Agent
 */
async function initializeEmailAgent() {
  try {
    contextLogger.info('Initializing Email Agent');

    // Create setup instance
    const agentSetup = new EmailAgentSetup();

    // Initialize agent
    const result = await agentSetup.initialize();

    // Store reference
    emailAgent = agentSetup;

    // Initialize poller if agent email is configured
    if (process.env.AGENT_EMAIL && process.env.AGENT_EMAIL !== 'assistant@yourdomain.com') {
      poller = new EmailPoller({
        assistantEmail: process.env.AGENT_EMAIL,
        pollInterval: 60000, // 1 minute
        onEmailReceived: handleAgentEmail,
        onError: (error) => {
          contextLogger.error('Email poller error', { error: error.message });
        }
      });

      await poller.initialize();
      contextLogger.info('Email poller initialized', {
        assistantEmail: process.env.AGENT_EMAIL
      });
    }

    contextLogger.info('Email Agent initialized successfully', {
      tools: result.capabilities.tools,
      agentEmail: result.agentEmail
    });

    return true;
  } catch (error) {
    contextLogger.error('Failed to initialize Email Agent', {
      error: error.message
    });
    return false;
  }
}

/**
 * Handle agent email with database tracking
 */
async function handleAgentEmail(emailData, messageId) {
  try {
    contextLogger.info('Processing agent email', {
      from: emailData.from,
      subject: emailData.subject,
      messageId
    });

    // Check if already processed
    if (await emailState.isProcessed(messageId)) {
      contextLogger.info('Email already processed', { messageId });
      return;
    }

    // Check for duplicate
    if (await deduplicator.isDuplicate(messageId, emailData)) {
      contextLogger.info('Skipping duplicate agent email', { messageId });
      return;
    }

    // Process with agent
    const result = await emailAgent.handleAgentEmail(emailData, messageId);

    // Check if approval needed
    if (result.requiresApproval) {
      await approvalQueue.addToQueue({
        type: 'AGENT_ACTION',
        emailId: messageId,
        subject: emailData.subject,
        from: emailData.from,
        to: emailData.to,
        threadId: emailData.threadId,
        agentRequest: result.understanding,
        agentTools: result.plannedActions,
        confidence: result.confidence,
        reasoning: result.reasoning,
        userEmail: process.env.USER_EMAIL || 'terrance@goodportion.org'
      });

      contextLogger.info('Agent action requires approval', {
        messageId,
        action: result.plannedActions?.[0]?.action
      });
    }

    // Record in database
    await emailState.recordEmailProcessed({
      id: messageId,
      messageId,
      threadId: emailData.threadId,
      subject: emailData.subject,
      from: emailData.from,
      to: emailData.to,
      date: emailData.date,
      snippet: emailData.snippet,
      tier: 'AGENT',
      classification: 'agent_request',
      action: result.overallSuccess ? 'completed' : 'failed',
      confidence: result.confidence,
      agentProcessed: true,
      agentTools: result.executedActions?.map(a => a.tool),
      agentResult: result.response,
      processingTime: result.processingTime,
      userEmail: process.env.USER_EMAIL || 'terrance@goodportion.org'
    });

    // Track costs
    if (result.costs) {
      await monitoring.trackCosts({
        service: 'openrouter',
        model: process.env.REASONING_MODEL || 'deepseek/deepseek-r1',
        inputTokens: result.costs.inputTokens,
        outputTokens: result.costs.outputTokens,
        totalCost: result.costs.total
      });
    }

    // Mark as processed
    await deduplicator.markProcessed(messageId, {
      threadId: emailData.threadId,
      contentHash: deduplicator.generateContentHash(emailData)
    });

    return result;
  } catch (error) {
    contextLogger.error('Failed to handle agent email', {
      messageId,
      error: error.message
    });
    throw error;
  }
}

/**
 * Process emails with database integration
 */
async function processEmailsWithDatabase(mode, configPath, agentEnabled) {
  const startTime = Date.now();

  contextLogger.info('Starting email processing with database', { mode, agentEnabled });

  // Build enhanced prompt with context
  const prompt = await buildEnhancedPrompt(mode);

  // Execute Claude Code
  const claudeResult = await executeClaudeCode(prompt, configPath);

  // Process results and store in database
  const processedEmails = await processEmailResults(claudeResult);

  // Process agent emails if enabled
  let agentResults = null;
  if (agentEnabled && poller) {
    agentResults = await processAgentEmails();
  }

  // Get pending approvals count
  const pendingApprovals = await approvalQueue.getPendingApprovals(
    process.env.USER_EMAIL || 'terrance@goodportion.org',
    100
  );

  // Combine results
  return {
    emailsProcessed: processedEmails.length,
    agentEmailsProcessed: agentResults?.processed || 0,
    escalations: processedEmails.filter(e => e.tier === 'TIER_1').length,
    autoHandled: processedEmails.filter(e => e.tier === 'TIER_2').length,
    draftsCreated: processedEmails.filter(e => e.tier === 'TIER_3').length,
    flagged: processedEmails.filter(e => e.tier === 'TIER_4').length,
    pendingApprovals: pendingApprovals.length,
    processedEmails,
    message: claudeResult.message,
    costs: {
      claude: claudeResult.costs,
      agent: agentResults?.costs
    },
    duration: Date.now() - startTime
  };
}

/**
 * Process email results and store in database
 */
async function processEmailResults(claudeResult) {
  const processedEmails = [];

  if (!claudeResult.emails || !Array.isArray(claudeResult.emails)) {
    return processedEmails;
  }

  for (const email of claudeResult.emails) {
    try {
      // Check if already processed
      if (await emailState.isProcessed(email.id)) {
        contextLogger.debug('Email already in database', { emailId: email.id });
        continue;
      }

      // Record email state
      await emailState.recordEmailProcessed({
        id: email.id,
        messageId: email.messageId,
        threadId: email.threadId,
        subject: email.subject,
        from: email.from,
        to: email.to,
        cc: email.cc,
        date: email.date,
        snippet: email.snippet,
        tier: email.tier,
        classification: email.classification,
        action: email.action,
        confidence: email.confidence,
        labels: email.labels,
        tags: email.tags,
        responseGenerated: email.responseGenerated,
        responseSent: email.responseSent,
        responseContent: email.responseContent,
        processingTime: email.processingTime,
        userEmail: process.env.USER_EMAIL || 'terrance@goodportion.org'
      });

      // Add Tier 3 emails to approval queue
      if (email.tier === 'TIER_3' && email.draftContent) {
        await approvalQueue.addToQueue({
          type: 'EMAIL_DRAFT',
          emailId: email.id,
          subject: email.subject,
          from: email.from,
          to: email.to,
          threadId: email.threadId,
          tier: 'TIER_3',
          action: 'DRAFT_FOR_APPROVAL',
          draftContent: email.draftContent,
          suggestedResponse: email.suggestedResponse,
          confidence: email.confidence,
          reasoning: email.reasoning,
          userEmail: process.env.USER_EMAIL || 'terrance@goodportion.org'
        });
      }

      processedEmails.push(email);
    } catch (error) {
      contextLogger.error('Failed to process email result', {
        emailId: email.id,
        error: error.message
      });
    }
  }

  return processedEmails;
}

/**
 * Process approval queue
 */
async function processApprovalQueue(result) {
  const userEmail = process.env.USER_EMAIL || 'terrance@goodportion.org';

  // Get pending approvals
  const pendingApprovals = await approvalQueue.getPendingApprovals(userEmail, 100);

  if (pendingApprovals.length === 0) {
    contextLogger.info('No pending approvals');
    return;
  }

  contextLogger.info('Processing approval queue', {
    count: pendingApprovals.length
  });

  // Add pending approvals to result for summary
  result.pendingApprovals = pendingApprovals.map(approval => ({
    id: approval.approvalId,
    emailId: approval.emailId,
    subject: approval.subject,
    from: approval.from,
    type: approval.type,
    action: approval.action,
    timestamp: new Date(approval.timestamp).toISOString()
  }));
}

/**
 * Send summary email
 */
async function sendSummaryEmail(mode, result) {
  try {
    contextLogger.info('Generating summary email', { mode });

    // Prepare summary data
    const summaryData = {
      mode,
      date: new Date().toLocaleDateString(),
      time: new Date().toLocaleTimeString('en-US', { timeZone: 'America/New_York' }),
      statistics: {
        total: result.emailsProcessed,
        escalated: result.escalations,
        autoHandled: result.autoHandled,
        draftsCreated: result.draftsCreated,
        flagged: result.flagged || 0,
        agentProcessed: result.agentEmailsProcessed || 0
      },
      emails: result.processedEmails || [],
      pendingApprovals: result.pendingApprovals || [],
      costs: result.costs,
      insights: await monitoring.getInsights()
    };

    // Generate HTML email
    let htmlContent;
    if (mode === 'morning_brief') {
      htmlContent = summaryGenerator.generateMorningBrief(summaryData);
    } else if (mode === 'eod_report') {
      htmlContent = summaryGenerator.generateEODReport(summaryData);
    } else {
      htmlContent = summaryGenerator.generateHourlySummary(summaryData);
    }

    // Send email (implementation depends on your email service)
    // For now, just log that we would send it
    contextLogger.info('Summary email prepared', {
      mode,
      recipientCount: 1,
      htmlLength: htmlContent.length
    });

    // In production, you would send this via SES, SendGrid, etc.
    // await sendEmail({
    //   to: process.env.USER_EMAIL,
    //   subject: `Email Assistant ${mode.replace('_', ' ').toUpperCase()}`,
    //   html: htmlContent
    // });

  } catch (error) {
    contextLogger.error('Failed to send summary email', {
      error: error.message
    });
  }
}

/**
 * Build enhanced prompt with database context
 */
async function buildEnhancedPrompt(mode) {
  const hour = new Date().toLocaleString("en-US", {
    timeZone: "America/New_York"
  });

  // Load agent configuration
  const agentConfigPath = path.join(__dirname, '..', 'claude-agents', 'executive-email-assistant.md');
  const agentConfig = fs.existsSync(agentConfigPath)
    ? fs.readFileSync(agentConfigPath, 'utf-8')
    : '';

  // Get thread context
  const threadContext = await threadDetector.getActiveThreads();

  // Get recent patterns from database
  const learningPatterns = await emailState.getLearningPatterns(50);

  // Get recent escalations for context
  const recentEscalations = await emailState.getEmailsByTier('TIER_1', 10);

  return `You are Terrance Brandon's Executive Email Assistant, running autonomous hourly email management.

CURRENT CONTEXT:
- Execution Mode: ${mode}
- Current Time (EST): ${hour}
- Email Agent: ${process.env.ENABLE_EMAIL_AGENT === 'true' ? 'Enabled' : 'Disabled'}
- Agent Email: ${process.env.AGENT_EMAIL || 'Not configured'}

ACTIVE THREADS:
${threadContext ? JSON.stringify(threadContext, null, 2) : 'None'}

LEARNING PATTERNS:
${learningPatterns ? JSON.stringify(learningPatterns.commonMistakes, null, 2) : 'None'}

RECENT ESCALATIONS:
${recentEscalations.map(e => `- ${e.subject} from ${e.from}`).join('\n')}

YOUR CONFIGURATION:
${agentConfig}

EXECUTION INSTRUCTIONS:
${getInstructionsForMode(mode)}

IMPORTANT REMINDERS:
- Check email state to avoid reprocessing
- Add Tier 3 drafts to approval queue
- Track all decisions in database
- Consider thread context for responses
- Learn from previous classification patterns

Process emails now.`;
}

/**
 * Get execution mode based on current time
 */
function getExecutionMode() {
  const hour = new Date().getHours();

  if (hour === 7) return 'morning_brief';
  if (hour === 13) return 'midday_check';
  if (hour === 17) return 'eod_report';
  return 'hourly_process';
}

/**
 * Get instructions for mode
 */
function getInstructionsForMode(mode) {
  const instructions = {
    'morning_brief': 'Generate morning brief with overnight emails, escalations, and pending approvals',
    'midday_check': 'Quick check for urgent items only, minimal reporting',
    'eod_report': 'Comprehensive end-of-day report with all actions taken and pending items',
    'hourly_process': 'Silent processing, handle emails according to tiers, SMS for Tier 1 only',
    'test': 'Test mode - process but do not send any emails or SMS'
  };

  return instructions[mode] || instructions['hourly_process'];
}

/**
 * Should send summary based on mode and results
 */
function shouldSendSummary(mode, result) {
  if (mode === 'morning_brief' || mode === 'eod_report') {
    return true;
  }

  if (mode === 'midday_check' && result.escalations > 0) {
    return true;
  }

  return false;
}

/**
 * Setup Gmail credentials
 */
async function setupGmailCredentials() {
  const gmailMcpDir = '/tmp/gmail-mcp';
  const configPath = '/tmp/claude_code_config.json';

  await mkdir(gmailMcpDir, { recursive: true });

  // Write credentials
  await writeFile(
    path.join(gmailMcpDir, 'gcp-oauth.keys.json'),
    Buffer.from(process.env.GMAIL_OAUTH_CREDENTIALS, 'base64')
  );

  await writeFile(
    path.join(gmailMcpDir, 'credentials.json'),
    Buffer.from(process.env.GMAIL_CREDENTIALS, 'base64')
  );

  // Write Claude config
  const config = {
    mcpServers: {
      gmail: {
        command: "npx",
        args: ["@gongrzhe/server-gmail-autoauth-mcp"],
        env: {
          GMAIL_MCP_DIR: gmailMcpDir
        }
      }
    }
  };

  await writeFile(configPath, JSON.stringify(config, null, 2));

  return { gmailMcpDir, configPath };
}

/**
 * Execute Claude Code
 */
async function executeClaudeCode(prompt, configPath) {
  return new Promise((resolve, reject) => {
    const claudeProcess = spawn('claude', [
      '--print',
      '--mcp-config', configPath,
      '--dangerously-skip-permissions'
    ], {
      env: {
        ...process.env,
        CLAUDE_CODE_OAUTH_TOKEN: process.env.CLAUDE_CODE_OAUTH_TOKEN
      }
    });

    let output = '';
    let error = '';

    claudeProcess.stdout.on('data', (data) => {
      output += data.toString();
    });

    claudeProcess.stderr.on('data', (data) => {
      error += data.toString();
    });

    claudeProcess.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Claude Code failed: ${error}`));
      } else {
        // Parse output to extract results
        try {
          const result = parseClaudeOutput(output);
          resolve(result);
        } catch (parseError) {
          resolve({
            emailsProcessed: 0,
            message: output,
            emails: []
          });
        }
      }
    });

    // Send prompt
    claudeProcess.stdin.write(prompt);
    claudeProcess.stdin.end();
  });
}

/**
 * Parse Claude output
 */
function parseClaudeOutput(output) {
  // Try to extract structured data from Claude's response
  // This would need to be implemented based on your actual output format
  return {
    emailsProcessed: 0,
    escalations: 0,
    emails: [],
    message: output
  };
}

/**
 * Process agent emails
 */
async function processAgentEmails() {
  if (!poller) return null;

  try {
    // Poll for new emails
    const emails = await poller.poll();

    return {
      processed: emails.length,
      emails
    };
  } catch (error) {
    contextLogger.error('Failed to process agent emails', {
      error: error.message
    });
    return null;
  }
}

/**
 * Should send to DLQ
 */
function shouldSendToDLQ(error, event) {
  // Don't send test mode errors to DLQ
  if (event.testMode) return false;

  // Send critical errors to DLQ
  if (error.code === ErrorCodes.CRITICAL) return true;
  if (error.code === ErrorCodes.CONFIG_INVALID) return true;

  return false;
}

/**
 * Send to DLQ
 */
async function sendToDLQ(event, error) {
  if (!process.env.DLQ_URL) return;

  const AWS = require('aws-sdk');
  const sqs = new AWS.SQS();

  try {
    await sqs.sendMessage({
      QueueUrl: process.env.DLQ_URL,
      MessageBody: JSON.stringify({
        originalEvent: event,
        error: {
          message: error.message,
          stack: error.stack,
          code: error.code
        },
        timestamp: new Date().toISOString()
      })
    }).promise();

    contextLogger.info('Sent error to DLQ');
  } catch (dlqError) {
    contextLogger.error('Failed to send to DLQ', {
      error: dlqError.message
    });
  }
}

/**
 * Cleanup
 */
async function cleanup() {
  try {
    // Stop poller
    if (poller) {
      await poller.stop();
    }

    // Save deduplication state
    if (deduplicator) {
      await deduplicator.save();
    }

    // Export metrics
    if (monitoring) {
      await monitoring.exportMetrics();
    }

    // Clear caches
    if (emailState) {
      emailState.clearCache();
    }

    contextLogger.info('Cleanup completed');
  } catch (error) {
    contextLogger.error('Cleanup failed', {
      error: error.message
    });
  }
}

module.exports = { handler: exports.handler };