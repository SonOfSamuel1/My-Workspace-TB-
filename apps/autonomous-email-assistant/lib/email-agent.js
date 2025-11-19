/**
 * Email Agent System
 * Dedicated email address that can be CC'd or directly emailed
 * Uses OpenRouter reasoning models to understand and execute autonomous actions
 */

const logger = require('./logger');

class EmailAgent {
  constructor(config = {}) {
    this.agentEmail = config.agentEmail || process.env.AGENT_EMAIL || 'assistant@yourdomain.com';
    this.openRouterApiKey = config.openRouterApiKey || process.env.OPENROUTER_API_KEY;
    this.reasoningModel = config.reasoningModel || 'deepseek/deepseek-r1';
    this.enabled = false;
    this.tools = new Map();
    this.actionHistory = [];
    this.safetyMode = config.safetyMode !== false;
    this.autoApprove = config.autoApprove || [];

    // Initialize tools
    this.initializeTools();
  }

  /**
   * Enable the email agent
   */
  enable() {
    if (!this.openRouterApiKey) {
      throw new Error('OpenRouter API key is required');
    }

    this.enabled = true;
    logger.info('Email agent enabled', {
      agentEmail: this.agentEmail,
      model: this.reasoningModel,
      safetyMode: this.safetyMode
    });

    return {
      enabled: true,
      agentEmail: this.agentEmail,
      capabilities: this.getCapabilities()
    };
  }

  /**
   * Process incoming email to the agent
   */
  async processAgentEmail(email) {
    if (!this.enabled) {
      logger.warn('Email agent not enabled, ignoring request');
      return {
        processed: false,
        reason: 'Agent not enabled'
      };
    }

    logger.info('Processing agent email', {
      from: email.from,
      subject: email.subject,
      isCC: this.isCC(email),
      isDirect: this.isDirect(email)
    });

    try {
      // Step 1: Parse and understand the request
      const understanding = await this.understandRequest(email);

      // Step 2: Determine if action is needed
      if (!understanding.requiresAction) {
        return await this.sendInformationalResponse(email, understanding);
      }

      // Step 3: Safety check
      if (this.safetyMode && !this.isAutoApproved(understanding)) {
        return await this.requestApproval(email, understanding);
      }

      // Step 4: Execute action
      const execution = await this.executeAction(understanding);

      // Step 5: Send response
      const response = await this.sendActionResponse(email, understanding, execution);

      // Record action
      this.recordAction({
        email,
        understanding,
        execution,
        response,
        timestamp: new Date()
      });

      return {
        processed: true,
        understanding,
        execution,
        response
      };

    } catch (error) {
      logger.error('Failed to process agent email', {
        error: error.message,
        from: email.from,
        subject: email.subject
      });

      await this.sendErrorResponse(email, error);

      return {
        processed: false,
        error: error.message
      };
    }
  }

  /**
   * Use OpenRouter reasoning model to understand the request
   */
  async understandRequest(email) {
    logger.info('Using reasoning model to understand request', {
      model: this.reasoningModel
    });

    const prompt = this.buildUnderstandingPrompt(email);

    const response = await this.callOpenRouter({
      model: this.reasoningModel,
      messages: [
        {
          role: 'system',
          content: `You are an intelligent email assistant that can understand requests and determine appropriate actions.

Your capabilities:
${this.getCapabilitiesDescription()}

Analyze the email and determine:
1. What the sender wants
2. Whether action is required
3. What action(s) to take
4. What tools are needed
5. Safety considerations

Respond in JSON format.`
        },
        {
          role: 'user',
          content: prompt
        }
      ]
    });

    const understanding = this.parseUnderstanding(response);

    logger.info('Request understood', {
      intent: understanding.intent,
      requiresAction: understanding.requiresAction,
      actions: understanding.actions?.length || 0
    });

    return understanding;
  }

  /**
   * Build prompt for understanding
   */
  buildUnderstandingPrompt(email) {
    const context = [];

    // Basic email info
    context.push(`FROM: ${email.from}`);
    context.push(`TO: ${email.to}`);
    if (email.cc) context.push(`CC: ${email.cc.join(', ')}`);
    context.push(`SUBJECT: ${email.subject}`);
    context.push(`BODY:\n${email.body}`);

    // Thread context if available
    if (email.threadId) {
      context.push(`\nTHREAD CONTEXT: This is part of an ongoing conversation.`);
    }

    // Attachments
    if (email.attachments?.length > 0) {
      context.push(`\nATTACHMENTS: ${email.attachments.map(a => a.filename).join(', ')}`);
    }

    return context.join('\n');
  }

  /**
   * Call OpenRouter API
   */
  async callOpenRouter(payload) {
    const axios = require('axios');

    try {
      const response = await axios.post('https://openrouter.ai/api/v1/chat/completions', payload, {
        headers: {
          'Authorization': `Bearer ${this.openRouterApiKey}`,
          'Content-Type': 'application/json',
          'HTTP-Referer': 'https://github.com/your-repo',
          'X-Title': 'Autonomous Email Assistant'
        }
      });

      return response.data.choices[0].message.content;
    } catch (error) {
      logger.error('OpenRouter API call failed', {
        error: error.message,
        model: payload.model
      });
      throw error;
    }
  }

  /**
   * Parse understanding from reasoning model response
   */
  parseUnderstanding(response) {
    try {
      // Try to parse as JSON
      const parsed = JSON.parse(response);
      return {
        intent: parsed.intent || 'unknown',
        requiresAction: parsed.requiresAction || false,
        actions: parsed.actions || [],
        reasoning: parsed.reasoning || '',
        safetyLevel: parsed.safetyLevel || 'medium',
        confidence: parsed.confidence || 0.5
      };
    } catch (error) {
      // If not JSON, extract key information
      return {
        intent: 'unclear',
        requiresAction: /action|do|execute|run|perform/i.test(response),
        actions: [],
        reasoning: response,
        safetyLevel: 'high',
        confidence: 0.3
      };
    }
  }

  /**
   * Execute the determined action
   */
  async executeAction(understanding) {
    const results = [];

    for (const action of understanding.actions) {
      logger.info('Executing action', {
        type: action.type,
        tool: action.tool
      });

      try {
        const tool = this.tools.get(action.tool);

        if (!tool) {
          throw new Error(`Tool ${action.tool} not found`);
        }

        const result = await tool.execute(action.parameters);

        results.push({
          action: action.type,
          tool: action.tool,
          success: true,
          result
        });

      } catch (error) {
        logger.error('Action execution failed', {
          action: action.type,
          error: error.message
        });

        results.push({
          action: action.type,
          tool: action.tool,
          success: false,
          error: error.message
        });
      }
    }

    return {
      results,
      overallSuccess: results.every(r => r.success),
      summary: this.generateExecutionSummary(results)
    };
  }

  /**
   * Generate execution summary
   */
  generateExecutionSummary(results) {
    const successful = results.filter(r => r.success);
    const failed = results.filter(r => !r.success);

    return {
      total: results.length,
      successful: successful.length,
      failed: failed.length,
      details: results.map(r => ({
        action: r.action,
        success: r.success,
        summary: r.success ? 'Completed' : `Failed: ${r.error}`
      }))
    };
  }

  /**
   * Send action response
   */
  async sendActionResponse(email, understanding, execution) {
    const responseBody = this.formatActionResponse(understanding, execution);

    const response = {
      to: email.from,
      subject: `Re: ${email.subject}`,
      body: responseBody,
      inReplyTo: email.messageId
    };

    logger.info('Sending action response', {
      to: response.to,
      actionsPerformed: execution.results.length
    });

    // In production: Actually send the email via Gmail API
    return response;
  }

  /**
   * Format action response
   */
  formatActionResponse(understanding, execution) {
    let response = `Hi,\n\nI've processed your request.\n\n`;

    response += `**What I understood:**\n${understanding.intent}\n\n`;

    response += `**Actions taken:**\n`;
    for (const result of execution.results) {
      const status = result.success ? '✅' : '❌';
      response += `${status} ${result.action}\n`;

      if (result.success && result.result?.summary) {
        response += `   ${result.result.summary}\n`;
      } else if (!result.success) {
        response += `   Error: ${result.error}\n`;
      }
    }

    if (execution.overallSuccess) {
      response += `\n**Status:** All actions completed successfully.\n`;
    } else {
      response += `\n**Status:** Some actions failed. Please review above.\n`;
    }

    response += `\nBest regards,\nYour Email Assistant`;

    return response;
  }

  /**
   * Send informational response
   */
  async sendInformationalResponse(email, understanding) {
    const responseBody = this.formatInformationalResponse(understanding);

    const response = {
      to: email.from,
      subject: `Re: ${email.subject}`,
      body: responseBody,
      inReplyTo: email.messageId
    };

    logger.info('Sending informational response', { to: response.to });

    return response;
  }

  /**
   * Format informational response
   */
  formatInformationalResponse(understanding) {
    return `Hi,\n\nI've received your email. ${understanding.reasoning}\n\nBest regards,\nYour Email Assistant`;
  }

  /**
   * Request approval for action
   */
  async requestApproval(email, understanding) {
    const approvalRequest = {
      to: email.from,
      subject: `Approval Required: ${email.subject}`,
      body: this.formatApprovalRequest(understanding)
    };

    logger.info('Requesting approval', {
      to: approvalRequest.to,
      actions: understanding.actions.length
    });

    return {
      requiresApproval: true,
      approvalRequest
    };
  }

  /**
   * Format approval request
   */
  formatApprovalRequest(understanding) {
    let body = `Hi,\n\nI need your approval to proceed with the following actions:\n\n`;

    body += `**What I understood:**\n${understanding.intent}\n\n`;

    body += `**Planned actions:**\n`;
    for (const action of understanding.actions) {
      body += `- ${action.type} using ${action.tool}\n`;
    }

    body += `\n**Safety level:** ${understanding.safetyLevel}\n`;

    body += `\nPlease reply with "APPROVE" to proceed or "DENY" to cancel.\n`;

    body += `\nBest regards,\nYour Email Assistant`;

    return body;
  }

  /**
   * Send error response
   */
  async sendErrorResponse(email, error) {
    const response = {
      to: email.from,
      subject: `Re: ${email.subject}`,
      body: `Hi,\n\nI encountered an error processing your request:\n\n${error.message}\n\nPlease try again or contact support if the issue persists.\n\nBest regards,\nYour Email Assistant`
    };

    logger.info('Sending error response', { to: response.to });

    return response;
  }

  /**
   * Check if email is CC'd to agent
   */
  isCC(email) {
    return email.cc?.some(cc =>
      cc.toLowerCase().includes(this.agentEmail.toLowerCase())
    );
  }

  /**
   * Check if email is directly to agent
   */
  isDirect(email) {
    return email.to?.toLowerCase().includes(this.agentEmail.toLowerCase());
  }

  /**
   * Check if action is auto-approved
   */
  isAutoApproved(understanding) {
    return this.autoApprove.some(pattern =>
      understanding.intent.toLowerCase().includes(pattern.toLowerCase())
    );
  }

  /**
   * Initialize available tools
   */
  initializeTools() {
    // Tools will be registered by other modules
    // e.g., playwrightTool.register(this);
  }

  /**
   * Register a tool
   */
  registerTool(name, tool) {
    this.tools.set(name, tool);
    logger.info('Tool registered', { name });
  }

  /**
   * Get capabilities
   */
  getCapabilities() {
    return {
      reasoning: true,
      webAutomation: this.tools.has('playwright'),
      email: true,
      scheduling: this.tools.has('calendar'),
      dataProcessing: this.tools.has('data'),
      tools: Array.from(this.tools.keys())
    };
  }

  /**
   * Get capabilities description
   */
  getCapabilitiesDescription() {
    const descriptions = [];

    if (this.tools.has('playwright')) {
      descriptions.push('- Web automation: Navigate websites, fill forms, click buttons, extract data');
    }

    if (this.tools.has('calendar')) {
      descriptions.push('- Calendar management: Schedule meetings, check availability');
    }

    if (this.tools.has('data')) {
      descriptions.push('- Data processing: Analyze data, generate reports');
    }

    descriptions.push('- Email: Send emails, manage inbox');

    return descriptions.join('\n');
  }

  /**
   * Record action
   */
  recordAction(record) {
    this.actionHistory.push(record);

    // Keep last 100 actions
    if (this.actionHistory.length > 100) {
      this.actionHistory = this.actionHistory.slice(-100);
    }
  }

  /**
   * Get action history
   */
  getActionHistory(limit = 10) {
    return this.actionHistory.slice(-limit);
  }

  /**
   * Get statistics
   */
  getStatistics() {
    const successful = this.actionHistory.filter(a =>
      a.execution?.overallSuccess
    ).length;

    return {
      enabled: this.enabled,
      agentEmail: this.agentEmail,
      totalActions: this.actionHistory.length,
      successfulActions: successful,
      successRate: this.actionHistory.length > 0 ?
        ((successful / this.actionHistory.length) * 100).toFixed(1) + '%' : '0%',
      availableTools: Array.from(this.tools.keys()),
      safetyMode: this.safetyMode
    };
  }
}

module.exports = new EmailAgent();
module.exports.EmailAgent = EmailAgent;
