/**
 * Email Agent Setup
 * Initialize and configure the autonomous email agent
 */

const logger = require('./logger');
const emailAgent = require('./email-agent');
const config = require('../config/email-agent-config');

// Import tools
const playwrightTool = require('./tools/playwright-tool');
const calendarTool = require('./tools/calendar-tool');
const dataTool = require('./tools/data-tool');

class EmailAgentSetup {
  constructor() {
    this.initialized = false;
    this.monitoringInterval = null;
  }

  /**
   * Initialize the email agent
   */
  async initialize() {
    if (this.initialized) {
      logger.warn('Email agent already initialized');
      return;
    }

    logger.info('Initializing email agent');

    try {
      // Step 1: Configure agent
      emailAgent.agentEmail = config.agentEmail;
      emailAgent.openRouterApiKey = config.openRouter.apiKey;
      emailAgent.reasoningModel = config.openRouter.reasoningModel;
      emailAgent.safetyMode = config.safety.enabled;
      emailAgent.autoApprove = config.safety.autoApprove;

      // Step 2: Register tools
      if (config.tools.playwright.enabled) {
        playwrightTool.register(emailAgent);
        logger.info('Playwright tool enabled');
      }

      if (config.tools.calendar.enabled) {
        calendarTool.register(emailAgent);
        logger.info('Calendar tool enabled');
      }

      if (config.tools.data.enabled) {
        dataTool.register(emailAgent);
        logger.info('Data tool enabled');
      }

      // Step 3: Enable agent
      const result = emailAgent.enable();

      logger.info('Email agent initialized successfully', {
        agentEmail: result.agentEmail,
        tools: result.capabilities.tools
      });

      this.initialized = true;

      return result;

    } catch (error) {
      logger.error('Failed to initialize email agent', {
        error: error.message
      });
      throw error;
    }
  }

  /**
   * Start monitoring for agent emails
   */
  async startMonitoring(gmailClient) {
    if (!this.initialized) {
      throw new Error('Agent not initialized. Call initialize() first.');
    }

    if (this.monitoringInterval) {
      logger.warn('Monitoring already started');
      return;
    }

    logger.info('Starting email agent monitoring', {
      agentEmail: config.agentEmail,
      pollInterval: config.monitoring.pollInterval
    });

    // Monitor for emails
    this.monitoringInterval = setInterval(async () => {
      await this.checkForAgentEmails(gmailClient);
    }, config.monitoring.pollInterval);

    // Run first check immediately
    await this.checkForAgentEmails(gmailClient);
  }

  /**
   * Check for emails to the agent
   */
  async checkForAgentEmails(gmailClient) {
    try {
      logger.debug('Checking for agent emails');

      // Build search query
      const query = [
        `to:${config.agentEmail}`,
        'is:unread'
      ].join(' ');

      // Get unread emails to agent (using Gmail MCP)
      // In production: Use actual Gmail MCP tools
      const emails = []; // Would fetch via Gmail MCP

      if (emails.length === 0) {
        return;
      }

      logger.info('Found agent emails', { count: emails.length });

      // Process each email
      for (const email of emails.slice(0, config.monitoring.maxEmailsPerCycle)) {
        try {
          await this.processAgentEmail(email);

          // Mark as read
          // In production: Mark via Gmail MCP
        } catch (error) {
          logger.error('Failed to process agent email', {
            emailId: email.id,
            error: error.message
          });
        }
      }

    } catch (error) {
      logger.error('Error checking for agent emails', {
        error: error.message
      });
    }
  }

  /**
   * Process a single agent email
   */
  async processAgentEmail(email) {
    logger.info('Processing agent email', {
      from: email.from,
      subject: email.subject
    });

    const result = await emailAgent.processAgentEmail(email);

    if (result.processed) {
      logger.info('Agent email processed successfully', {
        from: email.from,
        actionsPerformed: result.execution?.results?.length || 0
      });

      // Send response email
      if (result.response) {
        await this.sendResponse(result.response);
      }
    } else if (result.requiresApproval) {
      logger.info('Action requires approval', {
        from: email.from
      });

      // Send approval request
      if (result.approvalRequest) {
        await this.sendResponse(result.approvalRequest);
      }
    }
  }

  /**
   * Send response email
   */
  async sendResponse(response) {
    logger.info('Sending agent response', {
      to: response.to,
      subject: response.subject
    });

    // In production: Send via Gmail MCP
    // For now, log the response
    logger.debug('Response body', { body: response.body });
  }

  /**
   * Stop monitoring
   */
  stopMonitoring() {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
      logger.info('Email agent monitoring stopped');
    }
  }

  /**
   * Process a single email manually (for testing)
   */
  async processSingleEmail(email) {
    if (!this.initialized) {
      await this.initialize();
    }

    return await emailAgent.processAgentEmail(email);
  }

  /**
   * Get agent status
   */
  getStatus() {
    return {
      initialized: this.initialized,
      monitoring: !!this.monitoringInterval,
      statistics: emailAgent.getStatistics(),
      config: {
        agentEmail: config.agentEmail,
        reasoningModel: config.openRouter.reasoningModel,
        safetyMode: config.safety.enabled,
        enabledTools: Object.keys(config.tools).filter(t => config.tools[t].enabled)
      }
    };
  }

  /**
   * Get action history
   */
  getActionHistory(limit = 10) {
    return emailAgent.getActionHistory(limit);
  }

  /**
   * Shutdown
   */
  async shutdown() {
    logger.info('Shutting down email agent');

    this.stopMonitoring();

    // Close Playwright browser
    if (config.tools.playwright.enabled) {
      await playwrightTool.close();
    }

    this.initialized = false;
  }
}

module.exports = new EmailAgentSetup();
module.exports.EmailAgentSetup = EmailAgentSetup;
