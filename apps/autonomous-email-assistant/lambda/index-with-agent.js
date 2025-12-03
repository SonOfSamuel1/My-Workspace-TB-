/**
 * AWS Lambda Handler for Autonomous Email Assistant with Email Agent Integration
 * Version 3.0 - Includes Email Agent, Deduplication, and Monitoring
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
const { selectModel, analyzeEmailComplexity } = require('../lib/model-router');

// Email Agent modules
const EmailAgentSetup = require('../lib/email-agent-setup');
const EmailPoller = require('../lib/email-poller');

// Additional modules
const emailDeduplication = require('../lib/email-deduplication');
const threadDetector = require('../lib/thread-detector');
const costTracker = require('../lib/cost-tracker');

const writeFile = promisify(fs.writeFile);
const mkdir = promisify(fs.mkdir);

// Initialize components
let contextLogger = logger;
let emailAgent = null;
let poller = null;
let deduplicator = null;

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

    // Step 2: Determine execution mode
    const mode = event.mode || getExecutionMode();
    validateExecutionMode(mode);

    contextLogger.info('Execution mode determined', { mode });

    // Step 3: Setup credentials
    const { gmailMcpDir, configPath } = await setupGmailCredentials();

    // Step 4: Initialize Email Agent if enabled
    let agentEnabled = false;
    if (process.env.ENABLE_EMAIL_AGENT === 'true') {
      agentEnabled = await initializeEmailAgent();
    }

    // Step 5: Initialize deduplication
    deduplicator = await emailDeduplication.initialize({
      storePath: '/tmp/processed-emails.json',
      maxAge: 86400000 // 24 hours
    });

    // Step 6: Process emails based on mode
    const result = await processEmailsWithMode(mode, configPath, agentEnabled);

    // Step 7: Track costs
    if (result.costs) {
      await costTracker.trackExecution({
        mode,
        costs: result.costs,
        duration: Date.now() - startTime
      });
    }

    // Step 8: Generate response
    const response = {
      statusCode: 200,
      body: JSON.stringify({
        success: true,
        mode,
        processed: result.emailsProcessed || 0,
        agentProcessed: result.agentEmailsProcessed || 0,
        escalations: result.escalations || 0,
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
 * Handle agent email
 */
async function handleAgentEmail(emailData, messageId) {
  try {
    contextLogger.info('Processing agent email', {
      from: emailData.from,
      subject: emailData.subject,
      messageId
    });

    // Check for duplicate
    if (deduplicator && await deduplicator.isDuplicate(messageId)) {
      contextLogger.info('Skipping duplicate agent email', { messageId });
      return;
    }

    // Process with agent
    const result = await emailAgent.handleAgentEmail(emailData, messageId);

    // Track cost
    if (result.costs) {
      await costTracker.trackAgentExecution({
        messageId,
        model: process.env.REASONING_MODEL || 'deepseek/deepseek-r1',
        costs: result.costs
      });
    }

    // Mark as processed
    if (deduplicator) {
      await deduplicator.markProcessed(messageId);
    }

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
 * Process emails based on mode
 */
async function processEmailsWithMode(mode, configPath, agentEnabled) {
  const startTime = Date.now();

  contextLogger.info('Starting email processing', { mode, agentEnabled });

  // Build prompt
  const prompt = await buildEnhancedPrompt(mode);

  // Execute Claude Code
  const claudeResult = await executeClaudeCode(prompt, configPath);

  // Process agent emails if enabled
  let agentResults = null;
  if (agentEnabled && poller) {
    agentResults = await processAgentEmails();
  }

  // Combine results
  return {
    emailsProcessed: claudeResult.emailsProcessed || 0,
    agentEmailsProcessed: agentResults?.processed || 0,
    escalations: claudeResult.escalations || 0,
    message: claudeResult.message,
    costs: {
      claude: claudeResult.costs,
      agent: agentResults?.costs
    },
    duration: Date.now() - startTime
  };
}

/**
 * Build enhanced prompt with context
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

  // Get thread context if available
  const threadContext = await threadDetector.getActiveThreads();

  return `You are Terrance Brandon's Executive Email Assistant, running autonomous hourly email management.

CURRENT CONTEXT:
- Execution Mode: ${mode}
- Current Time (EST): ${hour}
- Email Agent: ${process.env.ENABLE_EMAIL_AGENT === 'true' ? 'Enabled' : 'Disabled'}
- Agent Email: ${process.env.AGENT_EMAIL || 'Not configured'}

ACTIVE THREADS:
${threadContext ? JSON.stringify(threadContext, null, 2) : 'None'}

YOUR CONFIGURATION:
${agentConfig}

EXECUTION INSTRUCTIONS:
${getInstructionsForMode(mode)}

IMPORTANT REMINDERS:
- Check for duplicate emails before processing
- Maintain thread context for conversations
- Track all costs for monitoring
- Use Email Agent for complex requests when enabled
- Follow the 4-tier classification strictly

Begin processing emails now.`;
}

/**
 * Get instructions for execution mode
 */
function getInstructionsForMode(mode) {
  const instructions = {
    'morning_brief': `
1. Generate comprehensive morning brief of overnight emails
2. List all Tier 1 escalations requiring immediate attention
3. Show Tier 3 drafts pending approval
4. Summarize Tier 2 actions taken overnight
5. Include Email Agent activity summary if enabled`,

    'eod_report': `
1. Generate end-of-day summary report
2. List all actions taken today
3. Show pending items for tomorrow
4. Include cost analysis for the day
5. Highlight any unresolved escalations`,

    'midday_check': `
1. Quick scan for Tier 1 urgent items only
2. Send SMS alerts if found
3. Skip report if no urgent items
4. Check Email Agent queue if enabled`,

    'hourly_process': `
1. Process new emails silently
2. Handle Tier 2 items autonomously
3. Draft Tier 3 responses
4. Escalate Tier 1 items via SMS
5. Log all actions taken`
  };

  return instructions[mode] || instructions['hourly_process'];
}

/**
 * Execute Claude Code CLI
 */
async function executeClaudeCode(prompt, configPath) {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();

    const claudeProcess = spawn('claude', [
      '--mcp-config', configPath,
      '--dangerously-skip-permissions',
      '--no-interactive',
      '--max-tokens', '8192',
      '--timeout', '540000', // 9 minutes
      prompt
    ], {
      env: {
        ...process.env,
        HOME: '/tmp',
        CLAUDE_CODE_OAUTH_TOKEN: process.env.CLAUDE_CODE_OAUTH_TOKEN
      },
      cwd: '/tmp'
    });

    let stdout = '';
    let stderr = '';

    claudeProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    claudeProcess.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    claudeProcess.on('close', (code) => {
      const duration = Date.now() - startTime;

      if (code !== 0) {
        contextLogger.error('Claude process failed', {
          code,
          stderr,
          duration
        });
        reject(new Error(`Claude process exited with code ${code}`));
      } else {
        contextLogger.info('Claude process completed', {
          duration,
          outputLength: stdout.length
        });

        // Parse results from output
        const results = parseClaudeOutput(stdout);

        resolve({
          ...results,
          duration,
          costs: calculateClaudeCosts(stdout.length)
        });
      }
    });

    claudeProcess.on('error', (error) => {
      contextLogger.error('Failed to spawn Claude process', {
        error: error.message
      });
      reject(error);
    });
  });
}

/**
 * Process agent emails
 */
async function processAgentEmails() {
  if (!poller) {
    return { processed: 0 };
  }

  try {
    contextLogger.info('Polling for agent emails');

    // Force immediate poll
    await poller.forcePoll();

    // Get statistics
    const stats = poller.getStats();

    contextLogger.info('Agent email poll completed', {
      processed: stats.emailsProcessed,
      found: stats.emailsFound,
      errors: stats.errors
    });

    return {
      processed: stats.emailsProcessed,
      costs: calculateAgentCosts(stats.emailsProcessed)
    };
  } catch (error) {
    contextLogger.error('Failed to process agent emails', {
      error: error.message
    });
    return { processed: 0, error: error.message };
  }
}

/**
 * Parse Claude output
 */
function parseClaudeOutput(output) {
  const results = {
    emailsProcessed: 0,
    escalations: 0,
    message: ''
  };

  // Extract metrics from output
  const processedMatch = output.match(/processed (\d+) email/i);
  if (processedMatch) {
    results.emailsProcessed = parseInt(processedMatch[1]);
  }

  const escalationMatch = output.match(/(\d+) escalation/i);
  if (escalationMatch) {
    results.escalations = parseInt(escalationMatch[1]);
  }

  // Extract summary message
  const summaryMatch = output.match(/SUMMARY: (.+)/);
  if (summaryMatch) {
    results.message = summaryMatch[1];
  }

  return results;
}

/**
 * Calculate Claude costs
 */
function calculateClaudeCosts(outputLength) {
  // Estimate tokens (rough approximation)
  const estimatedTokens = Math.ceil(outputLength / 4);

  // Claude Sonnet pricing (example)
  const costPer1kTokens = 0.003;
  const cost = (estimatedTokens / 1000) * costPer1kTokens;

  return {
    tokens: estimatedTokens,
    cost: cost.toFixed(4)
  };
}

/**
 * Calculate Email Agent costs
 */
function calculateAgentCosts(emailsProcessed) {
  if (!emailsProcessed) return null;

  // DeepSeek R1 pricing
  const model = process.env.REASONING_MODEL || 'deepseek/deepseek-r1';
  const avgTokensPerEmail = 2000; // Estimate

  const pricing = {
    'deepseek/deepseek-r1': { input: 0.00014, output: 0.00028 },
    'openai/o1': { input: 0.015, output: 0.060 },
    'openai/o1-mini': { input: 0.003, output: 0.012 }
  };

  const modelPricing = pricing[model] || pricing['deepseek/deepseek-r1'];
  const totalTokens = emailsProcessed * avgTokensPerEmail;

  const cost = (totalTokens / 1000) * ((modelPricing.input + modelPricing.output) / 2);

  return {
    model,
    emailsProcessed,
    estimatedTokens: totalTokens,
    cost: cost.toFixed(4)
  };
}

/**
 * Check if should send to DLQ
 */
function shouldSendToDLQ(error, event) {
  // Don't DLQ for transient errors
  if (error.retryable) return false;

  // Don't DLQ for test mode
  if (event.testMode) return false;

  // DLQ for persistent failures
  return true;
}

/**
 * Send to Dead Letter Queue
 */
async function sendToDLQ(event, error) {
  if (!process.env.DLQ_URL) {
    contextLogger.warn('DLQ not configured');
    return;
  }

  try {
    const AWS = require('aws-sdk');
    const sqs = new AWS.SQS();

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

    contextLogger.info('Sent to DLQ');
  } catch (dlqError) {
    contextLogger.error('Failed to send to DLQ', {
      error: dlqError.message
    });
  }
}

/**
 * Cleanup resources
 */
async function cleanup() {
  try {
    // Stop email poller
    if (poller && poller.isPolling()) {
      poller.stop();
    }

    // Stop email agent monitoring
    if (emailAgent) {
      emailAgent.stopMonitoring();
    }

    // Save deduplication state
    if (deduplicator) {
      await deduplicator.save();
    }

    // Save cost tracking data
    await costTracker.save();

    contextLogger.info('Cleanup completed');
  } catch (error) {
    contextLogger.error('Cleanup error', {
      error: error.message
    });
  }
}

/**
 * Setup Gmail MCP credentials
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

    // Decode and write credentials
    const gmailOauthCreds = Buffer.from(
      process.env.GMAIL_OAUTH_CREDENTIALS,
      'base64'
    ).toString('utf-8');

    const gmailUserCreds = Buffer.from(
      process.env.GMAIL_CREDENTIALS,
      'base64'
    ).toString('utf-8');

    // Validate JSON
    JSON.parse(gmailOauthCreds);
    JSON.parse(gmailUserCreds);

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
    contextLogger.info('Gmail credentials configured', {
      durationMs: duration
    });

    return {
      gmailMcpDir,
      configPath: path.join(configDir, 'claude_code_config.json')
    };
  } catch (error) {
    contextLogger.error('Failed to setup Gmail credentials', {
      error: error.message
    });
    throw error;
  }
}

/**
 * Get execution mode based on time
 */
function getExecutionMode() {
  const estDate = new Date().toLocaleString("en-US", {
    timeZone: "America/New_York"
  });
  const hour = new Date(estDate).getHours();

  if (hour === 7) return 'morning_brief';
  if (hour === 17) return 'eod_report';
  if (hour === 13) return 'midday_check';
  return 'hourly_process';
}