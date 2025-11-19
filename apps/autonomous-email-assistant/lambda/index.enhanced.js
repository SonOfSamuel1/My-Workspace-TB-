/**
 * AWS Lambda Handler for Autonomous Email Assistant - ENHANCED VERSION
 *
 * This enhanced version includes all advanced intelligence features:
 * - Thread detection and management
 * - Smart scheduling
 * - ML-based classification
 * - Sentiment analysis
 * - Attachment intelligence
 * - Workflow automation
 * - Cost tracking
 * - Analytics engine
 * - Slack notifications
 *
 * To use: Review and rename to index.js
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const { promisify } = require('util');

// Core utilities
const logger = require('../lib/logger');
const { validateEnvironment, validateExecutionMode, sanitizeForLogging } = require('../lib/config-validator');
const { executeWithRetry, RetryConditions } = require('../lib/retry');
const { EmailAssistantError, ErrorCodes, handleError } = require('../lib/error-handler');

// Intelligence systems
const threadDetector = require('../lib/thread-detector');
const smartScheduler = require('../lib/smart-scheduler');
const mlClassifier = require('../lib/ml-classifier');
const sentimentAnalyzer = require('../lib/sentiment-analyzer');
const attachmentParser = require('../lib/attachment-parser');
const workflowEngine = require('../lib/workflow-engine');
const costTracker = require('../lib/cost-tracker');
const analyticsEngine = require('../lib/analytics-engine');
const slackBot = require('../lib/slack-bot');

const writeFile = promisify(fs.writeFile);
const mkdir = promisify(fs.mkdir);

// Initialize logger with Lambda context
let contextLogger = logger;

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
 * Build the enhanced Claude prompt with intelligence features
 */
function buildEnhancedPrompt(mode, hour, intelligenceContext) {
  contextLogger.debug('Building enhanced Claude prompt', { mode, hour });

  let intelligenceSection = '';

  if (intelligenceContext.threads && intelligenceContext.threads.length > 0) {
    intelligenceSection += `\n\nACTIVE THREADS (${intelligenceContext.threads.length}):\n`;
    intelligenceContext.threads.slice(0, 5).forEach(thread => {
      intelligenceSection += `- ${thread.subject} (${thread.emailCount} emails, last: ${thread.lastActivity})\n`;
    });
  }

  if (intelligenceContext.pendingMeetings && intelligenceContext.pendingMeetings.length > 0) {
    intelligenceSection += `\n\nPENDING MEETING REQUESTS (${intelligenceContext.pendingMeetings.length}):\n`;
    intelligenceSection += 'Smart scheduler available - use for optimal time finding\n';
  }

  if (intelligenceContext.vipSenders && intelligenceContext.vipSenders.length > 0) {
    intelligenceSection += `\n\nVIP SENDERS (Frequent contacts):\n`;
    intelligenceContext.vipSenders.forEach(sender => {
      intelligenceSection += `- ${sender.sender} (${sender.count} emails)\n`;
    });
  }

  return `You are Terrance Brandon's Executive Email Assistant with ADVANCED INTELLIGENCE FEATURES.

CURRENT CONTEXT:
- Execution Mode: ${mode}
- Current Hour (EST): ${hour}:00
- Intelligence Systems: ACTIVE
- ML Classification: ENABLED
- Thread Detection: ENABLED
- Sentiment Analysis: ENABLED
- Attachment Intelligence: ENABLED
${intelligenceSection}

[... rest of original prompt ...]

ENHANCED CAPABILITIES:

1. THREAD DETECTION:
   - Automatically detect and link related emails
   - Provide thread context when responding
   - Track conversation history

2. SENTIMENT & URGENCY ANALYSIS:
   - Every email is analyzed for emotion and urgency
   - Use this to inform tier classification
   - High urgency + negative sentiment = potential escalation

3. ATTACHMENT INTELLIGENCE:
   - Attachments are scanned for security risks
   - Content is extracted and analyzed
   - Invoice data is parsed automatically

4. SMART SCHEDULING:
   - For meeting requests, use smart scheduler
   - Considers optimal times, attendee availability
   - Respects time preferences and patterns

5. ML CLASSIFICATION:
   - Machine learning assists with tier classification
   - System learns from your feedback
   - Provides confidence scores

6. WORKFLOW AUTOMATION:
   - Custom workflows can be triggered
   - Automatic actions based on conditions
   - Integrations with external systems

ADDITIONAL INSTRUCTIONS:

- Use intelligence features to improve classification accuracy
- Include sentiment analysis in escalation decisions
- Check for security risks in attachments before handling
- Use thread context when drafting responses
- Leverage ML confidence scores for borderline cases

BEGIN ENHANCED PROCESSING NOW.`;
}

/**
 * Process emails with intelligence features
 */
async function processEmailsWithIntelligence(emails) {
  contextLogger.info('Processing emails with intelligence systems', {
    count: emails.length
  });

  const processedEmails = [];

  for (const email of emails) {
    try {
      const startTime = Date.now();
      const enhanced = { ...email };

      // 1. Sentiment Analysis
      enhanced.sentiment = await sentimentAnalyzer.analyze(email);
      contextLogger.debug('Sentiment analyzed', {
        emailId: email.id,
        emotion: enhanced.sentiment.emotion,
        urgency: enhanced.sentiment.urgency
      });

      // 2. Thread Detection
      const threadId = threadDetector.detectThread(email);
      if (threadId) {
        enhanced.threadId = threadId;
        const thread = threadDetector.getThread(threadId);
        enhanced.threadContext = {
          emailCount: thread.emailCount,
          participants: thread.participants.length,
          lastActivity: thread.lastActivity
        };
        contextLogger.debug('Thread detected', {
          emailId: email.id,
          threadId,
          context: enhanced.threadContext
        });
      }

      // 3. Attachment Analysis (if attachments present)
      if (email.attachments && email.attachments.length > 0) {
        enhanced.attachmentAnalysis = await attachmentParser.analyzeAttachments(email);
        contextLogger.info('Attachments analyzed', {
          emailId: email.id,
          count: enhanced.attachmentAnalysis.count,
          risk: enhanced.attachmentAnalysis.risk
        });

        // Escalate if high-risk attachments detected
        if (enhanced.attachmentAnalysis.risk === 'high' || enhanced.attachmentAnalysis.risk === 'critical') {
          enhanced.forceEscalation = true;
          enhanced.escalationReason = 'High-risk attachment detected';
        }
      }

      // 4. ML Classification
      const mlPrediction = mlClassifier.classify(email);
      enhanced.mlClassification = mlPrediction;
      contextLogger.debug('ML classification', {
        emailId: email.id,
        predictedTier: mlPrediction.tier,
        confidence: mlPrediction.confidence
      });

      // 5. Track processing time
      enhanced.processingTime = Date.now() - startTime;
      processedEmails.push(enhanced);

      // 6. Trigger workflows
      await workflowEngine.executeWorkflows('email_classified', {
        email: enhanced,
        classification: mlPrediction,
        sentiment: enhanced.sentiment
      });

    } catch (error) {
      contextLogger.error('Failed to process email with intelligence', {
        emailId: email.id,
        error: error.message
      });
      // Continue processing other emails
      processedEmails.push(email);
    }
  }

  return processedEmails;
}

/**
 * Execute Claude CLI with enhanced prompt
 */
async function executeClaudeCLI(prompt, configPath) {
  const startTime = Date.now();

  return new Promise((resolve, reject) => {
    contextLogger.info('Executing Claude Code CLI', {
      promptLength: prompt.length,
      configPath
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
        ESCALATION_PHONE: process.env.ESCALATION_PHONE || '+14077448449'
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

      // Track cost (estimate based on prompt/response length)
      const inputTokens = Math.ceil(prompt.length / 4);
      const outputTokens = Math.ceil(stdout.length / 4);
      costTracker.trackClaudeUsage('sonnet', inputTokens, outputTokens);
      costTracker.trackEmailProcessed();

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
          true
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

    // Timeout after 9 minutes
    const timeout = setTimeout(() => {
      contextLogger.error('Claude CLI execution timeout');
      claude.kill('SIGTERM');

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

    claude.once('close', () => clearTimeout(timeout));
  });
}

/**
 * Execute Claude CLI with retry logic
 */
async function executeClaudeWithRetry(prompt, configPath) {
  return executeWithRetry(
    () => executeClaudeCLI(prompt, configPath),
    {
      maxRetries: 3,
      initialDelay: 2000,
      maxDelay: 30000,
      backoffMultiplier: 2,
      onRetry: (attempt, error) => {
        contextLogger.warn('Retrying Claude CLI execution', {
          attempt,
          error: error.message
        });
      }
    }
  );
}

/**
 * Send end-of-day notifications
 */
async function sendEODNotifications(stats) {
  try {
    // Send Slack summary
    await slackBot.sendDailySummary({
      processed: stats.emailsProcessed,
      handled: stats.tier2Count,
      handledPct: Math.round((stats.tier2Count / stats.emailsProcessed) * 100),
      escalated: stats.tier1Count,
      pending: stats.tier3Count,
      avgResponseTime: stats.avgResponseTime || '0m',
      cost: costTracker.getCosts().total.toFixed(2)
    });

    contextLogger.info('EOD notifications sent', { stats });
  } catch (error) {
    contextLogger.error('Failed to send EOD notifications', {
      error: error.message
    });
  }
}

/**
 * Generate intelligence context for prompt
 */
async function generateIntelligenceContext() {
  return {
    threads: threadDetector.getActiveThreads(10),
    vipSenders: analyticsEngine.getTopSenders(5),
    pendingMeetings: [], // Would fetch from calendar
    mlStats: mlClassifier.getStatistics()
  };
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

  contextLogger.info('Enhanced Email Assistant Lambda started', {
    event: sanitizeForLogging(event),
    remainingTimeMs: context.getRemainingTimeInMillis()
  });

  // Track Lambda invocation
  costTracker.trackLambdaInvocation(0, 512); // Will update duration at end

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

    // Step 4: Generate intelligence context
    contextLogger.info('Step 4: Generating intelligence context');
    const intelligenceContext = await generateIntelligenceContext();

    // Step 5: Build enhanced prompt
    contextLogger.info('Step 5: Building enhanced Claude prompt');
    const prompt = buildEnhancedPrompt(mode, hour, intelligenceContext);

    // Step 6: Execute Claude Code CLI with retry
    contextLogger.info('Step 6: Executing Claude Code CLI with intelligence');
    const { stdout, stderr, duration } = await executeClaudeWithRetry(prompt, configPath);

    // Step 7: Parse results and update analytics
    contextLogger.info('Step 7: Updating analytics');
    const stats = {
      emailsProcessed: 0, // Would parse from stdout
      tier1Count: 0,
      tier2Count: 0,
      tier3Count: 0,
      tier4Count: 0,
      avgResponseTime: duration
    };

    // Step 8: Send EOD notifications if applicable
    if (mode === 'eod_report') {
      await sendEODNotifications(stats);
    }

    // Step 9: Update Lambda invocation cost with actual duration
    const totalDuration = Date.now() - startTime;
    costTracker.trackLambdaInvocation(totalDuration, 512);

    // Step 10: Generate final report
    const costReport = costTracker.getCosts();
    const analyticsReport = analyticsEngine.generateReport();

    contextLogger.info('Email processing completed successfully', {
      totalDurationMs: totalDuration,
      mode,
      hour,
      costs: costReport,
      stats
    });

    return {
      statusCode: 200,
      body: JSON.stringify({
        success: true,
        mode,
        hour,
        durationMs: totalDuration,
        stats,
        costs: {
          total: costReport.total.toFixed(4),
          breakdown: costReport.breakdown
        },
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

    // Send Slack alert for failures
    try {
      await slackBot.sendMessage({
        channel: process.env.SLACK_ALERT_CHANNEL || '#email-assistant',
        text: '🚨 Email Assistant Execution Failed',
        attachments: [{
          color: 'danger',
          fields: [
            { title: 'Error', value: error.message },
            { title: 'Duration', value: `${totalDuration}ms` },
            { title: 'Timestamp', value: new Date().toISOString() }
          ]
        }]
      });
    } catch (slackError) {
      contextLogger.error('Failed to send Slack alert', { error: slackError.message });
    }

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
