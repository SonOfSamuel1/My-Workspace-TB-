/**
 * Workflow Engine
 * Visual workflow builder for custom email automation
 */

const logger = require('./logger');
const { v4: uuidv4 } = require('crypto').randomUUID ? require('crypto') : { v4: () => Math.random().toString(36) };

class WorkflowEngine {
  constructor() {
    this.workflows = new Map();
    this.executionHistory = [];
    this.triggers = this.initializeTriggers();
    this.actions = this.initializeActions();
    this.conditions = this.initializeConditions();
  }

  /**
   * Initialize available triggers
   */
  initializeTriggers() {
    return {
      'email_received': {
        name: 'Email Received',
        description: 'Triggers when a new email arrives',
        parameters: ['from', 'subject', 'body', 'tier']
      },
      'email_classified': {
        name: 'Email Classified',
        description: 'Triggers after email classification',
        parameters: ['email', 'classification', 'confidence']
      },
      'draft_created': {
        name: 'Draft Created',
        description: 'Triggers when a draft response is created',
        parameters: ['email', 'draft']
      },
      'escalation': {
        name: 'Escalation',
        description: 'Triggers when an email is escalated',
        parameters: ['email', 'tier', 'reason']
      },
      'schedule': {
        name: 'Schedule',
        description: 'Triggers on a schedule',
        parameters: ['cron', 'timezone']
      },
      'attachment_detected': {
        name: 'Attachment Detected',
        description: 'Triggers when email has attachments',
        parameters: ['email', 'attachments', 'risk']
      },
      'thread_updated': {
        name: 'Thread Updated',
        description: 'Triggers when email thread is updated',
        parameters: ['threadId', 'email', 'history']
      }
    };
  }

  /**
   * Initialize available actions
   */
  initializeActions() {
    return {
      'send_email': {
        name: 'Send Email',
        description: 'Send an email',
        parameters: ['to', 'subject', 'body'],
        execute: async (params) => this.actionSendEmail(params)
      },
      'create_draft': {
        name: 'Create Draft',
        description: 'Create a draft response',
        parameters: ['to', 'subject', 'body'],
        execute: async (params) => this.actionCreateDraft(params)
      },
      'forward_email': {
        name: 'Forward Email',
        description: 'Forward email to another address',
        parameters: ['to', 'email'],
        execute: async (params) => this.actionForwardEmail(params)
      },
      'add_label': {
        name: 'Add Label',
        description: 'Add a label to email',
        parameters: ['email', 'label'],
        execute: async (params) => this.actionAddLabel(params)
      },
      'send_slack': {
        name: 'Send Slack Message',
        description: 'Send notification to Slack',
        parameters: ['channel', 'message'],
        execute: async (params) => this.actionSendSlack(params)
      },
      'create_task': {
        name: 'Create Task',
        description: 'Create a task in task manager',
        parameters: ['title', 'description', 'dueDate'],
        execute: async (params) => this.actionCreateTask(params)
      },
      'schedule_meeting': {
        name: 'Schedule Meeting',
        description: 'Schedule a meeting',
        parameters: ['attendees', 'duration', 'preferences'],
        execute: async (params) => this.actionScheduleMeeting(params)
      },
      'wait': {
        name: 'Wait',
        description: 'Wait for a specified time',
        parameters: ['duration'],
        execute: async (params) => this.actionWait(params)
      },
      'webhook': {
        name: 'Call Webhook',
        description: 'Call external webhook',
        parameters: ['url', 'method', 'body'],
        execute: async (params) => this.actionWebhook(params)
      },
      'ai_analyze': {
        name: 'AI Analysis',
        description: 'Perform AI analysis',
        parameters: ['email', 'prompt'],
        execute: async (params) => this.actionAIAnalyze(params)
      }
    };
  }

  /**
   * Initialize available conditions
   */
  initializeConditions() {
    return {
      'from_contains': (email, value) => (email.from || '').toLowerCase().includes(value.toLowerCase()),
      'subject_contains': (email, value) => (email.subject || '').toLowerCase().includes(value.toLowerCase()),
      'body_contains': (email, value) => (email.body || '').toLowerCase().includes(value.toLowerCase()),
      'tier_equals': (email, value) => email.tier === parseInt(value),
      'has_attachments': (email) => (email.attachments || []).length > 0,
      'attachment_count': (email, operator, value) => this.compare((email.attachments || []).length, operator, parseInt(value)),
      'sentiment_is': (email, value) => email.sentiment?.emotion === value,
      'urgency_is': (email, value) => email.sentiment?.urgency === value,
      'confidence_above': (email, value) => (email.classification?.confidence || 0) > parseFloat(value),
      'is_vip': (email) => this.isVIPSender(email.from),
      'time_of_day': (email, start, end) => this.isTimeInRange(new Date(email.date), start, end),
      'day_of_week': (email, ...days) => {
        const day = new Date(email.date).getDay();
        return days.map(d => parseInt(d)).includes(day);
      }
    };
  }

  /**
   * Create a workflow
   */
  createWorkflow(definition) {
    const workflow = {
      id: definition.id || `wf_${Date.now()}`,
      name: definition.name,
      description: definition.description || '',
      enabled: definition.enabled !== false,
      trigger: definition.trigger,
      conditions: definition.conditions || [],
      actions: definition.actions || [],
      errorHandling: definition.errorHandling || 'stop',
      createdAt: new Date(),
      updatedAt: new Date(),
      executionCount: 0,
      lastExecuted: null
    };

    this.workflows.set(workflow.id, workflow);
    logger.info('Workflow created', { workflowId: workflow.id, name: workflow.name });

    return workflow;
  }

  /**
   * Update workflow
   */
  updateWorkflow(id, updates) {
    const workflow = this.workflows.get(id);
    if (!workflow) {
      throw new Error(`Workflow ${id} not found`);
    }

    Object.assign(workflow, updates, { updatedAt: new Date() });
    logger.info('Workflow updated', { workflowId: id });

    return workflow;
  }

  /**
   * Delete workflow
   */
  deleteWorkflow(id) {
    const deleted = this.workflows.delete(id);
    if (deleted) {
      logger.info('Workflow deleted', { workflowId: id });
    }
    return deleted;
  }

  /**
   * Get workflow
   */
  getWorkflow(id) {
    return this.workflows.get(id);
  }

  /**
   * List all workflows
   */
  listWorkflows() {
    return Array.from(this.workflows.values());
  }

  /**
   * Execute workflows based on trigger
   */
  async executeWorkflows(triggerType, data) {
    const matchingWorkflows = this.findMatchingWorkflows(triggerType);

    logger.info('Executing workflows', {
      trigger: triggerType,
      count: matchingWorkflows.length
    });

    const results = [];

    for (const workflow of matchingWorkflows) {
      try {
        const result = await this.executeWorkflow(workflow, data);
        results.push(result);
      } catch (error) {
        logger.error('Workflow execution failed', {
          workflowId: workflow.id,
          error: error.message
        });
        results.push({
          workflowId: workflow.id,
          success: false,
          error: error.message
        });
      }
    }

    return results;
  }

  /**
   * Execute single workflow
   */
  async executeWorkflow(workflow, data) {
    const executionId = `exec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const startTime = Date.now();

    logger.info('Workflow execution started', {
      executionId,
      workflowId: workflow.id,
      workflow: workflow.name
    });

    const execution = {
      id: executionId,
      workflowId: workflow.id,
      startTime: new Date(),
      status: 'running',
      steps: [],
      data
    };

    try {
      // Check conditions
      const conditionsMet = await this.evaluateConditions(workflow.conditions, data);

      if (!conditionsMet) {
        execution.status = 'skipped';
        execution.reason = 'Conditions not met';
        logger.info('Workflow skipped - conditions not met', { workflowId: workflow.id });
        return execution;
      }

      // Execute actions
      for (let i = 0; i < workflow.actions.length; i++) {
        const actionDef = workflow.actions[i];
        const stepResult = await this.executeAction(actionDef, data);

        execution.steps.push(stepResult);

        if (!stepResult.success && workflow.errorHandling === 'stop') {
          execution.status = 'failed';
          break;
        }

        // Update data with step output for next action
        if (stepResult.output) {
          data = { ...data, ...stepResult.output };
        }
      }

      // Update execution status
      if (execution.status !== 'failed') {
        execution.status = 'completed';
      }

      // Update workflow stats
      workflow.executionCount++;
      workflow.lastExecuted = new Date();

    } catch (error) {
      execution.status = 'error';
      execution.error = error.message;
      logger.error('Workflow execution error', {
        executionId,
        workflowId: workflow.id,
        error: error.message
      });
    }

    execution.endTime = new Date();
    execution.duration = Date.now() - startTime;

    this.executionHistory.push(execution);

    logger.info('Workflow execution completed', {
      executionId,
      workflowId: workflow.id,
      status: execution.status,
      duration: `${execution.duration}ms`
    });

    return execution;
  }

  /**
   * Execute single action
   */
  async executeAction(actionDef, data) {
    const startTime = Date.now();
    const step = {
      action: actionDef.type,
      startTime: new Date(),
      success: false
    };

    try {
      const actionHandler = this.actions[actionDef.type];

      if (!actionHandler) {
        throw new Error(`Unknown action type: ${actionDef.type}`);
      }

      // Resolve parameters with data
      const params = this.resolveParameters(actionDef.parameters, data);

      // Execute action
      const output = await actionHandler.execute(params);

      step.success = true;
      step.output = output;

      logger.debug('Action executed', {
        action: actionDef.type,
        duration: `${Date.now() - startTime}ms`
      });

    } catch (error) {
      step.success = false;
      step.error = error.message;

      logger.error('Action execution failed', {
        action: actionDef.type,
        error: error.message
      });
    }

    step.endTime = new Date();
    step.duration = Date.now() - startTime;

    return step;
  }

  /**
   * Evaluate conditions
   */
  async evaluateConditions(conditions, data) {
    if (!conditions || conditions.length === 0) {
      return true; // No conditions = always match
    }

    for (const condition of conditions) {
      const handler = this.conditions[condition.type];

      if (!handler) {
        logger.warn('Unknown condition type', { type: condition.type });
        continue;
      }

      const result = handler(data, ...condition.values);

      if (!result) {
        return false; // Any condition fails = don't execute
      }
    }

    return true; // All conditions passed
  }

  /**
   * Find workflows matching trigger
   */
  findMatchingWorkflows(triggerType) {
    return Array.from(this.workflows.values()).filter(w =>
      w.enabled && w.trigger.type === triggerType
    );
  }

  /**
   * Resolve parameters with data
   */
  resolveParameters(params, data) {
    const resolved = {};

    for (const [key, value] of Object.entries(params)) {
      if (typeof value === 'string' && value.startsWith('{{') && value.endsWith('}}')) {
        // Template variable like {{email.subject}}
        const path = value.slice(2, -2).trim();
        resolved[key] = this.getNestedValue(data, path);
      } else {
        resolved[key] = value;
      }
    }

    return resolved;
  }

  /**
   * Get nested value from object
   */
  getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) =>
      current?.[key], obj
    );
  }

  /**
   * Compare values
   */
  compare(a, operator, b) {
    switch (operator) {
      case '>': return a > b;
      case '<': return a < b;
      case '>=': return a >= b;
      case '<=': return a <= b;
      case '==': return a == b;
      case '===': return a === b;
      case '!=': return a != b;
      case '!==': return a !== b;
      default: return false;
    }
  }

  /**
   * Check if time is in range
   */
  isTimeInRange(date, startHour, endHour) {
    const hour = date.getHours();
    return hour >= startHour && hour <= endHour;
  }

  /**
   * Check if sender is VIP
   */
  isVIPSender(email) {
    const vips = ['ceo@', 'cto@', 'cfo@', 'board@'];
    return vips.some(vip => email.toLowerCase().includes(vip));
  }

  // ===== ACTION IMPLEMENTATIONS =====

  async actionSendEmail(params) {
    logger.info('Sending email', { to: params.to, subject: params.subject });
    // In production, integrate with Gmail API
    return { sent: true, messageId: `msg_${Date.now()}` };
  }

  async actionCreateDraft(params) {
    logger.info('Creating draft', { to: params.to });
    return { draftId: `draft_${Date.now()}` };
  }

  async actionForwardEmail(params) {
    logger.info('Forwarding email', { to: params.to });
    return { forwarded: true };
  }

  async actionAddLabel(params) {
    logger.info('Adding label', { label: params.label });
    return { labeled: true };
  }

  async actionSendSlack(params) {
    logger.info('Sending Slack message', { channel: params.channel });
    // Integrate with Slack bot
    return { sent: true };
  }

  async actionCreateTask(params) {
    logger.info('Creating task', { title: params.title });
    return { taskId: `task_${Date.now()}` };
  }

  async actionScheduleMeeting(params) {
    logger.info('Scheduling meeting', { attendees: params.attendees });
    // Integrate with smart scheduler
    return { meetingId: `meeting_${Date.now()}` };
  }

  async actionWait(params) {
    const ms = this.parseDuration(params.duration);
    await new Promise(resolve => setTimeout(resolve, ms));
    return { waited: ms };
  }

  async actionWebhook(params) {
    logger.info('Calling webhook', { url: params.url });
    // In production, make HTTP request
    return { called: true };
  }

  async actionAIAnalyze(params) {
    logger.info('AI analysis requested');
    // Integrate with Claude
    return { analysis: 'AI analysis result' };
  }

  /**
   * Parse duration string to milliseconds
   */
  parseDuration(duration) {
    const match = duration.match(/^(\d+)(ms|s|m|h|d)$/);
    if (!match) return 0;

    const value = parseInt(match[1]);
    const unit = match[2];

    const multipliers = {
      ms: 1,
      s: 1000,
      m: 60 * 1000,
      h: 60 * 60 * 1000,
      d: 24 * 60 * 60 * 1000
    };

    return value * multipliers[unit];
  }

  /**
   * Get execution history
   */
  getExecutionHistory(workflowId = null, limit = 50) {
    let history = this.executionHistory;

    if (workflowId) {
      history = history.filter(e => e.workflowId === workflowId);
    }

    return history.slice(-limit);
  }

  /**
   * Get workflow statistics
   */
  getStatistics() {
    const workflows = Array.from(this.workflows.values());

    return {
      totalWorkflows: workflows.length,
      enabledWorkflows: workflows.filter(w => w.enabled).length,
      totalExecutions: workflows.reduce((sum, w) => sum + w.executionCount, 0),
      successRate: this.calculateSuccessRate(),
      avgExecutionTime: this.calculateAvgExecutionTime()
    };
  }

  /**
   * Calculate success rate
   */
  calculateSuccessRate() {
    if (this.executionHistory.length === 0) return 0;

    const successful = this.executionHistory.filter(e =>
      e.status === 'completed'
    ).length;

    return ((successful / this.executionHistory.length) * 100).toFixed(1);
  }

  /**
   * Calculate average execution time
   */
  calculateAvgExecutionTime() {
    if (this.executionHistory.length === 0) return 0;

    const total = this.executionHistory.reduce((sum, e) =>
      sum + (e.duration || 0), 0
    );

    return Math.round(total / this.executionHistory.length);
  }

  /**
   * Export workflows
   */
  exportWorkflows() {
    return {
      workflows: Array.from(this.workflows.values()),
      exportedAt: new Date().toISOString()
    };
  }

  /**
   * Import workflows
   */
  importWorkflows(data) {
    let imported = 0;

    for (const workflow of data.workflows) {
      this.createWorkflow(workflow);
      imported++;
    }

    logger.info('Workflows imported', { count: imported });
    return { imported };
  }
}

module.exports = new WorkflowEngine();
module.exports.WorkflowEngine = WorkflowEngine;
